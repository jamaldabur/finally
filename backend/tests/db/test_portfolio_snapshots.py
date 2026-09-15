import pytest

from app.db import portfolio_snapshots as snapshots_module


@pytest.mark.asyncio
async def test_get_snapshots_empty_before_any_insert():
    await snapshots_module.init_db()
    assert await snapshots_module.get_snapshots() == []


@pytest.mark.asyncio
async def test_insert_and_get_snapshots_ordered_ascending():
    await snapshots_module.init_db()
    await snapshots_module.insert_snapshot("default", 10000.0)
    await snapshots_module.insert_snapshot("default", 10500.0)
    await snapshots_module.insert_snapshot("default", 10250.0)

    snapshots = await snapshots_module.get_snapshots()
    assert [s["total_value"] for s in snapshots] == [10000.0, 10500.0, 10250.0]


@pytest.mark.asyncio
async def test_insert_snapshot_rounds_total_value_to_cents():
    await snapshots_module.init_db()
    await snapshots_module.insert_snapshot("default", 10000.005001)

    snapshots = await snapshots_module.get_snapshots()
    assert snapshots[0]["total_value"] == 10000.01


@pytest.mark.asyncio
async def test_get_snapshots_scoped_per_user():
    await snapshots_module.init_db()
    await snapshots_module.insert_snapshot("default", 10000.0)
    await snapshots_module.insert_snapshot("someone-else", 999.0)

    default_snapshots = await snapshots_module.get_snapshots()
    assert len(default_snapshots) == 1
    assert default_snapshots[0]["total_value"] == 10000.0
