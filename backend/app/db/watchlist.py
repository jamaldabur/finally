"""SQLite-backed watchlist storage.

Lazily initializes its own table and seeds PLAN.md §7's 10 default tickers
on first use — no separate migration step (PLAN.md §7 "Lazy Initialization").
This is the one piece of persistence the market data layer depends on:
`run_update_loop` (app/market/loop.py) needs to know which tickers to
poll/tick for on every cycle.

Read path (`get_watchlist_tickers`, `get_watchlist_entries`) plus mutation
(`add_watchlist_ticker`, `remove_watchlist_ticker`) all live here — this is
the full read/write persistence layer for the watchlist table. Ticker
validity/normalization is the caller's job (see app/routes/watchlist.py);
this module stays a thin persistence layer (01-PATTERNS.md).
"""

from __future__ import annotations

import asyncio
import os
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from ..market.simulator import DEFAULT_WATCHLIST

# backend/app/db/watchlist.py -> parents[3] is the repo root, so this
# defaults to <repo root>/db/finally.db (PLAN.md §4's runtime volume mount
# point) regardless of the process's current working directory. Override
# with FINALLY_DB_PATH once a real Docker layout exists (PLAN.md §11).
_DEFAULT_DB_PATH = Path(__file__).resolve().parents[3] / "db" / "finally.db"
DB_PATH = Path(os.environ.get("FINALLY_DB_PATH", str(_DEFAULT_DB_PATH)))

DEFAULT_USER_ID = "default"


@dataclass(frozen=True)
class WatchlistEntry:
    ticker: str
    added_at: str


_SCHEMA = """
CREATE TABLE IF NOT EXISTS watchlist (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL DEFAULT 'default',
    ticker TEXT NOT NULL,
    added_at TEXT NOT NULL,
    UNIQUE(user_id, ticker)
);
"""


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH, timeout=5.0)


def _init_db_sync() -> None:
    with _connect() as conn:
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
    with _connect() as conn:
        rows = conn.execute(
            "SELECT ticker FROM watchlist WHERE user_id = ?", (user_id,)
        ).fetchall()
    return [row[0] for row in rows]


def _add_watchlist_ticker_sync(ticker: str, user_id: str) -> bool:
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        cursor = conn.execute(
            "INSERT OR IGNORE INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
            (str(uuid.uuid4()), user_id, ticker, now),
        )
        return cursor.rowcount != 0


def _remove_watchlist_ticker_sync(ticker: str, user_id: str) -> bool:
    with _connect() as conn:
        cursor = conn.execute(
            "DELETE FROM watchlist WHERE user_id = ? AND ticker = ?", (user_id, ticker)
        )
        return cursor.rowcount != 0


def _get_watchlist_entries_sync(user_id: str) -> list[WatchlistEntry]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT ticker, added_at FROM watchlist WHERE user_id = ? ORDER BY ticker",
            (user_id,),
        ).fetchall()
    return [WatchlistEntry(ticker=row[0], added_at=row[1]) for row in rows]


async def init_db() -> None:
    """Called once at app startup (see app/main.py's lifespan). Creates the
    watchlist table if missing and seeds the default tickers if empty —
    idempotent, safe to call on every startup."""
    await asyncio.to_thread(_init_db_sync)


async def get_watchlist_tickers(user_id: str = DEFAULT_USER_ID) -> list[str]:
    """Matches the zero-arg `Callable[[], Awaitable[list[str]]]` shape
    run_update_loop expects, via the default argument."""
    return await asyncio.to_thread(_get_watchlist_tickers_sync, user_id)


async def add_watchlist_ticker(ticker: str, user_id: str = DEFAULT_USER_ID) -> bool:
    """Idempotent add via INSERT OR IGNORE, leaning on the table's
    UNIQUE(user_id, ticker) constraint — a duplicate add is a silent no-op
    rather than an IntegrityError the caller would have to catch. Returns
    whether a new row was actually inserted."""
    return await asyncio.to_thread(_add_watchlist_ticker_sync, ticker, user_id)


async def remove_watchlist_ticker(ticker: str, user_id: str = DEFAULT_USER_ID) -> bool:
    """Idempotent delete — returns whether a row was actually removed."""
    return await asyncio.to_thread(_remove_watchlist_ticker_sync, ticker, user_id)


async def get_watchlist_entries(user_id: str = DEFAULT_USER_ID) -> list[WatchlistEntry]:
    """Every watched ticker with its added_at timestamp, sorted by ticker."""
    return await asyncio.to_thread(_get_watchlist_entries_sync, user_id)
