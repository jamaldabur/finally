"""Tests for app/llm/client.py::parse_llm_response() and is_mock_mode()
(03-01-PLAN.md Task 3, tests 8-10)."""

from __future__ import annotations

from app.llm.client import is_mock_mode, parse_llm_response


def test_parse_llm_response_never_raises_and_falls_back_to_message() -> None:
    """Test 8: empty content, non-JSON prose, and JSON that fails schema
    validation each return a ChatResponseSchema with a non-empty message and
    both action lists empty — none of them raise."""
    for raw in ("", "I think you should buy Apple.", '{"message": 42}'):
        result = parse_llm_response(raw)
        assert result.message
        assert result.trades == []
        assert result.watchlist_changes == []


def test_parse_llm_response_preserves_multibyte_characters() -> None:
    """Test 9: a message containing emoji and CJK characters survives
    model_validate_json() with identical code points."""
    raw = '{"message": "\\ud83d\\ude80 你好", "trades": [], "watchlist_changes": []}'
    result = parse_llm_response(raw)
    assert result.message == "\U0001f680 你好"


def test_is_mock_mode_reads_truthy_and_falsy_values(monkeypatch) -> None:
    """Test 10: is_mock_mode() returns True for "true"/"TRUE"/" true " and
    False for ""/"false"/unset."""
    for truthy in ("true", "TRUE", " true "):
        monkeypatch.setenv("LLM_MOCK", truthy)
        assert is_mock_mode() is True

    for falsy in ("", "false"):
        monkeypatch.setenv("LLM_MOCK", falsy)
        assert is_mock_mode() is False

    monkeypatch.delenv("LLM_MOCK", raising=False)
    assert is_mock_mode() is False
