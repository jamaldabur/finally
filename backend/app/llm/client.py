"""LiteLLM → OpenRouter structured-output call for the chat copilot
(PLAN.md §9 "LLM Integration").

`is_mock_mode()` is the single place `LLM_MOCK` is read anywhere under
`backend/app/` — no other module may check that variable, mirroring the
"check once, never scattered" rule `app/market/factory.py` documents for
`MASSIVE_API_KEY`. `get_chat_response()` is the one entry point callers use;
it branches mock vs. real internally so `app/routes/chat.py` never has to
know which path ran.

Schema validation is owned entirely by this module's own
`parse_llm_response()`, not by any library-level toggle. A debug session
(`.planning/debug/llm-raw-garbage-as-message.md`, G-03-3) found this module
previously set a LiteLLM client-side validation flag as a described
backstop, but that flag's only consumer in the library never ran, because
the structured call itself streamed its response — so it was dead code,
and the raw model text it should have blocked was rendered to the user
verbatim on every parse failure, with no log line. Streaming is gone now (see
`_call_model_once()` below), which would make that flag live again — but
re-enabling it would be strictly worse than removing it: it raises *before*
`parse_llm_response()`'s own fence-recovery logic ever runs, which would
reintroduce the exact silently-dropped-trade failure this module now
prevents. `parse_llm_response()` validates against the same schema and
additionally recovers a markdown-fenced valid response, so it is a
strictly better validator than the library flag ever was.
"""

from __future__ import annotations

import json
import logging
import os
import re

from litellm import (
    APIConnectionError,
    APIError,
    AuthenticationError,
    RateLimitError,
    ServiceUnavailableError,
    Timeout,
    acompletion,
)
from pydantic import ValidationError

from .mock import build_mock_response
from .schema import ChatResponseSchema

logger = logging.getLogger(__name__)

MODEL = "openrouter/openrouter/free"

# Last-resort safety net for when the free auto-router endpoint itself has
# trouble — a distinct, non-router free model (this repo's own agent-teams
# branch independently settled on the same one for the same reason). A
# paid model is not viable here: this OpenRouter account has no purchased
# credits, which is the 402 that caused Plan 03-01's model deviation in the
# first place. Used at most once per turn, only after a transient error on
# MODEL — see `_TRANSIENT_ERRORS` below.
FALLBACK_MODEL = "openrouter/nvidia/nemotron-3-super-120b-a12b:free"

# Errors worth exactly one further attempt against FALLBACK_MODEL: the
# provider/router had trouble serving the request (rate-limited,
# momentarily unavailable, connection/timeout hiccup). Deliberately
# narrower than a bare `except Exception` — AuthenticationError and
# BadRequestError are real configuration bugs that a second model cannot
# fix and must not be hidden behind one, so neither appears here; imported
# above only so `_call_llm_structured()` lets them propagate untouched.
_TRANSIENT_ERRORS = (
    RateLimitError,
    APIError,
    ServiceUnavailableError,
    Timeout,
    APIConnectionError,
)

# Two distinct, named, user-visible fallback sentences — assertable by
# content from a test, unlike the truthiness-only oracle that let G-03-3
# ship. "Could not reach" (a real exception at the call site: network,
# rate limit, or both models failing) and "could not understand" (a reply
# arrived but failed schema validation even after fence recovery) are
# different situations, and the user benefits from being able to tell them
# apart.
LLM_UNAVAILABLE_MESSAGE = (
    "I'm having trouble reaching the assistant right now — please try again shortly."
)
PARSE_FALLBACK_MESSAGE = "I could not understand the assistant's reply — please try again."

# Anchored at both ends so it only matches when the ENTIRE trimmed text is
# one fenced block (not merely a text that happens to contain a fenced
# excerpt somewhere in the middle); non-greedy across newlines (re.DOTALL)
# so a fence whose body itself contains a backtick sequence doesn't overrun
# past the first closing fence. Compiled once at module scope and applied
# at most once per parse (T-03-26) — never in a loop, never re-applied to
# its own output — so a pathological input cannot drive repeated stripping.
_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL)


def _strip_code_fence(text: str) -> str:
    """Returns the fenced body when the whole trimmed `text` is one
    markdown code fence (```json ... ``` or an untagged ``` ... ```), and
    returns the *trimmed* `text` unchanged otherwise (not the raw input) so
    the caller's `stripped != raw.strip()` comparison is meaningful — a
    text with only leading/trailing whitespace and no fence must compare
    equal, not spuriously differ. The caller compares the result against
    the trimmed input to decide whether stripping actually did anything
    before retrying validation."""
    trimmed = text.strip()
    match = _CODE_FENCE_RE.match(trimmed)
    return match.group(1) if match else trimmed


# PLAN.md §9 step 2 says "recent conversation history" without a number, and
# 03-RESEARCH.md Pitfall 5 flags the unbounded-growth cost of feeding the
# whole stored conversation into every prompt. 20 messages is roughly ten
# turns — enough for continuity without the per-request prompt growing for
# the length of a demo session. The cap is applied inside build_messages()
# rather than at the call site so no caller can bypass it.
PROMPT_HISTORY_LIMIT = 20

