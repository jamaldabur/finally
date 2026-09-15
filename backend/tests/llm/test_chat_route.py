"""Route-level tests for /api/chat* (PLAN.md §7 "How It Works").

`POST /api/chat` now streams `text/event-stream`. Tests call the module's
`_chat_event_stream` async generator directly (mirrors the rest of this
codebase's pattern of testing route logic directly rather than through a
live TestClient - see tests/routes/test_portfolio.py) and parse the raw SSE
text blocks it yields, rather than going through a real LLM: `stream_chat_message`
and `get_actions` are monkeypatched.
"""

import json
from types import SimpleNamespace

import pytest

import app.routes.chat as chat_module
from app.db import chat_messages
from app.llm.client import FALLBACK_MESSAGE
from app.llm.schema import ActionsResult, TradeAction, WatchlistChangeAction
from app.market.base import ChangeDirection, PriceTick
from app.portfolio.service import TradeError
from app.routes.chat import get_chat
from app.watchlist.service import WatchlistError


class _FakeCache:
    def __init__(self, prices: dict[str, float]):
        self._prices = prices

    async def get(self, ticker: str):
        if ticker not in self._prices:
            return None
        price = self._prices[ticker]
        return PriceTick(ticker, price, price, None, ChangeDirection.UNCHANGED)


def _state(prices: dict[str, float] | None = None):
    return SimpleNamespace(price_cache=_FakeCache(prices or {}), market_source=None)


def _parse_sse(raw: str) -> tuple[str, dict]:
    event = None
    data = None
    for line in raw.strip("\n").split("\n"):
        if line.startswith("event: "):
            event = line[len("event: "):]
        elif line.startswith("data: "):
            data = json.loads(line[len("data: "):])
    return event, data


async def _collect_events(app_state, message) -> list[tuple[str, dict]]:
    return [
        _parse_sse(raw)
        async for raw in chat_module._chat_event_stream(app_state, message)
    ]


def _deltas(events: list[tuple[str, dict]]) -> list[str]:
    return [data["text"] for event, data in events if event == "delta"]


def _done(events: list[tuple[str, dict]]) -> dict:
    done_events = [data for event, data in events if event == "done"]
    assert len(done_events) == 1
    return done_events[0]


@pytest.fixture(autouse=True)
async def seeded_db():
    import app.db as db

    await db.init_db()


async def test_get_chat_returns_recent_history():
    await chat_messages.insert_message("default", "user", "hello")
    await chat_messages.insert_message("default", "assistant", "hi there", actions=None)

    result = await get_chat()

    assert [m["role"] for m in result] == ["user", "assistant"]
    assert result[0]["content"] == "hello"
    assert result[1]["content"] == "hi there"


async def test_post_chat_streams_deltas_in_order_then_done(monkeypatch):
    async def _stream(messages, user_message):
        yield "Your "
        yield "portfolio "
        yield "is fine."

    async def _actions(messages, user_message):
        return ActionsResult()

    monkeypatch.setattr(chat_module, "stream_chat_message", _stream)
    monkeypatch.setattr(chat_module, "get_actions", _actions)

    events = await _collect_events(_state(), "how am I doing?")

    assert _deltas(events) == ["Your ", "portfolio ", "is fine."]
    done = _done(events)
    assert done["message"] == "Your portfolio is fine."
    assert done["trades"] == []
    assert done["watchlist_changes"] == []


async def test_post_chat_executes_trade_and_annotates_success(monkeypatch):
    async def _stream(messages, user_message):
        yield "Buying AAPL."

    async def _actions(messages, user_message):
        return ActionsResult(trades=[TradeAction(ticker="AAPL", side="buy", quantity=5)])

    monkeypatch.setattr(chat_module, "stream_chat_message", _stream)
    monkeypatch.setattr(chat_module, "get_actions", _actions)

    events = await _collect_events(_state(prices={"AAPL": 100.0}), "buy 5 AAPL")

    done = _done(events)
    assert done["message"] == "Buying AAPL."
    assert done["trades"] == [
        {"ticker": "AAPL", "side": "buy", "quantity": 5, "status": "executed", "reason": None}
    ]

    history = await get_chat()
    assert history[-1]["actions"]["trades"] == done["trades"]


