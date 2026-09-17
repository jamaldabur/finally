"""LiteLLM → OpenRouter structured-output call for the chat copilot
(PLAN.md §9 "LLM Integration").

`is_mock_mode()` is the single place `LLM_MOCK` is read anywhere under
`backend/app/` — no other module may check that variable, mirroring the
"check once, never scattered" rule `app/market/factory.py` documents for
`MASSIVE_API_KEY`. `get_chat_response()` is the one entry point callers use;
it branches mock vs. real internally so `app/routes/chat.py` never has to
know which path ran.

`litellm.enable_json_schema_validation = True` is set at module import time
as a client-side backstop: OpenRouter's structured-output enforcement is
provider-dependent (03-RESEARCH.md Pitfall 1), so this makes LiteLLM itself
validate the model's JSON against the schema rather than trusting the
provider unconditionally.
"""

from __future__ import annotations

import json
import logging
import os

import litellm
from litellm import acompletion
from pydantic import ValidationError

from .mock import build_mock_response
from .schema import ChatResponseSchema

logger = logging.getLogger(__name__)

litellm.enable_json_schema_validation = True

MODEL = "openrouter/openrouter/free"

# PLAN.md §9 "System Prompt Guidance". Two hard constraints beyond the
# feature list: the assistant describes what it is *requesting*, never
# asserts an action already succeeded or failed (outcomes are computed by
# the server after this response is parsed — see app/llm/actions.py), and it
# must never use urgency, scarcity, loss-aversion, or guaranteed-return
# framing to push the user toward a trade.
SYSTEM_PROMPT = """You are FinAlly, an AI trading assistant embedded in a \
simulated trading workstation. You help the user understand and manage \
their simulated portfolio.

Responsibilities:
- Analyze portfolio composition, risk concentration, and P&L.
- Suggest trades with clear, data-driven reasoning.
- Execute trades when the user asks for one or agrees to your suggestion.
- Manage the watchlist proactively when it helps the user.
- Be concise and data-driven in your responses.
- Always respond with valid structured JSON matching the required schema.

Hard constraints:
- Describe trades and watchlist changes you are REQUESTING, never assert
  that an action has already succeeded or failed. The server executes your
  requested actions after you respond and reports the real outcome
  separately — your message is written before that happens and cannot know
  it.
- Never use urgency, scarcity, FOMO, loss-aversion, or guaranteed-return
  framing. You may suggest trades with reasoning; you must never pressure
  the user into making one.
"""


def is_mock_mode() -> bool:
    """The single place LLM_MOCK is read (03-01-PLAN.md acceptance
    criteria) — evaluated fresh on every call so concurrent requests under
    the same env value both take the same branch."""
    return os.environ.get("LLM_MOCK", "").strip().lower() == "true"


def build_messages(
    *,
    portfolio_view: object,
    watchlist_entries: list[dict],
    history: list[dict],
    user_message: str,
) -> list[dict]:
    """Pure function assembling the OpenAI-style message list: system
    message, one compact portfolio/watchlist context message, prior
    conversation turns, then the new user message last."""
    context_lines = [
        f"Cash balance: {portfolio_view.cash_balance:.2f}",
        f"Total portfolio value: {portfolio_view.total_value:.2f}",
        f"Total unrealized P&L: {portfolio_view.total_unrealized_pnl:.2f}",
        "Positions:",
    ]
    if portfolio_view.positions:
        for position in portfolio_view.positions:
            context_lines.append(
                f"  {position.ticker}: qty={position.quantity} "
                f"avg_cost={position.avg_cost:.2f} "
                f"current_price={position.current_price} "
                f"unrealized_pnl={position.unrealized_pnl:.2f}"
            )
    else:
        context_lines.append("  (none)")

    context_lines.append("Watchlist:")
    if watchlist_entries:
        for entry in watchlist_entries:
            context_lines.append(
                f"  {entry.get('ticker')}: price={entry.get('price')}"
            )
    else:
        context_lines.append("  (none)")

    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": "\n".join(context_lines)},
    ]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})
    return messages


async def _call_llm_structured(messages: list[dict]) -> str:
    """Follows .claude/skills/litellm-stream/SKILL.md's structured-output
    snippet, async: internal streaming is purely a server-side accumulation
    detail — POST /api/chat itself returns one complete JSON body
    (PLAN.md §9 step 4), never a streamed response to the browser."""
    response = await acompletion(
        model=MODEL,
        messages=messages,
        response_format=ChatResponseSchema,
        reasoning_effort="low",
        stream=True,
    )
    json_string = ""
    async for chunk in response:
        content = chunk.choices[0].delta.content
        if content:
            json_string += content
    return json_string


def parse_llm_response(raw: str) -> ChatResponseSchema:
    """Defensive parse — must never raise. Empty content, non-JSON text, or
    JSON that fails schema validation all fall back to a message-only
    response rather than a 5xx (CHAT-02 edge cases)."""
    try:
        return ChatResponseSchema.model_validate_json(raw)
    except (ValidationError, json.JSONDecodeError, ValueError):
        stripped = raw.strip()
        message = stripped if stripped else "I couldn't process that — please try again."
        return ChatResponseSchema(message=message, trades=[], watchlist_changes=[])


async def get_chat_response(
    *,
    portfolio_view: object,
    watchlist_entries: list[dict],
    history: list[dict],
    user_message: str,
) -> ChatResponseSchema:
    """The one entry point app/routes/chat.py calls. Branches mock vs. real
    internally; the real path degrades any failure (network error, rate
    limit, missing key) to a message-only response instead of ever letting
    an exception reach the route."""
    if is_mock_mode():
        return build_mock_response(user_message)

    messages = build_messages(
        portfolio_view=portfolio_view,
        watchlist_entries=watchlist_entries,
        history=history,
        user_message=user_message,
    )
    try:
        raw = await _call_llm_structured(messages)
    except Exception as exc:  # noqa: BLE001 - must never propagate to the route
        # Log the exception type/message only — never the request body, the
        # response body, or an environment variable value (mirrors
        # app/market/massive.py's MASSIVE_API_KEY handling).
        logger.error("LLM call failed: %s: %s", type(exc).__name__, exc)
        return ChatResponseSchema(
            message="I'm having trouble reaching the assistant right now — please try again shortly.",
            trades=[],
            watchlist_changes=[],
        )

    return parse_llm_response(raw)
