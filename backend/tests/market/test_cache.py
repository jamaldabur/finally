import pytest

from app.market.base import ChangeDirection
from app.market.cache import PriceCache


@pytest.mark.asyncio
async def test_first_update_is_unchanged_with_previous_equal_to_price():
    cache = PriceCache()
    tick = await cache.update("AAPL", 190.00)
    assert tick.ticker == "AAPL"
    assert tick.price == 190.00
    assert tick.previous_price == 190.00
    assert tick.direction == ChangeDirection.UNCHANGED


@pytest.mark.asyncio
async def test_price_increase_reports_up_direction():
    cache = PriceCache()
    await cache.update("AAPL", 190.00)
    tick = await cache.update("AAPL", 190.42)
    assert tick.price == 190.42
    assert tick.previous_price == 190.00
    assert tick.direction == ChangeDirection.UP


@pytest.mark.asyncio
async def test_price_decrease_reports_down_direction():
    cache = PriceCache()
    await cache.update("AAPL", 190.00)
    tick = await cache.update("AAPL", 189.50)
    assert tick.price == 189.50
    assert tick.previous_price == 190.00
    assert tick.direction == ChangeDirection.DOWN


@pytest.mark.asyncio
async def test_previous_price_carries_forward_on_heartbeat():
    """The subtle behavior PLAN.md §6 requires: `previous_price` reflects
    the last *different* price, not simply the prior event, so repeated
    heartbeats of an unchanged price don't re-trigger the frontend flash."""
    cache = PriceCache()
    await cache.update("AAPL", 190.00)
    tick2 = await cache.update("AAPL", 190.42)
    assert tick2.previous_price == 190.00
    assert tick2.direction == ChangeDirection.UP

    tick3 = await cache.update("AAPL", 190.42)  # heartbeat, no real change
    assert tick3.previous_price == 190.00  # carried forward, not 190.42
    assert tick3.direction == ChangeDirection.UP  # carried forward too

    tick4 = await cache.update("AAPL", 190.42)  # another heartbeat
    assert tick4.previous_price == 190.00
    assert tick4.direction == ChangeDirection.UP


@pytest.mark.asyncio
async def test_multiple_heartbeats_then_a_real_move():
    cache = PriceCache()
    await cache.update("AAPL", 190.00)
    await cache.update("AAPL", 190.42)
    await cache.update("AAPL", 190.42)
    tick = await cache.update("AAPL", 191.00)
    assert tick.previous_price == 190.42
    assert tick.direction == ChangeDirection.UP


@pytest.mark.asyncio
async def test_snapshot_returns_all_tracked_tickers():
    cache = PriceCache()
    await cache.update("AAPL", 190.00)
    await cache.update("GOOGL", 175.00)
    ticks = await cache.snapshot()
    tickers = {t.ticker for t in ticks}
    assert tickers == {"AAPL", "GOOGL"}


@pytest.mark.asyncio
async def test_snapshot_on_empty_cache_is_empty_list():
    cache = PriceCache()
    assert await cache.snapshot() == []


@pytest.mark.asyncio
async def test_get_returns_none_for_untracked_ticker():
    cache = PriceCache()
    assert await cache.get("ZZZZ") is None


@pytest.mark.asyncio
async def test_get_returns_latest_tick_for_ticker():
    cache = PriceCache()
    await cache.update("AAPL", 190.00)
    await cache.update("AAPL", 191.00)
    tick = await cache.get("AAPL")
    assert tick is not None
    assert tick.price == 191.00


@pytest.mark.asyncio
async def test_independent_tickers_do_not_affect_each_other():
    cache = PriceCache()
    await cache.update("AAPL", 190.00)
    await cache.update("GOOGL", 175.00)
    await cache.update("AAPL", 191.00)
    googl_tick = await cache.get("GOOGL")
    assert googl_tick.price == 175.00
    assert googl_tick.direction == ChangeDirection.UNCHANGED