# PLAN.md §9 "System Prompt Guidance". Three hard constraints beyond the
# feature list: the assistant describes what it is *requesting*, never
# asserts an action already succeeded or failed (outcomes are computed by
# the server after this response is parsed — see app/llm/actions.py); it
# must never use urgency, scarcity, loss-aversion, or guaranteed-return
# framing to push the user toward a trade; and quantity is always a
# positive magnitude, with side alone conveying direction (G-03-5). This
# third rule was A/B tested live against the real free router
# (.planning/debug/llm-negative-sell-quantity.md) and flipped the one
# backing model that was reproducibly emitting signed quantities from 2/2
# negative to 2/2 positive — but it is a mitigation, not a guarantee,
# because the router serves a different backing model per call. The actual
# guarantee is the sell-only sign recovery in
# app/llm/actions.py::_normalize_trade_item().
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
- Quantity is always a positive number of shares. The side field alone
  says whether it is a buy or a sell, so a sell must never be expressed as
  a negative quantity.
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
    # Cap applied here, not at the call site, so no caller can bypass it.
    # Only role/content are replayed — the actions column is server-computed
    # outcome data, never conversation content (PLAN.md §9 step 7, T-03-09).
    capped_history = history[-PROMPT_HISTORY_LIMIT:] if history else history
    messages.extend(
        {"role": item["role"], "content": item["content"]} for item in capped_history
    )
    messages.append({"role": "user", "content": user_message})
    return messages


async def _call_model_once(model: str, messages: list[dict]) -> str:
    """Single non-streaming structured-output call against `model`. Not
    passing a truthy `stream` is the load-bearing fix for G-03-3's silent
    failure: the earlier version of this call streamed the response, which
    was purely a server-side accumulation detail — `POST /api/chat` itself
    always returns one complete JSON body (PLAN.md §9 step 4), never a
    streamed response to the browser — but streaming also routed every
    provider/validation error around LiteLLM's normal error-raising path,
    so a bad response returned silently with HTTP 200 and zero log lines.
    Without streaming, the identical failure surfaces as a real exception
    here, where the caller can log it and, if it's transient, fail over."""
    response = await acompletion(
        model=model,
        messages=messages,
        response_format=ChatResponseSchema,
        reasoning_effort="low",
    )
    content = response.choices[0].message.content
    return content or ""


async def _call_llm_structured(messages: list[dict]) -> str:
    """Tries MODEL once; on a transient provider error (`_TRANSIENT_ERRORS`
    above), tries FALLBACK_MODEL once with the identical `messages` list —
    nothing derived from the failed attempt is added, since that text is
    untrusted model output (T-03-27). No loop, no recursion, no retry
    counter: exactly two attempts, expressed as two straight-line calls.
    An authentication or bad-request error is not transient and is left to
    propagate immediately, so `get_chat_response()`'s handler surfaces it
    as a real configuration bug instead of masking it behind a second
    model."""
    try:
        return await _call_model_once(MODEL, messages)
    except _TRANSIENT_ERRORS as exc:
        logger.warning(
            "Primary model %s failed transiently, trying fallback model %s: %s: %s",
            MODEL,
            FALLBACK_MODEL,
            type(exc).__name__,
            exc,
        )
        try:
            return await _call_model_once(FALLBACK_MODEL, messages)
        except Exception as fallback_exc:
            logger.error(
                "Fallback model %s also failed: %s: %s",
                FALLBACK_MODEL,
                type(fallback_exc).__name__,
                fallback_exc,
            )
            raise


def parse_llm_response(raw: str) -> ChatResponseSchema:
    """Defensive parse — must never raise, on any input. First attempts
    validation of the raw text as-is. On failure, computes the
    fence-stripped text and, only if it actually differs from the trimmed
    input, retries validation once against it — this fence recovery is the
    load-bearing fix for G-03-3: without it, a correctly-formed response
    wrapped in a markdown code fence (a documented free-router quirk) is
    rejected and its trades vanish silently, and the user is told nothing
    happened. Only when both attempts fail does this log a warning
    (exception type plus a bounded prefix of the raw text — never the whole
    body) and return PARSE_FALLBACK_MESSAGE with both action lists empty.
    The model's own text is never assigned into the returned message on any
    path: as the debug session established, pydantic tags unparseable
    garbage and legitimate prose identically (`json_invalid` for both), so
    no classifier can separate a leaked instruction string from a real
    answer — the only safe behavior is to never show raw model text."""
    try:
        return ChatResponseSchema.model_validate_json(raw)
    except (ValidationError, json.JSONDecodeError, ValueError) as first_exc:
        stripped = _strip_code_fence(raw)
        if stripped != raw.strip():
            try:
                return ChatResponseSchema.model_validate_json(stripped)
            except (ValidationError, json.JSONDecodeError, ValueError):
                pass
        logger.warning(
            "Failed to parse LLM response as %s: %s: %s (raw prefix: %r)",
            ChatResponseSchema.__name__,
            type(first_exc).__name__,
            first_exc,
            raw[:200],
        )
        return ChatResponseSchema(
            message=PARSE_FALLBACK_MESSAGE, trades=[], watchlist_changes=[]
        )


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
            message=LLM_UNAVAILABLE_MESSAGE,
            trades=[],
            watchlist_changes=[],
        )

    return parse_llm_response(raw)
