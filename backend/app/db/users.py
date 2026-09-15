"""SQLite-backed user profile storage (PLAN.md §7 users_profile table).

Single-user for now (PLAN.md §7): lazily creates the table and seeds the one
`"default"` row with the starting $10,000 cash balance on first use.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from . import connection

DEFAULT_USER_ID = "default"
DEFAULT_CASH_BALANCE = 10000.0

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users_profile (
    id TEXT PRIMARY KEY,
    cash_balance REAL NOT NULL,
    created_at TEXT NOT NULL
);
"""


def _init_db_sync() -> None:
    with connection.connect() as conn:
        conn.execute(_SCHEMA)
        (count,) = conn.execute(
            "SELECT COUNT(*) FROM users_profile WHERE id = ?", (DEFAULT_USER_ID,)
        ).fetchone()
        if count == 0:
            now = datetime.now(timezone.utc).isoformat()
            conn.execute(
                "INSERT INTO users_profile (id, cash_balance, created_at) VALUES (?, ?, ?)",
                (DEFAULT_USER_ID, DEFAULT_CASH_BALANCE, now),
            )


def _get_cash_balance_sync(user_id: str) -> float:
    with connection.connect() as conn:
        row = conn.execute(
            "SELECT cash_balance FROM users_profile WHERE id = ?", (user_id,)
        ).fetchone()
    if row is None:
        raise ValueError(f"no users_profile row for user_id={user_id!r}")
    return row[0]


def _set_cash_balance_sync(user_id: str, new_balance: float) -> None:
    # Rounded to cents at the storage boundary — see connection.MONEY_DECIMALS.
    new_balance = round(new_balance, connection.MONEY_DECIMALS)
    with connection.connect() as conn:
        conn.execute(
            "UPDATE users_profile SET cash_balance = ? WHERE id = ?",
            (new_balance, user_id),
        )


async def init_db() -> None:
    """Creates the users_profile table if missing and seeds the default
    user's $10,000 balance if empty — idempotent, safe on every startup."""
    await asyncio.to_thread(_init_db_sync)


async def get_cash_balance(user_id: str = DEFAULT_USER_ID) -> float:
    return await asyncio.to_thread(_get_cash_balance_sync, user_id)


async def set_cash_balance(user_id: str, new_balance: float) -> None:
    await asyncio.to_thread(_set_cash_balance_sync, user_id, new_balance)
