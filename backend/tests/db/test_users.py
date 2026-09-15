import pytest

from app.db import users as users_module


@pytest.mark.asyncio
async def test_init_db_seeds_default_user_with_starting_balance():
    await users_module.init_db()
    balance = await users_module.get_cash_balance()
    assert balance == 10000.0


@pytest.mark.asyncio
async def test_init_db_is_idempotent_does_not_reset_balance():
    await users_module.init_db()
    await users_module.set_cash_balance("default", 5000.0)
    await users_module.init_db()  # must not overwrite the existing balance
    balance = await users_module.get_cash_balance()
    assert balance == 5000.0


@pytest.mark.asyncio
async def test_set_cash_balance_updates_value():
    await users_module.init_db()
    await users_module.set_cash_balance("default", 12345.67)
    balance = await users_module.get_cash_balance("default")
    assert balance == 12345.67


@pytest.mark.asyncio
async def test_set_cash_balance_rounds_to_cents():
    await users_module.init_db()
    await users_module.set_cash_balance("default", 9999.999999999998)
    balance = await users_module.get_cash_balance("default")
    assert balance == 10000.0


@pytest.mark.asyncio
async def test_get_cash_balance_unknown_user_raises():
    await users_module.init_db()
    with pytest.raises(ValueError):
        await users_module.get_cash_balance("someone-else")
