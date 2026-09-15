"""The two-call chat LLM interface (PLAN.md §7): `stream_chat_message` (the
streamed, unstructured conversational reply) and `get_actions` (the
separate, structured trades/watchlist_changes call). Covers LLM_MOCK
simulated streaming, primary/fallback failover for both calls (including the
"no failover once something has already streamed" rule), and the actions
call's malformed-response recovery/degradation.
"""

import pytest
from litellm import RateLimitError, ServiceUnavailableError

import app.llm.client as client_module
from app.llm.client import get_actions, stream_chat_message
from app.llm.schema import ActionsResult


async def _collect(async_iter):
    return [chunk async for chunk in async_iter]


def _rate_limit_error(model: str) -> RateLimitError:
    return RateLimitError(message="rate limited", llm_provider="openrouter", model=model)


# ---- LLM_MOCK ----


async def test_mock_stream_yields_multiple_chunks_that_join_to_mock_message(monkeypatch):
    monkeypatch.setenv("LLM_MOCK", "true")

    chunks = await _collect(stream_chat_message([], "Buy 4 shares of AAPL"))

    assert "".join(chunks) == "Mock: buying 4 share(s) of AAPL."
    assert len(chunks) > 1  # genuinely chunked, not one blob


async def test_mock_actions_match_mock_response_for_action_message(monkeypatch):
    monkeypatch.setenv("LLM_MOCK", "true")

    result = await get_actions([], "Buy 4 shares of AAPL")

    assert len(result.trades) == 1
    assert result.trades[0].ticker == "AAPL"
    assert result.trades[0].side == "buy"
    assert result.watchlist_changes == []


async def test_mock_actions_empty_for_non_action_message(monkeypatch):
    monkeypatch.setenv("LLM_MOCK", "true")

    result = await get_actions([], "How is my portfolio doing?")

    assert result == ActionsResult()


# ---- stream_chat_message failover ----


async def test_stream_fails_over_before_yielding_anything(monkeypatch):
    monkeypatch.delenv("LLM_MOCK", raising=False)

    async def _fake_stream(model, messages):
        if model == client_module.MODEL:
            raise _rate_limit_error(model)
        yield "hello "
        yield "world"

    monkeypatch.setattr(client_module, "_stream_model_text", _fake_stream)

    chunks = await _collect(stream_chat_message([], "hi"))

    assert "".join(chunks) == "hello world"


async def test_stream_mid_failure_does_not_fail_over(monkeypatch):
    # Once real text has already reached the client, switching models would
    # mix two different answers together - stop there instead.
    monkeypatch.delenv("LLM_MOCK", raising=False)
    calls = []

    async def _fake_stream(model, messages):
        calls.append(model)
        yield "partial "
        raise _rate_limit_error(model)

    monkeypatch.setattr(client_module, "_stream_model_text", _fake_stream)

    chunks = await _collect(stream_chat_message([], "hi"))

    assert "".join(chunks) == "partial "
    assert calls == [client_module.MODEL]


async def test_stream_both_models_fail_before_yielding_uses_fallback_message(monkeypatch):
    monkeypatch.delenv("LLM_MOCK", raising=False)

    async def _fake_stream(model, messages):
        raise _rate_limit_error(model)
        yield  # pragma: no cover - unreachable; keeps this an async generator

    monkeypatch.setattr(client_module, "_stream_model_text", _fake_stream)

    chunks = await _collect(stream_chat_message([], "hi"))

    assert "".join(chunks) == client_module.FALLBACK_MESSAGE


async def test_stream_non_transient_error_skips_fallback_model(monkeypatch):
    monkeypatch.delenv("LLM_MOCK", raising=False)
    calls = []

    async def _fake_stream(model, messages):
        calls.append(model)
        raise RuntimeError("boom")
        yield  # pragma: no cover - unreachable; keeps this an async generator

    monkeypatch.setattr(client_module, "_stream_model_text", _fake_stream)

    chunks = await _collect(stream_chat_message([], "hi"))

    assert "".join(chunks) == client_module.FALLBACK_MESSAGE
    assert calls == [client_module.MODEL]


async def test_stream_recovers_when_model_replies_with_json_instead_of_prose(monkeypatch):
    # Regression: reported live as "trades not executing" - the model
    # actually ignored the "plain language, no JSON" instruction and echoed
    # a full JSON blob (shaped like the old combined schema) as its reply,
    # which streamed as garbled JSON fragments in the chat bubble even
    # though the real, separate actions call executed the trades correctly.
    monkeypatch.delenv("LLM_MOCK", raising=False)

    async def _fake_stream(model, messages):
        for chunk in ['{"message": "Selling ', 'NVDA.", "trades": [{"ticker": "NVDA"}]}']:
            yield chunk

    monkeypatch.setattr(client_module, "_stream_model_text", _fake_stream)

    chunks = await _collect(stream_chat_message([], "sell NVDA"))

    # Recovered cleanly - just the extracted message, not raw JSON fragments.
    assert chunks == ["Selling NVDA."]


async def test_stream_json_reply_without_message_field_falls_back_to_raw_text(monkeypatch):
    monkeypatch.delenv("LLM_MOCK", raising=False)

    async def _fake_stream(model, messages):
        yield '{"trades": []}'

    monkeypatch.setattr(client_module, "_stream_model_text", _fake_stream)

    chunks = await _collect(stream_chat_message([], "hi"))

    assert chunks == ['{"trades": []}']


