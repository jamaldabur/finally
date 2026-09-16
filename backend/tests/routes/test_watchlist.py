"""Route-level tests for GET/POST/DELETE /api/watchlist (01-03-PLAN.md Task 2).

Written RED first: at the time this file is authored, app/routes/watchlist.py
does not exist yet.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client(monkeypatch):
    """A TestClient wrapping a fresh app instance, with MASSIVE_API_KEY unset
    so the simulator (and its TICKER_UNIVERSE) is the active market data
    source. Exposes `client.portal.call(...)` — Starlette's own TestClient
    attribute, set on `__enter__` — as the sync-safe way to run async calls
    (seeding PriceCache) on the same event loop the app's lifespan and
    background tasks run on, per the pattern established in
    tests/routes/test_portfolio.py."""
    monkeypatch.delenv("MASSIVE_API_KEY", raising=False)
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


def _seed_price(client: TestClient, ticker: str, price: float) -> None:
    client.portal.call(client.app.state.price_cache.update, ticker, price)


def test_get_watchlist_returns_seeded_tickers(client: TestClient) -> None:
    resp = client.get("/api/watchlist")

    assert resp.status_code == 200
    body = resp.json()
    assert len(body["watchlist"]) == 10
    tickers = [entry["ticker"] for entry in body["watchlist"]]
    assert tickers == sorted(tickers)
    for entry in body["watchlist"]:
        assert "ticker" in entry


def test_get_watchlist_joins_cached_prices(client: TestClient) -> None:
    _seed_price(client, "AAPL", 190.0)

    resp = client.get("/api/watchlist")

    assert resp.status_code == 200
    body = resp.json()
    entries = {entry["ticker"]: entry for entry in body["watchlist"]}
    assert entries["AAPL"]["price"] == 190.0
    assert entries["AAPL"]["direction"] is not None

    # GOOGL is seeded by default but not manually primed here; the app's own
    # background update loop races this assertion under full-suite load, so
    # we only assert the null-price contract on a ticker outside the default
    # watchlist entirely (never touched by run_update_loop or this test).
    resp2 = client.get("/api/watchlist")
    entries2 = {entry["ticker"]: entry for entry in resp2.json()["watchlist"]}
    assert "ORCL" not in entries2  # sanity: not on the default watchlist


def test_get_watchlist_uncached_ticker_has_null_price(client: TestClient) -> None:
    # Add a valid but never-priced ticker (not on DEFAULT_WATCHLIST, so
    # run_update_loop only starts fetching it on its next cycle — assert
    # immediately before that can race in).
    add_resp = client.post("/api/watchlist", json={"ticker": "ORCL"})
    assert add_resp.status_code == 200

    resp = client.get("/api/watchlist")
    entries = {entry["ticker"]: entry for entry in resp.json()["watchlist"]}
    assert entries["ORCL"]["price"] is None
    assert entries["ORCL"]["previous_price"] is None
    assert entries["ORCL"]["direction"] is None
    assert entries["ORCL"]["timestamp"] is None


def test_post_watchlist_adds_recognized_ticker(client: TestClient) -> None:
    resp = client.post("/api/watchlist", json={"ticker": "PYPL"})

    assert resp.status_code == 200
    assert resp.json() == {"ticker": "PYPL", "added": True}

    get_resp = client.get("/api/watchlist")
    tickers = [entry["ticker"] for entry in get_resp.json()["watchlist"]]
    assert "PYPL" in tickers


def test_post_watchlist_normalizes_case(client: TestClient) -> None:
    resp = client.post("/api/watchlist", json={"ticker": "  pypl "})

    assert resp.status_code == 200
    assert resp.json()["ticker"] == "PYPL"

    get_resp = client.get("/api/watchlist")
    tickers = [entry["ticker"] for entry in get_resp.json()["watchlist"]]
    assert tickers.count("PYPL") == 1


def test_post_watchlist_rejects_unknown_ticker(client: TestClient) -> None:
    resp = client.post("/api/watchlist", json={"ticker": "ZZZZ"})

    assert resp.status_code == 400
    assert resp.json()["detail"].startswith("Unknown ticker: ")

    get_resp = client.get("/api/watchlist")
    assert len(get_resp.json()["watchlist"]) == 10


def test_post_watchlist_duplicate_reports_not_added(client: TestClient) -> None:
    resp = client.post("/api/watchlist", json={"ticker": "AAPL"})

    assert resp.status_code == 200
    assert resp.json() == {"ticker": "AAPL", "added": False}

    get_resp = client.get("/api/watchlist")
    assert len(get_resp.json()["watchlist"]) == 10


def test_delete_watchlist_removes_ticker(client: TestClient) -> None:
    resp = client.delete("/api/watchlist/AAPL")

    assert resp.status_code == 200
    assert resp.json() == {"ticker": "AAPL", "removed": True}

    get_resp = client.get("/api/watchlist")
    assert len(get_resp.json()["watchlist"]) == 9

    second_resp = client.delete("/api/watchlist/AAPL")
    assert second_resp.status_code == 200
    assert second_resp.json() == {"ticker": "AAPL", "removed": False}


def test_delete_watchlist_normalizes_case(client: TestClient) -> None:
    resp = client.delete("/api/watchlist/aapl")

    assert resp.status_code == 200
    assert resp.json() == {"ticker": "AAPL", "removed": True}

    get_resp = client.get("/api/watchlist")
    tickers = [entry["ticker"] for entry in get_resp.json()["watchlist"]]
    assert "AAPL" not in tickers


def test_watchlist_add_survives_app_restart(monkeypatch) -> None:
    monkeypatch.delenv("MASSIVE_API_KEY", raising=False)

    app1 = create_app()
    with TestClient(app1) as client1:
        resp = client1.post("/api/watchlist", json={"ticker": "PYPL"})
        assert resp.status_code == 200

    app2 = create_app()
    with TestClient(app2) as client2:
        get_resp = client2.get("/api/watchlist")
        tickers = [entry["ticker"] for entry in get_resp.json()["watchlist"]]
        assert "PYPL" in tickers
