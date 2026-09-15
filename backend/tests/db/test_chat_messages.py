import pytest

from app.db import chat_messages as chat_module


@pytest.mark.asyncio
async def test_get_recent_messages_empty_before_any_insert():
    await chat_module.init_db()
    assert await chat_module.get_recent_messages() == []


@pytest.mark.asyncio
async def test_insert_message_without_actions_round_trips_none():
    await chat_module.init_db()
    inserted = await chat_module.insert_message("default", "user", "Hello")
    assert inserted["actions"] is None

    messages = await chat_module.get_recent_messages()
    assert len(messages) == 1
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Hello"
    assert messages[0]["actions"] is None


@pytest.mark.asyncio
async def test_insert_message_with_actions_round_trips_json():
    await chat_module.init_db()
    actions = [{"type": "trade", "ticker": "AAPL", "side": "buy", "outcome": "executed"}]
    inserted = await chat_module.insert_message("default", "assistant", "Bought it.", actions)
    assert inserted["actions"] == actions

    messages = await chat_module.get_recent_messages()
    assert messages[0]["actions"] == actions


@pytest.mark.asyncio
async def test_get_recent_messages_ordered_oldest_first():
    await chat_module.init_db()
    await chat_module.insert_message("default", "user", "first")
    await chat_module.insert_message("default", "assistant", "second")
    await chat_module.insert_message("default", "user", "third")

    messages = await chat_module.get_recent_messages()
    assert [m["content"] for m in messages] == ["first", "second", "third"]


@pytest.mark.asyncio
async def test_get_recent_messages_respects_limit_keeping_most_recent():
    await chat_module.init_db()
    for i in range(5):
        await chat_module.insert_message("default", "user", f"message-{i}")

    messages = await chat_module.get_recent_messages(limit=2)
    assert [m["content"] for m in messages] == ["message-3", "message-4"]


@pytest.mark.asyncio
async def test_get_recent_messages_scoped_per_user():
    await chat_module.init_db()
    await chat_module.insert_message("default", "user", "hi")
    await chat_module.insert_message("someone-else", "user", "other user's message")

    messages = await chat_module.get_recent_messages()
    assert [m["content"] for m in messages] == ["hi"]
