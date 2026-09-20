"""Tests for app/llm/client.py::parse_llm_response() and is_mock_mode()
(03-01-PLAN.md Task 3, tests 8-10), plus G-03-3 gap-closure regression tests
(03-06-PLAN.md): code-fence recovery, a content-asserting fallback-message
oracle, a non-streaming structured call, and a one-shot transient-error
failover."""

from __future__ import annotations

import pytest

import app.llm.client as client_module
from app.llm.client import (
    FALLBACK_MODEL,
    LLM_UNAVAILABLE_MESSAGE,
    PARSE_FALLBACK_MESSAGE,
    get_chat_response,
    is_mock_mode,
    parse_llm_response,
)
from app.portfolio.service import PortfolioView

# The exact string from the UAT report (G-03-3, test 4) — a leaked
# schema-enforcement instruction from the free router's backing model.
UAT_GARBAGE = "Invalid placeholder, avoid outputting non-JSON text when schema is required."

FENCED_VALID_JSON = (
    "```json\n"
    '{"message": "Selling 2 shares of AAPL.", '
    '"trades": [{"ticker": "AAPL", "side": "sell", "quantity": 2}], '
    '"watchlist_changes": []}'
    "\n```"
)

UNTAGGED_FENCED_JSON = (
    "  \n```\n"
    '{"message": "hi there", "trades": [], "watchlist_changes": []}'
    "\n```  \n"
)


def _portfolio_view() -> PortfolioView:
    return PortfolioView(
        cash_balance=10000.0,
        positions=[],
        positions_value=0.0,
        total_value=10000.0,
        total_unrealized_pnl=0.0,
    )


def test_parse_llm_response_recovers_fenced_valid_json_tagged() -> None:
    """A response whose entire body is valid ChatResponseSchema JSON wrapped
    in a ```json fence parses to the inner object: message is the JSON's
    own message (fences absent), and the trade survives intact. This is the
    load-bearing fix for G-03-3 — without it the trade silently vanishes."""
    result = parse_llm_response(FENCED_VALID_JSON)
    assert result.message == "Selling 2 shares of AAPL."
    assert len(result.trades) == 1
    assert result.trades[0].ticker == "AAPL"
    assert result.trades[0].side == "sell"
    assert result.trades[0].quantity == 2


def test_parse_llm_response_recovers_untagged_fenced_json_with_whitespace() -> None:
    """The same recovery works for an untagged triple-backtick fence with
    surrounding whitespace and newlines."""
    result = parse_llm_response(UNTAGGED_FENCED_JSON)
    assert result.message == "hi there"
    assert result.trades == []
    assert result.watchlist_changes == []


@pytest.mark.parametrize(
    "raw",
    [
        UAT_GARBAGE,
        "I think you should buy Apple.",
        '{"message": 42}',
        "",
    ],
    ids=["uat-garbage", "plain-prose", "wrong-schema-json", "empty-string"],
)
def test_parse_llm_response_never_shows_raw_text_and_falls_back_to_constant(
    raw: str,
) -> None:
    """Every unparseable/unrecoverable input returns the exact constant
    PARSE_FALLBACK_MESSAGE — never the raw model text, however plausible it
    reads as prose. Content-asserting oracle: this replaces the truthiness
    check that let G-03-3 ship (03-UAT.md gap G-03-3, missing item 5)."""
    result = parse_llm_response(raw)
    assert result.message == PARSE_FALLBACK_MESSAGE
    assert raw not in result.message if raw else True
    assert result.trades == []
    assert result.watchlist_changes == []


def test_parse_llm_response_never_raises() -> None:
    """None of the failure inputs raise — the defensive-parse contract
    preserved from Plan 03-01."""
    for raw in ("", "I think you should buy Apple.", '{"message": 42}', UAT_GARBAGE):
        parse_llm_response(raw)  # must not raise


def test_parse_llm_response_preserves_multibyte_characters() -> None:
    """Test 9 (preserved unchanged): a message containing emoji and CJK
    characters survives model_validate_json() with identical code points."""
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


