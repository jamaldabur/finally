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
async def test_sell_at_a_loss_credits_market_price_and_keeps_avg_cost() -> None:
    """PLAN.md section 12 names "selling at a loss" as a backend portfolio
    edge case; no prior test in this file sold below average cost — every
    existing sell (e.g. test_sell_does_not_change_avg_cost) sells at or
    above the buy price. Buys 10 CSCO at 100.00, moves the cached price to
    80.00, then sells 4: proves the fill credits cash at the current market
    price (not the average cost), avg_cost is left unchanged on the
    remaining position, and compute_portfolio_view() reports the resulting
    unrealized loss."""
    await _init_tables()
    cache = PriceCache()
    market_source = SimulatorMarketDataSource()
    lock = asyncio.Lock()

    # Arrange: buy 10 CSCO at 100.00.
    await cache.update("CSCO", 100.0)
    await execute_trade(
        price_cache=cache,
        market_source=market_source,
        lock=lock,
        ticker="CSCO",
        side="buy",
        quantity=10,
    )

    # Act: price drops to 80.00, sell 4 shares.
    await cache.update("CSCO", 80.0)
    result = await execute_trade(
        price_cache=cache,
        market_source=market_source,
        lock=lock,
        ticker="CSCO",
        side="sell",
        quantity=4,
    )

    # Assert: fill at market price, cash and position reflect the loss, and
    # avg_cost on the remaining 6 shares is untouched by the sale.
    assert result.status == "executed"
    assert result.reason is None
    assert result.trade is not None
    assert result.trade.price == 80.0
    assert result.cash_balance == 9320.0
    assert result.position is not None
    assert result.position.quantity == 6.0
    assert result.position.avg_cost == 100.0

    assert await users_profile_module.get_cash_balance() == 9320.0

    view = await compute_portfolio_view(price_cache=cache)
    assert len(view.positions) == 1
    position = view.positions[0]
    assert position.current_price == 80.0
    assert position.market_value == 480.0
    assert position.unrealized_pnl == -120.0
    assert position.pct_change == -20.0
    assert view.total_value == 9800.0


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
async def test_execute_trade_rejects_invalid_quantity_and_side() -> None:
    """01-VALIDATION.md T-03-01 / STATE.md blocker: execute_trade() must
    reject a bad quantity or side for every caller (not just the HTTP
    route's Pydantic layer), since Phase 3's chat flow calls it directly.
    Tests 1-4 from 03-01-PLAN.md Task 3; test 5 (no new trades rows) is
    folded into each case via the cash-balance/positions assertions plus an
    explicit trades-count check at the end."""
    await _init_tables()
    cache = PriceCache()
    market_source = SimulatorMarketDataSource()
    lock = asyncio.Lock()
    await cache.update("CSCO", 100.0)

    starting_cash = await users_profile_module.get_cash_balance()

    # Test 1: negative quantity, valid side.
    result = await execute_trade(
        price_cache=cache,
        market_source=market_source,
        lock=lock,
        ticker="CSCO",
        side="buy",
        quantity=-100,
    )
    assert result.status == "error"
    assert await users_profile_module.get_cash_balance() == starting_cash

    # Test 2: zero quantity.
    result = await execute_trade(
        price_cache=cache,
        market_source=market_source,
        lock=lock,
        ticker="CSCO",
        side="buy",
        quantity=0,
    )
    assert result.status == "error"
    assert await users_profile_module.get_cash_balance() == starting_cash

    # Test 3: non-finite quantity (NaN and infinity).
    result = await execute_trade(
        price_cache=cache,
        market_source=market_source,
        lock=lock,
        ticker="CSCO",
        side="buy",
        quantity=float("nan"),
    )
    assert result.status == "error"
    result = await execute_trade(
        price_cache=cache,
        market_source=market_source,
        lock=lock,
        ticker="CSCO",
        side="buy",
        quantity=float("inf"),
    )
    assert result.status == "error"
    assert await users_profile_module.get_cash_balance() == starting_cash

    # Test 4: invalid side ("hold") and case-mismatched side ("BUY") must
    # both be rejected — neither may silently fall into the sell branch.
    result = await execute_trade(
        price_cache=cache,
        market_source=market_source,
        lock=lock,
        ticker="CSCO",
        side="hold",
        quantity=1,
    )
    assert result.status == "error"
    result = await execute_trade(
        price_cache=cache,
        market_source=market_source,
        lock=lock,
        ticker="CSCO",
        side="BUY",
        quantity=1,
    )
    assert result.status == "error"
    assert await users_profile_module.get_cash_balance() == starting_cash

    # Test 5: none of the rejected calls above wrote a trades row.
    all_trades = await trades_module.get_trades()
    assert all_trades == []


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
