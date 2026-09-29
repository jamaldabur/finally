"""Determinism and distinguishability tests for the LLM_MOCK branch
(03-02-PLAN.md Task 2).

`build_mock_response()`'s matcher logic was already built in 03-01; these
tests lock the determinism contract and the buy/sell/add/remove coverage as
regression tests so a future change cannot silently break either guarantee.
"""

from __future__ import annotations

from app.llm.mock import build_mock_response


def test_build_mock_response_is_deterministic() -> None:
    """Test 1: the same input returns byte-identical output on every call —
    no dependence on time, randomness, or environment."""
    first = build_mock_response("buy 5 CSCO")
    second = build_mock_response("buy 5 CSCO")

    assert first.model_dump() == second.model_dump()


def test_build_mock_response_parses_buy() -> None:
    """Test 2: a buy request yields one trade with the parsed side,
    quantity, and upper-cased ticker."""
    result = build_mock_response("BUY 2.5 aapl")

    assert len(result.trades) == 1
    trade = result.trades[0]
    assert trade.side == "buy"
    assert trade.quantity == 2.5
    assert trade.ticker == "AAPL"


def test_build_mock_response_parses_sell() -> None:
    """Test 3: a sell request yields one trade with side=='sell'."""
    result = build_mock_response("sell 3 NVDA")

    assert len(result.trades) == 1
    assert result.trades[0].side == "sell"


def test_build_mock_response_parses_watchlist_add() -> None:
    """Test 4: an add-to-watchlist request yields one watchlist change and
    no trades."""
    result = build_mock_response("please add PYPL to my watchlist")

    assert result.trades == []
    assert len(result.watchlist_changes) == 1
    change = result.watchlist_changes[0]
    assert change.action == "add"
    assert change.ticker == "PYPL"


def test_build_mock_response_parses_watchlist_remove() -> None:
    """Test 5: a remove-from-watchlist request yields action=='remove'."""
    result = build_mock_response("remove META from the watchlist")

    assert len(result.watchlist_changes) == 1
    assert result.watchlist_changes[0].action == "remove"


def test_build_mock_response_conversational_fallback() -> None:
    """Test 6: a message with no trade or watchlist request yields a
    non-empty message with both action lists empty."""
    result = build_mock_response("how am I doing?")

    assert result.message
    assert result.trades == []
    assert result.watchlist_changes == []


def test_build_mock_response_always_prefixed() -> None:
    """Test 7: every branch's message begins with [LLM_MOCK], so a mock
    reply is never mistakable for genuine model output."""
    for text in ("buy 5 CSCO", "add PYPL to my watchlist", "how am I doing?"):
        result = build_mock_response(text)
        assert result.message.startswith("[LLM_MOCK]")


def test_build_mock_response_requires_watchlist_keyword() -> None:
    """Test 8: an add/remove verb alone, without the word "watchlist",
    yields no watchlist change — the watchlist branch requires both
    signals."""
    result = build_mock_response("add PYPL")

    assert result.watchlist_changes == []