async def test_post_chat_actually_calls_execute_trade_with_correct_args(monkeypatch):
    # Explicit regression guard (reported bug: trades appearing in the done
    # event without ever having been run through execute_trade at all) - a
    # spy proves the real annotation loop invoked execute_trade, not just
    # that its result happened to look right.
    calls = []

    async def _stream(messages, user_message):
        yield "Buying AAPL."

    async def _actions(messages, user_message):
        return ActionsResult(trades=[TradeAction(ticker="AAPL", side="buy", quantity=5)])

    async def _spy_execute_trade(app_state, ticker, side, quantity, user_id="default"):
        calls.append((ticker, side, quantity))
        return {"ticker": ticker, "side": side, "quantity": quantity, "price": 100.0, "executed_at": "now"}

    monkeypatch.setattr(chat_module, "stream_chat_message", _stream)
    monkeypatch.setattr(chat_module, "get_actions", _actions)
    monkeypatch.setattr(chat_module, "execute_trade", _spy_execute_trade)

    events = await _collect_events(_state(prices={"AAPL": 100.0}), "buy 5 AAPL")

    assert calls == [("AAPL", "buy", 5)]
    done = _done(events)
    assert done["trades"] == [
        {"ticker": "AAPL", "side": "buy", "quantity": 5, "status": "executed", "reason": None}
    ]


async def test_post_chat_annotates_trade_error(monkeypatch):
    async def _stream(messages, user_message):
        yield "Buying AAPL."

    async def _actions(messages, user_message):
        return ActionsResult(trades=[TradeAction(ticker="AAPL", side="buy", quantity=5)])

    async def _raise_trade_error(app_state, ticker, side, quantity, user_id="default"):
        raise TradeError("insufficient cash")

    monkeypatch.setattr(chat_module, "stream_chat_message", _stream)
    monkeypatch.setattr(chat_module, "get_actions", _actions)
    monkeypatch.setattr(chat_module, "execute_trade", _raise_trade_error)

    events = await _collect_events(_state(prices={"AAPL": 100.0}), "buy 5 AAPL")

    done = _done(events)
    assert done["trades"] == [
        {
            "ticker": "AAPL",
            "side": "buy",
            "quantity": 5,
            "status": "error",
            "reason": "insufficient cash",
        }
    ]


async def test_post_chat_executes_watchlist_change_and_annotates_success(monkeypatch):
    async def _stream(messages, user_message):
        yield "Adding PYPL."

    async def _actions(messages, user_message):
        return ActionsResult(watchlist_changes=[WatchlistChangeAction(ticker="PYPL", action="add")])

    async def _fake_add(app_state, ticker, user_id="default"):
        return None

    monkeypatch.setattr(chat_module, "stream_chat_message", _stream)
    monkeypatch.setattr(chat_module, "get_actions", _actions)
    monkeypatch.setattr(chat_module, "add_watchlist_ticker", _fake_add)

    events = await _collect_events(_state(), "add PYPL")

    done = _done(events)
    assert done["watchlist_changes"] == [
        {"ticker": "PYPL", "action": "add", "status": "executed", "reason": None}
    ]


async def test_post_chat_annotates_watchlist_error(monkeypatch):
    async def _stream(messages, user_message):
        yield "Adding ZZZZ."

    async def _actions(messages, user_message):
        return ActionsResult(watchlist_changes=[WatchlistChangeAction(ticker="ZZZZ", action="add")])

    async def _raise_watchlist_error(app_state, ticker, user_id="default"):
        raise WatchlistError("unrecognized ticker")

    monkeypatch.setattr(chat_module, "stream_chat_message", _stream)
    monkeypatch.setattr(chat_module, "get_actions", _actions)
    monkeypatch.setattr(chat_module, "add_watchlist_ticker", _raise_watchlist_error)

    events = await _collect_events(_state(), "add ZZZZ")

    done = _done(events)
    assert done["watchlist_changes"] == [
        {
            "ticker": "ZZZZ",
            "action": "add",
            "status": "error",
            "reason": "unrecognized ticker",
        }
    ]


async def test_post_chat_persists_user_and_assistant_messages(monkeypatch):
    async def _stream(messages, user_message):
        yield "Just chatting"

    async def _actions(messages, user_message):
        return ActionsResult()

    monkeypatch.setattr(chat_module, "stream_chat_message", _stream)
    monkeypatch.setattr(chat_module, "get_actions", _actions)

    await _collect_events(_state(), "how am I doing?")

    history = await get_chat()
    assert [m["role"] for m in history] == ["user", "assistant"]
    assert history[0]["content"] == "how am I doing?"
    assert history[1]["content"] == "Just chatting"


