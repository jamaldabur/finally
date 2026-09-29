"""GET/POST/DELETE /api/watchlist — watchlist read + mutation (PLAN.md §8
"Watchlist").

The only module in the watchlist request path permitted to raise
HTTPException, matching the layering 01-01-PLAN.md established for trades
(01-RESEARCH.md Pattern 3). Ticker normalization (see `_normalize` below) is
applied here, as the very first statement of every endpoint, before
validation and before persistence — `is_valid_ticker()` is a case-sensitive
membership check against uppercase TICKER_UNIVERSE keys, so an unnormalized
"aapl" would be wrongly rejected (01-RESEARCH.md Pitfall 2).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from ..db.watchlist import (
    add_watchlist_ticker,
    get_watchlist_entries,
    remove_watchlist_ticker,
)

router = APIRouter()


class WatchlistAddRequest(BaseModel):
    ticker: str = Field(min_length=1)


class WatchlistEntryResponse(BaseModel):
    ticker: str
    price: float | None
    previous_price: float | None
    direction: str | None
    timestamp: str | None


class WatchlistResponse(BaseModel):
    watchlist: list[WatchlistEntryResponse]


class WatchlistAddResponse(BaseModel):
    ticker: str
    added: bool


class WatchlistRemoveResponse(BaseModel):
    ticker: str
    removed: bool


def _normalize(ticker: str) -> str:
    return ticker.strip().upper()


@router.get("/api/watchlist")
async def get_watchlist(request: Request) -> WatchlistResponse:
    cache = request.app.state.price_cache
    entries = await get_watchlist_entries()

    watchlist: list[WatchlistEntryResponse] = []
    for entry in entries:
        # Defensive normalization: entries are always persisted uppercase
        # (every write path normalizes first), but re-normalizing on read
        # keeps this endpoint's output canonical even against any
        # pre-existing non-normalized row.
        ticker = _normalize(entry.ticker)
        tick = await cache.get(ticker)
        if tick is None:
            watchlist.append(
                WatchlistEntryResponse(
                    ticker=ticker,
                    price=None,
                    previous_price=None,
                    direction=None,
                    timestamp=None,
                )
            )
        else:
            watchlist.append(
                WatchlistEntryResponse(
                    ticker=ticker,
                    price=tick.price,
                    previous_price=tick.previous_price,
                    direction=tick.direction.value,
                    timestamp=tick.timestamp.isoformat(),
                )
            )

    return WatchlistResponse(watchlist=watchlist)


@router.post("/api/watchlist")
async def post_watchlist(body: WatchlistAddRequest, request: Request) -> WatchlistAddResponse:
    ticker = _normalize(body.ticker)

    if not await request.app.state.market_source.is_valid_ticker(ticker):
        raise HTTPException(status_code=400, detail=f"Unknown ticker: {ticker}")

    added = await add_watchlist_ticker(ticker)
    return WatchlistAddResponse(ticker=ticker, added=added)


@router.delete("/api/watchlist/{ticker}")
async def delete_watchlist(ticker: str) -> WatchlistRemoveResponse:
    normalized = _normalize(ticker)
    removed = await remove_watchlist_ticker(normalized)
    return WatchlistRemoveResponse(ticker=normalized, removed=removed)
