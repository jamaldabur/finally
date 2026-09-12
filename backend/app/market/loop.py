"""Background task driving a MarketDataSource's polling/tick cadence into
the shared PriceCache. One instance runs per running app (see PLAN.md §6)."""

import asyncio
import logging
from typing import Awaitable, Callable

from .base import MarketDataSource
from .cache import PriceCache

logger = logging.getLogger(__name__)

SIMULATOR_TICK_SECONDS = 0.5  # matches PLAN.md §6 "~500ms"
MASSIVE_POLL_SECONDS = 15  # matches PLAN.md §6 free-tier cadence


async def run_update_loop(
    source: MarketDataSource,
    cache: PriceCache,
    get_watchlist_tickers: Callable[[], Awaitable[list[str]]],
    interval_seconds: float,
) -> None:
    """One background task per running app. Wrapped in try/except so that
    even an implementation bug that somehow raises out of get_prices (rather
    than returning {} per its contract) can't kill the loop — this is the
    sole writer to `cache`, so if it dies, the SSE stream silently goes
    stale forever. Defense in depth on top of each source's own error
    handling."""
    while True:
        try:
            tickers = await get_watchlist_tickers()
            if tickers:
                prices = await source.get_prices(tickers)
                for ticker, price in prices.items():
                    await cache.update(ticker, price)
        except Exception:
            logger.exception("market data update loop iteration failed")
        await asyncio.sleep(interval_seconds)
