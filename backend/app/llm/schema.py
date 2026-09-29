"""Pydantic response_format models for the LLM structured output (PLAN.md §9
"Structured Output Schema").

These are deliberately permissive: `LlmTradeItem.side`/`LlmWatchlistChange.action`
are plain `str`, and `LlmTradeItem.quantity` is a plain `float` with no
`Field(gt=0)` constraint. A constrained schema would make Pydantic reject the
*entire* response the instant one item is malformed (e.g. a hallucinated
negative quantity or an unrecognized side string), destroying the model's
conversational `message` along with it. Per-item validation belongs one layer
up, in `app/llm/actions.py::_validate_trade_item()` /
`_validate_watchlist_item()`, where a single bad item can be annotated
`error` without discarding the rest of the response.

`LlmTradeItem.quantity` and `LlmTradeItem.side` carry a `Field(description=...)`
— text only, no numeric bound, no exclusive bound, no enumerated type. A
description is a *signal* the provider reads from the emitted JSON Schema and
costs nothing when the backing model ignores it; a constraint is a *gate* that
discards an entire otherwise-good response the moment the model ignores it
(G-03-5). That asymmetry is why a description is the right tool for telling
the model the quantity sign convention, and a constraint is the wrong one —
this module still never gates on anything itself. `LlmWatchlistChange` is
deliberately left without a description: its own failure mode (a padded
`" add"` reaching the destructive branch) is closed structurally in
`app/llm/actions.py`'s single-normalization fix, so no provider-facing signal
is needed there.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class LlmTradeItem(BaseModel):
    ticker: str
    side: str = Field(description=(
        "buy or sell, lower case. side alone conveys the direction of the "
        "trade — a sell is never expressed by negating quantity."
    ))
    quantity: float = Field(description=(
        "A positive magnitude — a count of shares. Always positive, never "
        "signed; direction comes only from side."
    ))


class LlmWatchlistChange(BaseModel):
    ticker: str
    action: str


class ChatResponseSchema(BaseModel):
    message: str
    trades: list[LlmTradeItem] = []
    watchlist_changes: list[LlmWatchlistChange] = []
