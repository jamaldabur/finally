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

from ..db import portfolio_snapshots, positions, trades, users_profile
from ..db.positions import Position
from ..db.trades import Trade
from ..db.watchlist import DEFAULT_USER_ID
from ..market.base import MarketDataSource
from ..market.cache import PriceCache

QUANTITY_EPSILON = 1e-9


@dataclass(frozen=True)
class PositionView:
    ticker: str
    quantity: float
    avg_cost: float
    current_price: float | None
    market_value: float
    unrealized_pnl: float
    pct_change: float


@dataclass(frozen=True)
class PortfolioView:
    cash_balance: float
    positions: list[PositionView]
    positions_value: float
    total_value: float
    total_unrealized_pnl: float


async def compute_portfolio_view(
    *, price_cache: PriceCache, user_id: str = DEFAULT_USER_ID
) -> PortfolioView:
    """Pure read: cash + positions joined with the live PriceCache, with
    unrealized P&L and % change computed fresh on every call. Nothing here
    is ever persisted to a column — PLAN.md §7's `positions` schema has no
    P&L field, and a stored value would go stale the instant the price
    ticks (01-RESEARCH.md Anti-Patterns).

    Deliberately does NOT acquire the portfolio lock — it's a read-only
    join, and execute_trade() calls it from inside its own already-held
    asyncio.Lock (a non-reentrant lock), so taking it here would deadlock.
    """
    cash_balance = await users_profile.get_cash_balance(user_id)
    held_positions = await positions.get_all_positions(user_id)

    position_views: list[PositionView] = []
    for position in held_positions:
        tick = await price_cache.get(position.ticker)
        if tick is None:
            # Locked mark-to-cost fallback: reachable by buying a ticker and
            # then removing it from the watchlist, since run_update_loop
            # only prices watched tickers. Stays in positions_value at cost
            # rather than silently dropping out of total_value.
            position_views.append(
                PositionView(
                    ticker=position.ticker,
                    quantity=position.quantity,
                    avg_cost=position.avg_cost,
                    current_price=None,
                    market_value=round(position.quantity * position.avg_cost, 2),
                    unrealized_pnl=0.0,
                    pct_change=0.0,
                )
            )
            continue

        current_price = tick.price
        # Rounded to cent/basis-point precision here (not on every read
        # downstream), matching the "round once" convention already
        # documented in app/market/simulator.py — division-based pct_change
        # in particular is not exactly representable in binary float (e.g.
        # 120.0/100.0 - 1) * 100 == 19.999999999999996, not 20.0) and would
        # otherwise leak that imprecision straight into the API response.
        market_value = round(position.quantity * current_price, 2)
        unrealized_pnl = round(
            (current_price - position.avg_cost) * position.quantity, 2
        )
        pct_change = (
            round((current_price / position.avg_cost - 1) * 100, 2)
            if position.avg_cost
            else 0.0
        )
        position_views.append(
            PositionView(
                ticker=position.ticker,
                quantity=position.quantity,
                avg_cost=position.avg_cost,
                current_price=current_price,
                market_value=market_value,
                unrealized_pnl=unrealized_pnl,
                pct_change=pct_change,
            )
        )

    positions_value = round(sum(view.market_value for view in position_views), 2)
    total_unrealized_pnl = round(
        sum(view.unrealized_pnl for view in position_views), 2
    )

    return PortfolioView(
        cash_balance=cash_balance,
        positions=position_views,
        positions_value=positions_value,
        total_value=round(cash_balance + positions_value, 2),
        total_unrealized_pnl=total_unrealized_pnl,
    )


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
            result = await _apply_buy(
                ticker=ticker,
                quantity=quantity,
                price=tick.price,
                cash=cash,
                existing=existing,
                user_id=user_id,
            )
        else:
            result = await _apply_sell(
                ticker=ticker,
                quantity=quantity,
                price=tick.price,
                cash=cash,
                existing=existing,
                user_id=user_id,
            )

        # DATA-04: an immediate snapshot on every successful trade, still
        # inside this lock so the recorded total_value reflects exactly the
        # state this trade just committed, with no interleaved trade able to
        # change it first. compute_portfolio_view() deliberately takes no
        # lock, so this nested call cannot deadlock. No rejection branch
        # reaches this line — both _apply_buy and _apply_sell return before
        # any write on their error paths.
        if result.status == "executed":
            view = await compute_portfolio_view(price_cache=price_cache, user_id=user_id)
            await portfolio_snapshots.insert_snapshot(view.total_value)

        return result


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


async def _apply_sell(
    *,
    ticker: str,
    quantity: float,
    price: float,
    cash: float,
    existing: Position | None,
    user_id: str,
) -> TradeResult:
    held = existing.quantity if existing is not None else 0
    if existing is None or quantity > existing.quantity + QUANTITY_EPSILON:
        return TradeResult(
            status="error",
            reason=(
                f"Insufficient shares: {ticker} sell of {quantity} exceeds held {held}"
            ),
            trade=None,
            cash_balance=None,
            position=None,
        )

    new_quantity = existing.quantity - quantity
    if abs(new_quantity) < QUANTITY_EPSILON:
        await positions.delete_position(ticker, user_id)
        new_position = None
    else:
        # avg_cost is left unchanged by a sell — average-cost accounting
        # realizes P&L against the existing average, it never re-bases it
        # (01-RESEARCH.md "Average-cost accounting (sell)").
        await positions.upsert_position(ticker, new_quantity, existing.avg_cost, user_id)
        new_position = Position(ticker=ticker, quantity=new_quantity, avg_cost=existing.avg_cost)

    new_cash_balance = cash + price * quantity
    await users_profile.set_cash_balance(new_cash_balance, user_id)
    trade = await trades.insert_trade(ticker, "sell", quantity, price, user_id)

    return TradeResult(
        status="executed",
        reason=None,
        trade=trade,
        cash_balance=new_cash_balance,
        position=new_position,
    )
