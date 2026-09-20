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
from app.db import watchlist as watchlist_module
from app.llm.actions import execute_llm_actions
from app.llm.schema import ChatResponseSchema, LlmTradeItem, LlmWatchlistChange
from app.market.cache import PriceCache
from app.market.simulator import SimulatorMarketDataSource


async def _init_tables() -> None:
    await users_profile_module.init_db()
    await positions_module.init_db()
    await trades_module.init_db()
    await portfolio_snapshots_module.init_db()
    await watchlist_module.init_db()


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


@pytest.mark.asyncio
async def test_execute_llm_actions_watchlist_add_and_remove_happy_path() -> None:
    """Adding a ticker not yet on the watchlist and removing one that is
    both report outcome == "executed", and the watchlist table reflects the
    changes (CR-01 / WR-03 happy-path coverage)."""
    await _init_tables()
    cache = PriceCache()
    market_source = SimulatorMarketDataSource()
    lock = asyncio.Lock()

    response = ChatResponseSchema(
        message="ok",
        watchlist_changes=[
            LlmWatchlistChange(ticker="PYPL", action="add"),
            LlmWatchlistChange(ticker="AAPL", action="remove"),
        ],
    )

    result = await execute_llm_actions(
        price_cache=cache,
        market_source=market_source,
        lock=lock,
        response=response,
    )

    assert len(result.watchlist_changes) == 2
    assert result.watchlist_changes[0].outcome == "executed"
    assert result.watchlist_changes[0].reason is None
    assert result.watchlist_changes[1].outcome == "executed"
    assert result.watchlist_changes[1].reason is None

    tickers = await watchlist_module.get_watchlist_tickers()
    assert "PYPL" in tickers
    assert "AAPL" not in tickers


@pytest.mark.asyncio
async def test_execute_llm_actions_watchlist_bad_item_annotated_error() -> None:
    """An invalid action string is rejected by _validate_watchlist_item()
    before ever touching the watchlist table."""
    await _init_tables()
    cache = PriceCache()
    market_source = SimulatorMarketDataSource()
    lock = asyncio.Lock()

    response = ChatResponseSchema(
        message="ok",
        watchlist_changes=[
            LlmWatchlistChange(ticker="PYPL", action="hold"),
        ],
    )

    result = await execute_llm_actions(
        price_cache=cache,
        market_source=market_source,
        lock=lock,
        response=response,
    )

    assert len(result.watchlist_changes) == 1
    assert result.watchlist_changes[0].outcome == "error"
    assert result.watchlist_changes[0].reason is not None

    tickers = await watchlist_module.get_watchlist_tickers()
    assert "PYPL" not in tickers


@pytest.mark.asyncio
async def test_execute_llm_actions_watchlist_unknown_ticker_rejected() -> None:
    """A ticker outside SimulatorMarketDataSource.TICKER_UNIVERSE is
    rejected with an error annotation and never reaches the watchlist
    table."""
    await _init_tables()
    cache = PriceCache()
    market_source = SimulatorMarketDataSource()
    lock = asyncio.Lock()

    response = ChatResponseSchema(
        message="ok",
        watchlist_changes=[
            LlmWatchlistChange(ticker="ZZZZ", action="add"),
        ],
    )

    result = await execute_llm_actions(
        price_cache=cache,
        market_source=market_source,
        lock=lock,
        response=response,
    )

    assert len(result.watchlist_changes) == 1
    assert result.watchlist_changes[0].outcome == "error"
    assert "Unknown ticker" in result.watchlist_changes[0].reason

    tickers = await watchlist_module.get_watchlist_tickers()
    assert "ZZZZ" not in tickers


@pytest.mark.asyncio
async def test_execute_llm_actions_watchlist_duplicate_items_not_collapsed() -> None:
    """Two identical watchlist add requests in the same response yield two
    independent annotations: the first actually inserts (executed), the
    second is a true no-op (error), matching CR-01's fixed contract."""
    await _init_tables()
    cache = PriceCache()
    market_source = SimulatorMarketDataSource()
    lock = asyncio.Lock()

    response = ChatResponseSchema(
        message="ok",
        watchlist_changes=[
            LlmWatchlistChange(ticker="PYPL", action="add"),
            LlmWatchlistChange(ticker="PYPL", action="add"),
        ],
    )

    result = await execute_llm_actions(
        price_cache=cache,
        market_source=market_source,
        lock=lock,
        response=response,
    )

    assert len(result.watchlist_changes) == 2
    assert result.watchlist_changes[0].outcome == "executed"
    assert result.watchlist_changes[1].outcome == "error"
    assert result.watchlist_changes[1].reason == "PYPL is already on the watchlist"


@pytest.mark.asyncio
async def test_execute_llm_actions_watchlist_noop_add_reports_error() -> None:
    """CR-01 regression: adding a ticker already on the watchlist must not
    be reported as "executed" — nothing was actually inserted."""
    await _init_tables()
    cache = PriceCache()
    market_source = SimulatorMarketDataSource()
    lock = asyncio.Lock()

    response = ChatResponseSchema(
        message="ok",
        watchlist_changes=[
            LlmWatchlistChange(ticker="AAPL", action="add"),  # already seeded
        ],
    )

    result = await execute_llm_actions(
        price_cache=cache,
        market_source=market_source,
        lock=lock,
        response=response,
    )

    assert len(result.watchlist_changes) == 1
    assert result.watchlist_changes[0].outcome == "error"
    assert result.watchlist_changes[0].reason == "AAPL is already on the watchlist"


@pytest.mark.asyncio
async def test_execute_llm_actions_watchlist_noop_remove_reports_error() -> None:
    """CR-01 regression: removing a ticker that isn't on the watchlist must
    not be reported as "executed" — nothing was actually deleted."""
    await _init_tables()
    cache = PriceCache()
    market_source = SimulatorMarketDataSource()
    lock = asyncio.Lock()

    response = ChatResponseSchema(
        message="ok",
        watchlist_changes=[
            LlmWatchlistChange(ticker="PYPL", action="remove"),  # never added
        ],
    )

    result = await execute_llm_actions(
        price_cache=cache,
        market_source=market_source,
        lock=lock,
        response=response,
    )

    assert len(result.watchlist_changes) == 1
    assert result.watchlist_changes[0].outcome == "error"
    assert result.watchlist_changes[0].reason == "PYPL is not on the watchlist"
