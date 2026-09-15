"""Shared SQLite path resolution and connection helper for all app/db/*
table modules.

Single place that resolves the DB file path and opens connections, so every
module gets identical `FINALLY_DB_PATH` env var behavior (PLAN.md §4/§7)
instead of each re-deriving it. Table modules should read/write `DB_PATH`
through this module (`connection.DB_PATH`, `connection.connect()`) rather
than importing the value directly, so tests can monkeypatch it in one place
and have every module pick up the change.

Every request/background task (routes, the 30s snapshot loop, the market
update loop) opens its own short-lived connection via `asyncio.to_thread` —
there's no pooling. `connect()` is a context manager (not a bare
`sqlite3.Connection`) so every call site's existing `with connection.connect()
as conn:` both commits/rolls back *and* closes the underlying connection,
rather than leaving it for the garbage collector to close eventually.
WAL journal mode is turned on per-connection (idempotent — it's stored in
the database file itself, not per-connection state) so concurrent readers
don't block behind a writer, which matters once the snapshot loop, the trade
route, and portfolio reads can all land close together in time.
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

# backend/app/db/connection.py -> parents[3] is the repo root, so this
# defaults to <repo root>/db/finally.db (PLAN.md §4's runtime volume mount
# point) regardless of the process's current working directory. Override
# with FINALLY_DB_PATH once a real Docker layout exists (PLAN.md §11).
_DEFAULT_DB_PATH = Path(__file__).resolve().parents[3] / "db" / "finally.db"
DB_PATH = Path(os.environ.get("FINALLY_DB_PATH", str(_DEFAULT_DB_PATH)))

# Rounding applied at the storage boundary (positions.apply_fill,
# trades.insert_trade, users.set_cash_balance, portfolio_snapshots) so binary
# float noise from repeated arithmetic (e.g. weighted-average cost across
# many fills) never accumulates in stored values or leaks into the UI as
# something like "9999.999999999998". Chosen to comfortably exceed any
# precision callers actually need at this app's demo scale (starting
# balance $10,000, market orders only): 6 dp for fractional share quantity,
# 2 dp (cents) for USD amounts (price, cost basis, cash, total value).
QUANTITY_DECIMALS = 6
MONEY_DECIMALS = 2


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=5.0)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        with conn:
            yield conn
    finally:
        conn.close()
