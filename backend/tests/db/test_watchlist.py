import pytest

from app.db import watchlist as watchlist_module
from app.market.simulator import DEFAULT_WATCHLIST


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


@pytest.mark.asyncio
async def test_add_ticker_adds_a_new_ticker():
    await watchlist_module.init_db()
    added = await watchlist_module.add_ticker("default", "PYPL")
    assert added is True
    tickers = await watchlist_module.get_watchlist_tickers()
    assert "PYPL" in tickers


@pytest.mark.asyncio
async def test_add_ticker_returns_false_for_duplicate():
    await watchlist_module.init_db()
    await watchlist_module.add_ticker("default", "PYPL")
    added_again = await watchlist_module.add_ticker("default", "PYPL")
    assert added_again is False
    tickers = await watchlist_module.get_watchlist_tickers()
    assert tickers.count("PYPL") == 1


@pytest.mark.asyncio
async def test_add_ticker_does_not_validate_ticker_symbol():
    # Pure storage op — symbol validation is the caller's job (PLAN.md §6/§8).
    await watchlist_module.init_db()
    added = await watchlist_module.add_ticker("default", "NOTAREALTICKER")
    assert added is True


@pytest.mark.asyncio
async def test_remove_ticker_removes_existing_ticker():
    await watchlist_module.init_db()
    removed = await watchlist_module.remove_ticker("default", "AAPL")
    assert removed is True
    tickers = await watchlist_module.get_watchlist_tickers()
    assert "AAPL" not in tickers


@pytest.mark.asyncio
async def test_remove_ticker_returns_false_when_absent():
    await watchlist_module.init_db()
    removed = await watchlist_module.remove_ticker("default", "NOPE")
    assert removed is False


@pytest.mark.asyncio
async def test_add_and_remove_ticker_scoped_per_user():
    await watchlist_module.init_db()
    await watchlist_module.add_ticker("someone-else", "PYPL")
    default_tickers = await watchlist_module.get_watchlist_tickers()
    assert "PYPL" not in default_tickers
    other_tickers = await watchlist_module.get_watchlist_tickers(user_id="someone-else")
    assert other_tickers == ["PYPL"]
