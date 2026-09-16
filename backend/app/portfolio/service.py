"""Trade validation and execution — the single path reused by the trade bar
route (this plan), Plan 02's sell branch, and Phase 3's chat flow
(01-RESEARCH.md Pattern 3, 01-PATTERNS.md).

execute_trade() returns a structured TradeResult and never raises an
HTTP-layer exception — this module knows nothing about HTTP.
app/routes/portfolio.py is the only layer permitted to translate a
TradeResult into an HTTP response.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Literal

from ..db import positions, trades, users_profile
from ..db.positions import Position
from ..db.trades import Trade
from ..db.watchlist import DEFAULT_USER_ID
from ..market.base import MarketDataSource
from ..market.cache import PriceCache

QUANTITY_EPSILON = 1e-9


@dataclass(frozen=True)
class TradeResult:
    status: Literal["executed", "error"]
    reason: str | None
    trade: Trade | None
    cash_balance: float | None
    position: Position | None


async def execute_trade(
    *,
    price_cache: PriceCache,
    market_source: MarketDataSource,
    lock: asyncio.Lock,
    ticker: str,
    side: str,
    quantity: float,
    user_id: str = DEFAULT_USER_ID,
) -> TradeResult:
    """Validate-and-apply a market order. Never re-fetches the price
    directly from the market source — PriceCache is the sole fill-price
    authority, since it's the same cache the SSE stream reads (the price
    the user's screen is showing)."""
    ticker = ticker.strip().upper()

    if not await market_source.is_valid_ticker(ticker):
        return TradeResult(
            status="error",
            reason=f"Unknown ticker: {ticker}",
            trade=None,
            cash_balance=None,
            position=None,
        )

    tick = await price_cache.get(ticker)
    if tick is None:
        return TradeResult(
            status="error",
            reason=(
                f"No live price available for {ticker} — add it to your "
                "watchlist first."
            ),
            trade=None,
            cash_balance=None,
            position=None,
        )

    async with lock:
        cash = await users_profile.get_cash_balance(user_id)
        existing = await positions.get_position(ticker, user_id)

        if side == "buy":
            return await _apply_buy(
                ticker=ticker,
                quantity=quantity,
                price=tick.price,
                cash=cash,
                existing=existing,
                user_id=user_id,
            )

        # Plan 02 adds a sibling _apply_sell(...) here — the tracer proves
        # the buy path only and must not fake the sell path.
        raise NotImplementedError("Sell execution is Plan 02's responsibility.")


async def _apply_buy(
    *,
    ticker: str,
    quantity: float,
    price: float,
    cash: float,
    existing: Position | None,
    user_id: str,
) -> TradeResult:
    cost = price * quantity
    if cost > cash + QUANTITY_EPSILON:
        return TradeResult(
            status="error",
            reason=(
                f"Insufficient cash: {ticker} x{quantity} at {price:.2f} "
                f"costs {cost:.2f}, available {cash:.2f}"
            ),
            trade=None,
            cash_balance=None,
            position=None,
        )

    if existing is None:
        new_quantity = quantity
        new_avg_cost = price
    else:
        new_quantity = existing.quantity + quantity
        new_avg_cost = (
            existing.avg_cost * existing.quantity + price * quantity
        ) / new_quantity

    await positions.upsert_position(ticker, new_quantity, new_avg_cost, user_id)
    new_cash_balance = cash - cost
    await users_profile.set_cash_balance(new_cash_balance, user_id)
    trade = await trades.insert_trade(ticker, "buy", quantity, price, user_id)

    return TradeResult(
        status="executed",
        reason=None,
        trade=trade,
        cash_balance=new_cash_balance,
        position=Position(ticker=ticker, quantity=new_quantity, avg_cost=new_avg_cost),
    )
