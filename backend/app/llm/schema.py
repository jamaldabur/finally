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
"""

from __future__ import annotations

from pydantic import BaseModel


class LlmTradeItem(BaseModel):
    ticker: str
    side: str
    quantity: float


class LlmWatchlistChange(BaseModel):
    ticker: str
    action: str


class ChatResponseSchema(BaseModel):
    message: str
    trades: list[LlmTradeItem] = []
    watchlist_changes: list[LlmWatchlistChange] = []
