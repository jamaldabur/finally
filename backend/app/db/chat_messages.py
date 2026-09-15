"""SQLite-backed chat conversation history (PLAN.md §7 chat_messages table).

`actions` (the trades/watchlist changes a message triggered, plus their
executed/error outcomes — PLAN.md §9) is stored as a JSON string and
transparently serialized/deserialized at the boundary, so callers only ever
deal in Python objects.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone

from . import connection

DEFAULT_USER_ID = "default"
DEFAULT_LIMIT = 50

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


def _row_to_dict(row) -> dict:
    id_, user_id, role, content, actions, created_at = row
    return {
        "id": id_,
        "user_id": user_id,
        "role": role,
        "content": content,
        "actions": json.loads(actions) if actions is not None else None,
        "created_at": created_at,
    }


def _init_db_sync() -> None:
    with connection.connect() as conn:
        conn.execute(_SCHEMA)


def _insert_message_sync(user_id: str, role: str, content: str, actions) -> dict:
    msg_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()
    actions_json = json.dumps(actions) if actions is not None else None
    with connection.connect() as conn:
        conn.execute(
            "INSERT INTO chat_messages (id, user_id, role, content, actions, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (msg_id, user_id, role, content, actions_json, created_at),
        )
    return {
        "id": msg_id,
        "user_id": user_id,
        "role": role,
        "content": content,
        "actions": actions,
        "created_at": created_at,
    }


def _get_recent_messages_sync(user_id: str, limit: int) -> list[dict]:
    # Take the most recent `limit` rows by insertion order (rowid), then
    # re-sort ascending — oldest-first, ready to feed straight into an LLM
    # conversation. rowid (not created_at) breaks ties reliably since two
    # inserts can share an ISO timestamp at this resolution.
    with connection.connect() as conn:
        rows = conn.execute(
            """
            SELECT id, user_id, role, content, actions, created_at FROM (
                SELECT id, user_id, role, content, actions, created_at, rowid
                FROM chat_messages
                WHERE user_id = ?
                ORDER BY rowid DESC
                LIMIT ?
            ) recent
            ORDER BY rowid ASC
            """,
            (user_id, limit),
        ).fetchall()
    return [_row_to_dict(row) for row in rows]


async def init_db() -> None:
    await asyncio.to_thread(_init_db_sync)


async def insert_message(user_id: str, role: str, content: str, actions=None) -> dict:
    return await asyncio.to_thread(_insert_message_sync, user_id, role, content, actions)


async def get_recent_messages(user_id: str = DEFAULT_USER_ID, limit: int = DEFAULT_LIMIT) -> list[dict]:
    return await asyncio.to_thread(_get_recent_messages_sync, user_id, limit)