async def test_post_chat_actions_failure_still_emits_done_with_empty_actions(monkeypatch):
    async def _stream(messages, user_message):
        yield "Here's my answer."

    async def _raise(messages, user_message):
        raise RuntimeError("boom")

    monkeypatch.setattr(chat_module, "stream_chat_message", _stream)
    monkeypatch.setattr(chat_module, "get_actions", _raise)

    events = await _collect_events(_state(), "buy 5 AAPL")

    done = _done(events)
    assert done["message"] == "Here's my answer."
    assert done["trades"] == []
    assert done["watchlist_changes"] == []


async def test_post_chat_unexpected_execute_trade_error_still_emits_done(monkeypatch):
    # Regression: reported live as a dropped connection with no `done` event
    # at all under concurrent load (plausibly SQLite lock contention) -
    # execute_trade raising something other than TradeError must not crash
    # the whole stream silently.
    async def _stream(messages, user_message):
        yield "Buying AAPL."

    async def _actions(messages, user_message):
        return ActionsResult(trades=[TradeAction(ticker="AAPL", side="buy", quantity=5)])

    async def _raise_unexpected(app_state, ticker, side, quantity, user_id="default"):
        raise RuntimeError("database is locked")

    monkeypatch.setattr(chat_module, "stream_chat_message", _stream)
    monkeypatch.setattr(chat_module, "get_actions", _actions)
    monkeypatch.setattr(chat_module, "execute_trade", _raise_unexpected)

    events = await _collect_events(_state(prices={"AAPL": 100.0}), "buy 5 AAPL")

    done = _done(events)
    assert done["message"] == "Buying AAPL."
    assert done["trades"] == [
        {
            "ticker": "AAPL",
            "side": "buy",
            "quantity": 5,
            "status": "error",
            "reason": "unexpected error",
        }
    ]


async def test_post_chat_earlier_trade_annotation_survives_a_later_unexpected_error(monkeypatch):
    # A real fill already happened for the first trade before the second one
    # hits an unexpected error - that must still show up as "executed", not
    # get lost because a later item in the same batch blew up.
    async def _stream(messages, user_message):
        yield "Selling AAPL and buying MSFT."

    async def _actions(messages, user_message):
        return ActionsResult(
            trades=[
                TradeAction(ticker="AAPL", side="sell", quantity=1),
                TradeAction(ticker="MSFT", side="buy", quantity=1),
            ]
        )

    async def _flaky_execute_trade(app_state, ticker, side, quantity, user_id="default"):
        if ticker == "MSFT":
            raise RuntimeError("database is locked")
        return {"ticker": ticker, "side": side, "quantity": quantity, "price": 100.0, "executed_at": "now"}

    monkeypatch.setattr(chat_module, "stream_chat_message", _stream)
    monkeypatch.setattr(chat_module, "get_actions", _actions)
    monkeypatch.setattr(chat_module, "execute_trade", _flaky_execute_trade)

    events = await _collect_events(_state(prices={"AAPL": 100.0, "MSFT": 100.0}), "sell AAPL buy MSFT")

    done = _done(events)
    assert done["trades"] == [
        {"ticker": "AAPL", "side": "sell", "quantity": 1, "status": "executed", "reason": None},
        {"ticker": "MSFT", "side": "buy", "quantity": 1, "status": "error", "reason": "unexpected error"},
    ]


async def test_post_chat_persistence_failure_still_emits_done(monkeypatch):
    async def _stream(messages, user_message):
        yield "Just chatting"

    async def _actions(messages, user_message):
        return ActionsResult()

    async def _raise(*args, **kwargs):
        raise RuntimeError("database is locked")

    monkeypatch.setattr(chat_module, "stream_chat_message", _stream)
    monkeypatch.setattr(chat_module, "get_actions", _actions)
    monkeypatch.setattr(chat_module, "insert_message", _raise)

    events = await _collect_events(_state(), "how am I doing?")

    done = _done(events)
    assert done["message"] == "Just chatting"


async def test_post_chat_unexpected_stream_error_still_emits_done_with_fallback_message(monkeypatch):
    async def _stream(messages, user_message):
        raise RuntimeError("boom")
        yield  # pragma: no cover - unreachable; keeps this an async generator

    async def _actions(messages, user_message):
        return ActionsResult()

    monkeypatch.setattr(chat_module, "stream_chat_message", _stream)
    monkeypatch.setattr(chat_module, "get_actions", _actions)

    events = await _collect_events(_state(), "hi")

    assert _deltas(events) == [FALLBACK_MESSAGE]
    done = _done(events)
    assert done["message"] == FALLBACK_MESSAGE