@pytest.mark.asyncio
async def test_get_chat_response_falls_back_when_call_llm_structured_raises(
    monkeypatch,
) -> None:
    """WR-02: the real (non-mock) path's try/except around
    _call_llm_structured() must actually protect callers — this is what
    keeps POST /api/chat from ever 500ing when OpenRouter is unreachable,
    rate-limited, or otherwise errors. Returns the named constant, not an
    ad-hoc string."""
    monkeypatch.delenv("LLM_MOCK", raising=False)

    async def _raise(messages: list[dict]) -> str:
        raise RuntimeError("simulated OpenRouter outage")

    monkeypatch.setattr(client_module, "_call_llm_structured", _raise)

    result = await get_chat_response(
        portfolio_view=_portfolio_view(),
        watchlist_entries=[],
        history=[],
        user_message="What's my portfolio worth?",
    )

    assert result.message == LLM_UNAVAILABLE_MESSAGE
    assert result.trades == []
    assert result.watchlist_changes == []


@pytest.mark.asyncio
async def test_get_chat_response_recovers_fenced_trades_end_to_end(
    monkeypatch,
) -> None:
    """Driving the real path end-to-end with the structured call stubbed to
    return the fenced response: get_chat_response() returns that response's
    trades intact — nothing between the call and the parse pre-empts the
    fence recovery (G-03-3's highest-severity finding: a correctly-formed,
    fenced response must never silently lose its trades)."""
    monkeypatch.delenv("LLM_MOCK", raising=False)

    async def _return_fenced(messages: list[dict]) -> str:
        return FENCED_VALID_JSON

    monkeypatch.setattr(client_module, "_call_llm_structured", _return_fenced)

    result = await get_chat_response(
        portfolio_view=_portfolio_view(),
        watchlist_entries=[],
        history=[],
        user_message="sell 2 AAPL",
    )

    assert result.message == "Selling 2 shares of AAPL."
    assert len(result.trades) == 1
    assert result.trades[0].ticker == "AAPL"


class _FakeMessage:
    def __init__(self, content: str | None) -> None:
        self.content = content


class _FakeChoice:
    def __init__(self, content: str | None) -> None:
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content: str | None) -> None:
        self.choices = [_FakeChoice(content)]


@pytest.mark.asyncio
async def test_call_llm_structured_passes_no_truthy_streaming_flag(monkeypatch) -> None:
    """The structured call passes no truthy streaming keyword — dropping
    stream=True is what restores real exceptions and logging at the call
    site (G-03-3's load-bearing config cause)."""
    captured_kwargs: dict = {}

    async def _fake_acompletion(**kwargs):
        captured_kwargs.update(kwargs)
        return _FakeResponse('{"message": "ok", "trades": [], "watchlist_changes": []}')

    monkeypatch.setattr(client_module, "acompletion", _fake_acompletion)

    await client_module._call_llm_structured([{"role": "user", "content": "hi"}])

    assert not captured_kwargs.get("stream")


@pytest.mark.asyncio
async def test_call_llm_structured_returns_empty_string_for_missing_content(
    monkeypatch,
) -> None:
    """A response whose content is missing yields an empty string rather
    than raising."""

    async def _fake_acompletion(**kwargs):
        return _FakeResponse(None)

    monkeypatch.setattr(client_module, "acompletion", _fake_acompletion)

    result = await client_module._call_llm_structured([{"role": "user", "content": "hi"}])

    assert result == ""


