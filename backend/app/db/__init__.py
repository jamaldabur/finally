"""Database layer entry point.

`init_db()` is the single call app/main.py's lifespan makes at startup: it
creates every PLAN.md §7 table (idempotent `CREATE TABLE IF NOT EXISTS`) and
seeds default data (the "default" user profile and the 10 default watchlist
tickers) across all app/db/* modules in one place, so callers don't need to
know how many tables exist or in what order they're created.
"""

from __future__ import annotations

from . import chat_messages, portfolio_snapshots, positions, trades, users, watchlist


async def init_db() -> None:
    await users.init_db()
    await watchlist.init_db()
    await positions.init_db()
    await trades.init_db()
    await portfolio_snapshots.init_db()
    await chat_messages.init_db()
