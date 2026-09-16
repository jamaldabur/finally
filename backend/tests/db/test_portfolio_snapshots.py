"""Unit tests for app/db/portfolio_snapshots.py (PLAN.md §7
"portfolio_snapshots" — Plan 04 Task 1).

Written RED first: at the time this file is authored,
app/db/portfolio_snapshots.py does not exist yet. Mirrors
tests/db/test_trades.py's append-only test style.
"""

import pytest

from app.db import portfolio_snapshots as portfolio_snapshots_module


@pytest.mark.asyncio
async def test_init_db_creates_table() -> None:
    await portfolio_snapshots_module.init_db()

    snapshots = await portfolio_snapshots_module.get_snapshots()

    assert snapshots == []


@pytest.mark.asyncio
async def test_init_db_is_idempotent() -> None:
    await portfolio_snapshots_module.init_db()
    await portfolio_snapshots_module.init_db()
    await portfolio_snapshots_module.insert_snapshot(10000.0)

    snapshots = await portfolio_snapshots_module.get_snapshots()

    assert len(snapshots) == 1


@pytest.mark.asyncio
async def test_inserts_are_append_only() -> None:
    await portfolio_snapshots_module.init_db()

    await portfolio_snapshots_module.insert_snapshot(1.0)
    await portfolio_snapshots_module.insert_snapshot(2.0)
    await portfolio_snapshots_module.insert_snapshot(3.0)

    snapshots = await portfolio_snapshots_module.get_snapshots()

    # Three distinct rows persisted (no overwriting) with three distinct
    # recorded_at timestamps — proof that each insert created its own row
    # under its own generated id, rather than upserting over a prior row.
    assert len(snapshots) == 3
    assert len({s.recorded_at for s in snapshots}) == 3
    assert [s.total_value for s in snapshots] == [1.0, 2.0, 3.0]


@pytest.mark.asyncio
async def test_get_snapshots_is_ordered_by_recorded_at() -> None:
    await portfolio_snapshots_module.init_db()

    await portfolio_snapshots_module.insert_snapshot(100.0)
    await portfolio_snapshots_module.insert_snapshot(200.0)
    await portfolio_snapshots_module.insert_snapshot(300.0)

    snapshots = await portfolio_snapshots_module.get_snapshots()

    assert [s.total_value for s in snapshots] == [100.0, 200.0, 300.0]
    recorded_ats = [s.recorded_at for s in snapshots]
    assert recorded_ats == sorted(recorded_ats)


@pytest.mark.asyncio
async def test_total_value_survives_float_round_trip() -> None:
    await portfolio_snapshots_module.init_db()

    await portfolio_snapshots_module.insert_snapshot(10123.456789)

    snapshots = await portfolio_snapshots_module.get_snapshots()

    assert len(snapshots) == 1
    assert snapshots[0].total_value == 10123.456789
