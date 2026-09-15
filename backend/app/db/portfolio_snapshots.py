"""SQLite-backed portfolio value snapshots (PLAN.md §7 portfolio_snapshots).

Recorded every 30 seconds by a background task and immediately after each
trade execution (caller's responsibility — this module just stores rows).
Rows are never pruned: unbounded growth over a session is an accepted
tradeoff for this single-user, demo-scale project, not a bug to fix.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

from . import connection

DEFAULT_USER_ID = "default"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL DEFAULT 'default',
    total_value REAL NOT NULL,
    recorded_at TEXT NOT NULL
);
"""


def _init_db_sync() -> None:
    with connection.connect() as conn:
        conn.execute(_SCHEMA)


def _insert_snapshot_sync(user_id: str, total_value: float) -> None:
    # Rounded to cents at the storage boundary — see connection.MONEY_DECIMALS.
    total_value = round(total_value, connection.MONEY_DECIMALS)
    with connection.connect() as conn:
        conn.execute(
            "INSERT INTO portfolio_snapshots (id, user_id, total_value, recorded_at) "
            "VALUES (?, ?, ?, ?)",
            (str(uuid.uuid4()), user_id, total_value, datetime.now(timezone.utc).isoformat()),
        )


def _get_snapshots_sync(user_id: str) -> list[dict]:
    with connection.connect() as conn:
        rows = conn.execute(
            "SELECT total_value, recorded_at FROM portfolio_snapshots "
            "WHERE user_id = ? ORDER BY recorded_at ASC",
            (user_id,),
        ).fetchall()
    return [{"total_value": row[0], "recorded_at": row[1]} for row in rows]


async def init_db() -> None:
    await asyncio.to_thread(_init_db_sync)


async def insert_snapshot(user_id: str, total_value: float) -> None:
    await asyncio.to_thread(_insert_snapshot_sync, user_id, total_value)


async def get_snapshots(user_id: str = DEFAULT_USER_ID) -> list[dict]:
    return await asyncio.to_thread(_get_snapshots_sync, user_id)
