"""SQLite-backed portfolio value history (PLAN.md §7 "portfolio_snapshots").

Append-only log of total portfolio value over time — recorded every 30
seconds by a background task (app/portfolio/snapshots.py) and immediately
after each successful trade (app/portfolio/service.py::execute_trade()).
Rows are deliberately never pruned: PLAN.md §7 explicitly accepts unbounded
growth for this single-user, demo-scale project. Mirrors app/db/trades.py's
append-only schema + idempotent-init pattern exactly — no update and no
delete function exists on this module by design.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from .watchlist import DEFAULT_USER_ID, _connect

_SCHEMA = """
CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL DEFAULT 'default',
    total_value REAL NOT NULL,
    recorded_at TEXT NOT NULL
);
"""


@dataclass(frozen=True)
class PortfolioSnapshot:
    total_value: float
    recorded_at: str


def _init_db_sync() -> None:
    with _connect() as conn:
        conn.execute(_SCHEMA)


def _insert_snapshot_sync(total_value: float, user_id: str) -> PortfolioSnapshot:
    snapshot_id = str(uuid.uuid4())
    # Microsecond-resolution ISO-8601 timestamps give consecutive inserts
    # distinct, monotonically increasing recorded_at strings, so the text
    # sort in _get_snapshots_sync matches chronological order.
    recorded_at = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO portfolio_snapshots (id, user_id, total_value, recorded_at)
            VALUES (?, ?, ?, ?)
            """,
            (snapshot_id, user_id, total_value, recorded_at),
        )
    return PortfolioSnapshot(total_value=total_value, recorded_at=recorded_at)


def _get_snapshots_sync(user_id: str) -> list[PortfolioSnapshot]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT total_value, recorded_at FROM portfolio_snapshots
            WHERE user_id = ? ORDER BY recorded_at
            """,
            (user_id,),
        ).fetchall()
    return [PortfolioSnapshot(total_value=row[0], recorded_at=row[1]) for row in rows]


async def init_db() -> None:
    """Called once at app startup (see app/main.py's lifespan). Creates the
    portfolio_snapshots table if missing — idempotent, safe to call on every
    startup."""
    await asyncio.to_thread(_init_db_sync)


async def insert_snapshot(
    total_value: float, user_id: str = DEFAULT_USER_ID
) -> PortfolioSnapshot:
    return await asyncio.to_thread(_insert_snapshot_sync, total_value, user_id)


async def get_snapshots(user_id: str = DEFAULT_USER_ID) -> list[PortfolioSnapshot]:
    return await asyncio.to_thread(_get_snapshots_sync, user_id)
