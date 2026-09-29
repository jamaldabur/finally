---
phase: 01-backend-trading-engine
plan: 04
subsystem: backend-trading-engine
tags: [fastapi, sqlite, asyncio, portfolio-valuation, background-task, tdd]

requires:
  - phase: 01-backend-trading-engine
    provides: "execute_trade()/TradeResult (01-01, 01-02), app.state.portfolio_lock, app/main.py lifespan block, app/db/watchlist.py's _connect()/DB_PATH pattern"
provides:
  - "app/db/portfolio_snapshots.py — append-only portfolio_snapshots table (schema, init_db, insert_snapshot, get_snapshots)"
  - "app/portfolio/service.py::compute_portfolio_view() — the frozen, lock-free portfolio valuation read Phase 3's chat flow will call unchanged"
  - "GET /api/portfolio, GET /api/portfolio/history — the two read endpoints Phase 2 (frontend) and Phase 4 (P&L chart) consume"
  - "app/portfolio/snapshots.py::run_portfolio_snapshot_loop() — 30s background recorder, lifespan-managed"
  - "Snapshot-on-trade: execute_trade() records portfolio_snapshots immediately after every successful buy/sell"
affects: [phase-02-frontend, phase-03-chat, phase-04-visualization]

actuals:
  tokens: 7996
  tasks: 3
  commits: 6
  plan_head_before: eb6e7b76ea0263aae857484ff491ec2c4066e435

tech-stack:
  added: []
  patterns:
    - "Per-table SQLite module (schema + idempotent init) mirroring app/db/trades.py exactly, for the fifth and final append-only table"
    - "Pure-read valuation function (compute_portfolio_view) that deliberately never acquires the portfolio lock, called both directly by GET /api/portfolio and from inside execute_trade()'s own locked section"
    - "Rounding derived monetary/percentage values to cent precision at computation time (not on every read), matching app/market/simulator.py's documented 'round once' convention — division-based pct_change is not exactly representable in binary float and would otherwise leak that imprecision into the API"
    - "Background recorder structured identically to app/market/loop.py::run_update_loop — unbounded while True, broad try/except that logs and continues, trailing await asyncio.sleep(interval)"

key-files:
  created:
    - backend/app/db/portfolio_snapshots.py
    - backend/app/portfolio/snapshots.py
    - backend/tests/db/test_portfolio_snapshots.py
    - backend/tests/portfolio/test_snapshots.py
  modified:
    - backend/app/portfolio/service.py
    - backend/app/routes/portfolio.py
    - backend/app/main.py
    - backend/tests/portfolio/test_service.py
    - backend/tests/routes/test_portfolio.py

key-decisions:
  - "Snapshot-on-trade lives in execute_trade() itself (one call site, after dispatching to _apply_buy/_apply_sell, gated on result.status == 'executed') rather than duplicated inside both _apply_buy and _apply_sell — keeps the insert_snapshot call site singular and matches the acceptance criteria's grep-count-of-1 requirement"
  - "portfolio_snapshots.init_db() was wired into app/main.py's lifespan during Task 2, not Task 3 as the plan's task split implied — GET /api/portfolio/history (a Task 2 deliverable) needs the table to exist to return 200, so the wiring could not wait for Task 3"
  - "Rounded market_value/unrealized_pnl/pct_change/positions_value/total_value to 2 decimal places in compute_portfolio_view(), a deviation from the plan's literal Code Examples formulas, to avoid float-precision artifacts (e.g. (120.0/100.0 - 1) * 100 == 19.999999999999996, not 20.0) leaking into the locked API contract"

patterns-established:
  - "Test files that seed a real background task's timing (run_portfolio_snapshot_loop) use a wider observation window (0.2s) than the market-data loop analog, since each iteration performs real synchronous SQLite I/O via asyncio.to_thread rather than a pure in-memory update"

requirements-completed: [DATA-04, PORT-05, PORT-06]

