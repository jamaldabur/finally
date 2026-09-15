"""Deterministic mock responses for `LLM_MOCK=true` (PLAN.md §9 "LLM Mock
Mode") — used for fast/free/reproducible E2E tests and for local development
without an `OPENROUTER_API_KEY`.

Not a real NLU: simple keyword/regex matching over the user's message, just
enough to exercise the structured-output schema meaningfully. Any message
that doesn't match a recognized buy/sell/watchlist pattern gets a plain
acknowledgement with no actions.
"""

from __future__ import annotations

import re

from ..market.simulator import TICKER_UNIVERSE
from .schema import ChatCompletionResult, TradeAction, WatchlistChangeAction

_TICKER_RE = re.compile(r"\b[A-Z]{1,5}\b")
_QUANTITY_RE = re.compile(r"\b(\d+(?:\.\d+)?)\b")

_STOPWORDS = {
    "BUY", "SELL", "ADD", "REMOVE", "TO", "OF", "SHARE", "SHARES", "THE",
    "A", "AI", "MY", "FROM", "ON", "IN", "IS", "PLEASE", "CAN", "YOU",
    "WATCHLIST", "WATCH", "STOCK", "STOCKS", "PORTFOLIO", "AND", "FOR", "AT",
    "MORE", "SOME", "ALL", "ABOUT", "THAT", "THIS", "WITH", "LIKE", "WANT",
    "NEED", "GET", "JUST", "NOW", "GOOD", "BAD", "THANKS", "THANK", "YES",
    "NO", "OK", "OKAY", "ME", "DO", "DID", "HAVE", "HAS", "WOULD", "COULD",
    "SHOULD", "WHAT", "HOW", "WHY", "LOT", "BIT", "FEW", "MUCH", "MANY",
    "IT", "ITS", "SO", "IF", "BUT", "NOT", "OUR", "US",
}


def _extract_ticker(text: str) -> str | None:
    """Prefers an actual recognized ticker symbol over the bare "any
    all-caps word" heuristic — "buy 5 more AAPL" should extract AAPL, not
    MORE, regardless of how complete the stopword list is. Falls back to the
    heuristic (first non-stopword all-caps word) only when no word in the
    message matches a known ticker, so messages naming an intentionally
    unrecognized ticker (exercising the "unrecognized ticker" validation
    path) still extract something."""
    words = _TICKER_RE.findall(text.upper())

    for word in words:
        if word in TICKER_UNIVERSE:
            return word

    for word in words:
        if word not in _STOPWORDS:
            return word

    return None


def build_mock_response(user_message: str) -> ChatCompletionResult:
    lower = user_message.lower()
    ticker = _extract_ticker(user_message)
    quantity_match = _QUANTITY_RE.search(user_message)
    quantity = float(quantity_match.group(1)) if quantity_match else 1.0

    if ticker and "buy" in lower:
        return ChatCompletionResult(
            message=f"Mock: buying {quantity:g} share(s) of {ticker}.",
            trades=[TradeAction(ticker=ticker, side="buy", quantity=quantity)],
        )
    if ticker and "sell" in lower:
        return ChatCompletionResult(
            message=f"Mock: selling {quantity:g} share(s) of {ticker}.",
            trades=[TradeAction(ticker=ticker, side="sell", quantity=quantity)],
        )
    if ticker and "watchlist" in lower and "remove" in lower:
        return ChatCompletionResult(
            message=f"Mock: removing {ticker} from your watchlist.",
            watchlist_changes=[WatchlistChangeAction(ticker=ticker, action="remove")],
        )
    if ticker and "watchlist" in lower and "add" in lower:
        return ChatCompletionResult(
            message=f"Mock: adding {ticker} to your watchlist.",
            watchlist_changes=[WatchlistChangeAction(ticker=ticker, action="add")],
        )
    return ChatCompletionResult(
        message="Mock response: no specific action recognized for that message."
    )
