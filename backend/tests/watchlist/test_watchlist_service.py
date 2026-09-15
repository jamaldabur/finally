"""Unit tests for app/watchlist/service.py."""

from types import SimpleNamespace

import pytest

from app.db import watchlist
from app.watchlist.service import (
    WatchlistError,
    add_watchlist_ticker,
    remove_watchlist_ticker,
)


class _FakeMarketSource:
    def __init__(self, valid_tickers: set[str]):
        self._valid = valid_tickers

    async def is_valid_ticker(self, ticker: str) -> bool:
        return ticker in self._valid


def _app_state(valid_tickers: set[str]):
    return SimpleNamespace(market_source=_FakeMarketSource(valid_tickers))


@pytest.fixture(autouse=True)
async def seeded_db():
    await watchlist.init_db()


async def test_add_valid_ticker_normalizes_and_stores():
    state = _app_state({"PYPL"})

    await add_watchlist_ticker(state, "pypl", user_id="default")

    tickers = await watchlist.get_watchlist_tickers("default")
    assert "PYPL" in tickers


async def test_add_unrecognized_ticker_raises():
    state = _app_state(set())

    with pytest.raises(WatchlistError, match="unrecognized ticker"):
        await add_watchlist_ticker(state, "ZZZZ", user_id="default")


async def test_add_duplicate_ticker_raises():
    state = _app_state({"PYPL"})
    await add_watchlist_ticker(state, "PYPL", user_id="default")

    with pytest.raises(WatchlistError, match="already on watchlist"):
        await add_watchlist_ticker(state, "PYPL", user_id="default")


async def test_remove_existing_ticker_succeeds():
    state = _app_state({"PYPL"})
    await add_watchlist_ticker(state, "PYPL", user_id="default")

    await remove_watchlist_ticker(state, "PYPL", user_id="default")

    tickers = await watchlist.get_watchlist_tickers("default")
    assert "PYPL" not in tickers


async def test_remove_missing_ticker_raises():
    state = _app_state(set())

    with pytest.raises(WatchlistError, match="not on watchlist"):
        await remove_watchlist_ticker(state, "ZZZZ", user_id="default")
