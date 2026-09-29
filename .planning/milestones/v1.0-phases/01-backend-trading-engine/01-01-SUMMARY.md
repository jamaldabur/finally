---
phase: 01-backend-trading-engine
plan: 01
subsystem: backend-trading-engine
tags: [fastapi, sqlite, asyncio, trade-execution, tdd]

requires: []
provides:
  - "SQLite tables users_profile, positions, trades — self-initializing on app startup"
  - "app/portfolio/service.py::execute_trade() — the single validate-and-apply path for market orders"
  - "POST /api/portfolio/trade — locked JSON request/response contract for the buy path"
  - "backend/tests/conftest.py — centralized isolated_db autouse fixture for all future db/route tests"
affects: [01-02-sell-and-concurrency, 01-03-watchlist-mutation, 01-04-snapshots-and-reads, phase-02-frontend, phase-03-chat]

actuals:
  tokens: 7514
  tasks: 3
  commits: 4
  plan_head_before: dd2db61c014b9661322fa00fcc3b2279e6805bbb

tech-stack:
  added: []
  patterns:
    - "Per-table SQLite module (schema + idempotent init) mirroring app/db/watchlist.py exactly"
    - "asyncio.Lock-guarded read-modify-write critical section on app.state.portfolio_lock, mirroring PriceCache's own lock"
    - "Service layer returns a structured TradeResult, never raises HTTPException — only the route layer translates to HTTP"
    - "TestClient.portal.call(...) as the sync-safe way to drive async setup/assertions on the SAME event loop the app's lifespan and background tasks run on"

key-files:
  created:
    - backend/tests/conftest.py
    - backend/app/db/users_profile.py
    - backend/app/db/positions.py
    - backend/app/db/trades.py
    - backend/app/portfolio/__init__.py
    - backend/app/portfolio/service.py
    - backend/app/routes/portfolio.py
    - backend/tests/routes/test_portfolio.py
    - backend/tests/db/test_users_profile.py
    - backend/tests/db/test_positions.py
    - backend/tests/db/test_trades.py
  modified:
    - backend/tests/db/test_watchlist.py
    - backend/tests/test_main.py
    - backend/tests/routes/test_health.py
    - backend/app/main.py

key-decisions:
  - "Buy-path route tests seed prices on a ticker not in DEFAULT_WATCHLIST (CSCO) rather than AAPL, to avoid racing run_update_loop's background fetch for on-watchlist tickers"
  - "TestClient.portal.call(...) established as the file's sync-safe pattern for running async setup/assertions on the app's own event loop, avoiding cross-event-loop hazards with a pytest-asyncio test loop"

patterns-established:
  - "New app/db/*.py modules import _connect (and DEFAULT_USER_ID) from .watchlist by function/name reference, never redeclare DB_PATH — preserves the single conftest.py monkeypatch target for all six tables"
  - "_apply_buy(...) isolated as a private helper in service.py so Plan 02 can add a sibling _apply_sell(...) without restructuring execute_trade()"

requirements-completed: [DATA-01, DATA-02, DATA-03, PORT-01, PORT-03]

