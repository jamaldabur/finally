"""SQLite-backed watchlist storage.

Lazily initializes its own table and seeds PLAN.md §7's 10 default tickers
on first use — no separate migration step (PLAN.md §7 "Lazy Initialization").
This is the one piece of persistence the market data layer depends on:
`run_update_loop` (app/market/loop.py) needs to know which tickers to
poll/tick for on every cycle.

`add_ticker`/`remove_ticker` are pure storage operations — they don't
validate that a ticker is a recognized symbol (PLAN.md §6/§8); that's the
caller's job (the watchlist route, validating against
`MarketDataSource.is_valid_ticker`).
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

from . import connection
from ..market.simulator import DEFAULT_WATCHLIST

DEFAULT_USER_ID = "default"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS watchlist (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL DEFAULT 'default',
    ticker TEXT NOT NULL,
    added_at TEXT NOT NULL,
    UNIQUE(user_id, ticker)
);
"""


def _init_db_sync() -> None:
    with connection.connect() as conn:
        conn.execute(_SCHEMA)
        (count,) = conn.execute(
            "SELECT COUNT(*) FROM watchlist WHERE user_id = ?", (DEFAULT_USER_ID,)
        ).fetchone()
        if count == 0:
            now = datetime.now(timezone.utc).isoformat()
            conn.executemany(
                "INSERT INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
                [(str(uuid.uuid4()), DEFAULT_USER_ID, ticker, now) for ticker in DEFAULT_WATCHLIST],
            )


def _get_watchlist_tickers_sync(user_id: str) -> list[str]:
    with connection.connect() as conn:
        rows = conn.execute(
            "SELECT ticker FROM watchlist WHERE user_id = ?", (user_id,)
        ).fetchall()
    return [row[0] for row in rows]


def _add_ticker_sync(user_id: str, ticker: str) -> bool:
    with connection.connect() as conn:
        cursor = conn.execute(
            "INSERT OR IGNORE INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
            (str(uuid.uuid4()), user_id, ticker, datetime.now(timezone.utc).isoformat()),
        )
        return cursor.rowcount > 0


def _remove_ticker_sync(user_id: str, ticker: str) -> bool:
    with connection.connect() as conn:
        cursor = conn.execute(
            "DELETE FROM watchlist WHERE user_id = ? AND ticker = ?", (user_id, ticker)
        )
        return cursor.rowcount > 0


async def init_db() -> None:
    """Called once at app startup (see app/main.py's lifespan). Creates the
    watchlist table if missing and seeds the default tickers if empty —
    idempotent, safe to call on every startup."""
    await asyncio.to_thread(_init_db_sync)


async def get_watchlist_tickers(user_id: str = DEFAULT_USER_ID) -> list[str]:
    """Matches the zero-arg `Callable[[], Awaitable[list[str]]]` shape
    run_update_loop expects, via the default argument."""
    return await asyncio.to_thread(_get_watchlist_tickers_sync, user_id)


async def add_ticker(user_id: str, ticker: str) -> bool:
    """Returns False if (user_id, ticker) already exists in the watchlist."""
    return await asyncio.to_thread(_add_ticker_sync, user_id, ticker)


async def remove_ticker(user_id: str, ticker: str) -> bool:
    """Returns False if no matching row existed to delete."""
    return await asyncio.to_thread(_remove_ticker_sync, user_id, ticker)
