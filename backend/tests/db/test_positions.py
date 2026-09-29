import pytest

from app.db import positions as positions_module


@pytest.mark.asyncio
async def test_upsert_position_twice_leaves_one_row_with_second_call_values():
    await positions_module.init_db()
    await positions_module.upsert_position("AAPL", 10.0, 100.0)
    await positions_module.upsert_position("AAPL", 15.0, 110.0)

    all_positions = await positions_module.get_all_positions()
    assert len(all_positions) == 1
    assert all_positions[0].quantity == 15.0
    assert all_positions[0].avg_cost == 110.0


@pytest.mark.asyncio
async def test_get_position_for_unheld_ticker_returns_none():
    await positions_module.init_db()
    position = await positions_module.get_position("AAPL")
    assert position is None


@pytest.mark.asyncio
async def test_get_all_positions_returns_rows_ordered_by_ticker():
    await positions_module.init_db()
    await positions_module.upsert_position("TSLA", 1.0, 250.0)
    await positions_module.upsert_position("AAPL", 2.0, 190.0)
    await positions_module.upsert_position("MSFT", 3.0, 420.0)

    all_positions = await positions_module.get_all_positions()
    assert [p.ticker for p in all_positions] == ["AAPL", "MSFT", "TSLA"]


@pytest.mark.asyncio
async def test_fractional_quantity_survives_round_trip():
    await positions_module.init_db()
    await positions_module.upsert_position("AAPL", 0.5, 190.0)

    position = await positions_module.get_position("AAPL")
    assert position is not None
    assert position.quantity == 0.5
