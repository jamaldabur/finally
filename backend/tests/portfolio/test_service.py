"""Service-level tests for app/portfolio/service.py::execute_trade() (Plan
02 Task 3, 01-VALIDATION.md 01-02-T3).

Exercises execute_trade() directly — no TestClient/HTTP layer — with real
async objects (PriceCache, SimulatorMarketDataSource, asyncio.Lock) rather
than mocks, following the same convention as backend/tests/market/test_cache.py.
Proves weighted-average cost math, both rejection result shapes, ticker
normalization, and that the portfolio lock actually serializes concurrent
trades (not just that it exists).
"""

import asyncio

import pytest

from app.db import portfolio_snapshots as portfolio_snapshots_module
from app.db import positions as positions_module
from app.db import trades as trades_module
from app.db import users_profile as users_profile_module
from app.market.cache import PriceCache
from app.market.simulator import SimulatorMarketDataSource
from app.portfolio.service import compute_portfolio_view, execute_trade


async def _init_tables() -> None:
    await users_profile_module.init_db()
    await positions_module.init_db()
    await trades_module.init_db()
    # execute_trade() writes an immediate portfolio_snapshots row on every
    # successful trade (DATA-04, Plan 04 Task 3) — this table must exist
    # before any of this module's execute_trade() calls, same as the other
    # three.
    await portfolio_snapshots_module.init_db()


@pytest.mark.asyncio
async def test_buy_then_buy_weights_avg_cost() -> None:
    await _init_tables()
    cache = PriceCache()
    market_source = SimulatorMarketDataSource()
    lock = asyncio.Lock()
    await cache.update("CSCO", 100.0)

    await execute_trade(
        price_cache=cache,
        market_source=market_source,
        lock=lock,
        ticker="CSCO",
        side="buy",
        quantity=10,
    )
    await cache.update("CSCO", 200.0)
    result = await execute_trade(
        price_cache=cache,
        market_source=market_source,
        lock=lock,
        ticker="CSCO",
        side="buy",
        quantity=30,
    )

    assert result.status == "executed"
    assert result.position is not None
    assert result.position.quantity == 40.0
    assert result.position.avg_cost == 175.0


@pytest.mark.asyncio
async def test_sell_does_not_change_avg_cost() -> None:
    await _init_tables()
    cache = PriceCache()
    market_source = SimulatorMarketDataSource()
    lock = asyncio.Lock()
    await cache.update("CSCO", 100.0)
    await execute_trade(
        price_cache=cache,
        market_source=market_source,
        lock=lock,
        ticker="CSCO",
        side="buy",
        quantity=10,
    )

    await cache.update("CSCO", 500.0)
    result = await execute_trade(
        price_cache=cache,
        market_source=market_source,
        lock=lock,
        ticker="CSCO",
        side="sell",
        quantity=5,
    )

    assert result.status == "executed"
    assert result.position is not None
    assert result.position.avg_cost == 100.0


@pytest.mark.asyncio
async def test_buy_insufficient_cash_returns_error_result() -> None:
    await _init_tables()
    cache = PriceCache()
    market_source = SimulatorMarketDataSource()
    lock = asyncio.Lock()
    await cache.update("CSCO", 100.0)

    result = await execute_trade(
        price_cache=cache,
        market_source=market_source,
        lock=lock,
        ticker="CSCO",
        side="buy",
        quantity=1000,
    )

    assert result.status == "error"
    assert result.reason is not None
    assert result.reason.startswith("Insufficient cash: ")
    assert result.trade is None


@pytest.mark.asyncio
async def test_sell_insufficient_shares_returns_error_result() -> None:
    await _init_tables()
    cache = PriceCache()
    market_source = SimulatorMarketDataSource()
    lock = asyncio.Lock()
    await cache.update("CSCO", 100.0)

    result = await execute_trade(
        price_cache=cache,
        market_source=market_source,
        lock=lock,
        ticker="CSCO",
        side="sell",
        quantity=1,
    )

    assert result.status == "error"
    assert result.reason is not None
    assert result.reason.startswith("Insufficient shares: ")
    assert result.trade is None


@pytest.mark.asyncio
async def test_unknown_ticker_returns_error_result() -> None:
    await _init_tables()
    cache = PriceCache()
    market_source = SimulatorMarketDataSource()
    lock = asyncio.Lock()

    result = await execute_trade(
        price_cache=cache,
        market_source=market_source,
        lock=lock,
        ticker="ZZZZ",
        side="buy",
        quantity=1,
    )

    assert result.status == "error"
    assert result.reason is not None
    assert result.reason.startswith("Unknown ticker: ")


