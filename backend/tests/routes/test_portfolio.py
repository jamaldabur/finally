"""Route-level tests for POST /api/portfolio/trade — the walking-skeleton
tracer slice (01-01-PLAN.md Task 2).

Written RED first: at the time this file is authored, `app/db/users_profile.py`,
`app/db/positions.py`, `app/db/trades.py`, `app/portfolio/service.py`, and
`app/routes/portfolio.py` do not exist yet.
"""

import asyncio

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
    # CSCO is a member of TICKER_UNIVERSE but not DEFAULT_WATCHLIST, so
    # run_update_loop (which only fetches watchlist tickers) never races our
    # manually-seeded price — see test_buy_unpriced_ticker_is_rejected for
    # the same reasoning applied to an intentionally-unseeded ticker.
    _seed_price(client, "CSCO", 100.0)

    resp = client.post(
        "/api/portfolio/trade",
        json={"ticker": "CSCO", "side": "buy", "quantity": 10},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["trade"]["price"] == 100.0
    assert body["trade"]["side"] == "buy"
    assert body["cash_balance"] == 9000.0
    assert body["position"] == {"ticker": "CSCO", "quantity": 10.0, "avg_cost": 100.0}


def test_second_buy_weights_avg_cost(client: TestClient) -> None:
    _seed_price(client, "CSCO", 100.0)
    resp1 = client.post(
        "/api/portfolio/trade",
        json={"ticker": "CSCO", "side": "buy", "quantity": 10},
    )
    assert resp1.status_code == 200

    _seed_price(client, "CSCO", 120.0)
    resp2 = client.post(
        "/api/portfolio/trade",
        json={"ticker": "CSCO", "side": "buy", "quantity": 10},
    )

    assert resp2.status_code == 200
    body = resp2.json()
    assert body["position"]["quantity"] == 20.0
    assert body["position"]["avg_cost"] == 110.0


def test_buy_writes_one_trades_row_per_fill(client: TestClient) -> None:
    _seed_price(client, "CSCO", 100.0)
    client.post("/api/portfolio/trade", json={"ticker": "CSCO", "side": "buy", "quantity": 10})
    _seed_price(client, "CSCO", 120.0)
    client.post("/api/portfolio/trade", json={"ticker": "CSCO", "side": "buy", "quantity": 10})

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
    _seed_price(client, "CSCO", 100.0)

    resp = client.post(
        "/api/portfolio/trade",
        json={"ticker": "CSCO", "side": "buy", "quantity": 1000},
    )

    assert resp.status_code == 400
    assert resp.json()["detail"].startswith("Insufficient cash: ")

    assert client.portal.call(users_profile_module.get_cash_balance) == 10000.0
    assert client.portal.call(positions_module.get_position, "CSCO") is None
    assert client.portal.call(trades_module.get_trades) == []


def test_sell_credits_cash_and_reduces_position(client: TestClient) -> None:
    # CSCO (not on DEFAULT_WATCHLIST) avoids the run_update_loop race — see
    # test_buy_fills_at_cached_price_and_persists.
    _seed_price(client, "CSCO", 100.0)
    buy_resp = client.post(
        "/api/portfolio/trade",
        json={"ticker": "CSCO", "side": "buy", "quantity": 10},
    )
    assert buy_resp.status_code == 200

    _seed_price(client, "CSCO", 120.0)
    resp = client.post(
        "/api/portfolio/trade",
        json={"ticker": "CSCO", "side": "sell", "quantity": 4},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["trade"]["side"] == "sell"
    assert body["trade"]["price"] == 120.0
    assert body["cash_balance"] == 9480.0
    assert body["position"] == {"ticker": "CSCO", "quantity": 6.0, "avg_cost": 100.0}


def test_sell_all_closes_position(client: TestClient) -> None:
    _seed_price(client, "CSCO", 100.0)
    client.post("/api/portfolio/trade", json={"ticker": "CSCO", "side": "buy", "quantity": 10})

    _seed_price(client, "CSCO", 120.0)
    resp = client.post(
        "/api/portfolio/trade",
        json={"ticker": "CSCO", "side": "sell", "quantity": 10},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["position"] is None
    assert client.portal.call(positions_module.get_position, "CSCO") is None


def test_sell_fractional_remainder_keeps_row(client: TestClient) -> None:
    _seed_price(client, "CSCO", 100.0)
    client.post("/api/portfolio/trade", json={"ticker": "CSCO", "side": "buy", "quantity": 1.5})

    resp = client.post(
        "/api/portfolio/trade",
        json={"ticker": "CSCO", "side": "sell", "quantity": 1.0},
    )

    assert resp.status_code == 200
    position = client.portal.call(positions_module.get_position, "CSCO")
    assert position is not None
    assert position.quantity == 0.5
    assert position.avg_cost == 100.0


def test_sell_records_trade_row(client: TestClient) -> None:
    _seed_price(client, "CSCO", 100.0)
    client.post("/api/portfolio/trade", json={"ticker": "CSCO", "side": "buy", "quantity": 10})
    client.post("/api/portfolio/trade", json={"ticker": "CSCO", "side": "sell", "quantity": 4})

    trades = client.portal.call(trades_module.get_trades)

    assert [t.side for t in trades] == ["buy", "sell"]


def test_sell_more_than_held_is_rejected(client: TestClient) -> None:
    _seed_price(client, "CSCO", 100.0)
    client.post("/api/portfolio/trade", json={"ticker": "CSCO", "side": "buy", "quantity": 10})

    resp = client.post(
        "/api/portfolio/trade",
        json={"ticker": "CSCO", "side": "sell", "quantity": 11},
    )

    assert resp.status_code == 400
    assert resp.json()["detail"].startswith("Insufficient shares: ")

    position = client.portal.call(positions_module.get_position, "CSCO")
    assert position is not None
    assert position.quantity == 10.0
    assert client.portal.call(users_profile_module.get_cash_balance) == 9000.0
    assert len(client.portal.call(trades_module.get_trades)) == 1


def test_sell_with_no_position_is_rejected(client: TestClient) -> None:
    _seed_price(client, "CSCO", 100.0)

    resp = client.post(
        "/api/portfolio/trade",
        json={"ticker": "CSCO", "side": "sell", "quantity": 1},
    )

    assert resp.status_code == 400
    assert resp.json()["detail"].startswith("Insufficient shares: ")


def test_sell_all_with_float_imprecision_succeeds(client: TestClient) -> None:
    _seed_price(client, "CSCO", 100.0)
    for _ in range(3):
        client.post("/api/portfolio/trade", json={"ticker": "CSCO", "side": "buy", "quantity": 0.1})

    resp = client.post(
        "/api/portfolio/trade",
        json={"ticker": "CSCO", "side": "sell", "quantity": 0.30000000000000004},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["position"] is None
    assert client.portal.call(positions_module.get_position, "CSCO") is None


def test_get_portfolio_returns_locked_shape(client: TestClient) -> None:
    resp = client.get("/api/portfolio")

    assert resp.status_code == 200
    body = resp.json()
    assert body["cash_balance"] == 10000.0
    assert body["positions"] == []
    assert body["positions_value"] == 0.0
    assert body["total_value"] == 10000.0
    assert body["total_unrealized_pnl"] == 0.0


def test_get_portfolio_reflects_a_trade(client: TestClient) -> None:
    _seed_price(client, "CSCO", 100.0)
    client.post("/api/portfolio/trade", json={"ticker": "CSCO", "side": "buy", "quantity": 10})

    resp = client.get("/api/portfolio")

    assert resp.status_code == 200
    body = resp.json()
    assert len(body["positions"]) == 1
    position = body["positions"][0]
    assert position["ticker"] == "CSCO"
    assert position["quantity"] == 10.0
    assert position["avg_cost"] == 100.0
    assert body["total_value"] == body["cash_balance"] + body["positions_value"]


def test_get_portfolio_positions_sorted_by_ticker(client: TestClient) -> None:
    _seed_price(client, "CSCO", 100.0)
    _seed_price(client, "ORCL", 50.0)
    client.post("/api/portfolio/trade", json={"ticker": "ORCL", "side": "buy", "quantity": 1})
    client.post("/api/portfolio/trade", json={"ticker": "CSCO", "side": "buy", "quantity": 1})

    resp = client.get("/api/portfolio")

    assert resp.status_code == 200
    tickers = [p["ticker"] for p in resp.json()["positions"]]
    assert tickers == sorted(tickers)
    assert tickers == ["CSCO", "ORCL"]


def test_get_portfolio_history_returns_snapshots(client: TestClient) -> None:
    resp = client.get("/api/portfolio/history")

    assert resp.status_code == 200
    body = resp.json()
    assert "snapshots" in body
    assert isinstance(body["snapshots"], list)
    for snapshot in body["snapshots"]:
        assert "total_value" in snapshot
        assert "recorded_at" in snapshot
    recorded_ats = [s["recorded_at"] for s in body["snapshots"]]
    assert recorded_ats == sorted(recorded_ats)


def test_rejected_buy_leaves_no_partial_write(client: TestClient) -> None:
    _seed_price(client, "CSCO", 100.0)
    first_resp = client.post(
        "/api/portfolio/trade",
        json={"ticker": "CSCO", "side": "buy", "quantity": 10},
    )
    assert first_resp.status_code == 200

    cash_before = client.portal.call(users_profile_module.get_cash_balance)
    position_before = client.portal.call(positions_module.get_position, "CSCO")
    trade_count_before = len(client.portal.call(trades_module.get_trades))

    resp = client.post(
        "/api/portfolio/trade",
        json={"ticker": "CSCO", "side": "buy", "quantity": 1000},
    )

    assert resp.status_code == 400
    assert client.portal.call(users_profile_module.get_cash_balance) == cash_before
    assert client.portal.call(positions_module.get_position, "CSCO") == position_before
    assert len(client.portal.call(trades_module.get_trades)) == trade_count_before


def test_trade_records_an_immediate_snapshot(client: TestClient) -> None:
    # The snapshot loop records at startup (before its first sleep), so
    # every TestClient-backed test begins with one snapshot already
    # present — assertions here are relative (grew by one), not absolute.
    # asyncio.create_task() only schedules the loop; it isn't guaranteed to
    # have run its first iteration by the time this synchronous test issues
    # its first request, so give the event loop one tick via portal.call to
    # let that startup write land before measuring the baseline (avoids the
    # same background-task race documented in 01-01-SUMMARY.md/01-03-SUMMARY.md).
    client.portal.call(asyncio.sleep, 0.05)
    _seed_price(client, "CSCO", 100.0)
    snapshots_before = client.get("/api/portfolio/history").json()["snapshots"]

    resp = client.post(
        "/api/portfolio/trade",
        json={"ticker": "CSCO", "side": "buy", "quantity": 10},
    )
    assert resp.status_code == 200

    snapshots_after = client.get("/api/portfolio/history").json()["snapshots"]
    portfolio_after = client.get("/api/portfolio").json()

    assert len(snapshots_after) == len(snapshots_before) + 1
    assert snapshots_after[-1]["total_value"] == portfolio_after["total_value"]


def test_rejected_trade_records_no_snapshot(client: TestClient) -> None:
    client.portal.call(asyncio.sleep, 0.05)
    _seed_price(client, "CSCO", 100.0)
    snapshots_before = client.get("/api/portfolio/history").json()["snapshots"]

    resp = client.post(
        "/api/portfolio/trade",
        json={"ticker": "CSCO", "side": "buy", "quantity": 1000},
    )
    assert resp.status_code == 400

    snapshots_after = client.get("/api/portfolio/history").json()["snapshots"]

    assert len(snapshots_after) == len(snapshots_before)


def test_lifespan_cancels_the_snapshot_task(monkeypatch) -> None:
    monkeypatch.delenv("MASSIVE_API_KEY", raising=False)
    app = create_app()
    with TestClient(app) as test_client:
        snapshot_task = test_client.app.state.snapshot_task
        assert not snapshot_task.done()

    assert snapshot_task.cancelled() or snapshot_task.done()

