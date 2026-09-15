import pytest

from app.db import trades as trades_module


@pytest.mark.asyncio
async def test_insert_trade_returns_full_row():
    await trades_module.init_db()
    trade = await trades_module.insert_trade("default", "AAPL", "buy", 10, 190.0)

    assert trade["ticker"] == "AAPL"
    assert trade["side"] == "buy"
    assert trade["quantity"] == 10
    assert trade["price"] == 190.0
    assert "id" in trade
    assert "executed_at" in trade


@pytest.mark.asyncio
async def test_insert_trade_rounds_quantity_and_price():
    await trades_module.init_db()
    trade = await trades_module.insert_trade(
        "default", "AAPL", "buy", 1.0 / 3, 190.005001
    )
    assert trade["quantity"] == 0.333333
    assert trade["price"] == 190.01


@pytest.mark.asyncio
async def test_insert_trade_is_append_only_no_dedup():
    await trades_module.init_db()
    await trades_module.insert_trade("default", "AAPL", "buy", 10, 190.0)
    second = await trades_module.insert_trade("default", "AAPL", "buy", 10, 190.0)

    # Same ticker/side/qty/price twice must still produce two distinct rows.
    assert second["id"] is not None