coverage:
  - id: D1
    description: "users_profile table persists cash balance, seeded at $10,000, self-initializing on startup (DATA-01)"
    requirement: "DATA-01"
    verification:
      - kind: unit
        ref: "backend/tests/db/test_users_profile.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "positions table persists ticker/quantity/avg_cost with UNIQUE(user_id, ticker) upsert semantics (DATA-02)"
    requirement: "DATA-02"
    verification:
      - kind: unit
        ref: "backend/tests/db/test_positions.py"
        status: pass
    human_judgment: false
  - id: D3
    description: "trades table is an append-only fill log, ordered by executed_at (DATA-03)"
    requirement: "DATA-03"
    verification:
      - kind: unit
        ref: "backend/tests/db/test_trades.py"
        status: pass
    human_judgment: false
  - id: D4
    description: "POST /api/portfolio/trade executes a real market buy — fills at the live PriceCache price, debits cash, creates/grows a weighted-avg-cost position, appends a trades row (PORT-01)"
    requirement: "PORT-01"
    verification:
      - kind: integration
        ref: "backend/tests/routes/test_portfolio.py::test_buy_fills_at_cached_price_and_persists"
        status: pass
      - kind: integration
        ref: "backend/tests/routes/test_portfolio.py::test_second_buy_weights_avg_cost"
        status: pass
      - kind: integration
        ref: "backend/tests/routes/test_portfolio.py::test_buy_writes_one_trades_row_per_fill"
        status: pass
    human_judgment: false
  - id: D5
    description: "A buy whose cost exceeds cash balance is rejected with 400 and leaves cash, positions, and trades byte-for-byte unchanged (PORT-03)"
    requirement: "PORT-03"
    verification:
      - kind: integration
        ref: "backend/tests/routes/test_portfolio.py::test_buy_beyond_cash_is_rejected"
        status: pass
    human_judgment: false
  - id: D6
    description: "Database isolation for tests is supplied once by an autouse root fixture instead of being duplicated per test module"
    verification:
      - kind: unit
        ref: "cd backend && uv run pytest -q (89 tests, run 3x for determinism)"
        status: pass
    human_judgment: false

duration: 17min
completed: 2026-09-16
status: complete
---

# Phase 1 Plan 01: Backend Trading Engine — BUY Tracer Summary

One real market BUY order proven end-to-end — `POST /api/portfolio/trade` → Pydantic validation → lock-guarded `execute_trade()` → three new SQLite tables → JSON response — with the fill price sourced exclusively from the live `PriceCache`, never re-fetched from the market source.

## Performance
- **Duration:** 17min
- **Started:** 2026-09-16T19:30:44Z (approx, per STATE.md pre-execution timestamp)
- **Completed:** 2026-09-16T19:47:34Z
- **Tasks:** 3 completed
- **Files modified:** 15 (11 created, 4 modified)

## Accomplishments
- Centralized `isolated_db` test database isolation into `backend/tests/conftest.py`, removing four duplicated inline `monkeypatch.setattr` call sites across three pre-existing test files
- Built the full walking-skeleton BUY path: three new SQLite table modules (`users_profile`, `positions`, `trades`), the shared `app/portfolio/service.py::execute_trade()` validation-and-apply function, and `POST /api/portfolio/trade` — proven by six route-level pytest tests plus the full 89-test suite passing deterministically across repeated runs
- Added per-table unit test coverage for all three new tables (schema creation, init idempotency, CRUD round-tripping) with zero duplicated fixtures

## Task Commits
1. **Task 1: Centralize the isolated_db test fixture** - `7c2065d` (test)
2. **Task 2 RED: Add failing route test for BUY tracer** - `59b3034` (test)
2. **Task 2 GREEN: Implement BUY tracer** - `74d6a03` (feat)
3. **Task 3: Per-table unit tests for users_profile, positions, trades** - `0db5022` (test)

**Plan metadata:** commit follows this summary

_Note: Task 2 (tdd="true") produced RED then GREEN commits; no REFACTOR commit was needed — the GREEN implementation required no follow-up cleanup._