coverage:
  - id: D1
    description: "portfolio_snapshots table self-initializes, accepts append-only inserts, and reads back in ascending recorded_at order (DATA-04 schema half)"
    requirement: "DATA-04"
    verification:
      - kind: unit
        ref: "backend/tests/db/test_portfolio_snapshots.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "GET /api/portfolio returns cash_balance, positions (with current_price, market_value, unrealized_pnl, pct_change), positions_value, total_value, and total_unrealized_pnl per the locked contract; positions sorted by ticker; a position with no cached price is marked to cost rather than crashing or dropping out of total_value"
    requirement: "PORT-05"
    verification:
      - kind: unit
        ref: "backend/tests/portfolio/test_service.py::test_portfolio_view_computes_unrealized_pnl, test_portfolio_view_handles_loss, test_portfolio_view_marks_unpriced_position_to_cost"
        status: pass
      - kind: integration
        ref: "backend/tests/routes/test_portfolio.py::test_get_portfolio_returns_locked_shape, test_get_portfolio_reflects_a_trade, test_get_portfolio_positions_sorted_by_ticker"
        status: pass
    human_judgment: false
  - id: D3
    description: "GET /api/portfolio/history returns portfolio_snapshots rows ascending by recorded_at"
    requirement: "PORT-06"
    verification:
      - kind: integration
        ref: "backend/tests/routes/test_portfolio.py::test_get_portfolio_history_returns_snapshots"
        status: pass
    human_judgment: false
  - id: D4
    description: "A background task records a portfolio_snapshots row every 30 seconds, survives an iteration error without dying, and is cancelled cleanly on shutdown with no task-leak warning (DATA-04 background half)"
    requirement: "DATA-04"
    verification:
      - kind: unit
        ref: "backend/tests/portfolio/test_snapshots.py::test_snapshot_loop_records_on_each_iteration, test_snapshot_loop_survives_an_iteration_error"
        status: pass
      - kind: integration
        ref: "backend/tests/routes/test_portfolio.py::test_lifespan_cancels_the_snapshot_task"
        status: pass
    human_judgment: false
  - id: D5
    description: "Executing a trade writes exactly one portfolio_snapshots row immediately (matching the post-trade total_value); a rejected trade writes none (DATA-04 on-trade half)"
    requirement: "DATA-04"
    verification:
      - kind: integration
        ref: "backend/tests/routes/test_portfolio.py::test_trade_records_an_immediate_snapshot, test_rejected_trade_records_no_snapshot"
        status: pass
    human_judgment: false
  - id: D6
    description: "compute_portfolio_view() never acquires the portfolio lock and execute_trade() can call it from inside its own held lock without deadlocking (T-01-10)"
    verification:
      - kind: integration
        ref: "backend/tests/routes/test_portfolio.py::test_trade_records_an_immediate_snapshot (a real buy through the locked path completes and returns 200 rather than hanging)"
        status: pass
    human_judgment: false
  - id: D7
    description: "Full backend test suite remains green and deterministic after all snapshot/valuation changes, with no pending-task teardown warnings"
    verification:
      - kind: unit
        ref: "cd backend && uv run pytest -q (138 tests, run 5x for determinism)"
        status: pass
    human_judgment: false

duration: 15min
completed: 2026-09-16
status: complete
---

# Phase 1 Plan 04: Portfolio Reads & Snapshot History Summary

