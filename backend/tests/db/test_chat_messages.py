"""Schema-only tests for the chat_messages table (01-03-PLAN.md Task 3).

Written RED first: at the time this file is authored, app/db/chat_messages.py
does not exist yet. Only schema creation is exercised this phase — read/write
logic is Phase 3's concern (DATA-05).
"""

import uuid
from datetime import datetime, timezone

import pytest

from app.db import chat_messages as chat_messages_module
from app.db.watchlist import _connect


@pytest.mark.asyncio
async def test_init_db_creates_chat_messages_table():
    await chat_messages_module.init_db()

    with _connect() as conn:
        columns = [row[1] for row in conn.execute("PRAGMA table_info(chat_messages)").fetchall()]

    assert columns == ["id", "user_id", "role", "content", "actions", "created_at"]


@pytest.mark.asyncio
async def test_init_db_is_idempotent():
    await chat_messages_module.init_db()
    await chat_messages_module.init_db()

    with _connect() as conn:
        columns = [row[1] for row in conn.execute("PRAGMA table_info(chat_messages)").fetchall()]

    assert columns == ["id", "user_id", "role", "content", "actions", "created_at"]


@pytest.mark.asyncio
async def test_actions_column_is_nullable():
    await chat_messages_module.init_db()

    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        conn.execute(
            "INSERT INTO chat_messages (id, user_id, role, content, actions, created_at) "
            "VALUES (?, ?, ?, ?, NULL, ?)",
            (str(uuid.uuid4()), "default", "user", "hello", now),
        )
        conn.commit()
        (actions,) = conn.execute(
            "SELECT actions FROM chat_messages WHERE role = 'user'"
        ).fetchone()

    assert actions is None