@pytest.mark.asyncio
async def test_call_llm_structured_fails_over_once_on_transient_error(monkeypatch) -> None:
    """A transient provider error on the primary model triggers exactly one
    further call, against FALLBACK_MODEL, with the identical message list.
    The value returned is the fallback's content."""
    messages = [{"role": "user", "content": "sell 2 AAPL"}]
    calls: list[tuple[str, list[dict]]] = []

    async def _fake_acompletion(**kwargs):
        calls.append((kwargs["model"], kwargs["messages"]))
        if kwargs["model"] == client_module.MODEL:
            raise client_module.RateLimitError(
                message="rate limited", llm_provider="openrouter", model=client_module.MODEL
            )
        return _FakeResponse('{"message": "fallback reply", "trades": [], "watchlist_changes": []}')

    monkeypatch.setattr(client_module, "acompletion", _fake_acompletion)

    result = await client_module._call_llm_structured(messages)

    assert result == '{"message": "fallback reply", "trades": [], "watchlist_changes": []}'
    assert len(calls) == 2
    assert calls[0][0] == client_module.MODEL
    assert calls[1][0] == FALLBACK_MODEL
    assert calls[0][1] is messages
    assert calls[1][1] is messages


@pytest.mark.asyncio
async def test_call_llm_structured_never_exceeds_two_calls_when_both_fail(
    monkeypatch,
) -> None:
    """The total number of completion calls for one turn never exceeds two,
    even when both the primary and the fallback fail."""
    calls: list[str] = []

    async def _fake_acompletion(**kwargs):
        calls.append(kwargs["model"])
        raise client_module.RateLimitError(
            message="rate limited", llm_provider="openrouter", model=kwargs["model"]
        )

    monkeypatch.setattr(client_module, "acompletion", _fake_acompletion)

    with pytest.raises(client_module.RateLimitError):
        await client_module._call_llm_structured([{"role": "user", "content": "hi"}])

    assert len(calls) == 2
    assert calls == [client_module.MODEL, FALLBACK_MODEL]


@pytest.mark.asyncio
async def test_call_llm_structured_does_not_fail_over_on_authentication_error(
    monkeypatch,
) -> None:
    """An authentication error on the primary triggers no second call at
    all and propagates out of the structured call helper — a real
    configuration bug must not be masked by a second model."""
    calls: list[str] = []

    async def _fake_acompletion(**kwargs):
        calls.append(kwargs["model"])
        raise client_module.AuthenticationError(
            message="bad key", llm_provider="openrouter", model=kwargs["model"]
        )

    monkeypatch.setattr(client_module, "acompletion", _fake_acompletion)

    with pytest.raises(client_module.AuthenticationError):
        await client_module._call_llm_structured([{"role": "user", "content": "hi"}])

    assert calls == [client_module.MODEL]


@pytest.mark.asyncio
async def test_get_chat_response_returns_unavailable_message_when_both_models_fail(
    monkeypatch, caplog
) -> None:
    """When both models fail, get_chat_response() returns exactly
    LLM_UNAVAILABLE_MESSAGE with empty action lists and emits an
    error-level log record — every degraded turn must be attributable."""
    monkeypatch.delenv("LLM_MOCK", raising=False)

    async def _fake_acompletion(**kwargs):
        raise client_module.RateLimitError(
            message="rate limited", llm_provider="openrouter", model=kwargs["model"]
        )

    monkeypatch.setattr(client_module, "acompletion", _fake_acompletion)

    with caplog.at_level("ERROR"):
        result = await get_chat_response(
            portfolio_view=_portfolio_view(),
            watchlist_entries=[],
            history=[],
            user_message="sell 2 AAPL",
        )

    assert result.message == LLM_UNAVAILABLE_MESSAGE
    assert result.trades == []
    assert result.watchlist_changes == []
    assert any(record.levelname == "ERROR" for record in caplog.records)


@pytest.mark.asyncio
async def test_mock_mode_never_calls_completion_function(monkeypatch) -> None:
    """With mock mode enabled, the completion function is never called at
    all."""
    monkeypatch.setenv("LLM_MOCK", "true")
    calls: list[str] = []

    async def _fake_acompletion(**kwargs):
        calls.append(kwargs["model"])
        return _FakeResponse('{"message": "should not be called", "trades": [], "watchlist_changes": []}')

    monkeypatch.setattr(client_module, "acompletion", _fake_acompletion)

    await get_chat_response(
        portfolio_view=_portfolio_view(),
        watchlist_entries=[],
        history=[],
        user_message="hi",
    )

    assert calls == []
