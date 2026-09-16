"""POST /api/portfolio/trade — market order execution (PLAN.md §8
"Portfolio").

The only module in the request path permitted to raise HTTPException;
app/portfolio/service.py returns a structured TradeResult that this route
translates into HTTP (01-RESEARCH.md Pattern 3).
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from ..portfolio.service import execute_trade

router = APIRouter()


class TradeRequest(BaseModel):
    ticker: str = Field(min_length=1)
    side: Literal["buy", "sell"]
    quantity: float = Field(gt=0)


class TradeRecord(BaseModel):
    id: str
    ticker: str
    side: str
    quantity: float
    price: float
    executed_at: str


class PositionRecord(BaseModel):
    ticker: str
    quantity: float
    avg_cost: float


class TradeResponse(BaseModel):
    trade: TradeRecord
    cash_balance: float
    position: PositionRecord | None


@router.post("/api/portfolio/trade")
async def post_trade(body: TradeRequest, request: Request) -> TradeResponse:
    result = await execute_trade(
        price_cache=request.app.state.price_cache,
        market_source=request.app.state.market_source,
        lock=request.app.state.portfolio_lock,
        ticker=body.ticker,
        side=body.side,
        quantity=body.quantity,
    )

    if result.status == "error":
        raise HTTPException(status_code=400, detail=result.reason)

    assert result.trade is not None and result.cash_balance is not None

    return TradeResponse(
        trade=TradeRecord(
            id=result.trade.id,
            ticker=result.trade.ticker,
            side=result.trade.side,
            quantity=result.trade.quantity,
            price=result.trade.price,
            executed_at=result.trade.executed_at,
        ),
        cash_balance=result.cash_balance,
        position=(
            PositionRecord(
                ticker=result.position.ticker,
                quantity=result.position.quantity,
                avg_cost=result.position.avg_cost,
            )
            if result.position is not None
            else None
        ),
    )
