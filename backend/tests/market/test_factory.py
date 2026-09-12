from app.market.factory import build_market_data_source
from app.market.massive import MassiveMarketDataSource
from app.market.simulator import SimulatorMarketDataSource


def test_no_api_key_selects_simulator(monkeypatch):
    monkeypatch.delenv("MASSIVE_API_KEY", raising=False)
    source = build_market_data_source()
    assert isinstance(source, SimulatorMarketDataSource)


def test_empty_api_key_selects_simulator(monkeypatch):
    monkeypatch.setenv("MASSIVE_API_KEY", "")
    source = build_market_data_source()
    assert isinstance(source, SimulatorMarketDataSource)


def test_whitespace_only_api_key_selects_simulator(monkeypatch):
    monkeypatch.setenv("MASSIVE_API_KEY", "   ")
    source = build_market_data_source()
    assert isinstance(source, SimulatorMarketDataSource)


def test_non_empty_api_key_selects_massive(monkeypatch):
    monkeypatch.setenv("MASSIVE_API_KEY", "some-real-key")
    source = build_market_data_source()
    assert isinstance(source, MassiveMarketDataSource)
    assert source._api_key == "some-real-key"


def test_api_key_is_stripped(monkeypatch):
    monkeypatch.setenv("MASSIVE_API_KEY", "  some-real-key  ")
    source = build_market_data_source()
    assert isinstance(source, MassiveMarketDataSource)
    assert source._api_key == "some-real-key"
