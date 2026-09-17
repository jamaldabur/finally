"""Tests for app/llm/actions.py::execute_llm_actions() (03-01-PLAN.md Task 3,
tests 6-7).

Builds ChatResponseSchema instances directly rather than going through the
route, and drives them through execute_llm_actions() with a real
PriceCache, the simulator market source, and a real asyncio.Lock — same
convention as backend/tests/portfolio/test_service.py.
"""

from __future__ import annotations

import asyncio

import pytest

from app.db import portfolio_snapshots as portfolio_snapshots_module
from app.db import positions as positions_module
from app.db import trades as trades_module
from app.db import users_profile as users_profile_module
from app.llm.actions import execute_llm_actions
from app.llm.schema import ChatResponseSchema, LlmTradeItem
from app.market.cache import PriceCache
from app.market.simulator import SimulatorMarketDataSource


async def _init_tables() -> None:
    await users_profile_module.init_db()
    await positions_module.init_db()
    await trades_module.init_db()
    await portfolio_snapshots_module.init_db()


@pytest.mark.asyncio
async def test_execute_llm_actions_annotates_bad_item_and_executes_good_one() -> None:
    """Test 6: one bad item (quantity=-1) and one good item yield two
    annotations in source order — error then executed — and only the good
    one produced a trade."""
    await _init_tables()
    cache = PriceCache()
    market_source = SimulatorMarketDataSource()
    lock = asyncio.Lock()
    await cache.update("CSCO", 100.0)

    response = ChatResponseSchema(
        message="ok",
        trades=[
            LlmTradeItem(ticker="CSCO", side="buy", quantity=-1),
            LlmTradeItem(ticker="CSCO", side="buy", quantity=5),
        ],
    )

    result = await execute_llm_actions(
        price_cache=cache,
        market_source=market_source,
        lock=lock,
        response=response,
    )

    assert len(result.trades) == 2
    assert result.trades[0].outcome == "error"
    assert result.trades[1].outcome == "executed"

    all_trades = await trades_module.get_trades()
    assert len(all_trades) == 1
    assert all_trades[0].quantity == 5


@pytest.mark.asyncio
async def test_execute_llm_actions_does_not_collapse_duplicate_items() -> None:
    """Test 7: two identical trade items yield two independent executed
    annotations, and the cash balance reflects both fills."""
    await _init_tables()
    cache = PriceCache()
    market_source = SimulatorMarketDataSource()
    lock = asyncio.Lock()
    await cache.update("CSCO", 100.0)

    response = ChatResponseSchema(
        message="ok",
        trades=[
            LlmTradeItem(ticker="CSCO", side="buy", quantity=5),
            LlmTradeItem(ticker="CSCO", side="buy", quantity=5),
        ],
    )

    result = await execute_llm_actions(
        price_cache=cache,
        market_source=market_source,
        lock=lock,
        response=response,
    )

    assert len(result.trades) == 2
    assert result.trades[0].outcome == "executed"
    assert result.trades[1].outcome == "executed"

    cash = await users_profile_module.get_cash_balance()
    assert cash == 9000.0
