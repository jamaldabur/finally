"""Schema and read/write tests for the chat_messages table.

The original three tests (schema-only) were written RED first in Phase 1,
before app/db/chat_messages.py existed. The read/write tests below were added
in 03-02-PLAN.md Task 1, once insert_message()/get_messages() were built.
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


@pytest.mark.asyncio
async def test_insert_message_round_trips_through_get_messages():
    """Test 1: insert_message() then get_messages() returns one ChatMessage
    with the fields set as written, a non-empty id, and a parseable ISO
    created_at."""
    await chat_messages_module.init_db()

    await chat_messages_module.insert_message("user", "hello", None)

    messages = await chat_messages_module.get_messages()

    assert len(messages) == 1
    message = messages[0]
    assert message.role == "user"
    assert message.content == "hello"
    assert message.actions is None
    assert message.id
    # Must not raise — created_at is a valid ISO 8601 timestamp.
    datetime.fromisoformat(message.created_at)


@pytest.mark.asyncio
async def test_get_messages_orders_by_rowid_not_created_at():
    """Test 2: three rows sharing an identical created_at timestamp still
    come back oldest-first, in insertion order — because ordering is by
    rowid (monotonic per insert), not the (possibly-tied) timestamp
    string."""
    await chat_messages_module.init_db()

    same_timestamp = datetime.now(timezone.utc).isoformat()
    rows = [
        (str(uuid.uuid4()), "user", "first", None, same_timestamp),
        (str(uuid.uuid4()), "assistant", "second", None, same_timestamp),
        (str(uuid.uuid4()), "user", "third", None, same_timestamp),
    ]
    with _connect() as conn:
        conn.executemany(
            "INSERT INTO chat_messages (id, user_id, role, content, actions, created_at) "
            "VALUES (?, 'default', ?, ?, ?, ?)",
            [(row[0], row[1], row[2], row[3], row[4]) for row in rows],
        )
        conn.commit()

    messages = await chat_messages_module.get_messages()

    assert [m.content for m in messages] == ["first", "second", "third"]


@pytest.mark.asyncio
async def test_get_messages_limit_returns_most_recent_oldest_first():
    """Test 3: get_messages(limit=2) after five inserts returns the two most
    recent, still ordered oldest-first."""
    await chat_messages_module.init_db()

    for i in range(5):
        await chat_messages_module.insert_message("user", f"message {i}", None)

    messages = await chat_messages_module.get_messages(limit=2)

    assert [m.content for m in messages] == ["message 3", "message 4"]


@pytest.mark.asyncio
async def test_insert_message_preserves_multibyte_characters():
    """Test 4: emoji and CJK content round-trips with identical code
    points."""
    await chat_messages_module.init_db()

    content = "買い 📈 AAPL"
    await chat_messages_module.insert_message("user", content, None)

    messages = await chat_messages_module.get_messages()

    assert messages[0].content == content
