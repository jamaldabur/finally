"""LiteLLM -> OpenRouter calls for the chat assistant (PLAN.md §7).

Two separate LLM interactions per chat message, not one:

- `stream_chat_message` — the natural-language reply. No `response_format`
  at all (plain text can't be validated against a schema mid-stream anyway),
  genuinely streamed token-by-token via litellm's native async streaming
  (`acompletion(..., stream=True)` returns an async iterator - no manual
  thread bridging needed) all the way out to the HTTP response.
- `get_actions` — a separate, non-streaming, structured-output call
  (`response_format=ActionsResult`) that determines what trades/watchlist
  changes (if any) the user's message calls for. Runs concurrently with the
  streamed reply from the route's point of view.

Both share the same primary-model + fallback-model failover story (see
`MODEL`/`FALLBACK_MODEL` below), since `openrouter/free` (a free-model
router) can put either call on a congested or non-conforming underlying
model. A malformed/non-conforming actions response degrades to "no actions"
rather than blocking or corrupting the conversational reply.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from typing import AsyncIterator, TypeVar

from litellm import (
    APIConnectionError,
    APIError,
    RateLimitError,
    ServiceUnavailableError,
    Timeout,
    acompletion,
)
from pydantic import BaseModel, ValidationError

from .mock import build_mock_response
from .schema import ActionsResult

logger = logging.getLogger(__name__)

# `openrouter/free` ("Free Models Router") is OpenRouter's own auto-routing
# model: it picks among free models on OpenRouter for us, filtering for ones
# that support what the request needs (here, response_format/structured
# outputs for the actions call) — confirmed via OpenRouter's live model
# listing and `litellm.supports_response_schema("openrouter/openrouter/free")`.
# `FALLBACK_MODEL` is a last-resort safety net (a different, non-router
# provider - NVIDIA) in case the router endpoint itself has trouble; kept
# cheap since it's only ever one extra request, on failure. Paid models
# aren't viable here — this OpenRouter account has no purchased credits (a
# real 402 confirmed that), so any non-free model fails outright.
MODEL = "openrouter/openrouter/free"
FALLBACK_MODEL = "openrouter/nvidia/nemotron-3-super-120b-a12b:free"

# Errors worth failing over on: the provider/router had trouble serving the
# request (rate-limited, momentarily unavailable, connection/timeout hiccup).
# Deliberately NOT a bare `except Exception` — an auth or bad-request error
# is a real bug that failing over to a second model wouldn't fix and
# shouldn't be hidden by silently trying another model.
_TRANSIENT_ERRORS = (RateLimitError, APIError, ServiceUnavailableError, Timeout, APIConnectionError)

FALLBACK_MESSAGE = "Sorry, I had trouble processing that."

# Cheap simulated "typing" cadence for LLM_MOCK=true so the frontend/E2E
# tests can exercise real incremental-delta rendering without hitting the
# live API.
_MOCK_STREAM_DELAY_SECONDS = 0.03

_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL)

# Cheap heuristic to skip the actions LLM call entirely for messages that
# obviously aren't asking for a trade or watchlist change - halves real LLM
# call volume for purely conversational messages ("how am I doing?") against
# an already rate-limit-prone free router. False negatives (a phrasing that
# implies an action without using these words) just mean occasionally
# missing an action - no worse than a malformed LLM response already
# degrades, and the user can always just ask again more directly.
_ACTION_KEYWORDS = (
    "buy", "sell", "trade", "purchase", "acquire", "sold", "bought",
    "watchlist", "watch list", "unwatch", "add ", "remove ", "drop ",
)

_ResponseModel = TypeVar("_ResponseModel", bound=BaseModel)


def _llm_mock_enabled() -> bool:
    return os.environ.get("LLM_MOCK", "false").strip().lower() == "true"


def _looks_action_oriented(user_message: str) -> bool:
    lower = user_message.lower()
    return any(keyword in lower for keyword in _ACTION_KEYWORDS)


def _mock_chunks(text: str) -> list[str]:
    parts = text.split(" ")
    return [part if i == len(parts) - 1 else part + " " for i, part in enumerate(parts)]


def _strip_code_fence(text: str) -> str:
    match = _CODE_FENCE_RE.match(text.strip())
    return match.group(1) if match else text


def _looks_like_json_reply(first_chunk: str) -> bool:
    """True when the very first chunk of the *conversational* reply looks
    like the start of JSON or a markdown-fenced code block, rather than
    natural language — observed live: a router-selected model occasionally
    ignores the "plain language, no JSON" system prompt entirely and echoes
    a JSON blob shaped like the old combined message+trades+watchlist_changes
    schema. Real prose essentially never starts with these characters, so
    this is a cheap, low-false-positive signal checked once per reply."""
    stripped = first_chunk.strip()
    return stripped.startswith("{") or stripped.startswith("```")


def _extract_message_from_json_blob(text: str) -> str | None:
    """Best-effort recovery when `_looks_like_json_reply` fires: pull just
    the "message" text out of the blob so the chat bubble shows a normal
    reply instead of raw JSON. Returns `None` if the text isn't actually
    parseable JSON with a string "message" field, in which case the caller
    falls back to showing the raw text verbatim (still better than nothing)."""
    try:
        parsed = json.loads(_strip_code_fence(text))
    except json.JSONDecodeError:
        return None
    if isinstance(parsed, dict) and isinstance(parsed.get("message"), str):
        return parsed["message"]
    return None


def _is_json_invalid_error(exc: ValidationError) -> bool:
    """True when the raw text wasn't valid JSON at all (vs. valid JSON that
    just doesn't match our schema, e.g. a missing/wrong-type field) —
    pydantic tags these distinctly (`json_invalid` vs. `missing`/`*_type`)."""
    return any(err.get("type") == "json_invalid" for err in exc.errors())


def _recover_actions_json(raw: str, exc: ValidationError) -> ActionsResult | None:
    """Best-effort recovery for one non-conforming shape observed live from
    `openrouter/free`'s randomly-selected underlying models: the actions
    JSON wrapped in a markdown code fence. Returns `None` for anything else
    (plain prose, broken JSON, valid-but-wrong-shape JSON) — there's no
    trades/watchlist_changes to recover from those, so the caller degrades
    to "no actions" instead of guessing."""
    if not _is_json_invalid_error(exc):
        return None

    stripped = _strip_code_fence(raw)
    if stripped != raw.strip():
        try:
            return ActionsResult.model_validate_json(stripped)
        except ValidationError:
            pass

    return None


async def _stream_model_text(model: str, messages: list[dict]) -> AsyncIterator[str]:
    response = await acompletion(model=model, messages=messages, reasoning_effort="low", stream=True)
    async for chunk in response:
        content = chunk.choices[0].delta.content
        if content:
            yield content


async def _call_model_json(
    model: str, messages: list[dict], response_format: type[_ResponseModel]
) -> str:
    response = await acompletion(
        model=model,
        messages=messages,
        response_format=response_format,
        reasoning_effort="low",
        stream=True,
    )
    json_string = ""
    async for chunk in response:
        content = chunk.choices[0].delta.content
        if content:
            json_string += content
    return json_string


async def _call_structured_llm(
    messages: list[dict], response_format: type[_ResponseModel]
) -> str:
    """Tries `MODEL` once; on a transient error, immediately fails over to
    `FALLBACK_MODEL` once. No retry against `MODEL` itself — see the
    `_TRANSIENT_ERRORS` note above for why a pinned-model retry loop was
    removed in an earlier round (it only multiplied failed requests without
    ever succeeding once the shared pool was actually congested)."""
    try:
        return await _call_model_json(MODEL, messages, response_format)
    except _TRANSIENT_ERRORS as exc:
        logger.warning(
            "Primary model %s failed transiently for a structured call, trying fallback model %s: %s",
            MODEL,
            FALLBACK_MODEL,
            exc,
        )

    try:
        return await _call_model_json(FALLBACK_MODEL, messages, response_format)
    except Exception:
        logger.exception("Fallback model %s also failed for a structured call", FALLBACK_MODEL)
        raise


async def stream_chat_message(
    messages: list[dict], user_message: str
) -> AsyncIterator[str]:
    """Yields chunks of the assistant's natural-language reply as they
    arrive. Sniffs the very first chunk: if it looks like the model ignored
    the "plain language" instruction and started a JSON/fenced-code reply
    instead, streaming stops there and the rest is buffered so a clean
    "message" can be extracted (or the raw text shown verbatim) instead of
    dribbling out garbled JSON fragments as if they were prose. Otherwise
    streams normally, chunk by chunk, all the way through."""
    if _llm_mock_enabled():
        mock = build_mock_response(user_message)
        for chunk in _mock_chunks(mock.message):
            await asyncio.sleep(_MOCK_STREAM_DELAY_SECONDS)
            yield chunk
        return

    raw = _raw_stream_chat_message(messages)
    try:
        first_chunk = await raw.__anext__()
    except StopAsyncIteration:
        return

    if _looks_like_json_reply(first_chunk):
        logger.warning(
            "Conversational reply looks like JSON instead of plain text; "
            "buffering and extracting the message field instead of streaming it raw"
        )
        full = first_chunk + "".join([chunk async for chunk in raw])
        yield _extract_message_from_json_blob(full) or full
        return

    yield first_chunk
    async for chunk in raw:
        yield chunk


async def _raw_stream_chat_message(messages: list[dict]) -> AsyncIterator[str]:
    """The actual primary/fallback-model streaming logic, without the
    JSON-sniffing wrapper above. Fails over to `FALLBACK_MODEL` only if the
    primary errors before yielding anything (a clean swap, invisible to the
    client) — once anything has already streamed, a further error just ends
    the stream there rather than risk mixing two different models' output
    mid-answer. If nothing could be streamed at all, yields
    `FALLBACK_MESSAGE` as a last resort so the chat bubble is never left
    completely empty."""
    yielded_any = False
    try:
        async for chunk in _stream_model_text(MODEL, messages):
            yielded_any = True
            yield chunk
        return
    except _TRANSIENT_ERRORS as exc:
        if yielded_any:
            logger.warning("Primary model %s failed mid-stream: %s", MODEL, exc)
            return
        logger.warning(
            "Primary model %s failed before streaming anything, trying fallback model %s: %s",
            MODEL,
            FALLBACK_MODEL,
            exc,
        )
    except Exception:
        if yielded_any:
            logger.exception("Primary model %s failed mid-stream", MODEL)
            return
        logger.exception("Primary model %s failed unexpectedly before streaming anything", MODEL)
        yield FALLBACK_MESSAGE
        return

    try:
        async for chunk in _stream_model_text(FALLBACK_MODEL, messages):
            yielded_any = True
            yield chunk
    except Exception:
        logger.exception("Fallback model %s also failed to stream", FALLBACK_MODEL)
        if not yielded_any:
            yield FALLBACK_MESSAGE


async def get_actions(messages: list[dict], user_message: str) -> ActionsResult:
    """Returns the trades/watchlist changes (if any) the user's message
    calls for. Never raises and never blocks the conversational reply on
    trouble here — any failure (network, rate limit, malformed/unparseable
    response) degrades to "no actions" rather than being surfaced to the
    user, since this call is a best-effort addition to the real reply, not
    the primary thing the user is waiting on."""
    if _llm_mock_enabled():
        mock = build_mock_response(user_message)
        return ActionsResult(trades=mock.trades, watchlist_changes=mock.watchlist_changes)

    if not _looks_action_oriented(user_message):
        return ActionsResult()

    try:
        json_string = await _call_structured_llm(messages, ActionsResult)
    except Exception:
        logger.exception("Actions LLM call failed")
        return ActionsResult()

    try:
        return ActionsResult.model_validate_json(json_string)
    except ValidationError as exc:
        recovered = _recover_actions_json(json_string, exc)
        if recovered is not None:
            logger.warning(
                "Recovered a non-conforming actions response (raw, truncated): %.200s",
                json_string,
            )
            return recovered
        logger.exception("Actions LLM returned unparseable/non-conforming output")
        return ActionsResult()
