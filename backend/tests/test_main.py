import asyncio
import threading

import httpx
import respx
from fastapi.testclient import TestClient

from app import main
from app.main import create_app
from app.market.base import MarketDataSource
from app.market.cache import PriceCache
from app.market.massive import MassiveMarketDataSource
from app.market.simulator import SimulatorMarketDataSource


def test_lifespan_wires_simulator_by_default(monkeypatch, tmp_path):
    monkeypatch.delenv("MASSIVE_API_KEY", raising=False)

    app = create_app()
    with TestClient(app):
        assert isinstance(app.state.market_source, SimulatorMarketDataSource)
        assert isinstance(app.state.price_cache, PriceCache)


@respx.mock
def test_lifespan_wires_massive_when_api_key_set(monkeypatch, tmp_path):
    # The update loop fires off a real get_prices() call as soon as the
    # background task starts — mock the endpoint so this test never makes an
    # actual network call.
    respx.get(url__regex=r".*/v2/snapshot/.*").mock(
        return_value=httpx.Response(200, json={"tickers": []})
    )
    monkeypatch.setenv("MASSIVE_API_KEY", "test-key")

    app = create_app()
    with TestClient(app):
        assert isinstance(app.state.market_source, MassiveMarketDataSource)


def test_cors_allows_local_dev_frontend_origin(monkeypatch, tmp_path):
    # Plan 02-01: next dev (:3000) must be able to reach this backend (:8000)
    # cross-origin during local development (see CORSMiddleware comment in
    # app/main.py).
    monkeypatch.delenv("MASSIVE_API_KEY", raising=False)

    app = create_app()
    with TestClient(app) as client:
        response = client.get(
            "/api/health", headers={"Origin": "http://localhost:3000"}
        )
        assert (
            response.headers.get("access-control-allow-origin")
            == "http://localhost:3000"
        )


def test_create_app_skips_static_mount_when_directory_absent(monkeypatch, tmp_path):
    # Phase 5 regression lock: Starlette's StaticFiles.__init__ raises
    # RuntimeError when its directory is missing and check_dir is left at
    # its default True. Without the is_dir() guard in create_app(), this
    # would take down all 224+ backend tests on a fresh clone that has
    # never run `npm run build` (static/ only exists inside the built
    # Docker image), and would also break a contributor running the API
    # without ever touching Node.
    monkeypatch.delenv("MASSIVE_API_KEY", raising=False)
    monkeypatch.setattr(main, "STATIC_DIR", tmp_path / "does-not-exist")

    app = main.create_app()

    assert not any(getattr(route, "name", None) == "static" for route in app.routes)


def test_static_mount_serves_index_when_directory_present(monkeypatch, tmp_path):
    # Proves html=True actually serves index.html at the mount root, rather
    # than just asserting the mount exists.
    monkeypatch.delenv("MASSIVE_API_KEY", raising=False)
    marker = "FINALLY_STATIC_MOUNT_MARKER"
    (tmp_path / "index.html").write_text(f"<html><body>{marker}</body></html>")
    monkeypatch.setattr(main, "STATIC_DIR", tmp_path)

    app = main.create_app()
    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert marker in response.text


def test_api_route_wins_over_static_mount(monkeypatch, tmp_path):
    # D-04's ordering rule: routers are registered before the static mount,
    # so a request to /api/health is resolved by the health router and
    # never falls through to the StaticFiles mount at "/", even when that
    # mount is present and populated.
    monkeypatch.delenv("MASSIVE_API_KEY", raising=False)
    (tmp_path / "index.html").write_text("<html><body>static index</body></html>")
    monkeypatch.setattr(main, "STATIC_DIR", tmp_path)

    app = main.create_app()
    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


class _ParkedSource(MarketDataSource):
    """Fake MarketDataSource whose get_prices() parks inside an await for the
    lifetime of the test, so stop() can observe the exact instant shutdown
    calls it — before or after the update loop has actually unwound (WR-01,
    05-REVIEW.md)."""

    def __init__(self) -> None:
        self.in_flight: bool = False
        self.entered = threading.Event()
        self.in_flight_at_stop: bool | None = None
        self.snapshot_task: asyncio.Task[None] | None = None
        self.snapshot_done_at_stop: bool | None = None

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        self.in_flight_at_stop = self.in_flight
        if self.snapshot_task is not None:
            self.snapshot_done_at_stop = self.snapshot_task.done()

    async def get_prices(self, tickers: list[str]) -> dict[str, float]:
        self.in_flight = True
        self.entered.set()
        try:
            await asyncio.sleep(3600)
        finally:
            self.in_flight = False
        return {}

    async def is_valid_ticker(self, ticker: str) -> bool:
        return True


def test_lifespan_awaits_background_tasks_before_stopping_source(monkeypatch, tmp_path):
    # WR-01: Task.cancel() only schedules delivery of CancelledError at the
    # task's next suspension point; without awaiting the cancelled tasks,
    # MassiveMarketDataSource.stop() closes the shared httpx.AsyncClient
    # while run_update_loop may still be inside get_prices() on it.
    monkeypatch.delenv("MASSIVE_API_KEY", raising=False)

    fake = _ParkedSource()
    monkeypatch.setattr(main, "build_market_data_source", lambda: fake)

    app = main.create_app()
    with TestClient(app):
        assert fake.entered.wait(timeout=5) is True
        fake.snapshot_task = app.state.snapshot_task

    assert fake.in_flight_at_stop is False
    assert fake.snapshot_done_at_stop is True
