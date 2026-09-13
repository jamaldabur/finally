"""Tests exercise `_price_event_generator`/`stream_prices` directly rather
than through a live TestClient streaming round-trip: Starlette's TestClient
doesn't reliably surface an ASGI `http.disconnect` when a test stops reading
early, so `request.is_disconnected()` never returns True and the endpoint's
intentionally-infinite loop just hangs the test. Driving the generator with
a fake request that reports "disconnected" after N iterations exercises the
exact same production code with a deterministic stop condition instead.
"""

import json
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.market.base import ChangeDirection, PriceTick
from app.market.cache import PriceCache
from app.routes import stream as stream_module
from app.routes.stream import _price_event_generator, _serialize_tick, stream_prices


class _FakeRequest:
    """Reports disconnected after `max_iterations` truthy checks, so a loop
    keyed on `await request.is_disconnected()` terminates deterministically."""

    def __init__(self, max_iterations: int, app=None):
        self._remaining = max_iterations
        self.app = app

    async def is_disconnected(self) -> bool:
        if self._remaining <= 0:
            return True
        self._remaining -= 1
        return False


@pytest.fixture(autouse=True)
def fast_broadcast(monkeypatch):
    monkeypatch.setattr(stream_module, "SSE_BROADCAST_SECONDS", 0.001)


def test_serialize_tick_shape():
    tick = PriceTick(
        ticker="AAPL",
        price=190.42,
        previous_price=190.00,
        timestamp=datetime.now(timezone.utc),
        direction=ChangeDirection.UP,
    )
    data = _serialize_tick(tick)
    assert data == {
        "ticker": "AAPL",
        "price": 190.42,
        "previous_price": 190.00,
        "timestamp": tick.timestamp.isoformat(),
        "direction": "up",
    }


@pytest.mark.asyncio
async def test_generator_emits_one_event_per_tick_with_all_tracked_tickers():
    cache = PriceCache()
    await cache.update("AAPL", 190.00)
    await cache.update("GOOGL", 175.00)

    request = _FakeRequest(max_iterations=2)
    events = [event async for event in _price_event_generator(request, cache)]

    assert len(events) == 2
    for event in events:
        assert event.startswith("event: prices\ndata: ")
        assert event.endswith("\n\n")
        payload = json.loads(event[len("event: prices\ndata: ") : -2])
        tickers = {t["ticker"] for t in payload["ticks"]}
        assert tickers == {"AAPL", "GOOGL"}
        for tick in payload["ticks"]:
            assert tick["direction"] in ("up", "down", "unchanged")


@pytest.mark.asyncio
async def test_generator_stops_immediately_when_already_disconnected():
    cache = PriceCache()
    await cache.update("AAPL", 190.00)

    request = _FakeRequest(max_iterations=0)
    events = [event async for event in _price_event_generator(request, cache)]

    assert events == []


@pytest.mark.asyncio
async def test_stream_prices_route_sets_event_stream_media_type_and_headers():
    cache = PriceCache()
    await cache.update("AAPL", 190.00)
    fake_app = SimpleNamespace(state=SimpleNamespace(price_cache=cache))
    request = _FakeRequest(max_iterations=0, app=fake_app)

    response = await stream_prices(request)

    assert response.media_type == "text/event-stream"
    assert response.headers["cache-control"] == "no-cache"
    assert response.headers["connection"] == "keep-alive"
