"""Watchlist REST routes (PLAN.md §8 "Watchlist")."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..db.watchlist import get_watchlist_tickers
from ..watchlist.service import (
    WatchlistError,
    add_watchlist_ticker,
    remove_watchlist_ticker,
)

router = APIRouter()


class WatchlistRequest(BaseModel):
    ticker: str


@router.get("/api/watchlist")
async def get_watchlist(request: Request) -> list[dict]:
    tickers = await get_watchlist_tickers()
    cache = request.app.state.price_cache
    result = []
    for ticker in tickers:
        tick = await cache.get(ticker)
        result.append(
            {
                "ticker": ticker,
                "price": tick.price if tick is not None else None,
                "previous_price": tick.previous_price if tick is not None else None,
                "direction": tick.direction.value if tick is not None else None,
            }
        )
    return result


@router.post("/api/watchlist")
async def post_watchlist(request: Request, body: WatchlistRequest) -> dict:
    try:
        await add_watchlist_ticker(request.app.state, body.ticker)
    except WatchlistError as exc:
        raise HTTPException(status_code=400, detail=exc.reason) from exc
    return {"ticker": body.ticker.strip().upper()}


@router.delete("/api/watchlist/{ticker}")
async def delete_watchlist(request: Request, ticker: str) -> dict:
    try:
        await remove_watchlist_ticker(request.app.state, ticker)
    except WatchlistError as exc:
        raise HTTPException(status_code=404, detail=exc.reason) from exc
    return {"ticker": ticker.strip().upper()}
