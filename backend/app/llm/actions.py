"""Validate-then-execute-then-annotate loop for LLM-proposed trades and
watchlist changes (PLAN.md §9 "How It Works" step 6-7).

This module applies exactly one validated path for each kind of action: a
trade is applied only by calling `app/portfolio/service.py::execute_trade()`
— the same function `POST /api/portfolio/trade` calls — and a watchlist
change is applied only by calling `add_watchlist_ticker()` /
`remove_watchlist_ticker()` — the same functions `POST` / `DELETE
/api/watchlist` call. There is no second, chat-only code path that mutates
cash balance, positions, trades, or the watchlist table (T-03-02). This
module must never import or call the cash-balance, position-upsert, or
trade-insert persistence helpers directly — the only portfolio write it can
cause is the one inside `execute_trade()`.

Two independent validation layers guard `execute_trade()` against a
hallucinated item (T-03-01): `_validate_trade_item()` here rejects a bad
item *before* `execute_trade()` is even called, and `execute_trade()` itself
(Task 3) carries the same guard for every other caller. Belt and suspenders,
not a duplicate of one layer standing in for the other.

Each item is normalized exactly once, by `_normalize_trade_item()` /
`_normalize_watchlist_item()`, and validation, execution and annotation all
read that one result thereafter (G-03-6). Before this, the validators
normalized with a strip and a case fold while the executor separately
re-derived the same fields with only a case fold — so a value that passed
validation was not always the value that got executed. Confirmed live: an
action of `" add"` with a leading space passed validation as `"add"`, then
failed an equality check in the executor, fell into the `else` branch, and
called the REMOVE function — a watched ticker was deleted and the user was
shown a green "executed" badge. Any future field added to `LlmTradeItem` or
`LlmWatchlistChange` must follow the same single-normalization rule: derive
it once, and have every downstream reader use that one derived value.
"""

from __future__ import annotations

import asyncio
import math
from dataclasses import dataclass
from typing import Literal

from ..db.watchlist import add_watchlist_ticker, remove_watchlist_ticker
from ..market.base import MarketDataSource
from ..market.cache import PriceCache
from ..portfolio.service import execute_trade
from .schema import ChatResponseSchema, LlmTradeItem, LlmWatchlistChange


@dataclass(frozen=True)
class AnnotatedTrade:
    ticker: str
    side: str
    quantity: float
    price: float | None
    outcome: Literal["executed", "error"]
    reason: str | None


@dataclass(frozen=True)
class AnnotatedWatchlistChange:
    ticker: str
    action: str
    outcome: Literal["executed", "error"]
    reason: str | None


@dataclass(frozen=True)
class ExecutedActions:
    trades: list[AnnotatedTrade]
    watchlist_changes: list[AnnotatedWatchlistChange]


def _normalize_trade_item(item: LlmTradeItem) -> tuple[str, str, float]:
    """Normalizes one `LlmTradeItem` exactly once. Returns a tuple of
    `(ticker, side, quantity)` in that order — this is the single
    normalized result that `_validate_trade_item()`, `execute_trade()` and
    the annotation built afterward all read, so a value admitted by
    validation can never be swapped for a different one at execution
    (G-03-6). `ticker` is trimmed and upper-cased; `side` is trimmed and
    lower-cased — the same normalization the validator used to perform on
    its own copy, now done in exactly one place.

    Sell-only sign recovery (G-03-5): when the normalized `side` is
    `"sell"`, and `quantity` is a real, finite number strictly less than
    zero, the returned quantity is its absolute magnitude — recovering a
    backing model's redundant signed-quantity encoding of "sell 2" as
    `(side="sell", quantity=-2)`, confirmed live against the free
    auto-router. This is conditioned on `side` and applied nowhere else: a
    *buy* with a negative quantity is genuinely ambiguous, because a model
    using a pure signed-quantity convention may have meant a sell, and this
    project auto-executes trades with no confirmation dialog (PLAN.md §9)
    — silently flipping a negative buy to positive could execute a real
    trade in the opposite direction from what was intended. It is
    deliberately left untouched here and stays rejected by
    `_validate_trade_item()`. The finiteness check also keeps NaN and
    infinity out of the recovery branch (both fall through untouched and
    are rejected downstream), and negative zero is not strictly less than
    zero, so it too falls through untouched and is rejected downstream as
    a non-positive quantity — both are intended, not oversights.
    """
    ticker = item.ticker.strip().upper()
    side = item.side.strip().lower()
    quantity = item.quantity
    if (
        side == "sell"
        and isinstance(quantity, (int, float))
        and math.isfinite(quantity)
        and quantity < 0
    ):
        quantity = abs(quantity)
    return ticker, side, quantity


