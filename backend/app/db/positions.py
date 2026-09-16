"""SQLite-backed positions storage (PLAN.md §7 "positions").

One row per (user_id, ticker) — current holdings with a running average
cost. The weighted-average arithmetic on a buy is the caller's job
(app/portfolio/service.py); this module's upsert stores exactly what it is
handed, matching app/db/watchlist.py's thin-persistence-layer convention.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from .watchlist import DEFAULT_USER_ID, _connect

_SCHEMA = """
CREATE TABLE IF NOT EXISTS positions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL DEFAULT 'default',
    ticker TEXT NOT NULL,
    quantity REAL NOT NULL,
    avg_cost REAL NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(user_id, ticker)
);
"""


@dataclass(frozen=True)
class Position:
    ticker: str
    quantity: float
    avg_cost: float


def _init_db_sync() -> None:
    with _connect() as conn:
        conn.execute(_SCHEMA)


def _get_position_sync(ticker: str, user_id: str) -> Position | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT ticker, quantity, avg_cost FROM positions WHERE user_id = ? AND ticker = ?",
            (user_id, ticker),
        ).fetchone()
    if row is None:
        return None
    return Position(ticker=row[0], quantity=row[1], avg_cost=row[2])


def _get_all_positions_sync(user_id: str) -> list[Position]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT ticker, quantity, avg_cost FROM positions WHERE user_id = ? ORDER BY ticker",
            (user_id,),
        ).fetchall()
    return [Position(ticker=row[0], quantity=row[1], avg_cost=row[2]) for row in rows]


def _upsert_position_sync(
    ticker: str, quantity: float, avg_cost: float, user_id: str
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO positions (id, user_id, ticker, quantity, avg_cost, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, ticker) DO UPDATE SET
                quantity = excluded.quantity,
                avg_cost = excluded.avg_cost,
                updated_at = excluded.updated_at
            """,
            (str(uuid.uuid4()), user_id, ticker, quantity, avg_cost, now),
        )


async def init_db() -> None:
    """Called once at app startup (see app/main.py's lifespan). Creates the
    positions table if missing — idempotent, safe to call on every
    startup."""
    await asyncio.to_thread(_init_db_sync)


async def get_position(ticker: str, user_id: str = DEFAULT_USER_ID) -> Position | None:
    return await asyncio.to_thread(_get_position_sync, ticker, user_id)


async def get_all_positions(user_id: str = DEFAULT_USER_ID) -> list[Position]:
    return await asyncio.to_thread(_get_all_positions_sync, user_id)


async def upsert_position(
    ticker: str, quantity: float, avg_cost: float, user_id: str = DEFAULT_USER_ID
) -> None:
    await asyncio.to_thread(_upsert_position_sync, ticker, quantity, avg_cost, user_id)
