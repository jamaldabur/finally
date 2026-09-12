"""Shared, in-memory price cache.

Written to by `run_update_loop` (the sole writer, regardless of which
`MarketDataSource` is active); read by the SSE endpoint and by trade
fill-price lookups. It — not either market data source — computes
`previous_price` and `direction`, because that comparison is about what the
frontend has already seen, not something either backend knows natively.
"""

import asyncio
from datetime import datetime, timezone

from .base import ChangeDirection, PriceTick


class PriceCache:
    """Guarded by a lock since multiple SSE connections and the update loop
    can all await it concurrently."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._latest: dict[str, PriceTick] = {}

    async def update(self, ticker: str, price: float) -> PriceTick:
        """Record a new observed price. If it equals the last known price,
        the emitted tick keeps the OLD previous_price/direction rather than
        collapsing to UNCHANGED-vs-itself — this is what lets the frontend's
        `price !== previous_price` flash check ignore no-op heartbeats while
        still reflecting the last real move."""
        async with self._lock:
            prior = self._latest.get(ticker)
            now = datetime.now(timezone.utc)
            if prior is None:
                tick = PriceTick(ticker, price, price, now, ChangeDirection.UNCHANGED)
            elif price == prior.price:
                tick = PriceTick(ticker, price, prior.previous_price, now, prior.direction)
            else:
                direction = ChangeDirection.UP if price > prior.price else ChangeDirection.DOWN
                tick = PriceTick(ticker, price, prior.price, now, direction)
            self._latest[ticker] = tick
            return tick

    async def snapshot(self) -> list[PriceTick]:
        """All tickers currently tracked, for one SSE broadcast tick."""
        async with self._lock:
            return list(self._latest.values())

    async def get(self, ticker: str) -> PriceTick | None:
        """Single-ticker lookup — used by trade fill-price resolution."""
        async with self._lock:
            return self._latest.get(ticker)
