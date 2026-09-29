import pytest

from app.db import users_profile as users_profile_module


@pytest.mark.asyncio
async def test_init_db_seeds_one_row_with_ten_thousand_cash():
    await users_profile_module.init_db()
    balance = await users_profile_module.get_cash_balance()
    assert balance == 10000.0


@pytest.mark.asyncio
async def test_init_db_is_idempotent_and_does_not_reset_balance():
    await users_profile_module.init_db()
    await users_profile_module.set_cash_balance(1234.5)

    await users_profile_module.init_db()  # must not duplicate or reset the row

    balance = await users_profile_module.get_cash_balance()
    assert balance == 1234.5


@pytest.mark.asyncio
async def test_set_then_get_cash_balance_round_trips_fractional_value():
    await users_profile_module.init_db()
    await users_profile_module.set_cash_balance(9876.54)
    balance = await users_profile_module.get_cash_balance()
    assert balance == 9876.54
