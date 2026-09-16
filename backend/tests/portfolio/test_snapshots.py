"""Tests for app/portfolio/snapshots.py::run_portfolio_snapshot_loop() (Plan
04 Task 3, DATA-04).

Exercises the periodic recorder directly as an asyncio.Task, mirroring
tests/market/test_loop.py's style for testing run_update_loop.
"""

import asyncio

import pytest

from app.db import portfolio_snapshots as portfolio_snapshots_module
from app.db import positions as positions_module
from app.db import trades as trades_module
from app.db import users_profile as users_profile_module
from app.market.cache import PriceCache
from app.portfolio import snapshots as snapshots_module
from app.portfolio.snapshots import run_portfolio_snapshot_loop


async def _init_tables() -> None:
    await users_profile_module.init_db()
    await positions_module.init_db()
    await trades_module.init_db()
    await portfolio_snapshots_module.init_db()


async def _run_briefly(coro_task: asyncio.Task, seconds: float = 0.05) -> None:
    await asyncio.sleep(seconds)
    coro_task.cancel()
    try:
        await coro_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_snapshot_loop_records_on_each_iteration() -> None:
    await _init_tables()
    cache = PriceCache()

    task = asyncio.create_task(run_portfolio_snapshot_loop(cache, interval_seconds=0.01))
    await _run_briefly(task)

    snapshots = await portfolio_snapshots_module.get_snapshots()

    assert len(snapshots) >= 2
    for snapshot in snapshots:
        assert snapshot.total_value == 10000.0


@pytest.mark.asyncio
async def test_snapshot_loop_survives_an_iteration_error(monkeypatch) -> None:
    await _init_tables()
    cache = PriceCache()

    real_compute_portfolio_view = snapshots_module.compute_portfolio_view
    call_count = {"n": 0}

    async def _flaky_compute_portfolio_view(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RuntimeError("boom")
        return await real_compute_portfolio_view(*args, **kwargs)

    monkeypatch.setattr(
        snapshots_module, "compute_portfolio_view", _flaky_compute_portfolio_view
    )

    task = asyncio.create_task(run_portfolio_snapshot_loop(cache, interval_seconds=0.01))
    await _run_briefly(task)

    assert call_count["n"] >= 2
    snapshots = await portfolio_snapshots_module.get_snapshots()
    assert len(snapshots) >= 1
