"""SSE price stream — GET /api/stream/prices (PLAN.md §6/§8).

One SSE event per broadcast tick, containing the full array of all tracked
tickers, per planning/MARKET_DATA_DESIGN.md §9 (resolving REVIEW.md §B2's
ambiguity between one-event-per-tick vs. one-event-per-ticker). No SSE
helper library is used — a plain async generator with
media_type="text/event-stream" is sufficient for this project's needs.
"""

import asyncio
import json

from fastapi import APIRouter, Request
from starlette.responses import StreamingResponse

from ..market.base import PriceTick
from ..market.cache import PriceCache

router = APIRouter()

SSE_BROADCAST_SECONDS = 0.5


def _serialize_tick(tick: PriceTick) -> dict:
    return {
        "ticker": tick.ticker,
        "price": tick.price,
        "previous_price": tick.previous_price,
        "timestamp": tick.timestamp.isoformat(),
        "direction": tick.direction.value,
    }


async def _price_event_generator(request: Request, cache: PriceCache):
    while True:
        if await request.is_disconnected():
            break
        ticks = await cache.snapshot()
        payload = {"ticks": [_serialize_tick(t) for t in ticks]}
        yield f"event: prices\ndata: {json.dumps(payload)}\n\n"
        await asyncio.sleep(SSE_BROADCAST_SECONDS)


@router.get("/api/stream/prices")
async def stream_prices(request: Request):
    cache: PriceCache = request.app.state.price_cache
    return StreamingResponse(
        _price_event_generator(request, cache),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # disable proxy buffering if ever fronted by nginx
        },
    )
