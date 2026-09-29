"""Contract tests for app/llm/schema.py's generated JSON Schema (03-08-PLAN.md
Task 2, G-03-5 gap closure).

Assertions are driven off `ChatResponseSchema.model_json_schema()` — the
generated schema is what actually reaches the provider via
`response_format=ChatResponseSchema` (app/llm/client.py::_call_model_once) —
rather than off the pydantic class attributes, so this test is meaningful
rather than a restatement of the source.
"""

from __future__ import annotations

from app.llm.client import MODEL, SYSTEM_PROMPT
from app.llm.schema import ChatResponseSchema, LlmTradeItem, LlmWatchlistChange


def _trade_item_properties() -> dict:
    schema = ChatResponseSchema.model_json_schema()
    return schema["$defs"]["LlmTradeItem"]["properties"]


def test_trade_item_quantity_and_side_carry_descriptions() -> None:
    """The emitted JSON Schema — what the provider actually enforces — must
    carry a non-empty description on both quantity and side, telling the
    model the sign convention (G-03-5)."""
    properties = _trade_item_properties()

    assert isinstance(properties["quantity"].get("description"), str)
    assert properties["quantity"]["description"].strip() != ""
    assert isinstance(properties["side"].get("description"), str)
    assert properties["side"]["description"].strip() != ""


def test_trade_item_quantity_and_side_carry_no_constraint() -> None:
    """No lower bound, exclusive lower bound, or enumeration on either
    field — a constraint would make pydantic reject the entire response the
    instant one item is malformed, destroying the conversational message
    and every other valid action alongside it (schema.py's own docstring)."""
    properties = _trade_item_properties()

    for field in ("quantity", "side"):
        prop = properties[field]
        assert "minimum" not in prop
        assert "exclusiveMinimum" not in prop
        assert "enum" not in prop


def test_malformed_trade_item_still_parses_into_chat_response_schema() -> None:
    """A response containing a trade item with a negative quantity and an
    unrecognized side still validates into ChatResponseSchema, with the
    message intact and the item present — per-item annotation happens one
    layer up in app/llm/actions.py, never by pydantic rejecting the whole
    response."""
    response = ChatResponseSchema(
        message="Attempting a trade.",
        trades=[LlmTradeItem(ticker="AAPL", side="sideways", quantity=-5)],
    )

    assert response.message == "Attempting a trade."
    assert len(response.trades) == 1
    assert response.trades[0].side == "sideways"
    assert response.trades[0].quantity == -5


def test_watchlist_change_schema_is_unchanged() -> None:
    """LlmWatchlistChange deliberately gets no field description this
    round — its padded-action failure is closed structurally by Task 1's
    single normalization (planner_assumptions #2)."""
    schema = ChatResponseSchema.model_json_schema()
    properties = schema["$defs"]["LlmWatchlistChange"]["properties"]

    assert "description" not in properties["ticker"]
    assert "description" not in properties["action"]

    # Still permissive — a bad action string still parses.
    change = LlmWatchlistChange(ticker="AAPL", action="hold")
    assert change.action == "hold"


def test_system_prompt_states_quantity_is_positive_and_side_conveys_direction() -> None:
    """SYSTEM_PROMPT carries a hard-constraint rule matching Task 1's
    recovery: quantity is always a positive magnitude, and side alone
    conveys direction, so a sell must never be expressed as a negative
    quantity."""
    lowered = SYSTEM_PROMPT.lower()
    assert "positive" in lowered
    assert "quantity" in lowered
    assert "side" in lowered
    assert "negative" in lowered


def test_model_constant_unchanged() -> None:
    """This gap-closure round does not revisit Plan 03-01's user-approved
    model deviation."""
    assert MODEL == "openrouter/openrouter/free"
