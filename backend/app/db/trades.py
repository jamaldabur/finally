"""SQLite-backed trade history storage (PLAN.md §7 "trades").

Append-only log of executed fills — no update or delete function exists on
this module by design. Mirrors app/db/watchlist.py's schema + idempotent-init
pattern.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from .watchlist import DEFAULT_USER_ID, _connect

_SCHEMA = """
CREATE TABLE IF NOT EXISTS trades (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL DEFAULT 'default',
    ticker TEXT NOT NULL,
    side TEXT NOT NULL,
    quantity REAL NOT NULL,
    price REAL NOT NULL,
    executed_at TEXT NOT NULL
);
"""


@dataclass(frozen=True)
class Trade:
    id: str
    ticker: str
    side: str
    quantity: float
    price: float
    executed_at: str


def _init_db_sync() -> None:
    with _connect() as conn:
        conn.execute(_SCHEMA)


def _insert_trade_sync(
    ticker: str, side: str, quantity: float, price: float, user_id: str
) -> Trade:
    trade_id = str(uuid.uuid4())
    executed_at = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO trades (id, user_id, ticker, side, quantity, price, executed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (trade_id, user_id, ticker, side, quantity, price, executed_at),
        )
    return Trade(
        id=trade_id,
        ticker=ticker,
        side=side,
        quantity=quantity,
        price=price,
        executed_at=executed_at,
    )


def _get_trades_sync(user_id: str) -> list[Trade]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT id, ticker, side, quantity, price, executed_at
            FROM trades WHERE user_id = ? ORDER BY executed_at ASC
            """,
            (user_id,),
        ).fetchall()
    return [
        Trade(id=row[0], ticker=row[1], side=row[2], quantity=row[3], price=row[4], executed_at=row[5])
        for row in rows
    ]


async def init_db() -> None:
    """Called once at app startup (see app/main.py's lifespan). Creates the
    trades table if missing — idempotent, safe to call on every startup."""
    await asyncio.to_thread(_init_db_sync)


async def insert_trade(
    ticker: str, side: str, quantity: float, price: float, user_id: str = DEFAULT_USER_ID
) -> Trade:
    return await asyncio.to_thread(_insert_trade_sync, ticker, side, quantity, price, user_id)


async def get_trades(user_id: str = DEFAULT_USER_ID) -> list[Trade]:
    return await asyncio.to_thread(_get_trades_sync, user_id)
