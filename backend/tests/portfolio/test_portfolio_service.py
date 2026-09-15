"""Unit tests for app/portfolio/service.py.

`app_state` is stubbed with a fake price_cache rather than driving the real
simulator, per the team's testing convention (see tests/db/conftest.py for
the parallel DB isolation fixture)."""

from types import SimpleNamespace

import pytest

from app.db import portfolio_snapshots, positions, trades, users
from app.market.base import ChangeDirection, PriceTick
from app.portfolio.service import TradeError, execute_trade, get_portfolio_state


class _FakeCache:
    def __init__(self, prices: dict[str, float]):
        self._prices = prices

    async def get(self, ticker: str):
        if ticker not in self._prices:
            return None
        price = self._prices[ticker]
        return PriceTick(ticker, price, price, None, ChangeDirection.UNCHANGED)


def _app_state(prices: dict[str, float]):
    return SimpleNamespace(price_cache=_FakeCache(prices))


@pytest.fixture(autouse=True)
async def seeded_db():
    await users.init_db()
    await positions.init_db()
    await trades.init_db()
    await portfolio_snapshots.init_db()


async def test_buy_deducts_cash_and_creates_position():
    state = _app_state({"AAPL": 100.0})

    fill = await execute_trade(state, "AAPL", "buy", 10, user_id="default")

    assert fill == {
        "ticker": "AAPL",
        "side": "buy",
        "quantity": 10,
        "price": 100.0,
        "executed_at": fill["executed_at"],
    }
    assert await users.get_cash_balance("default") == 9000.0
    position = await positions.get_position("default", "AAPL")
    assert position["quantity"] == 10
    assert position["avg_cost"] == 100.0


async def test_buy_normalizes_lowercase_ticker():
    state = _app_state({"AAPL": 100.0})

    fill = await execute_trade(state, "aapl", "buy", 10, user_id="default")

    assert fill["ticker"] == "AAPL"
    position = await positions.get_position("default", "AAPL")
    assert position["quantity"] == 10


async def test_sell_adds_cash_and_reduces_position():
    state = _app_state({"AAPL": 100.0})
    await execute_trade(state, "AAPL", "buy", 10, user_id="default")

    state = _app_state({"AAPL": 120.0})
    fill = await execute_trade(state, "AAPL", "sell", 4, user_id="default")

    assert fill["price"] == 120.0
    assert await users.get_cash_balance("default") == 9000.0 + 4 * 120.0
    position = await positions.get_position("default", "AAPL")
    assert position["quantity"] == 6


async def test_sell_at_a_loss_still_succeeds():
    state = _app_state({"AAPL": 100.0})
    await execute_trade(state, "AAPL", "buy", 10, user_id="default")

    state = _app_state({"AAPL": 50.0})
    fill = await execute_trade(state, "AAPL", "sell", 10, user_id="default")

    assert fill["price"] == 50.0
    assert await users.get_cash_balance("default") == 9000.0 + 10 * 50.0
    assert await positions.get_position("default", "AAPL") is None


async def test_buy_with_insufficient_cash_raises():
    state = _app_state({"AAPL": 100000.0})

    with pytest.raises(TradeError, match="insufficient cash"):
        await execute_trade(state, "AAPL", "buy", 1, user_id="default")


async def test_sell_more_than_owned_raises():
    state = _app_state({"AAPL": 100.0})
    await execute_trade(state, "AAPL", "buy", 5, user_id="default")

    with pytest.raises(TradeError, match="insufficient shares"):
        await execute_trade(state, "AAPL", "sell", 10, user_id="default")


async def test_buy_exactly_exhausting_cash_succeeds_despite_float_noise():
    # price=282.56, quantity=10000/282.56 computes quantity*price as
    # 10000.000000000002 in float64 — a strict `>` comparison against the
    # $10,000 starting balance would spuriously reject this trade.
    price = 282.56
    quantity = 10000.0 / price
    assert quantity * price > 10000.0  # sanity-check the float noise exists
    state = _app_state({"AAPL": price})

    fill = await execute_trade(state, "AAPL", "buy", quantity, user_id="default")

    assert fill["quantity"] == quantity
    assert await users.get_cash_balance("default") == pytest.approx(0.0, abs=1e-6)


async def test_sell_all_within_epsilon_of_owned_quantity_succeeds():
    state = _app_state({"AAPL": 100.0})
    await execute_trade(state, "AAPL", "buy", 10, user_id="default")

    # Simulate a client-computed "sell everything" quantity that overshoots
    # the stored 10.0 by float noise smaller than the tolerance.
    fill = await execute_trade(
        state, "AAPL", "sell", 10.0 + 1e-9, user_id="default"
    )

    assert fill["quantity"] == 10.0
    assert await positions.get_position("default", "AAPL") is None


async def test_nan_quantity_raises_instead_of_bypassing_validation():
    # NaN <= 0 is False in Python, so a naive `quantity <= 0` check alone
    # would let a NaN quantity slip through and corrupt a position.
    state = _app_state({"AAPL": 100.0})

    with pytest.raises(TradeError, match="quantity must be positive"):
        await execute_trade(state, "AAPL", "buy", float("nan"), user_id="default")


async def test_infinite_quantity_raises():
    state = _app_state({"AAPL": 100.0})

    with pytest.raises(TradeError, match="quantity must be positive"):
        await execute_trade(state, "AAPL", "buy", float("inf"), user_id="default")


async def test_sell_with_no_position_raises():
    state = _app_state({"AAPL": 100.0})

    with pytest.raises(TradeError, match="insufficient shares"):
        await execute_trade(state, "AAPL", "sell", 1, user_id="default")


async def test_unknown_ticker_raises():
    state = _app_state({})

    with pytest.raises(TradeError, match="no price available"):
        await execute_trade(state, "ZZZZ", "buy", 1, user_id="default")


async def test_non_positive_quantity_raises():
    state = _app_state({"AAPL": 100.0})

    with pytest.raises(TradeError, match="quantity must be positive"):
        await execute_trade(state, "AAPL", "buy", 0, user_id="default")


async def test_get_portfolio_state_computes_unrealized_pnl():
    state = _app_state({"AAPL": 100.0})
    await execute_trade(state, "AAPL", "buy", 10, user_id="default")

    state = _app_state({"AAPL": 150.0})
    result = await get_portfolio_state(state, user_id="default")

    assert result["cash_balance"] == 9000.0
    assert len(result["positions"]) == 1
    pos = result["positions"][0]
    assert pos["ticker"] == "AAPL"
    assert pos["current_price"] == 150.0
    assert pos["unrealized_pnl"] == 500.0
    assert pos["unrealized_pnl_pct"] == pytest.approx(0.5)
    assert result["total_value"] == 9000.0 + 10 * 150.0
