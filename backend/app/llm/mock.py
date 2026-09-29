"""Deterministic mock LLM response for LLM_MOCK=true (PLAN.md §9 "LLM Mock
Mode").

`build_mock_response()` is a pure function of the message text rather than a
single static reply, so Phase 6's E2E "mocked chat trade execution" scenario
has a real action to assert against (03-RESEARCH.md Pitfall 4 / Assumption
A1). The `[LLM_MOCK]` prefix on every returned `message` makes mock output
impossible to mistake for genuine model output.

Determinism contract (locked by tests/llm/test_mock.py): this function takes
only the message string, uses no clock, no randomness, and no environment
read, so the same input always produces byte-identical output on every call.
This is what makes `LLM_MOCK=true` usable for Phase 6's E2E suite — a test
can assert on the exact response a given input produces.
"""

from __future__ import annotations

import re

from .schema import ChatResponseSchema, LlmTradeItem, LlmWatchlistChange

_TRADE_PATTERN = re.compile(
    r"\b(buy|sell)\s+(\d+(?:\.\d+)?)\s+([A-Za-z]{1,5})\b", re.IGNORECASE
)
_WATCHLIST_PATTERN = re.compile(r"\b(add|remove)\s+([A-Za-z]{1,5})\b", re.IGNORECASE)


def build_mock_response(user_message: str) -> ChatResponseSchema:
    stripped = user_message.strip()

    trade_match = _TRADE_PATTERN.search(stripped)
    if trade_match:
        side = trade_match.group(1).lower()
        quantity = float(trade_match.group(2))
        ticker = trade_match.group(3).upper()
        return ChatResponseSchema(
            message=(
                f"[LLM_MOCK] Requesting to {side} {quantity} shares of {ticker}."
            ),
            trades=[LlmTradeItem(ticker=ticker, side=side, quantity=quantity)],
            watchlist_changes=[],
        )

    if "watchlist" in stripped.lower():
        watchlist_match = _WATCHLIST_PATTERN.search(stripped)
        if watchlist_match:
            action = watchlist_match.group(1).lower()
            ticker = watchlist_match.group(2).upper()
            return ChatResponseSchema(
                message=f"[LLM_MOCK] Requesting to {action} {ticker} on the watchlist.",
                trades=[],
                watchlist_changes=[LlmWatchlistChange(ticker=ticker, action=action)],
            )

    return ChatResponseSchema(
        message="[LLM_MOCK] I received your message but found no trade or watchlist request in it.",
        trades=[],
        watchlist_changes=[],
    )
