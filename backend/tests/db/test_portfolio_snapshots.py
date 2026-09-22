"""Unit tests for app/db/portfolio_snapshots.py (PLAN.md §7
"portfolio_snapshots" — Plan 04 Task 1).

Written RED first: at the time this file is authored,
app/db/portfolio_snapshots.py does not exist yet. Mirrors
tests/db/test_trades.py's append-only test style.

04-07-PLAN.md Task 1 adds coverage for the bounded, most-recent window
(`get_snapshots(limit=...)`), selected by `rowid` rather than `recorded_at`
so a duplicate timestamp cannot make the window boundary arbitrary — see
`test_window_survives_duplicate_recorded_at` below.
"""

import inspect
from datetime import datetime, timezone

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

    # Three distinct rows persisted (no overwriting), proven by the row
    # count and the preserved insertion-order total_values — each insert
    # created its own row under its own generated id rather than upserting
    # over a prior one. Not asserting on distinct recorded_at strings here:
    # on some platforms datetime.now()'s effective clock resolution can be
    # coarser than microseconds, so three inserts issued back-to-back in a
    # tight loop can legitimately share a timestamp string without that
    # indicating a collision or an overwrite.
    assert len(snapshots) == 3
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


@pytest.mark.asyncio
async def test_get_snapshots_limit_returns_most_recent_oldest_first() -> None:
    await portfolio_snapshots_module.init_db()

    for value in (1.0, 2.0, 3.0, 4.0, 5.0):
        await portfolio_snapshots_module.insert_snapshot(value)

    snapshots = await portfolio_snapshots_module.get_snapshots(limit=2)

    # Fourth and fifth inserted, in that order: most-recent selected,
    # oldest-first returned.
    assert [s.total_value for s in snapshots] == [4.0, 5.0]


@pytest.mark.asyncio
async def test_get_snapshots_limit_above_row_count_returns_all() -> None:
    await portfolio_snapshots_module.init_db()

    for value in (10.0, 20.0, 30.0):
        await portfolio_snapshots_module.insert_snapshot(value)

    snapshots = await portfolio_snapshots_module.get_snapshots(limit=50)

    # A limit above the row count is not an error and truncates nothing.
    assert [s.total_value for s in snapshots] == [10.0, 20.0, 30.0]


@pytest.mark.asyncio
async def test_get_snapshots_limit_one_returns_most_recent_only() -> None:
    await portfolio_snapshots_module.init_db()

    for value in (100.0, 200.0, 300.0):
        await portfolio_snapshots_module.insert_snapshot(value)

    snapshots = await portfolio_snapshots_module.get_snapshots(limit=1)

    assert [s.total_value for s in snapshots] == [300.0]


@pytest.mark.asyncio
async def test_window_survives_duplicate_recorded_at(monkeypatch) -> None:
    # Pin the clock so several inserts genuinely share one recorded_at
    # string — the 30-second recorder and an on-trade insert can collide on
    # timestamp in production, and that collision is precisely the condition
    # rowid-based ordering exists to survive. A test that does not force it
    # is not testing the fix (see chat_messages.py's identical reasoning).
    fixed_now = datetime(2026, 1, 1, tzinfo=timezone.utc)

    class _FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_now

    monkeypatch.setattr(portfolio_snapshots_module, "datetime", _FixedDatetime)

    await portfolio_snapshots_module.init_db()
    for value in (1.0, 2.0, 3.0, 4.0, 5.0):
        await portfolio_snapshots_module.insert_snapshot(value)

    all_snapshots = await portfolio_snapshots_module.get_snapshots()
    assert all(s.recorded_at == fixed_now.isoformat() for s in all_snapshots)

    # Even with every recorded_at string identical, the window still selects
    # by insertion order — the most recently inserted rows, not an arbitrary
    # subset at the tie boundary.
    windowed = await portfolio_snapshots_module.get_snapshots(limit=2)
    assert [s.total_value for s in windowed] == [4.0, 5.0]


def test_get_snapshots_default_limit_is_the_declared_constant() -> None:
    # Asserts the wiring (which constant the default is bound to), not the
    # behaviour under load — a half-thousand-row fixture would buy nothing
    # but runtime.
    signature = inspect.signature(portfolio_snapshots_module.get_snapshots)
    assert (
        signature.parameters["limit"].default
        == portfolio_snapshots_module.DEFAULT_SNAPSHOT_LIMIT
    )
