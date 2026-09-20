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


def _validate_trade_item(item: LlmTradeItem) -> str | None:
    """Mirrors exactly what TradeRequest enforces at the HTTP layer
    (app/routes/portfolio.py): non-empty ticker, side in {buy, sell}, and a
    finite quantity strictly greater than zero."""
    if not item.ticker.strip():
        return "Invalid ticker: empty"
    if item.side not in ("buy", "sell"):
        return f"Invalid side: {item.side!r}"
    if not isinstance(item.quantity, (int, float)) or not math.isfinite(item.quantity):
        return f"Invalid quantity: {item.quantity!r}"
    if item.quantity <= 0:
        return f"Invalid quantity: {item.quantity!r}"
    return None


def _validate_watchlist_item(item: LlmWatchlistChange) -> str | None:
    if not item.ticker.strip():
        return "Invalid ticker: empty"
    if item.action not in ("add", "remove"):
        return f"Invalid action: {item.action!r}"
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
        reason = _validate_trade_item(item)
        if reason is not None:
            annotated_trades.append(
                AnnotatedTrade(
                    ticker=item.ticker,
                    side=item.side,
                    quantity=item.quantity,
                    price=None,
                    outcome="error",
                    reason=reason,
                )
            )
            continue

        ticker = item.ticker.strip().upper()
        side = item.side.lower()
        result = await execute_trade(
            price_cache=price_cache,
            market_source=market_source,
            lock=lock,
            ticker=ticker,
            side=side,
            quantity=item.quantity,
        )
        annotated_trades.append(
            AnnotatedTrade(
                ticker=ticker,
                side=side,
                quantity=item.quantity,
                price=result.trade.price if result.status == "executed" and result.trade else None,
                outcome=result.status,
                reason=result.reason,
            )
        )

    annotated_watchlist_changes: list[AnnotatedWatchlistChange] = []
    for change in response.watchlist_changes:
        reason = _validate_watchlist_item(change)
        if reason is not None:
            annotated_watchlist_changes.append(
                AnnotatedWatchlistChange(
                    ticker=change.ticker,
                    action=change.action,
                    outcome="error",
                    reason=reason,
                )
            )
            continue

        ticker = change.ticker.strip().upper()
        action = change.action.lower()

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

        if action == "add":
            changed = await add_watchlist_ticker(ticker)
        else:
            changed = await remove_watchlist_ticker(ticker)

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
