"""POST /api/portfolio/trade, GET /api/portfolio, GET /api/portfolio/history
— market order execution and portfolio reads (PLAN.md §8 "Portfolio").

The only module in the request path permitted to raise HTTPException;
app/portfolio/service.py returns a structured TradeResult that this route
translates into HTTP (01-RESEARCH.md Pattern 3). Neither GET endpoint raises
HTTPException — there is no failure mode to translate; an empty portfolio is
a valid 200.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from ..db import portfolio_snapshots
from ..db.portfolio_snapshots import DEFAULT_SNAPSHOT_LIMIT, MAX_SNAPSHOT_LIMIT
from ..portfolio.service import compute_portfolio_view, execute_trade

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


class PositionViewResponse(BaseModel):
    ticker: str
    quantity: float
    avg_cost: float
    current_price: float | None
    market_value: float
    unrealized_pnl: float
    pct_change: float


class PortfolioResponse(BaseModel):
    cash_balance: float
    positions: list[PositionViewResponse]
    positions_value: float
    total_value: float
    total_unrealized_pnl: float


class SnapshotResponse(BaseModel):
    total_value: float
    recorded_at: str


class PortfolioHistoryResponse(BaseModel):
    snapshots: list[SnapshotResponse]


@router.get("/api/portfolio")
async def get_portfolio(request: Request) -> PortfolioResponse:
    view = await compute_portfolio_view(price_cache=request.app.state.price_cache)

    return PortfolioResponse(
        cash_balance=view.cash_balance,
        positions=[
            PositionViewResponse(
                ticker=position.ticker,
                quantity=position.quantity,
                avg_cost=position.avg_cost,
                current_price=position.current_price,
                market_value=position.market_value,
                unrealized_pnl=position.unrealized_pnl,
                pct_change=position.pct_change,
            )
            for position in view.positions
        ],
        positions_value=view.positions_value,
        total_value=view.total_value,
        total_unrealized_pnl=view.total_unrealized_pnl,
    )


@router.get("/api/portfolio/history")
async def get_portfolio_history(
    limit: int = Query(default=DEFAULT_SNAPSHOT_LIMIT, ge=1, le=MAX_SNAPSHOT_LIMIT),
) -> PortfolioHistoryResponse:
    """Return a bounded window of the most recent snapshots, oldest-first.
    Omitting `limit` yields DEFAULT_SNAPSHOT_LIMIT. FastAPI's own Query
    validation rejects an out-of-range value as a 422 before this handler
    runs; the bounded read in get_snapshots() is the single place the
    window is applied — this handler never slices the result itself."""
    snapshots = await portfolio_snapshots.get_snapshots(limit=limit)

    return PortfolioHistoryResponse(
        snapshots=[
            SnapshotResponse(total_value=s.total_value, recorded_at=s.recorded_at)
            for s in snapshots
        ]
    )


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
