"""SQLite-backed chat_messages storage.

Created in Phase 1 for schema completeness (DATA-05) — the LLM chat flow
that populates this table (read/write logic, structured-output parsing,
auto-execution of trades/watchlist changes) is Phase 3's concern. This
module only creates the table; no read or write helper is shipped here to
avoid dead code against an unbuilt caller.

Mirrors app/db/watchlist.py's structure exactly: lazy schema init via
CREATE TABLE IF NOT EXISTS, sync work wrapped in asyncio.to_thread.
"""

from __future__ import annotations

import asyncio

from .watchlist import _connect

_SCHEMA = """
CREATE TABLE IF NOT EXISTS chat_messages (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL DEFAULT 'default',
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    actions TEXT,
    created_at TEXT NOT NULL
);
"""


def _init_db_sync() -> None:
    with _connect() as conn:
        conn.execute(_SCHEMA)


async def init_db() -> None:
    """Called once at app startup (see app/main.py's lifespan), before any
    asyncio.create_task(...) call (01-RESEARCH.md Pitfall 6). Creates the
    chat_messages table if missing — idempotent, safe to call on every
    startup. `actions` is deliberately nullable: PLAN.md §7 specifies JSON
    for assistant messages and null for user messages."""
    await asyncio.to_thread(_init_db_sync)