@pytest.mark.asyncio
async def test_lowercase_ticker_is_normalized() -> None:
    await _init_tables()
    cache = PriceCache()
    market_source = SimulatorMarketDataSource()
    lock = asyncio.Lock()
    await cache.update("AAPL", 190.0)

    result = await execute_trade(
        price_cache=cache,
        market_source=market_source,
        lock=lock,
        ticker="aapl",
        side="buy",
        quantity=1,
    )

    assert result.status == "executed"
    assert result.position is not None
    assert result.position.ticker == "AAPL"
    assert result.trade is not None
    assert result.trade.ticker == "AAPL"


@pytest.mark.asyncio
async def test_concurrent_trades_are_serialized_by_the_lock() -> None:
    """Proves the lock prevents a double-spend rather than both requests
    reading the same pre-trade cash balance: 10000 cash, two concurrent
    buys of 60 shares each at 100.0 (6000 each, 12000 total) — only one
    can possibly succeed."""
    await _init_tables()
    cache = PriceCache()
    market_source = SimulatorMarketDataSource()
    lock = asyncio.Lock()
    await cache.update("CSCO", 100.0)

    results = await asyncio.gather(
        execute_trade(
            price_cache=cache,
            market_source=market_source,
            lock=lock,
            ticker="CSCO",
            side="buy",
            quantity=60,
        ),
        execute_trade(
            price_cache=cache,
            market_source=market_source,
            lock=lock,
            ticker="CSCO",
            side="buy",
            quantity=60,
        ),
    )

    statuses = sorted(r.status for r in results)
    assert statuses == ["error", "executed"]
    error_result = next(r for r in results if r.status == "error")
    assert error_result.reason is not None
    assert error_result.reason.startswith("Insufficient cash: ")

    final_cash = await users_profile_module.get_cash_balance()
    assert final_cash == 4000.0


@pytest.mark.asyncio
async def test_portfolio_view_computes_unrealized_pnl() -> None:
    """01-04-PLAN.md Task 2 behavior: buy 10 @ 100.0, move the cached price
    to 120.0; the view reports current_price/market_value/unrealized_pnl/
    pct_change/positions_value/total_value per the locked contract."""
    await _init_tables()
    cache = PriceCache()
    market_source = SimulatorMarketDataSource()
    lock = asyncio.Lock()
    await cache.update("CSCO", 100.0)
    await execute_trade(
        price_cache=cache,
        market_source=market_source,
        lock=lock,
        ticker="CSCO",
        side="buy",
        quantity=10,
    )

    await cache.update("CSCO", 120.0)
    view = await compute_portfolio_view(price_cache=cache)

    assert len(view.positions) == 1
    position = view.positions[0]
    assert position.ticker == "CSCO"
    assert position.current_price == 120.0
    assert position.market_value == 1200.0
    assert position.unrealized_pnl == 200.0
    assert position.pct_change == 20.0
    assert view.positions_value == 1200.0
    assert view.total_value == 10200.0


@pytest.mark.asyncio
async def test_portfolio_view_handles_loss() -> None:
    await _init_tables()
    cache = PriceCache()
    market_source = SimulatorMarketDataSource()
    lock = asyncio.Lock()
    await cache.update("CSCO", 100.0)
    await execute_trade(
        price_cache=cache,
        market_source=market_source,
        lock=lock,
        ticker="CSCO",
        side="buy",
        quantity=10,
    )

    await cache.update("CSCO", 90.0)
    view = await compute_portfolio_view(price_cache=cache)

    position = view.positions[0]
    assert position.unrealized_pnl == -100.0
    assert position.pct_change == -10.0


@pytest.mark.asyncio
async def test_portfolio_view_marks_unpriced_position_to_cost() -> None:
    """A position whose ticker has no entry in a fresh PriceCache is marked
    to cost rather than crashing the read or dropping out of total_value
    (the locked mark-to-cost fallback, 01-04-PLAN.md)."""
    await _init_tables()
    cache = PriceCache()
    market_source = SimulatorMarketDataSource()
    lock = asyncio.Lock()
    await cache.update("CSCO", 100.0)
    await execute_trade(
        price_cache=cache,
        market_source=market_source,
        lock=lock,
        ticker="CSCO",
        side="buy",
        quantity=10,
    )

    empty_cache = PriceCache()
    view = await compute_portfolio_view(price_cache=empty_cache)

    position = view.positions[0]
    assert position.current_price is None
    assert position.market_value == 1000.0
    assert position.unrealized_pnl == 0.0
    assert position.pct_change == 0.0
    assert view.total_value == 10000.0