## Files Created/Modified
- `backend/tests/conftest.py` - autouse `isolated_db` fixture patching `watchlist.DB_PATH`, isolating all six tables via Python's late-binding of the module global
- `backend/app/db/users_profile.py` - `users_profile` schema, idempotent seed ($10,000), `get_cash_balance`/`set_cash_balance`
- `backend/app/db/positions.py` - `positions` schema (`UNIQUE(user_id, ticker)`), `Position` dataclass, `get_position`/`get_all_positions`/`upsert_position` (SQLite `ON CONFLICT DO UPDATE`)
- `backend/app/db/trades.py` - `trades` schema (append-only), `Trade` dataclass, `insert_trade`/`get_trades`
- `backend/app/portfolio/service.py` - `TradeResult`, `execute_trade()`, private `_apply_buy()` helper; lock-guarded, never raises an HTTP-layer exception, never re-fetches price from the market source
- `backend/app/routes/portfolio.py` - `POST /api/portfolio/trade`, the only module in the request path permitted to raise `HTTPException`
- `backend/app/main.py` - lifespan now calls the three new `init_db()`s before any `asyncio.create_task(...)`, registers `portfolio.router`, adds `app.state.portfolio_lock`
- `backend/tests/routes/test_portfolio.py` - 6 route-level tests covering fill/persist, weighted avg-cost, trades-row-per-fill, unpriced-ticker rejection, 422 on non-positive quantity, PORT-03 zero-state-change rejection
- `backend/tests/db/test_users_profile.py`, `test_positions.py`, `test_trades.py` - per-table unit tests
- `backend/tests/db/test_watchlist.py`, `backend/tests/test_main.py`, `backend/tests/routes/test_health.py` - dropped their inline `DB_PATH` monkeypatch in favor of the new root fixture

## Decisions Made
- Used `client.portal.call(...)` (Starlette `TestClient`'s own attribute, set on `__enter__`) as the established sync-safe pattern for seeding `PriceCache` and reading DB state from route tests — this runs the async call on the exact same event loop the app's lifespan and background tasks use, avoiding a cross-event-loop hazard that a plain `await` from a pytest-asyncio test coroutine would hit (the app runs inside `TestClient`'s dedicated portal thread with its own loop).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Route test race between manually-seeded price and the background update loop**
- **Found during:** Task 2, full-suite verification (individual file run was green; full-suite run failed non-deterministically)
- **Issue:** The plan's `<behavior>` block specifies seeding `AAPL`'s price via `price_cache.update("AAPL", 100.0)` before each buy assertion. `AAPL` is a member of `DEFAULT_WATCHLIST`, so the app's real `run_update_loop` background task also writes to the same cache entry concurrently. Under full-suite load, the background loop's fetch could land after the test's seed but before the POST request read the cache, non-deterministically overwriting `100.0` with the simulator's live-drifted AAPL price (observed: `189.97`).
- **Fix:** Switched the four price-seeding tests (`test_buy_fills_at_cached_price_and_persists`, `test_second_buy_weights_avg_cost`, `test_buy_writes_one_trades_row_per_fill`, `test_buy_beyond_cash_is_rejected`) to use `CSCO` — a `TICKER_UNIVERSE` member that is *not* in `DEFAULT_WATCHLIST`, so `run_update_loop` never fetches a price for it. This is the same technique already required by `test_buy_unpriced_ticker_is_rejected` (which uses `ORCL` for the same reason), just applied more broadly.
- **Files modified:** `backend/tests/routes/test_portfolio.py`
- **Verification:** Full suite run 3 times consecutively after the fix — 89/89 passing each time, no flakiness observed
- **Commit:** `74d6a03`

**Total deviations:** 1 auto-fixed (1 Rule 1 — bug/test-flakiness fix).
**Impact on plan:** None on the locked API contract, schema, or service-layer behavior — only the test ticker choice changed, to eliminate a genuine (if narrow) race condition against a live background task that the plan's literal `<behavior>` text did not anticipate.

## Issues Encountered
None beyond the deviation above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- The locked `POST /api/portfolio/trade` request/response contract (§ "Locked API contract" in `01-01-PLAN.md`) is implemented exactly as specified and is ready for Plan 02 (sell branch, concurrency tests) and Plan 03/04 to build on.
- `app/portfolio/service.py::execute_trade()` raises `NotImplementedError` for `side == "sell"` — Plan 02 adds `_apply_sell(...)` without restructuring the function, per the plan's explicit design intent.
- No blockers for Plan 02.

---
*Phase: 01-backend-trading-engine*
*Completed: 2026-09-16*

## Self-Check: PASSED

All 11 created files verified present on disk. All 4 task commit hashes
(`7c2065d`, `59b3034`, `74d6a03`, `0db5022`) verified present in git log.