async def test_stream_code_fenced_json_reply_is_recovered(monkeypatch):
    monkeypatch.delenv("LLM_MOCK", raising=False)

    async def _fake_stream(model, messages):
        for chunk in ["```json\n", '{"message": "hi"}', "\n```"]:
            yield chunk

    monkeypatch.setattr(client_module, "_stream_model_text", _fake_stream)

    chunks = await _collect(stream_chat_message([], "hi"))

    assert chunks == ["hi"]


async def test_stream_normal_prose_is_unaffected_by_json_sniffing(monkeypatch):
    monkeypatch.delenv("LLM_MOCK", raising=False)

    async def _fake_stream(model, messages):
        yield "Your "
        yield "portfolio is up."

    monkeypatch.setattr(client_module, "_stream_model_text", _fake_stream)

    chunks = await _collect(stream_chat_message([], "how am I doing?"))

    assert chunks == ["Your ", "portfolio is up."]


# ---- get_actions ----


def test_looks_action_oriented():
    assert client_module._looks_action_oriented("buy 5 AAPL")
    assert client_module._looks_action_oriented("please sell my TSLA")
    assert client_module._looks_action_oriented("add PYPL to my watchlist")
    assert not client_module._looks_action_oriented("how is my portfolio doing?")


async def test_get_actions_skips_llm_call_for_non_action_message(monkeypatch):
    monkeypatch.delenv("LLM_MOCK", raising=False)
    called = []

    async def _fake_structured(messages, response_format):
        called.append(response_format)
        return '{"trades": [], "watchlist_changes": []}'

    monkeypatch.setattr(client_module, "_call_structured_llm", _fake_structured)

    result = await get_actions([], "How is my portfolio doing?")

    assert result == ActionsResult()
    assert called == []


async def test_get_actions_calls_llm_for_action_oriented_message(monkeypatch):
    monkeypatch.delenv("LLM_MOCK", raising=False)

    async def _fake_structured(messages, response_format):
        return '{"trades": [{"ticker": "AAPL", "side": "buy", "quantity": 5}]}'

    monkeypatch.setattr(client_module, "_call_structured_llm", _fake_structured)

    result = await get_actions([], "buy 5 AAPL")

    assert result.trades[0].ticker == "AAPL"


async def test_get_actions_llm_failure_degrades_to_no_actions(monkeypatch):
    monkeypatch.delenv("LLM_MOCK", raising=False)

    async def _raise(messages, response_format):
        raise RuntimeError("boom")

    monkeypatch.setattr(client_module, "_call_structured_llm", _raise)

    result = await get_actions([], "buy 5 AAPL")

    assert result == ActionsResult()


async def test_get_actions_recovers_code_fenced_json(monkeypatch):
    monkeypatch.delenv("LLM_MOCK", raising=False)
    fenced = '```json\n{"trades": [{"ticker": "AAPL", "side": "buy", "quantity": 1}]}\n```'

    async def _fake_structured(messages, response_format):
        return fenced

    monkeypatch.setattr(client_module, "_call_structured_llm", _fake_structured)

    result = await get_actions([], "buy AAPL")

    assert result.trades[0].ticker == "AAPL"


async def test_get_actions_unrecoverable_malformed_response_degrades_to_no_actions(monkeypatch):
    monkeypatch.delenv("LLM_MOCK", raising=False)

    async def _fake_structured(messages, response_format):
        return "not json at all and no fence around it"

    monkeypatch.setattr(client_module, "_call_structured_llm", _fake_structured)

    result = await get_actions([], "buy AAPL")

    assert result == ActionsResult()


# ---- _call_structured_llm failover (shared by get_actions) ----


async def test_structured_call_fails_over_on_transient_error(monkeypatch):
    calls = []

    async def _fake_call(model, messages, response_format):
        calls.append(model)
        if model == client_module.MODEL:
            raise _rate_limit_error(model)
        return '{"trades": [], "watchlist_changes": []}'

    monkeypatch.setattr(client_module, "_call_model_json", _fake_call)

    result = await client_module._call_structured_llm([], ActionsResult)

    assert result == '{"trades": [], "watchlist_changes": []}'
    assert calls == [client_module.MODEL, client_module.FALLBACK_MODEL]


async def test_structured_call_other_transient_error_types_also_fail_over(monkeypatch):
    calls = []

    async def _fake_call(model, messages, response_format):
        calls.append(model)
        if model == client_module.MODEL:
            raise ServiceUnavailableError(
                message="temporarily overloaded", llm_provider="openrouter", model=model
            )
        return '{"trades": [], "watchlist_changes": []}'

    monkeypatch.setattr(client_module, "_call_model_json", _fake_call)

    result = await client_module._call_structured_llm([], ActionsResult)

    assert result == '{"trades": [], "watchlist_changes": []}'
    assert calls == [client_module.MODEL, client_module.FALLBACK_MODEL]


async def test_structured_call_non_transient_error_skips_fallback(monkeypatch):
    calls = []

    async def _fake_call(model, messages, response_format):
        calls.append(model)
        raise RuntimeError("boom")

    monkeypatch.setattr(client_module, "_call_model_json", _fake_call)

    with pytest.raises(RuntimeError):
        await client_module._call_structured_llm([], ActionsResult)

    assert calls == [client_module.MODEL]
