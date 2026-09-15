"""Route-level tests for /api/portfolio*.

Route coroutines are called directly with a fake `Request` (exposing only
`.app.state`) rather than through a live TestClient — mirrors
tests/routes/test_stream.py's rationale: it avoids depending on the real
background market-data loop's timing to populate the price cache before
assertions run.
"""

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.db import portfolio_snapshots, positions, trades, users
from app.market.base import ChangeDirection, PriceTick
from app.routes.portfolio import (
    TradeRequest,
    get_portfolio,
    get_portfolio_history,
    post_trade,
)


class _FakeCache:
    def __init__(self, prices: dict[str, float]):
        self._prices = prices

    async def get(self, ticker: str):
        if ticker not in self._prices:
            return None
        price = self._prices[ticker]
        return PriceTick(ticker, price, price, None, ChangeDirection.UNCHANGED)


def _request(prices: dict[str, float]):
    state = SimpleNamespace(price_cache=_FakeCache(prices))
    return SimpleNamespace(app=SimpleNamespace(state=state))


@pytest.fixture(autouse=True)
async def seeded_db():
    await users.init_db()
    await positions.init_db()
    await trades.init_db()
    await portfolio_snapshots.init_db()


async def test_get_portfolio_returns_cash_and_positions():
    request = _request({})

    result = await get_portfolio(request)

    assert result == {"cash_balance": 10000.0, "positions": [], "total_value": 10000.0}


async def test_post_trade_returns_fill_on_success():
    request = _request({"AAPL": 100.0})

    result = await post_trade(request, TradeRequest(ticker="AAPL", quantity=5, side="buy"))

    assert result["ticker"] == "AAPL"
    assert result["side"] == "buy"
    assert result["quantity"] == 5
    assert result["price"] == 100.0


async def test_post_trade_returns_400_on_insufficient_cash():
    request = _request({"AAPL": 1_000_000.0})

    with pytest.raises(HTTPException) as exc_info:
        await post_trade(request, TradeRequest(ticker="AAPL", quantity=1, side="buy"))

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "insufficient cash"


async def test_post_trade_returns_400_on_unknown_ticker():
    request = _request({})

    with pytest.raises(HTTPException) as exc_info:
        await post_trade(request, TradeRequest(ticker="ZZZZ", quantity=1, side="buy"))

    assert exc_info.value.status_code == 400


async def test_post_trade_returns_400_on_nan_quantity():
    # Pydantic's float field accepts NaN/Infinity by default (confirmed:
    # TradeRequest(quantity=float("nan")) validates fine) — execute_trade's
    # own math.isfinite guard is what has to catch this, not the schema.
    request = _request({"AAPL": 100.0})

    with pytest.raises(HTTPException) as exc_info:
        await post_trade(
            request, TradeRequest(ticker="AAPL", quantity=float("nan"), side="buy")
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "quantity must be positive"


async def test_get_portfolio_history_returns_snapshot_list():
    request = _request({"AAPL": 100.0})
    await post_trade(request, TradeRequest(ticker="AAPL", quantity=1, side="buy"))

    result = await get_portfolio_history()

    assert len(result) == 1
    assert result[0]["total_value"] == pytest.approx(10000.0)
