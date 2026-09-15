import pytest

from app import db as db_module
from app.db import chat_messages, portfolio_snapshots, positions, trades, users, watchlist
from app.market.simulator import DEFAULT_WATCHLIST


@pytest.mark.asyncio
async def test_init_db_creates_and_seeds_everything():
    await db_module.init_db()

    assert await users.get_cash_balance() == 10000.0
    assert set(await watchlist.get_watchlist_tickers()) == set(DEFAULT_WATCHLIST)
    assert await positions.get_positions() == []
    assert await portfolio_snapshots.get_snapshots() == []
    assert await chat_messages.get_recent_messages() == []
    # trades has no read-all helper (append-only log); insert must not raise
    # against a table that init_db() already created.
    await trades.insert_trade("default", "AAPL", "buy", 1, 190.0)


@pytest.mark.asyncio
async def test_init_db_is_idempotent():
    await db_module.init_db()
    await db_module.init_db()

    tickers = await watchlist.get_watchlist_tickers()
    assert len(tickers) == len(DEFAULT_WATCHLIST)
    assert await users.get_cash_balance() == 10000.0
