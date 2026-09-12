import httpx
import pytest
import respx

from app.market.base import MarketDataSource
from app.market.massive import MassiveMarketDataSource
from app.market.simulator import SimulatorMarketDataSource


@pytest.fixture(params=["simulator", "massive"])
async def source(request):
    if request.param == "simulator":
        src = SimulatorMarketDataSource(seed=42)
        await src.start()
        yield src
        await src.stop()
    else:
        with respx.mock:
            respx.get(url__regex=r".*/v2/snapshot/.*").mock(
                return_value=httpx.Response(
                    200, json={"tickers": [{"ticker": "AAPL", "lastTrade": {"p": 190.42}}]}
                )
            )
            src = MassiveMarketDataSource(api_key="test-key")
            await src.start()
            yield src
            await src.stop()


def test_both_implementations_are_market_data_sources(source):
    assert isinstance(source, MarketDataSource)


@pytest.mark.asyncio
async def test_get_prices_omits_unknown_tickers(source):
    prices = await source.get_prices(["AAPL", "ZZZZ_NOT_REAL"])
    assert "AAPL" in prices
    assert "ZZZZ_NOT_REAL" not in prices


@pytest.mark.asyncio
async def test_get_prices_returns_a_plain_float_per_ticker(source):
    prices = await source.get_prices(["AAPL"])
    assert isinstance(prices["AAPL"], float)


@pytest.mark.asyncio
async def test_is_valid_ticker_true_for_aapl(source):
    assert await source.is_valid_ticker("AAPL") is True
