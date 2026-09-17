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
from app.main import create_app


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
