"""Chat REST/SSE routes (PLAN.md §7 "LLM Integration").

`POST /api/chat` streams a `text/event-stream` response (mirrors the
plain-async-generator + `StreamingResponse` pattern already used by
`GET /api/stream/prices` in `routes/stream.py` — no SSE helper library):

- `event: delta` — `data: {"text": "<chunk>"}`, one per streamed piece of the
  conversational reply, in order.
- `event: done` — `data: {"message": <full text>, "trades": [...annotated],
  "watchlist_changes": [...annotated]}`, exactly one, final, after the text
  stream completes and any requested trades/watchlist changes have been
  auto-executed through the same validated code paths the trade bar and
  watchlist panel use (`execute_trade`, `add_watchlist_ticker`,
  `remove_watchlist_ticker`).

The conversational reply (streamed, unstructured) and the actions
determination (structured, non-streaming) are two separate LLM calls fired
concurrently — see `app/llm/client.py`.
"""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, Request
from pydantic import BaseModel
from starlette.responses import StreamingResponse

from ..db.chat_messages import get_recent_messages, insert_message
from ..llm.client import FALLBACK_MESSAGE, get_actions, stream_chat_message
from ..llm.prompt import build_actions_messages, build_conversational_messages, build_portfolio_context
from ..portfolio.service import TradeError, execute_trade
from ..watchlist.service import (
    WatchlistError,
    add_watchlist_ticker,
    remove_watchlist_ticker,
)

logger = logging.getLogger(__name__)

router = APIRouter()


class ChatRequest(BaseModel):
    message: str


@router.get("/api/chat")
async def get_chat() -> list[dict]:
    return await get_recent_messages()


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def _annotate_trades(app_state, trades) -> list[dict]:
    annotated = []
    for trade in trades:
        action = {"ticker": trade.ticker, "side": trade.side, "quantity": trade.quantity}
        try:
            await execute_trade(app_state, trade.ticker, trade.side, trade.quantity)
            action["status"] = "executed"
            action["reason"] = None
        except TradeError as exc:
            action["status"] = "error"
            action["reason"] = exc.reason
        except Exception:
            # Not a validation failure (e.g. a DB contention error) - still
            # record *something* for this action rather than letting one bad
            # item crash the loop and silently lose the annotation for
            # trades that already executed for real before it.
            logger.exception(
                "Unexpected error executing trade %s %s %s", trade.side, trade.quantity, trade.ticker
            )
            action["status"] = "error"
            action["reason"] = "unexpected error"
        annotated.append(action)
    return annotated


async def _annotate_watchlist_changes(app_state, watchlist_changes) -> list[dict]:
    annotated = []
    for change in watchlist_changes:
        action = {"ticker": change.ticker, "action": change.action}
        try:
            if change.action == "add":
                await add_watchlist_ticker(app_state, change.ticker)
            else:
                await remove_watchlist_ticker(app_state, change.ticker)
            action["status"] = "executed"
            action["reason"] = None
        except WatchlistError as exc:
            action["status"] = "error"
            action["reason"] = exc.reason
        except Exception:
            logger.exception(
                "Unexpected error applying watchlist change %s %s", change.action, change.ticker
            )
            action["status"] = "error"
            action["reason"] = "unexpected error"
        annotated.append(action)
    return annotated


async def _chat_event_stream(app_state, user_message: str):
    history = await get_recent_messages()
    portfolio_context = await build_portfolio_context(app_state)
    conversational_messages = build_conversational_messages(portfolio_context, history, user_message)
    actions_messages = build_actions_messages(portfolio_context, history, user_message)

    # Fired concurrently: the actions call runs alongside the streamed
    # reply rather than after it, so it doesn't add extra wall-clock time to
    # a response the client is already occupied reading.
    actions_task = asyncio.create_task(get_actions(actions_messages, user_message))

    message_parts: list[str] = []
    try:
        async for chunk in stream_chat_message(conversational_messages, user_message):
            message_parts.append(chunk)
            yield _sse("delta", {"text": chunk})
    except Exception:
        logger.exception("Unexpected error while streaming the chat reply")
        if not message_parts:
            message_parts.append(FALLBACK_MESSAGE)
            yield _sse("delta", {"text": FALLBACK_MESSAGE})

    full_message = "".join(message_parts)

    # From here on, a `done` event must reach the client no matter what goes
    # wrong — an unexpected exception anywhere in determining/executing
    # actions or persisting messages (a real one observed under concurrent
    # load: SQLite lock contention raising something other than
    # TradeError/WatchlistError) must not silently drop the connection
    # without ever telling the client whether their trade went through.
    annotated_trades: list[dict] = []
    annotated_watchlist_changes: list[dict] = []
    try:
        actions_result = await actions_task
        annotated_trades = await _annotate_trades(app_state, actions_result.trades)
        annotated_watchlist_changes = await _annotate_watchlist_changes(
            app_state, actions_result.watchlist_changes
        )
    except Exception:
        logger.exception("Unexpected error while determining/executing chat actions")

    try:
        await insert_message("default", "user", user_message)
        await insert_message(
            "default",
            "assistant",
            full_message,
            actions={"trades": annotated_trades, "watchlist_changes": annotated_watchlist_changes},
        )
    except Exception:
        logger.exception("Unexpected error while persisting chat messages")

    yield _sse(
        "done",
        {
            "message": full_message,
            "trades": annotated_trades,
            "watchlist_changes": annotated_watchlist_changes,
        },
    )


@router.post("/api/chat")
async def post_chat(request: Request, body: ChatRequest) -> StreamingResponse:
    return StreamingResponse(
        _chat_event_stream(request.app.state, body.message),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
