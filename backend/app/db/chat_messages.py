"""SQLite-backed chat_messages storage.

Created in Phase 1 for schema completeness (DATA-05). Read/write logic below
was added in 03-02-PLAN.md Task 1 — the persistence half of the LLM chat
flow (structured-output parsing and auto-execution of trades/watchlist
changes live in app/llm/ and app/routes/chat.py).

Mirrors app/db/trades.py's structure exactly: frozen dataclass, sync helpers
using `with _connect() as conn:`, then thin async wrappers delegating
through asyncio.to_thread.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from .watchlist import DEFAULT_USER_ID, _connect

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


@dataclass(frozen=True)
class ChatMessage:
    id: str
    role: str
    content: str
    actions: str | None
    created_at: str


def _init_db_sync() -> None:
    with _connect() as conn:
        conn.execute(_SCHEMA)


def _insert_message_sync(
    role: str, content: str, actions: str | None, user_id: str
) -> ChatMessage:
    message_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO chat_messages (id, user_id, role, content, actions, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (message_id, user_id, role, content, actions, created_at),
        )
    return ChatMessage(
        id=message_id, role=role, content=content, actions=actions, created_at=created_at
    )


def _get_messages_sync(user_id: str, limit: int) -> list[ChatMessage]:
    # Ordered by rowid, not created_at: two messages written inside one
    # request (the user turn and its assistant reply) can carry identical
    # ISO timestamps, which would make their relative order arbitrary. The
    # table is not WITHOUT ROWID, so rowid is available with no schema
    # change and is monotonic per insert.
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT id, role, content, actions, created_at
            FROM chat_messages WHERE user_id = ?
            ORDER BY rowid DESC LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    messages = [
        ChatMessage(id=row[0], role=row[1], content=row[2], actions=row[3], created_at=row[4])
        for row in rows
    ]
    return list(reversed(messages))


async def init_db() -> None:
    """Called once at app startup (see app/main.py's lifespan), before any
    asyncio.create_task(...) call (01-RESEARCH.md Pitfall 6). Creates the
    chat_messages table if missing — idempotent, safe to call on every
    startup. `actions` is deliberately nullable: PLAN.md §7 specifies JSON
    for assistant messages and null for user messages."""
    await asyncio.to_thread(_init_db_sync)


async def insert_message(
    role: str,
    content: str,
    actions: str | None = None,
    user_id: str = DEFAULT_USER_ID,
) -> ChatMessage:
    return await asyncio.to_thread(_insert_message_sync, role, content, actions, user_id)


async def get_messages(user_id: str = DEFAULT_USER_ID, limit: int = 50) -> list[ChatMessage]:
    return await asyncio.to_thread(_get_messages_sync, user_id, limit)
