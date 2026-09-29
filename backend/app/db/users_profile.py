"""SQLite-backed user profile storage (PLAN.md §7 "users_profile").

Single-row-per-user table holding cash balance. Lazily initialized and
seeded with $10,000 on first use, mirroring app/db/watchlist.py's schema +
idempotent-init pattern exactly.
"""

from __future__ import annotations

import asyncio
import sqlite3
from datetime import datetime, timezone

from .watchlist import DEFAULT_USER_ID, _connect

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users_profile (
    id TEXT PRIMARY KEY,
    cash_balance REAL NOT NULL,
    created_at TEXT NOT NULL
);
"""

_STARTING_CASH_BALANCE = 10000.0


def _init_db_sync() -> None:
    with _connect() as conn:
        conn.execute(_SCHEMA)
        row = conn.execute(
            "SELECT id FROM users_profile WHERE id = ?", (DEFAULT_USER_ID,)
        ).fetchone()
        if row is None:
            now = datetime.now(timezone.utc).isoformat()
            conn.execute(
                "INSERT INTO users_profile (id, cash_balance, created_at) VALUES (?, ?, ?)",
                (DEFAULT_USER_ID, _STARTING_CASH_BALANCE, now),
            )


def _get_cash_balance_sync(user_id: str) -> float:
    with _connect() as conn:
        row = conn.execute(
            "SELECT cash_balance FROM users_profile WHERE id = ?", (user_id,)
        ).fetchone()
    if row is None:
        raise sqlite3.OperationalError(
            "No users_profile row for user_id=%r" % (user_id,)
        )
    return row[0]


def _set_cash_balance_sync(new_balance: float, user_id: str) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE users_profile SET cash_balance = ? WHERE id = ?",
            (new_balance, user_id),
        )


async def init_db() -> None:
    """Called once at app startup (see app/main.py's lifespan). Creates the
    users_profile table if missing and seeds the default $10,000 row if
    empty — idempotent, safe to call on every startup."""
    await asyncio.to_thread(_init_db_sync)


async def get_cash_balance(user_id: str = DEFAULT_USER_ID) -> float:
    return await asyncio.to_thread(_get_cash_balance_sync, user_id)


async def set_cash_balance(new_balance: float, user_id: str = DEFAULT_USER_ID) -> None:
    await asyncio.to_thread(_set_cash_balance_sync, new_balance, user_id)
