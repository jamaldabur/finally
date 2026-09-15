"""Prompt construction for the chat assistant (PLAN.md §7 "System Prompt
Guidance" and "How It Works").

Two separate prompts/message-lists now, matching the two-call design:
`build_conversational_messages` for the streamed natural-language reply (no
structured output involved at all), and `build_actions_messages` for the
separate structured trades/watchlist-changes call. Both share the same
portfolio/watchlist JSON context and conversation history.
"""

from __future__ import annotations

import json

from ..db.watchlist import get_watchlist_tickers
from ..portfolio.service import get_portfolio_state

CONVERSATIONAL_SYSTEM_PROMPT = """You are FinAlly, an AI trading assistant embedded in a trading workstation.

You have access to the user's live portfolio (cash, positions with unrealized P&L) and watchlist (with live prices), provided as JSON context in this conversation. Use it to:
- Analyze portfolio composition, risk concentration, and P&L
- Suggest trades with clear, data-driven reasoning
- Acknowledge when the user is asking for a trade or watchlist change - a separate process (not you) determines and executes the exact action, so just respond naturally as if it's being taken care of
- Be concise

Respond in plain, natural conversational language only - no JSON, no code blocks, no markdown formatting, no curly braces. Just the reply text a user would read in a chat bubble, as if you were texting them. Do NOT output anything shaped like {"message": ..., "trades": ...} - that is a different system's job, not yours."""

ACTIONS_SYSTEM_PROMPT = """You are FinAlly's trade/watchlist action extractor, working alongside a separate assistant that replies to the user in natural language.

Given the user's message and the portfolio/watchlist context, determine what trades or watchlist changes (if any) the user is asking for now or has clearly agreed to. Respond ONLY with valid JSON matching the schema: an optional "trades" array of {"ticker", "side", "quantity"} to execute now, and an optional "watchlist_changes" array of {"ticker", "action"} ("add" or "remove") to apply now. These are auto-executed immediately with no confirmation step, so only include an action the user actually asked for or clearly agreed to - never a hypothetical or suggestion. If no action is called for, respond with {"trades": [], "watchlist_changes": []}."""


async def build_portfolio_context(app_state, user_id: str = "default") -> str:
    """JSON context describing current cash, positions, and watched tickers
    with live prices (PLAN.md §7 step 1)."""
    state = await get_portfolio_state(app_state, user_id)
    tickers = await get_watchlist_tickers(user_id)

    watchlist_view = []
    for ticker in tickers:
        tick = await app_state.price_cache.get(ticker)
        watchlist_view.append(
            {"ticker": ticker, "price": tick.price if tick is not None else None}
        )

    context = {
        "cash_balance": state["cash_balance"],
        "total_value": state["total_value"],
        "positions": state["positions"],
        "watchlist": watchlist_view,
    }
    return json.dumps(context)


def _build_messages(
    system_prompt: str,
    portfolio_context_json: str,
    history: list[dict],
    user_message: str,
) -> list[dict]:
    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "system",
            "content": f"Current portfolio and watchlist context:\n{portfolio_context_json}",
        },
    ]
    for msg in history:
        role = msg["role"] if msg["role"] in ("user", "assistant") else "user"
        messages.append({"role": role, "content": msg["content"]})
    messages.append({"role": "user", "content": user_message})
    return messages


def build_conversational_messages(
    portfolio_context_json: str, history: list[dict], user_message: str
) -> list[dict]:
    """Message list for the streamed, unstructured conversational reply."""
    return _build_messages(
        CONVERSATIONAL_SYSTEM_PROMPT, portfolio_context_json, history, user_message
    )


def build_actions_messages(
    portfolio_context_json: str, history: list[dict], user_message: str
) -> list[dict]:
    """Message list for the separate, structured trades/watchlist_changes call."""
    return _build_messages(
        ACTIONS_SYSTEM_PROMPT, portfolio_context_json, history, user_message
    )
