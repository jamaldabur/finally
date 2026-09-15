"""SQLite-backed positions storage (PLAN.md §7 positions table).

Pure storage: `apply_fill` does not validate that a sell has enough shares or
a buy has enough cash — that's the trade service's job (caller validates
before calling here). One row per (user_id, ticker); a sell that reduces a
position to ~0 deletes the row rather than leaving a zero-quantity position
behind.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

from . import connection

DEFAULT_USER_ID = "default"

# Fractional-share arithmetic can leave a sell-to-zero as e.g. 1e-16 instead
# of exactly 0.0; treat anything smaller than this as "fully closed."
_ZERO_EPSILON = 1e-9

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


def _row_to_dict(row) -> dict:
    ticker, quantity, avg_cost, updated_at = row
    return {
        "ticker": ticker,
        "quantity": quantity,
        "avg_cost": avg_cost,
        "updated_at": updated_at,
    }


def _init_db_sync() -> None:
    with connection.connect() as conn:
        conn.execute(_SCHEMA)


def _get_positions_sync(user_id: str) -> list[dict]:
    with connection.connect() as conn:
        rows = conn.execute(
            "SELECT ticker, quantity, avg_cost, updated_at FROM positions WHERE user_id = ?",
            (user_id,),
        ).fetchall()
    return [_row_to_dict(row) for row in rows]


def _get_position_sync(user_id: str, ticker: str) -> dict | None:
    with connection.connect() as conn:
        row = conn.execute(
            "SELECT ticker, quantity, avg_cost, updated_at FROM positions WHERE user_id = ? AND ticker = ?",
            (user_id, ticker),
        ).fetchone()
    return _row_to_dict(row) if row is not None else None


def _apply_fill_sync(
    user_id: str, ticker: str, side: str, quantity: float, price: float
) -> None:
    if side not in ("buy", "sell"):
        raise ValueError(f"unknown side {side!r}")

    # Rounded at the storage boundary — see connection.QUANTITY_DECIMALS /
    # MONEY_DECIMALS — so weighted-average cost math can't leave binary float
    # noise (e.g. avg_cost = 149.99999999999997) sitting in stored rows.
    quantity = round(quantity, connection.QUANTITY_DECIMALS)
    price = round(price, connection.MONEY_DECIMALS)

    now = datetime.now(timezone.utc).isoformat()
    with connection.connect() as conn:
        row = conn.execute(
            "SELECT quantity, avg_cost FROM positions WHERE user_id = ? AND ticker = ?",
            (user_id, ticker),
        ).fetchone()

        if side == "buy":
            if row is None:
                conn.execute(
                    "INSERT INTO positions (id, user_id, ticker, quantity, avg_cost, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (str(uuid.uuid4()), user_id, ticker, quantity, price, now),
                )
            else:
                old_qty, old_avg = row
                new_qty = round(old_qty + quantity, connection.QUANTITY_DECIMALS)
                new_avg = round(
                    (old_qty * old_avg + quantity * price) / new_qty,
                    connection.MONEY_DECIMALS,
                )
                conn.execute(
                    "UPDATE positions SET quantity = ?, avg_cost = ?, updated_at = ? "
                    "WHERE user_id = ? AND ticker = ?",
                    (new_qty, new_avg, now, user_id, ticker),
                )
        else:  # sell
            if row is None:
                raise ValueError(
                    f"no position to sell for user_id={user_id!r} ticker={ticker!r}"
                )
            old_qty, old_avg = row
            new_qty = round(old_qty - quantity, connection.QUANTITY_DECIMALS)
            if abs(new_qty) < _ZERO_EPSILON:
                conn.execute(
                    "DELETE FROM positions WHERE user_id = ? AND ticker = ?",
                    (user_id, ticker),
                )
            else:
                conn.execute(
                    "UPDATE positions SET quantity = ?, updated_at = ? "
                    "WHERE user_id = ? AND ticker = ?",
                    (new_qty, now, user_id, ticker),
                )


async def init_db() -> None:
    await asyncio.to_thread(_init_db_sync)


async def get_positions(user_id: str = DEFAULT_USER_ID) -> list[dict]:
    return await asyncio.to_thread(_get_positions_sync, user_id)


async def get_position(user_id: str, ticker: str) -> dict | None:
    return await asyncio.to_thread(_get_position_sync, user_id, ticker)


async def apply_fill(
    user_id: str, ticker: str, side: str, quantity: float, price: float
) -> None:
    await asyncio.to_thread(_apply_fill_sync, user_id, ticker, side, quantity, price)
