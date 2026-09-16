"""Route-level tests for POST /api/portfolio/trade — the walking-skeleton
tracer slice (01-01-PLAN.md Task 2).

Written RED first: at the time this file is authored, `app/db/users_profile.py`,
`app/db/positions.py`, `app/db/trades.py`, `app/portfolio/service.py`, and
`app/routes/portfolio.py` do not exist yet.
"""

import pytest
from fastapi.testclient import TestClient

from app.db import positions as positions_module
from app.db import trades as trades_module
from app.db import users_profile as users_profile_module
from app.main import create_app


@pytest.fixture
def client(monkeypatch):
    """A TestClient wrapping a fresh app instance, with MASSIVE_API_KEY unset
    so the simulator is the active market data source. Exposes
    `client.portal.call(...)` — Starlette's own TestClient attribute, set on
    `__enter__` — as the sync-safe way to run async calls (seeding
    PriceCache, reading DB state) on the SAME event loop the app's lifespan
    and background tasks run on. This avoids the cross-event-loop hazard of
    awaiting directly from a pytest-asyncio test coroutine while the app
    itself lives inside TestClient's dedicated portal thread."""
    monkeypatch.delenv("MASSIVE_API_KEY", raising=False)
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


def _seed_price(client: TestClient, ticker: str, price: float) -> None:
    client.portal.call(client.app.state.price_cache.update, ticker, price)


def test_buy_fills_at_cached_price_and_persists(client: TestClient) -> None:
    _seed_price(client, "AAPL", 100.0)

    resp = client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "side": "buy", "quantity": 10},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["trade"]["price"] == 100.0
    assert body["trade"]["side"] == "buy"
    assert body["cash_balance"] == 9000.0
    assert body["position"] == {"ticker": "AAPL", "quantity": 10.0, "avg_cost": 100.0}


def test_second_buy_weights_avg_cost(client: TestClient) -> None:
    _seed_price(client, "AAPL", 100.0)
    resp1 = client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "side": "buy", "quantity": 10},
    )
    assert resp1.status_code == 200

    _seed_price(client, "AAPL", 120.0)
    resp2 = client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "side": "buy", "quantity": 10},
    )

    assert resp2.status_code == 200
    body = resp2.json()
    assert body["position"]["quantity"] == 20.0
    assert body["position"]["avg_cost"] == 110.0


def test_buy_writes_one_trades_row_per_fill(client: TestClient) -> None:
    _seed_price(client, "AAPL", 100.0)
    client.post("/api/portfolio/trade", json={"ticker": "AAPL", "side": "buy", "quantity": 10})
    _seed_price(client, "AAPL", 120.0)
    client.post("/api/portfolio/trade", json={"ticker": "AAPL", "side": "buy", "quantity": 10})

    trades = client.portal.call(trades_module.get_trades)

    assert len(trades) == 2
    assert len({t.id for t in trades}) == 2


def test_buy_unpriced_ticker_is_rejected(client: TestClient) -> None:
    # ORCL is a member of TICKER_UNIVERSE (so is_valid_ticker() accepts it)
    # but is not in DEFAULT_WATCHLIST, so run_update_loop never fetches a
    # price for it and PriceCache.get("ORCL") is None.
    resp = client.post(
        "/api/portfolio/trade",
        json={"ticker": "ORCL", "side": "buy", "quantity": 1},
    )

    assert resp.status_code == 400
    assert resp.json()["detail"].startswith("No live price available for")


def test_buy_zero_or_negative_quantity_is_422(client: TestClient) -> None:
    resp_zero = client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "side": "buy", "quantity": 0},
    )
    assert resp_zero.status_code == 422

    resp_negative = client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "side": "buy", "quantity": -5},
    )
    assert resp_negative.status_code == 422


def test_buy_beyond_cash_is_rejected(client: TestClient) -> None:
    _seed_price(client, "AAPL", 100.0)

    resp = client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "side": "buy", "quantity": 1000},
    )

    assert resp.status_code == 400
    assert resp.json()["detail"].startswith("Insufficient cash: ")

    assert client.portal.call(users_profile_module.get_cash_balance) == 10000.0
    assert client.portal.call(positions_module.get_position, "AAPL") is None
    assert client.portal.call(trades_module.get_trades) == []
