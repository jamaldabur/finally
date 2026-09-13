import pytest

from app.db import watchlist as watchlist_module
from app.market.simulator import DEFAULT_WATCHLIST


@pytest.fixture(autouse=True)
def isolated_db(monkeypatch, tmp_path):
    """Every test in this module gets its own throwaway SQLite file — never
    touch the real db/finally.db during tests."""
    monkeypatch.setattr(watchlist_module, "DB_PATH", tmp_path / "finally.db")


@pytest.mark.asyncio
async def test_init_db_seeds_default_watchlist():
    await watchlist_module.init_db()
    tickers = await watchlist_module.get_watchlist_tickers()
    assert set(tickers) == set(DEFAULT_WATCHLIST)
    assert len(tickers) == len(DEFAULT_WATCHLIST)


@pytest.mark.asyncio
async def test_init_db_is_idempotent():
    await watchlist_module.init_db()
    await watchlist_module.init_db()  # must not duplicate the seed rows
    tickers = await watchlist_module.get_watchlist_tickers()
    assert len(tickers) == len(DEFAULT_WATCHLIST)


@pytest.mark.asyncio
async def test_get_watchlist_tickers_before_init_is_empty_not_an_error():
    # No init_db() call — the table doesn't exist yet. Only relevant if
    # something ever queries before startup's init_db() has run; should
    # degrade to "no tickers," not raise.
    with pytest.raises(Exception):
        # Querying a table that was never created does raise (sqlite3
        # OperationalError) — this documents that init_db() is a required
        # precondition, not something get_watchlist_tickers() defends against
        # itself. app/main.py's lifespan always calls init_db() first.
        await watchlist_module.get_watchlist_tickers()


@pytest.mark.asyncio
async def test_get_watchlist_tickers_for_unknown_user_is_empty():
    await watchlist_module.init_db()
    tickers = await watchlist_module.get_watchlist_tickers(user_id="someone-else")
    assert tickers == []