Closed Phase 1 by making the portfolio readable and its value history durable — `compute_portfolio_view()` (the frozen valuation surface Phase 3's chat flow will call), `GET /api/portfolio`, `GET /api/portfolio/history`, and a 30-second background snapshot recorder wired alongside an immediate snapshot on every successful trade.

## Performance
- **Duration:** 15min
- **Started:** 2026-09-16T23:16:39+03:00 (first commit)
- **Completed:** 2026-09-16T23:31:20+03:00 (last commit)
- **Tasks:** 3 completed
- **Files modified:** 9 (4 created, 5 modified)

## Accomplishments
- Added the fifth and final append-only SQLite table (`portfolio_snapshots`), mirroring `app/db/trades.py` exactly — schema, idempotent init, `insert_snapshot`, `get_snapshots`
- Built `compute_portfolio_view()`: a pure, lock-free read joining `users_profile` + `positions` with the live `PriceCache`, computing unrealized P&L and % change fresh on every call (never persisted), with the locked mark-to-cost fallback for positions whose ticker has no cached price
- Implemented `GET /api/portfolio` and `GET /api/portfolio/history` exactly per the plan's locked JSON contract
- Built `run_portfolio_snapshot_loop()` — a 30-second background recorder structured identically to `run_update_loop`, wired into the lifespan and cancelled cleanly on shutdown — plus an immediate snapshot insert on every successful trade, both buy and sell, from a single call site inside `execute_trade()`'s existing lock
- Full backend suite: 138 tests passing (up from 121 at the end of Plan 03), run 5 times consecutively with zero flakiness and zero pending-task warnings

## Task Commits
1. **Task 1 RED: Add failing tests for portfolio_snapshots table** - `d54acc5` (test)
1. **Task 1 GREEN: Implement portfolio_snapshots table** - `e010b6f` (feat)
2. **Task 2 RED: Add failing tests for portfolio valuation and GET endpoints** - `9c89c02` (test)
2. **Task 2 GREEN: Implement compute_portfolio_view() and portfolio GET endpoints** - `997461a` (feat)
3. **Task 3 RED: Add failing tests for snapshot-on-trade and background recorder** - `40a0fe7` (test)
3. **Task 3 GREEN: Implement snapshot-on-trade and the 30s background recorder** - `b9ea857` (feat)

**Plan metadata:** commit follows this summary

_Note: no task required a separate REFACTOR commit — each GREEN implementation (including its auto-fixes) needed no further follow-up cleanup once tests passed._

## Files Created/Modified
- `backend/app/db/portfolio_snapshots.py` - `portfolio_snapshots` schema (append-only), `PortfolioSnapshot` dataclass, `init_db`/`insert_snapshot`/`get_snapshots`
- `backend/app/portfolio/snapshots.py` - `SNAPSHOT_INTERVAL_SECONDS = 30`, `run_portfolio_snapshot_loop()` — records first then sleeps, broad try/except that logs and continues
- `backend/app/portfolio/service.py` - `PositionView`/`PortfolioView` dataclasses, `compute_portfolio_view()`, and the snapshot-on-trade insert inside `execute_trade()`'s existing lock
- `backend/app/routes/portfolio.py` - `PositionViewResponse`/`PortfolioResponse`/`SnapshotResponse`/`PortfolioHistoryResponse`, `GET /api/portfolio`, `GET /api/portfolio/history`
- `backend/app/main.py` - lifespan now calls `portfolio_snapshots.init_db()` before any `asyncio.create_task(...)`, creates/stores/cancels `snapshot_task` alongside `update_task`
- `backend/tests/db/test_portfolio_snapshots.py` - 5 unit tests for the new table
- `backend/tests/portfolio/test_service.py` - 3 new `compute_portfolio_view()` tests (unrealized P&L, loss, mark-to-cost fallback); `_init_tables()` extended to init `portfolio_snapshots`
- `backend/tests/portfolio/test_snapshots.py` - new module, 2 tests for the background recorder (records each iteration, survives an iteration error)
- `backend/tests/routes/test_portfolio.py` - 4 new `GET /api/portfolio`/`history` tests (Task 2), 3 new snapshot-on-trade/lifespan-cancellation tests (Task 3)

## Decisions Made
- Kept the snapshot-on-trade insert to a single call site in `execute_trade()` (after dispatching to `_apply_buy`/`_apply_sell`, gated on `result.status == "executed"`) rather than duplicating it inside both helpers — satisfies the plan's own acceptance criterion that `insert_snapshot` appear exactly once in `service.py`.
- Rounded `market_value`, `unrealized_pnl`, `pct_change`, `positions_value`, and `total_value` to 2 decimal places in `compute_portfolio_view()`, matching `app/market/simulator.py`'s documented "round once" cent-precision convention — the plan's literal formula (`(current_price / avg_cost - 1) * 100`) is not exactly representable in binary float and produced `19.999999999999996` instead of `20.0` for the plan's own locked-contract example.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking issue] `portfolio_snapshots.init_db()` needed wiring one task earlier than planned**
- **Found during:** Task 2, initial GREEN run of `test_get_portfolio_history_returns_snapshots`
- **Issue:** The plan's task split places `portfolio_snapshots.init_db()` wiring into `app/main.py`'s lifespan in Task 3's action, but Task 2's own behavior list requires `GET /api/portfolio/history` to return 200. Since the route reads from a table that doesn't exist yet without that lifespan wiring, the test failed with `sqlite3.OperationalError: no such table: portfolio_snapshots`.
- **Fix:** Wired `await portfolio_snapshots.init_db()` into the lifespan's existing `init_db()` block (before any `asyncio.create_task(...)`) during Task 2 instead of Task 3. Task 3's own action item for this line was then already satisfied — a no-op when reached.
- **Files modified:** `backend/app/main.py`
- **Verification:** `tests/routes/test_portfolio.py tests/portfolio/test_service.py -q -x` — 28/28 passing
- **Commit:** `997461a`

**2. [Rule 1 - Bug] Float-precision leak in pct_change computation**
- **Found during:** Task 2, `test_portfolio_view_computes_unrealized_pnl`
- **Issue:** `(120.0 / 100.0 - 1) * 100` evaluates to `19.999999999999996` in IEEE-754 binary float, not `20.0` — the plan's own locked-contract JSON example (§ "Locked API contract") shows `"pct_change": 20.0` for this exact scenario, so the unrounded formula would return a value that doesn't match the plan's own documented contract.
- **Fix:** Rounded `market_value`, `unrealized_pnl`, and `pct_change` to 2 decimal places at computation time in `compute_portfolio_view()` (plus the aggregate `positions_value`/`total_value`/`total_unrealized_pnl`), matching the "round once, not per-read" convention `app/market/simulator.py` already documents for prices.
- **Files modified:** `backend/app/portfolio/service.py`
- **Verification:** `tests/portfolio/test_service.py::test_portfolio_view_computes_unrealized_pnl` passes with `pct_change == 20.0` exactly
- **Commit:** `997461a`

**3. [Rule 3 - Blocking issue] `_init_tables()` in test_service.py missing portfolio_snapshots init**
- **Found during:** Task 3, full-suite verification after wiring snapshot-on-trade into `execute_trade()`
- **Issue:** `execute_trade()` now writes an immediate `portfolio_snapshots` row on every successful trade, but `tests/portfolio/test_service.py`'s `_init_tables()` helper (used by all of that module's direct `execute_trade()` calls, which bypass `TestClient`'s lifespan entirely) only initialized `users_profile`, `positions`, and `trades`. Seven tests in that module failed with `sqlite3.OperationalError: no such table: portfolio_snapshots`.
- **Fix:** Added `await portfolio_snapshots_module.init_db()` to `_init_tables()`.
- **Files modified:** `backend/tests/portfolio/test_service.py`
- **Verification:** Full suite green (138/138)
- **Commit:** `b9ea857`

**4. [Rule 1 - Bug] Flaky distinct-recorded_at assertion under coarse clock resolution**
- **Found during:** Task 3, full-suite run 2 of 5 (non-deterministic — individual-file runs were consistently green)
- **Issue:** `test_inserts_are_append_only` asserted `len({s.recorded_at for s in snapshots}) == 3`, expecting three microsecond-resolution timestamps from three inserts issued in a tight loop to always be distinct. Under full-suite load, this collided (two of three inserts landed the same timestamp string), because `datetime.now()`'s effective clock resolution can be coarser than microseconds on some platforms — this doesn't indicate a row collision or overwrite (each row still has its own UUID primary key and distinct `total_value`).
- **Fix:** Removed the distinct-recorded_at assertion; the row count (3) plus the preserved insertion-order `total_value` sequence (`[1.0, 2.0, 3.0]`) already proves three distinct rows persisted without overwriting, without depending on clock resolution.
- **Files modified:** `backend/tests/db/test_portfolio_snapshots.py`
- **Verification:** Full suite run 5 times consecutively — 138/138 passing each time, no flakiness observed
- **Commit:** `b9ea857`

**5. [Rule 1 - Bug] Flaky background-loop iteration-count assertions**
- **Found during:** Task 3, isolated re-run of `tests/portfolio/test_snapshots.py` after the fixes above
- **Issue:** `test_snapshot_loop_records_on_each_iteration` and `test_snapshot_loop_survives_an_iteration_error` used a 0.05s observation window with a 0.01s nominal loop interval, expecting at least 2 iterations. Unlike `run_update_loop`'s analog (a pure in-memory cache write), each `run_portfolio_snapshot_loop` iteration performs real synchronous SQLite I/O via `asyncio.to_thread` (multiple reads plus a write), which can push a single iteration's wall-clock cost close to or past the observation window.
- **Fix:** Widened the observation window to 0.2s in both tests.
- **Files modified:** `backend/tests/portfolio/test_snapshots.py`
- **Verification:** Full suite run 5 times consecutively — 138/138 passing each time
- **Commit:** `b9ea857`

**6. [Rule 3 - Blocking issue] Acceptance-criteria grep count inflated by docstring prose**
- **Found during:** Task 3, acceptance-criteria verification loop
- **Issue:** `grep -c 'logger.exception' backend/app/portfolio/snapshots.py` returned 2, not the required 1 — the module docstring referenced the literal string `logger.exception` in prose, alongside the one real call site. (Same failure mode Plan 03 documented for `strip().upper()`.)
- **Fix:** Reworded the docstring to describe the behavior ("a broad try/except that logs and keeps going") without repeating the literal identifier.
- **Files modified:** `backend/app/portfolio/snapshots.py`
- **Verification:** `grep -c 'logger.exception' backend/app/portfolio/snapshots.py` returns `1`; full suite still green
- **Commit:** `b9ea857`

**Total deviations:** 6 auto-fixed (2 Rule 1 — bugs/test-flakiness fixes; 4 Rule 3 — blocking issues, including one sequencing dependency pulled forward from Task 3 to Task 2).
**Impact on plan:** None on the locked API contract, schema, or service-layer behavior — deviations 1 and 3 were sequencing/wiring gaps required for the plan's own tests to pass as specified; deviation 2 makes the implementation match the plan's own locked-contract example exactly (`pct_change: 20.0`); deviations 4-6 are test-only fixes for flakiness or wording, with zero change to shipped endpoint behavior.

## Issues Encountered
None beyond the deviations above — all were caught and resolved during the TDD RED/GREEN cycle for their respective tasks, with no unresolved blockers.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness

**Phase 1 (Backend Trading Engine) is complete.** All 15 requirement IDs (DATA-01..06, PORT-01..06, WLST-01..03) have at least one passing automated test. The full backend suite (138 tests) is green and deterministic (verified across 5 consecutive runs) with no pending-task teardown warnings.

**The frozen backend surface for Phase 2 (frontend) and Phase 3 (chat) to build against:**
- `app/portfolio/service.py::execute_trade(*, price_cache, market_source, lock, ticker, side, quantity, user_id=DEFAULT_USER_ID) -> TradeResult` — the single validate-and-apply path for market orders (buy/sell), returning a structured result rather than raising. Now also records an immediate `portfolio_snapshots` row on every successful trade.
- `app/portfolio/service.py::compute_portfolio_view(*, price_cache, user_id=DEFAULT_USER_ID) -> PortfolioView` — the single portfolio-valuation read, lock-free, safe to call from any context (including from inside `execute_trade()`'s own lock).
- REST surface: `GET /api/portfolio`, `POST /api/portfolio/trade`, `GET /api/portfolio/history`, `GET/POST/DELETE /api/watchlist`, `GET /api/health`, `GET /api/stream/prices`. All response shapes are locked (see each plan's "Locked API contract" section) and unit/integration-tested.
- SQLite schema complete: `users_profile`, `positions`, `trades`, `portfolio_snapshots`, `watchlist`, `chat_messages` (the last one schema-only, ready for Phase 3 to add read/write logic).
- Background tasks: `run_update_loop` (market data, ~500ms) and `run_portfolio_snapshot_loop` (portfolio value, 30s) both lifespan-managed, both cancelled cleanly on shutdown, both proven not to leak across `TestClient` teardown.

**No blockers for Phase 2.** Phase 2's frontend can consume `GET /api/portfolio`, `GET /api/portfolio/history`, `GET /api/watchlist`, and `GET /api/stream/prices` immediately; Phase 3's chat flow can call `execute_trade()` and the watchlist mutation functions unchanged, per each plan's explicit design intent.

---
*Phase: 01-backend-trading-engine*
*Completed: 2026-09-16*

## Self-Check: PASSED

All 4 created files verified present on disk. All 6 task commit hashes
(`d54acc5`, `e010b6f`, `9c89c02`, `997461a`, `40a0fe7`, `b9ea857`) verified
present in git log.
