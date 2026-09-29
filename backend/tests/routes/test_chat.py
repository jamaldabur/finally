"""Route-level tests for POST /api/chat — the tracer slice proving the whole
agentic chat loop end-to-end (03-01-PLAN.md Task 2): a message goes to the
LLM (mock here), comes back as validated structured output, and a requested
trade or watchlist change executes through the exact same shared functions
the trade bar / watchlist routes use, annotated with its real outcome.

Mirrors backend/tests/routes/test_portfolio.py's `client` fixture and
`_seed_price` helper verbatim, and seeds prices on CSCO (in TICKER_UNIVERSE,
not on DEFAULT_WATCHLIST) to avoid the run_update_loop race documented
there.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import app.llm.client as llm_client_module
import app.routes.chat as chat_route_module
from app.db import chat_messages as chat_messages_module
from app.main import create_app
from app.portfolio.service import PortfolioView


@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv("MASSIVE_API_KEY", raising=False)
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


def _seed_price(client: TestClient, ticker: str, price: float) -> None:
    client.portal.call(client.app.state.price_cache.update, ticker, price)


def test_chat_trade_auto_executes(client: TestClient, monkeypatch) -> None:
    monkeypatch.setenv("LLM_MOCK", "true")
    _seed_price(client, "CSCO", 100.0)

    resp = client.post("/api/chat", json={"message": "buy 5 CSCO"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["trades"][0]["outcome"] == "executed"
    assert body["trades"][0]["price"] == 100.0

    portfolio_resp = client.get("/api/portfolio")
    assert portfolio_resp.status_code == 200
    portfolio_body = portfolio_resp.json()
    assert portfolio_body["cash_balance"] == 9500.0
    positions = {p["ticker"]: p for p in portfolio_body["positions"]}
    assert positions["CSCO"]["quantity"] == 5.0


def test_post_chat_returns_structured_response(client: TestClient, monkeypatch) -> None:
    monkeypatch.setenv("LLM_MOCK", "true")

    resp = client.post("/api/chat", json={"message": "what is my portfolio worth?"})

    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {"message", "trades", "watchlist_changes"}
    assert body["message"]
    assert body["trades"] == []
    assert body["watchlist_changes"] == []


def test_post_chat_rejects_blank_message(client: TestClient, monkeypatch) -> None:
    monkeypatch.setenv("LLM_MOCK", "true")

    resp_empty = client.post("/api/chat", json={"message": ""})
    assert resp_empty.status_code == 422

    resp_blank = client.post("/api/chat", json={"message": "   "})
    assert resp_blank.status_code == 422


def test_chat_watchlist_change_auto_executes(client: TestClient, monkeypatch) -> None:
    monkeypatch.setenv("LLM_MOCK", "true")

    resp = client.post("/api/chat", json={"message": "add PYPL to my watchlist"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["watchlist_changes"][0]["outcome"] == "executed"

    watchlist_resp = client.get("/api/watchlist")
    tickers = [entry["ticker"] for entry in watchlist_resp.json()["watchlist"]]
    assert "PYPL" in tickers


def test_chat_action_annotated_on_insufficient_cash(client: TestClient, monkeypatch) -> None:
    monkeypatch.setenv("LLM_MOCK", "true")
    _seed_price(client, "CSCO", 100.0)

    resp = client.post("/api/chat", json={"message": "buy 1000 CSCO"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["trades"][0]["outcome"] == "error"
    assert body["trades"][0]["reason"]

    portfolio_resp = client.get("/api/portfolio")
    assert portfolio_resp.json()["cash_balance"] == 10000.0


def test_chat_with_llm_mock(client: TestClient, monkeypatch) -> None:
    monkeypatch.setenv("LLM_MOCK", "true")

    def _boom(*args, **kwargs):
        raise AssertionError("real LLM call must not happen under LLM_MOCK=true")

    monkeypatch.setattr(llm_client_module, "acompletion", _boom)

    resp = client.post("/api/chat", json={"message": "buy 1 CSCO"})

    assert resp.status_code == 200


def test_get_chat_on_empty_database_returns_empty_history(client: TestClient) -> None:
    """Test 6: GET /api/chat on a fresh database returns 200 with no
    messages."""
    resp = client.get("/api/chat")

    assert resp.status_code == 200
    assert resp.json() == {"messages": []}


def test_get_chat_hydrates_history(client: TestClient, monkeypatch) -> None:
    """Test 7 — name referenced verbatim by 03-VALIDATION.md's Per-Task
    Verification Map. After one POST /api/chat, GET /api/chat returns
    exactly two messages: the user message, then the assistant message with
    its annotated actions."""
    monkeypatch.setenv("LLM_MOCK", "true")

    post_resp = client.post("/api/chat", json={"message": "what is my portfolio worth?"})
    assert post_resp.status_code == 200

    history_resp = client.get("/api/chat")
    assert history_resp.status_code == 200
    body = history_resp.json()

    assert len(body["messages"]) == 2
    assert body["messages"][0]["role"] == "user"
    assert body["messages"][0]["content"] == "what is my portfolio worth?"
    assert body["messages"][1]["role"] == "assistant"
    assert "trades" in body["messages"][1]
    assert "watchlist_changes" in body["messages"][1]


def test_get_chat_carries_executed_trade_outcome(client: TestClient, monkeypatch) -> None:
    """Test 8: after a POST /api/chat that executes a trade, the assistant
    message from GET /api/chat carries that trade with outcome=="executed"
    and the same price the POST response reported."""
    monkeypatch.setenv("LLM_MOCK", "true")
    _seed_price(client, "CSCO", 100.0)

    post_resp = client.post("/api/chat", json={"message": "buy 5 CSCO"})
    post_price = post_resp.json()["trades"][0]["price"]

    history_resp = client.get("/api/chat")
    assistant_message = history_resp.json()["messages"][1]

    assert assistant_message["trades"][0]["outcome"] == "executed"
    assert assistant_message["trades"][0]["price"] == post_price


def test_get_chat_degrades_unparseable_actions_to_empty_lists(client: TestClient) -> None:
    """Test 9: a row whose actions column holds unparseable text yields
    empty trades/watchlist_changes for that message, and GET /api/chat
    still returns 200."""
    client.portal.call(
        chat_messages_module.insert_message, "assistant", "some reply", "not json"
    )

    resp = client.get("/api/chat")

    assert resp.status_code == 200
    messages = resp.json()["messages"]
    assert len(messages) == 1
    assert messages[0]["trades"] == []
    assert messages[0]["watchlist_changes"] == []


def test_get_chat_never_returns_orphan_user_message(client: TestClient, monkeypatch) -> None:
    """Test 10: GET /api/chat returns no user message without its assistant
    reply — after a POST, the count of returned messages is even."""
    monkeypatch.setenv("LLM_MOCK", "true")

    client.post("/api/chat", json={"message": "how am I doing?"})

    resp = client.get("/api/chat")
    messages = resp.json()["messages"]

    assert len(messages) % 2 == 0


def test_build_messages_caps_history_at_prompt_history_limit() -> None:
    """Test 9: build_messages() with a 30-item history includes at most
    PROMPT_HISTORY_LIMIT of the most recent entries, plus the system and
    new-user messages."""
    from app.llm.client import PROMPT_HISTORY_LIMIT, build_messages

    portfolio_view = PortfolioView(
        cash_balance=10000.0,
        positions=[],
        positions_value=0.0,
        total_value=10000.0,
        total_unrealized_pnl=0.0,
    )
    history = [
        {"role": "user" if i % 2 == 0 else "assistant", "content": f"message {i}"}
        for i in range(30)
    ]

    messages = build_messages(
        portfolio_view=portfolio_view,
        watchlist_entries=[],
        history=history,
        user_message="new message",
    )

    # 2 system messages (SYSTEM_PROMPT + portfolio context) + capped history
    # + 1 new user message.
    assert len(messages) == 2 + PROMPT_HISTORY_LIMIT + 1
    history_portion = messages[2:-1]
    assert len(history_portion) == PROMPT_HISTORY_LIMIT
    assert history_portion[0]["content"] == "message 10"
    assert history_portion[-1]["content"] == "message 29"


def test_chat_history_reaches_second_prompt(client: TestClient, monkeypatch) -> None:
    """Test 10: after two POST /api/chat calls, the second call's prompt
    context contains the first exchange's text — history actually reaches
    the model."""
    monkeypatch.setenv("LLM_MOCK", "true")

    captured_history: list[list[dict]] = []
    original_get_chat_response = chat_route_module.get_chat_response

    async def _capture(*, portfolio_view, watchlist_entries, history, user_message):
        captured_history.append(history)
        return await original_get_chat_response(
            portfolio_view=portfolio_view,
            watchlist_entries=watchlist_entries,
            history=history,
            user_message=user_message,
        )

    monkeypatch.setattr(chat_route_module, "get_chat_response", _capture)

    client.post("/api/chat", json={"message": "first message unique text"})
    client.post("/api/chat", json={"message": "second message"})

    assert len(captured_history) == 2
    second_call_contents = [m["content"] for m in captured_history[1]]
    assert any("first message unique text" in c for c in second_call_contents)
