import pytest

from app.db import trades as trades_module


@pytest.mark.asyncio
async def test_two_inserts_produce_two_rows_with_distinct_ids():
    await trades_module.init_db()
    await trades_module.insert_trade("AAPL", "buy", 10.0, 100.0)
    await trades_module.insert_trade("AAPL", "buy", 5.0, 105.0)

    all_trades = await trades_module.get_trades()
    assert len(all_trades) == 2
    assert len({t.id for t in all_trades}) == 2


@pytest.mark.asyncio
async def test_get_trades_returns_rows_ordered_by_executed_at_ascending():
    await trades_module.init_db()
    first = await trades_module.insert_trade("AAPL", "buy", 10.0, 100.0)
    second = await trades_module.insert_trade("MSFT", "buy", 5.0, 420.0)

    all_trades = await trades_module.get_trades()
    assert [t.id for t in all_trades] == [first.id, second.id]


@pytest.mark.asyncio
async def test_returned_trade_carries_inserted_values():
    await trades_module.init_db()
    trade = await trades_module.insert_trade("AAPL", "buy", 10.0, 100.0)

    assert trade.ticker == "AAPL"
    assert trade.side == "buy"
    assert trade.quantity == 10.0
    assert trade.price == 100.0
