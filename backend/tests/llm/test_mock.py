"""Deterministic LLM_MOCK responses (PLAN.md §9 "LLM Mock Mode")."""

from app.llm.mock import build_mock_response
from app.llm.schema import WatchlistChangeAction


def test_buy_message_produces_buy_trade():
    result = build_mock_response("Buy 10 shares of AAPL")

    assert len(result.trades) == 1
    trade = result.trades[0]
    assert trade.ticker == "AAPL"
    assert trade.side == "buy"
    assert trade.quantity == 10
    assert result.watchlist_changes == []


def test_sell_message_produces_sell_trade():
    result = build_mock_response("sell 3 GOOGL")

    assert len(result.trades) == 1
    assert result.trades[0].ticker == "GOOGL"
    assert result.trades[0].side == "sell"
    assert result.trades[0].quantity == 3


def test_add_to_watchlist_message():
    result = build_mock_response("add PYPL to my watchlist")

    assert result.trades == []
    assert result.watchlist_changes == [WatchlistChangeAction(ticker="PYPL", action="add")]


def test_remove_from_watchlist_message():
    result = build_mock_response("remove PYPL from my watchlist")

    assert len(result.watchlist_changes) == 1
    assert result.watchlist_changes[0].ticker == "PYPL"
    assert result.watchlist_changes[0].action == "remove"


def test_unrecognized_message_has_no_actions():
    result = build_mock_response("What do you think of my portfolio?")

    assert result.trades == []
    assert result.watchlist_changes == []
    assert result.message


def test_response_is_deterministic():
    first = build_mock_response("Buy 5 shares of MSFT")
    second = build_mock_response("Buy 5 shares of MSFT")

    assert first == second


def test_lowercase_ticker_and_fractional_quantity():
    result = build_mock_response("buy 2.5 shares of aapl")

    assert len(result.trades) == 1
    assert result.trades[0].ticker == "AAPL"
    assert result.trades[0].quantity == 2.5


def test_sell_everything_has_no_ticker_falls_back_to_ack():
    # No recognizable ticker in "everything" (>5 letters) - by design this
    # mock does no real NLU, so it must fall back safely rather than guess.
    result = build_mock_response("sell everything")

    assert result.trades == []
    assert result.watchlist_changes == []
    assert result.message


def test_message_with_no_quantity_defaults_to_one():
    result = build_mock_response("buy AAPL")

    assert result.trades[0].quantity == 1.0


def test_message_mentioning_two_tickers_acts_on_first_match_only():
    # Documented, intentional limitation of the keyword-based mock (PLAN.md
    # §9 "don't overengineer a fake NLU") - it is not a real NLU and only
    # ever proposes a single action per message.
    result = build_mock_response("buy AAPL and sell GOOGL")

    assert len(result.trades) == 1
    assert result.trades[0].ticker == "AAPL"
    assert result.trades[0].side == "buy"


def test_no_recognized_intent_does_not_crash_or_misfire():
    result = build_mock_response("")

    assert result.trades == []
    assert result.watchlist_changes == []
    assert result.message


def test_known_ticker_preferred_over_incidental_capitalized_filler_word():
    # Regression: "MORE" used to win over "AAPL" because it wasn't in the
    # stopword list. A real ticker in TICKER_UNIVERSE must always take
    # priority over the bare all-caps heuristic.
    result = build_mock_response("buy 5 more AAPL")

    assert len(result.trades) == 1
    assert result.trades[0].ticker == "AAPL"
    assert result.trades[0].quantity == 5


def test_known_ticker_preferred_with_other_filler_phrasing():
    result = build_mock_response("I want to buy some more shares of TSLA please")

    assert len(result.trades) == 1
    assert result.trades[0].ticker == "TSLA"


def test_unrecognized_ticker_still_extracted_via_fallback_heuristic():
    # No real ticker present - falls back to the old heuristic so messages
    # naming a deliberately unrecognized symbol still produce an action
    # (which then fails downstream ticker validation, exercising that path).
    result = build_mock_response("buy 2 ZZZZ")

    assert len(result.trades) == 1
    assert result.trades[0].ticker == "ZZZZ"
