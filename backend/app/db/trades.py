"""SQLite-backed trade history storage (PLAN.md §7 trades table).

Append-only log: no update/delete path, only inserts and reads.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

from . import connection

DEFAULT_USER_ID = "default"

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


def _init_db_sync() -> None:
    with connection.connect() as conn:
        conn.execute(_SCHEMA)


def _insert_trade_sync(
    user_id: str, ticker: str, side: str, quantity: float, price: float
) -> dict:
    # Rounded at the storage boundary — see connection.QUANTITY_DECIMALS /
    # MONEY_DECIMALS — so the trade log matches what positions.apply_fill
    # actually stores for the same fill.
    quantity = round(quantity, connection.QUANTITY_DECIMALS)
    price = round(price, connection.MONEY_DECIMALS)

    trade_id = str(uuid.uuid4())
    executed_at = datetime.now(timezone.utc).isoformat()
    with connection.connect() as conn:
        conn.execute(
            "INSERT INTO trades (id, user_id, ticker, side, quantity, price, executed_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (trade_id, user_id, ticker, side, quantity, price, executed_at),
        )
    return {
        "id": trade_id,
        "user_id": user_id,
        "ticker": ticker,
        "side": side,
        "quantity": quantity,
        "price": price,
        "executed_at": executed_at,
    }


async def init_db() -> None:
    await asyncio.to_thread(_init_db_sync)


async def insert_trade(
    user_id: str, ticker: str, side: str, quantity: float, price: float
) -> dict:
    return await asyncio.to_thread(_insert_trade_sync, user_id, ticker, side, quantity, price)