def _normalize_watchlist_item(item: LlmWatchlistChange) -> tuple[str, str]:
    """Normalizes one `LlmWatchlistChange` exactly once. Returns a tuple of
    `(ticker, action)` in that order — the single normalized result that
    `_validate_watchlist_item()` and the add/remove dispatch both read
    thereafter. `ticker` is trimmed and upper-cased; `action` is trimmed
    and lower-cased."""
    return item.ticker.strip().upper(), item.action.strip().lower()


def _validate_trade_item(*, ticker: str, side: str, quantity: float) -> str | None:
    """Mirrors exactly what TradeRequest enforces at the HTTP layer
    (app/routes/portfolio.py): non-empty ticker, side in {buy, sell}, and a
    finite quantity strictly greater than zero. Takes the already-normalized
    values from `_normalize_trade_item()` — never the raw model item — so
    the value checked here is provably the same value the caller goes on to
    execute."""
    if not ticker:
        return "Invalid ticker: empty"
    if side not in ("buy", "sell"):
        return f"Invalid side: {side!r}"
    if not isinstance(quantity, (int, float)) or not math.isfinite(quantity):
        return f"Invalid quantity: {quantity!r}"
    if quantity <= 0:
        return f"Invalid quantity: {quantity!r}"
    return None


def _validate_watchlist_item(*, ticker: str, action: str) -> str | None:
    """Takes the already-normalized values from `_normalize_watchlist_item()`
    — never the raw model item — so the value checked here is provably the
    same value the caller goes on to dispatch on."""
    if not ticker:
        return "Invalid ticker: empty"
    if action not in ("add", "remove"):
        return f"Invalid action: {action!r}"
    return None


async def execute_llm_actions(
    *,
    price_cache: PriceCache,
    market_source: MarketDataSource,
    lock: asyncio.Lock,
    response: ChatResponseSchema,
) -> ExecutedActions:
    """Iterates `response.trades` then `response.watchlist_changes`, each in
    source order. Two identical items produce two independent annotations —
    duplicates are never collapsed (CHAT-04 adjacency edge)."""
    annotated_trades: list[AnnotatedTrade] = []
    for item in response.trades:
        ticker, side, quantity = _normalize_trade_item(item)
        reason = _validate_trade_item(ticker=ticker, side=side, quantity=quantity)
        if reason is not None:
            annotated_trades.append(
                AnnotatedTrade(
                    ticker=ticker,
                    side=side,
                    quantity=quantity,
                    price=None,
                    outcome="error",
                    reason=reason,
                )
            )
            continue

        result = await execute_trade(
            price_cache=price_cache,
            market_source=market_source,
            lock=lock,
            ticker=ticker,
            side=side,
            quantity=quantity,
        )
        annotated_trades.append(
            AnnotatedTrade(
                ticker=ticker,
                side=side,
                quantity=quantity,
                price=result.trade.price if result.status == "executed" and result.trade else None,
                outcome=result.status,
                reason=result.reason,
            )
        )

    annotated_watchlist_changes: list[AnnotatedWatchlistChange] = []
    for change in response.watchlist_changes:
        ticker, action = _normalize_watchlist_item(change)
        reason = _validate_watchlist_item(ticker=ticker, action=action)
        if reason is not None:
            annotated_watchlist_changes.append(
                AnnotatedWatchlistChange(
                    ticker=ticker,
                    action=action,
                    outcome="error",
                    reason=reason,
                )
            )
            continue

        if not await market_source.is_valid_ticker(ticker):
            annotated_watchlist_changes.append(
                AnnotatedWatchlistChange(
                    ticker=ticker,
                    action=action,
                    outcome="error",
                    reason=f"Unknown ticker: {ticker}",
                )
            )
            continue

        # Dispatch by naming both valid actions explicitly, with a
        # non-raising error branch for anything else (T-03-36). This branch
        # is unreachable while validation is intact — _validate_watchlist_item()
        # above already restricts `action` to {"add", "remove"} — and it is
        # deliberately here anyway: validation is exactly what failed in
        # G-03-6, and the destructive remove call must never be something a
        # value can reach by falling off the end of a conditional.
        if action == "add":
            changed = await add_watchlist_ticker(ticker)
        elif action == "remove":
            changed = await remove_watchlist_ticker(ticker)
        else:
            annotated_watchlist_changes.append(
                AnnotatedWatchlistChange(
                    ticker=ticker,
                    action=action,
                    outcome="error",
                    reason=f"Invalid action: {action!r}",
                )
            )
            continue

        annotated_watchlist_changes.append(
            AnnotatedWatchlistChange(
                ticker=ticker,
                action=action,
                outcome="executed" if changed else "error",
                reason=None if changed else (
                    f"{ticker} is already on the watchlist" if action == "add"
                    else f"{ticker} is not on the watchlist"
                ),
            )
        )

    return ExecutedActions(
        trades=annotated_trades, watchlist_changes=annotated_watchlist_changes
    )
