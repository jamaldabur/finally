import httpx
import respx
from fastapi.testclient import TestClient

from app.main import create_app
from app.market.cache import PriceCache
from app.market.massive import MassiveMarketDataSource
from app.market.simulator import SimulatorMarketDataSource


def test_lifespan_wires_simulator_by_default(monkeypatch, tmp_path):
    monkeypatch.setattr("app.db.connection.DB_PATH", tmp_path / "finally.db")
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
    monkeypatch.setattr("app.db.connection.DB_PATH", tmp_path / "finally.db")
    monkeypatch.setenv("MASSIVE_API_KEY", "test-key")

    app = create_app()
    with TestClient(app):
        assert isinstance(app.state.market_source, MassiveMarketDataSource)
