"""The single validated trade-execution path (PLAN.md §9 step 6).

Both `POST /api/portfolio/trade` and the future LLM chat flow call
`execute_trade` — there is exactly one code path that validates and applies a
trade, regardless of where it originated.
"""

from __future__ import annotations

import math
from typing import Literal

from ..db import positions, trades, users
from ..db.portfolio_snapshots import insert_snapshot

DEFAULT_USER_ID = "default"

# Tolerance for float rounding noise in the buy-side cash check and the
# sell-side shares check — e.g. quantity * price landing on
# 10000.000000000002 for a trade that should exactly exhaust a $10,000
# balance must not be spuriously rejected.
_EPSILON = 1e-6


class TradeError(Exception):
    """Raised when a requested trade fails validation. `.reason` is a
    human-readable string suitable for returning to the caller (REST 400
    body, or an LLM chat action's error annotation)."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


async def get_portfolio_state(app_state, user_id: str = DEFAULT_USER_ID) -> dict:
    """Current positions, cash balance, total value, unrealized P&L
    (PLAN.md §8 GET /api/portfolio)."""
    cash_balance = await users.get_cash_balance(user_id)
    raw_positions = await positions.get_positions(user_id)

    position_views = []
    total_positions_value = 0.0
    for pos in raw_positions:
        tick = await app_state.price_cache.get(pos["ticker"])
        current_price = tick.price if tick is not None else pos["avg_cost"]
        market_value = pos["quantity"] * current_price
        cost_basis = pos["quantity"] * pos["avg_cost"]
        unrealized_pnl = market_value - cost_basis
        unrealized_pnl_pct = (unrealized_pnl / cost_basis) if cost_basis else 0.0
        total_positions_value += market_value
        position_views.append(
            {
                "ticker": pos["ticker"],
                "quantity": pos["quantity"],
                "avg_cost": pos["avg_cost"],
                "current_price": current_price,
                "unrealized_pnl": unrealized_pnl,
                "unrealized_pnl_pct": unrealized_pnl_pct,
            }
        )

    return {
        "cash_balance": cash_balance,
        "positions": position_views,
        "total_value": cash_balance + total_positions_value,
    }


async def execute_trade(
    app_state,
    ticker: str,
    side: Literal["buy", "sell"],
    quantity: float,
    user_id: str = DEFAULT_USER_ID,
) -> dict:
    """Validates and applies a market order. Raises `TradeError` (with a
    human-readable `.reason`) on any validation failure; otherwise applies
    the fill, updates cash, logs the trade, records a portfolio snapshot, and
    returns a dict describing the fill."""
    ticker = ticker.strip().upper()
    if not math.isfinite(quantity) or quantity <= 0:
        raise TradeError("quantity must be positive")

    tick = await app_state.price_cache.get(ticker)
    if tick is None:
        raise TradeError(f"no price available for {ticker}")
    price = tick.price

    if side == "buy":
        cash_balance = await users.get_cash_balance(user_id)
        cost = quantity * price
        if cost > cash_balance + _EPSILON:
            raise TradeError("insufficient cash")
        new_cash_balance = cash_balance - cost
    elif side == "sell":
        position = await positions.get_position(user_id, ticker)
        if position is None or position["quantity"] < quantity - _EPSILON:
            raise TradeError("insufficient shares")
        # A request within epsilon of the owned quantity (e.g. "sell it all"
        # computed client-side) but a hair over it due to float noise must
        # not leave a dust-sized negative position behind.
        quantity = min(quantity, position["quantity"])
        cash_balance = await users.get_cash_balance(user_id)
        new_cash_balance = cash_balance + quantity * price
    else:
        raise TradeError(f"unknown side {side!r}")

    await positions.apply_fill(user_id, ticker, side, quantity, price)
    await users.set_cash_balance(user_id, new_cash_balance)
    trade = await trades.insert_trade(user_id, ticker, side, quantity, price)

    portfolio_state = await get_portfolio_state(app_state, user_id)
    await insert_snapshot(user_id, portfolio_state["total_value"])

    return {
        "ticker": ticker,
        "side": side,
        "quantity": quantity,
        "price": price,
        "executed_at": trade["executed_at"],
    }
