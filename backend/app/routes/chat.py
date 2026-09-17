"""POST /api/chat — the AI chat copilot round trip (PLAN.md §8 "Chat", §9
"LLM Integration").

The only module in the chat request path permitted to raise HTTPException;
`app/llm/` returns plain data (a `ChatResponseSchema` and an
`ExecutedActions`) that this route translates into HTTP, matching the
layering `app/routes/portfolio.py` established for trades. A failed
individual action is never an HTTP error here — it is a 200 response with
that action's `outcome` set to `"error"` (CHAT-04); only a structurally
invalid request (blank message) raises, and that is Pydantic's own 422 via
`ChatRequest`'s validator, not a hand-raised HTTPException.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field, field_validator

from ..db.watchlist import get_watchlist_entries
from ..llm.actions import execute_llm_actions
from ..llm.client import get_chat_response
from ..portfolio.service import compute_portfolio_view

router = APIRouter()


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)

    @field_validator("message")
    @classmethod
    def _message_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("message must not be blank")
        return value


class TradeActionResponse(BaseModel):
    ticker: str
    side: str
    quantity: float
    price: float | None
    outcome: str
    reason: str | None


class WatchlistActionResponse(BaseModel):
    ticker: str
    action: str
    outcome: str
    reason: str | None


class ChatResponse(BaseModel):
    message: str
    trades: list[TradeActionResponse] = []
    watchlist_changes: list[WatchlistActionResponse] = []


@router.post("/api/chat")
async def post_chat(body: ChatRequest, request: Request) -> ChatResponse:
    price_cache = request.app.state.price_cache
    market_source = request.app.state.market_source
    lock = request.app.state.portfolio_lock

    portfolio_view = await compute_portfolio_view(price_cache=price_cache)

    watchlist_rows = await get_watchlist_entries()
    watchlist_context: list[dict] = []
    for row in watchlist_rows:
        tick = await price_cache.get(row.ticker)
        watchlist_context.append(
            {"ticker": row.ticker, "price": tick.price if tick else None}
        )

    # Plan 03-02 supplies real conversation history from chat_messages; this
    # plan proves the round trip with an empty history.
    llm_response = await get_chat_response(
        portfolio_view=portfolio_view,
        watchlist_entries=watchlist_context,
        history=[],
        user_message=body.message,
    )

    executed = await execute_llm_actions(
        price_cache=price_cache,
        market_source=market_source,
        lock=lock,
        response=llm_response,
    )

    return ChatResponse(
        message=llm_response.message,
        trades=[
            TradeActionResponse(
                ticker=t.ticker,
                side=t.side,
                quantity=t.quantity,
                price=t.price,
                outcome=t.outcome,
                reason=t.reason,
            )
            for t in executed.trades
        ],
        watchlist_changes=[
            WatchlistActionResponse(
                ticker=w.ticker,
                action=w.action,
                outcome=w.outcome,
                reason=w.reason,
            )
            for w in executed.watchlist_changes
        ],
    )
