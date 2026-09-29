"""Background task recording portfolio value history (PLAN.md §7
"portfolio_snapshots" — "Recorded every 30 seconds by a background task").

Structured exactly like app/market/loop.py::run_update_loop — an unbounded
while True whose body is wrapped in a broad try/except that logs and keeps
going. This task is the sole writer of the 30-second cadence of the history
series (execute_trade() writes the immediate, on-trade datapoints
separately); an unhandled exception here would silently end that series for
the process's lifetime.
"""

import asyncio
import logging

from ..db import portfolio_snapshots
from ..market.cache import PriceCache
from .service import compute_portfolio_view

logger = logging.getLogger(__name__)

SNAPSHOT_INTERVAL_SECONDS = 30


async def run_portfolio_snapshot_loop(
    price_cache: PriceCache, interval_seconds: float = SNAPSHOT_INTERVAL_SECONDS
) -> None:
    """One background task per running app. Records first, then sleeps — so
    the very first datapoint lands at startup and the P&L chart has an
    origin point."""
    while True:
        try:
            view = await compute_portfolio_view(price_cache=price_cache)
            await portfolio_snapshots.insert_snapshot(view.total_value)
        except Exception:
            logger.exception("portfolio snapshot loop iteration failed")
        await asyncio.sleep(interval_seconds)
