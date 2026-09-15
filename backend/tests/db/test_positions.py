import pytest

from app.db import positions as positions_module


@pytest.mark.asyncio
async def test_get_positions_empty_before_any_fill():
    await positions_module.init_db()
    assert await positions_module.get_positions() == []


@pytest.mark.asyncio
async def test_apply_fill_buy_creates_new_position():
    await positions_module.init_db()
    await positions_module.apply_fill("default", "AAPL", "buy", 10, 100.0)

    position = await positions_module.get_position("default", "AAPL")
    assert position is not None
    assert position["ticker"] == "AAPL"
    assert position["quantity"] == 10
    assert position["avg_cost"] == 100.0


@pytest.mark.asyncio
async def test_apply_fill_buy_averages_cost_basis():
    await positions_module.init_db()
    await positions_module.apply_fill("default", "AAPL", "buy", 10, 100.0)
    await positions_module.apply_fill("default", "AAPL", "buy", 10, 200.0)

    position = await positions_module.get_position("default", "AAPL")
    assert position["quantity"] == 20
    # (10*100 + 10*200) / 20 == 150
    assert position["avg_cost"] == pytest.approx(150.0)


@pytest.mark.asyncio
async def test_apply_fill_sell_reduces_quantity_keeps_avg_cost():
    await positions_module.init_db()
    await positions_module.apply_fill("default", "AAPL", "buy", 10, 100.0)
    await positions_module.apply_fill("default", "AAPL", "sell", 4, 150.0)

    position = await positions_module.get_position("default", "AAPL")
    assert position["quantity"] == pytest.approx(6.0)
    assert position["avg_cost"] == 100.0


@pytest.mark.asyncio
async def test_apply_fill_sell_to_zero_deletes_position():
    await positions_module.init_db()
    await positions_module.apply_fill("default", "AAPL", "buy", 10, 100.0)
    await positions_module.apply_fill("default", "AAPL", "sell", 10, 150.0)

    position = await positions_module.get_position("default", "AAPL")
    assert position is None
    assert await positions_module.get_positions() == []


@pytest.mark.asyncio
async def test_apply_fill_sell_below_epsilon_deletes_position():
    await positions_module.init_db()
    await positions_module.apply_fill("default", "AAPL", "buy", 0.1, 100.0)
    await positions_module.apply_fill("default", "AAPL", "sell", 0.1 - 1e-12, 150.0)

    position = await positions_module.get_position("default", "AAPL")
    assert position is None


@pytest.mark.asyncio
async def test_apply_fill_sell_without_existing_position_raises():
    await positions_module.init_db()
    with pytest.raises(ValueError):
        await positions_module.apply_fill("default", "AAPL", "sell", 1, 100.0)


@pytest.mark.asyncio
async def test_apply_fill_unknown_side_raises():
    await positions_module.init_db()
    with pytest.raises(ValueError):
        await positions_module.apply_fill("default", "AAPL", "hold", 1, 100.0)


@pytest.mark.asyncio
async def test_apply_fill_buy_rounds_avg_cost_and_quantity_noise():
    await positions_module.init_db()
    # 1/3 + 1/3 + 1/3 style repeated fills are a classic source of binary
    # float noise (0.1 + 0.2 != 0.3) in both quantity and the weighted avg.
    await positions_module.apply_fill("default", "AAPL", "buy", 0.1, 100.0)
    await positions_module.apply_fill("default", "AAPL", "buy", 0.2, 100.0)

    position = await positions_module.get_position("default", "AAPL")
    # Without rounding this would be 0.30000000000000004.
    assert position["quantity"] == 0.3
    assert position["avg_cost"] == 100.0


@pytest.mark.asyncio
async def test_apply_fill_sell_exact_full_position_is_exact_zero():
    await positions_module.init_db()
    await positions_module.apply_fill("default", "AAPL", "buy", 0.1, 100.0)
    await positions_module.apply_fill("default", "AAPL", "buy", 0.2, 100.0)
    # Selling the same rounded total back out should net to exactly zero and
    # delete the row, not leave a dust position behind.
    await positions_module.apply_fill("default", "AAPL", "sell", 0.3, 120.0)

    assert await positions_module.get_position("default", "AAPL") is None


@pytest.mark.asyncio
async def test_get_positions_scoped_per_user():
    await positions_module.init_db()
    await positions_module.apply_fill("default", "AAPL", "buy", 10, 100.0)
    await positions_module.apply_fill("someone-else", "GOOGL", "buy", 5, 50.0)

    default_positions = await positions_module.get_positions()
    assert [p["ticker"] for p in default_positions] == ["AAPL"]
