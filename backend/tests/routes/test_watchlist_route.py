"""Route-level tests for /api/watchlist*. See test_portfolio.py for why
routes are called directly rather than through a live TestClient."""

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.db import watchlist
from app.market.base import ChangeDirection, PriceTick
from app.routes.watchlist import (
    WatchlistRequest,
    delete_watchlist,
    get_watchlist,
    post_watchlist,
)


class _FakeCache:
    def __init__(self, prices: dict[str, float]):
        self._prices = prices

    async def get(self, ticker: str):
        if ticker not in self._prices:
            return None
        price = self._prices[ticker]
        return PriceTick(ticker, price, price, None, ChangeDirection.UNCHANGED)


class _FakeMarketSource:
    def __init__(self, valid_tickers: set[str]):
        self._valid = valid_tickers

    async def is_valid_ticker(self, ticker: str) -> bool:
        return ticker in self._valid


def _request(prices: dict[str, float] | None = None, valid_tickers: set[str] | None = None):
    state = SimpleNamespace(
        price_cache=_FakeCache(prices or {}),
        market_source=_FakeMarketSource(valid_tickers or set()),
    )
    return SimpleNamespace(app=SimpleNamespace(state=state))


@pytest.fixture(autouse=True)
async def seeded_db():
    await watchlist.init_db()


async def test_get_watchlist_joins_tickers_with_prices():
    await watchlist.remove_ticker("default", "AAPL")
    await watchlist.add_ticker("default", "ONLYTICKER")
    for t in await watchlist.get_watchlist_tickers("default"):
        if t != "ONLYTICKER":
            await watchlist.remove_ticker("default", t)
    request = _request(prices={"ONLYTICKER": 42.0})

    result = await get_watchlist(request)

    assert result == [
        {
            "ticker": "ONLYTICKER",
            "price": 42.0,
            "previous_price": 42.0,
            "direction": "unchanged",
        }
    ]


async def test_get_watchlist_returns_nulls_when_no_price_cached():
    for t in await watchlist.get_watchlist_tickers("default"):
        await watchlist.remove_ticker("default", t)
    await watchlist.add_ticker("default", "NEWTICK")
    request = _request()

    result = await get_watchlist(request)

    assert result == [
        {"ticker": "NEWTICK", "price": None, "previous_price": None, "direction": None}
    ]


async def test_post_watchlist_adds_valid_ticker():
    request = _request(valid_tickers={"PYPL"})

    result = await post_watchlist(request, WatchlistRequest(ticker="pypl"))

    assert result == {"ticker": "PYPL"}
    assert "PYPL" in await watchlist.get_watchlist_tickers("default")


async def test_post_watchlist_returns_400_on_unrecognized_ticker():
    request = _request(valid_tickers=set())

    with pytest.raises(HTTPException) as exc_info:
        await post_watchlist(request, WatchlistRequest(ticker="ZZZZ"))

    assert exc_info.value.status_code == 400


async def test_delete_watchlist_removes_existing_ticker():
    request = _request()

    result = await delete_watchlist(request, "AAPL")

    assert result == {"ticker": "AAPL"}
    assert "AAPL" not in await watchlist.get_watchlist_tickers("default")


async def test_delete_watchlist_returns_404_on_missing_ticker():
    request = _request()

    with pytest.raises(HTTPException) as exc_info:
        await delete_watchlist(request, "ZZZZ")

    assert exc_info.value.status_code == 404
