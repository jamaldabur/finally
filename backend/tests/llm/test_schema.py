"""Structured-output schema parsing (PLAN.md §7 "Structured Output Schema")."""

from app.llm.schema import ActionsResult, ChatCompletionResult


def test_parses_message_only_response():
    result = ChatCompletionResult.model_validate_json('{"message": "Hello"}')

    assert result.message == "Hello"
    assert result.trades == []
    assert result.watchlist_changes == []


def test_parses_response_with_trades():
    payload = '{"message": "Buying", "trades": [{"ticker": "AAPL", "side": "buy", "quantity": 10}]}'

    result = ChatCompletionResult.model_validate_json(payload)

    assert len(result.trades) == 1
    trade = result.trades[0]
    assert trade.ticker == "AAPL"
    assert trade.side == "buy"
    assert trade.quantity == 10


def test_parses_response_with_watchlist_changes():
    payload = (
        '{"message": "Adding", '
        '"watchlist_changes": [{"ticker": "PYPL", "action": "add"}]}'
    )

    result = ChatCompletionResult.model_validate_json(payload)

    assert len(result.watchlist_changes) == 1
    change = result.watchlist_changes[0]
    assert change.ticker == "PYPL"
    assert change.action == "add"


def test_parses_response_with_both_trades_and_watchlist_changes():
    payload = (
        '{"message": "Doing both", '
        '"trades": [{"ticker": "AAPL", "side": "sell", "quantity": 2}], '
        '"watchlist_changes": [{"ticker": "PYPL", "action": "remove"}]}'
    )

    result = ChatCompletionResult.model_validate_json(payload)

    assert result.trades[0].side == "sell"
    assert result.watchlist_changes[0].action == "remove"


def test_actions_result_defaults_to_empty():
    result = ActionsResult.model_validate_json("{}")

    assert result.trades == []
    assert result.watchlist_changes == []


def test_actions_result_parses_trades_and_watchlist_changes():
    payload = (
        '{"trades": [{"ticker": "AAPL", "side": "buy", "quantity": 5}], '
        '"watchlist_changes": [{"ticker": "PYPL", "action": "add"}]}'
    )

    result = ActionsResult.model_validate_json(payload)

    assert result.trades[0].ticker == "AAPL"
    assert result.watchlist_changes[0].action == "add"
