import asyncio

import pytest

from app.market.base import MarketDataSource
from app.market.cache import PriceCache
from app.market.loop import run_update_loop


class StubSource(MarketDataSource):
    """A minimal in-memory MarketDataSource stand-in for exercising the
    update loop's orchestration without depending on the simulator or a
    mocked HTTP client."""

    def __init__(self, prices: dict[str, float] | None = None, raise_on_get: bool = False):
        self.prices = prices or {}
        self.raise_on_get = raise_on_get
        self.calls = 0

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    async def get_prices(self, tickers: list[str]) -> dict[str, float]:
        self.calls += 1
        if self.raise_on_get:
            raise RuntimeError("boom")
        return {t: self.prices[t] for t in tickers if t in self.prices}

    async def is_valid_ticker(self, ticker: str) -> bool:
        return ticker in self.prices


async def _run_briefly(coro_task: asyncio.Task, seconds: float = 0.05) -> None:
    await asyncio.sleep(seconds)
    coro_task.cancel()
    try:
        await coro_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_loop_writes_fetched_prices_into_cache():
    source = StubSource(prices={"AAPL": 190.00})
    cache = PriceCache()

    async def get_watchlist():
        return ["AAPL"]

    task = asyncio.create_task(run_update_loop(source, cache, get_watchlist, 0.01))
    await _run_briefly(task)

    tick = await cache.get("AAPL")
    assert tick is not None
    assert tick.price == 190.00
    assert source.calls >= 1


@pytest.mark.asyncio
async def test_loop_skips_get_prices_when_watchlist_is_empty():
    source = StubSource(prices={"AAPL": 190.00})
    cache = PriceCache()

    async def get_watchlist():
        return []

    task = asyncio.create_task(run_update_loop(source, cache, get_watchlist, 0.01))
    await _run_briefly(task)

    assert source.calls == 0
    assert await cache.snapshot() == []


@pytest.mark.asyncio
async def test_loop_survives_source_raising_and_keeps_running():
    source = StubSource(prices={"AAPL": 190.00}, raise_on_get=True)
    cache = PriceCache()

    async def get_watchlist():
        return ["AAPL"]

    task = asyncio.create_task(run_update_loop(source, cache, get_watchlist, 0.01))
    await _run_briefly(task)

    # The loop must not have crashed (call count kept incrementing despite
    # the exception) and the cache must remain empty (never written to).
    assert source.calls >= 1
    assert await cache.snapshot() == []


@pytest.mark.asyncio
async def test_loop_survives_get_watchlist_tickers_raising():
    source = StubSource(prices={"AAPL": 190.00})
    cache = PriceCache()

    async def get_watchlist():
        raise RuntimeError("db unavailable")

    task = asyncio.create_task(run_update_loop(source, cache, get_watchlist, 0.01))
    await _run_briefly(task)

    assert source.calls == 0
    assert await cache.snapshot() == []
