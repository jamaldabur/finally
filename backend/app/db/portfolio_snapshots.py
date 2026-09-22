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

# What a caller gets when it expresses no preference on how many snapshots
# to read back (04-07-PLAN.md Task 1, closing gap G-04-4). The ceiling a
# caller may explicitly ask for is MAX_SNAPSHOT_LIMIT, enforced by the route
# layer's request validation, not here. Neither constant prunes anything —
# the table itself stays append-only and unbounded per PLAN.md §7; they
# bound only what one read hands back.
DEFAULT_SNAPSHOT_LIMIT = 500
MAX_SNAPSHOT_LIMIT = 2000


@dataclass(frozen=True)
class PortfolioSnapshot:
    total_value: float
    recorded_at: str


def _init_db_sync() -> None:
    with _connect() as conn:
        conn.execute(_SCHEMA)


def _insert_snapshot_sync(total_value: float, user_id: str) -> PortfolioSnapshot:
    snapshot_id = str(uuid.uuid4())
    # ISO-8601 timestamp for display/tooltip purposes only. Read order no
    # longer depends on this string being distinct or monotonically
    # increasing between inserts — see _get_snapshots_sync's rowid-based
    # ordering below. On some platforms datetime.now()'s effective clock
    # resolution is coarser than microseconds, so back-to-back inserts (the
    # 30-second recorder and an on-trade insert) can legitimately share one
    # recorded_at string.
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


def _get_snapshots_sync(user_id: str, limit: int) -> list[PortfolioSnapshot]:
    # Select the most recent `limit` rows by insertion order (rowid), not by
    # recorded_at: the 30-second recorder and the insert that follows a
    # trade can write inside the same moment and carry an identical ISO
    # timestamp, which would make a descending sort on that column pick an
    # arbitrary subset at the window boundary. The table is not
    # WITHOUT ROWID, so rowid is available with no schema change and is
    # monotonic per insert — mirrors chat_messages.py's identical fix for
    # the same tie condition. Reverse the DESC-ordered result so the
    # function still returns oldest-first, matching every downstream
    # consumer's ascending-order contract.
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT total_value, recorded_at FROM portfolio_snapshots
            WHERE user_id = ? ORDER BY rowid DESC LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    snapshots = [
        PortfolioSnapshot(total_value=row[0], recorded_at=row[1]) for row in rows
    ]
    return list(reversed(snapshots))


async def init_db() -> None:
    """Called once at app startup (see app/main.py's lifespan). Creates the
    portfolio_snapshots table if missing — idempotent, safe to call on every
    startup."""
    await asyncio.to_thread(_init_db_sync)


async def insert_snapshot(
    total_value: float, user_id: str = DEFAULT_USER_ID
) -> PortfolioSnapshot:
    return await asyncio.to_thread(_insert_snapshot_sync, total_value, user_id)


async def get_snapshots(
    user_id: str = DEFAULT_USER_ID, limit: int = DEFAULT_SNAPSHOT_LIMIT
) -> list[PortfolioSnapshot]:
    """Return at most `limit` snapshots — the most recently recorded ones,
    ordered oldest-first. No delete, prune or aggregate function exists on
    this module by design (PLAN.md §7); this bounds only what a read hands
    back, never what is stored."""
    return await asyncio.to_thread(_get_snapshots_sync, user_id, limit)
