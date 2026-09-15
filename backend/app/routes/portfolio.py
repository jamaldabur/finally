"""Portfolio REST routes (PLAN.md §8 "Portfolio")."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..portfolio.service import TradeError, execute_trade, get_portfolio_state
from ..db.portfolio_snapshots import get_snapshots

router = APIRouter()


class TradeRequest(BaseModel):
    ticker: str
    quantity: float
    side: Literal["buy", "sell"]


@router.get("/api/portfolio")
async def get_portfolio(request: Request) -> dict:
    return await get_portfolio_state(request.app.state)


@router.post("/api/portfolio/trade")
async def post_trade(request: Request, body: TradeRequest) -> dict:
    try:
        return await execute_trade(
            request.app.state, body.ticker, body.side, body.quantity
        )
    except TradeError as exc:
        raise HTTPException(status_code=400, detail=exc.reason) from exc


@router.get("/api/portfolio/history")
async def get_portfolio_history() -> list[dict]:
    return await get_snapshots()
