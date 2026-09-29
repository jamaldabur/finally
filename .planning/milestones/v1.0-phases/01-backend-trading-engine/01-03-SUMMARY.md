---
phase: 01-backend-trading-engine
plan: 03
subsystem: backend-trading-engine
tags: [fastapi, sqlite, asyncio, watchlist, chat-schema, tdd]

requires:
  - phase: 01-backend-trading-engine
    provides: "app/db/watchlist.py's _connect()/DB_PATH pattern (Plan 01) and app/main.py's lifespan block (Plans 01-02)"
provides:
  - "Persisted watchlist add/remove/list-with-metadata (app/db/watchlist.py)"
  - "GET/POST/DELETE /api/watchlist over app/routes/watchlist.py, wired into create_app()"
  - "chat_messages SQLite table, self-initializing on startup, ready for Phase 3"
affects: [01-04-snapshots-and-reads, phase-02-frontend, phase-03-chat]

actuals:
  tokens: 5312
  tasks: 3
  commits: 6
  plan_head_before: 2bc528dfd39f2e06e3aeb51d851768185707ff76

tech-stack:
  added: []
  patterns:
    - "Persisted watchlist mutation via INSERT OR IGNORE / DELETE, mirroring app/db/watchlist.py's existing ?-parameterized SQL style"
    - "Route-layer ticker normalization (_normalize = strip().upper()) applied before any validation or persistence, single shared helper per module"
    - "Thin route/service split: db/watchlist.py stays a persistence-only layer, app/routes/watchlist.py owns HTTPException translation and is_valid_ticker() gating"
    - "chat_messages.py mirrors watchlist.py's schema-module shape exactly (CREATE TABLE IF NOT EXISTS + asyncio.to_thread), schema-only this phase, no speculative read/write helpers"

key-files:
  created:
    - backend/app/db/chat_messages.py
    - backend/app/routes/watchlist.py
    - backend/tests/db/test_chat_messages.py
    - backend/tests/routes/test_watchlist.py
    - backend/tests/__init__.py
    - backend/tests/db/__init__.py
    - backend/tests/routes/__init__.py
  modified:
    - backend/app/db/watchlist.py
    - backend/app/main.py
    - backend/tests/db/test_watchlist.py

key-decisions:
  - "test_get_watchlist_joins_cached_prices seeds/asserts price on a ticker added via POST (ORCL) rather than a DEFAULT_WATCHLIST ticker, avoiding the same run_update_loop race against the background price loop that 01-01-SUMMARY.md documented for the BUY route tests"
  - "Added backend/tests/__init__.py, tests/db/__init__.py, tests/routes/__init__.py to disambiguate the plan's locked backend/tests/routes/test_watchlist.py from the pre-existing backend/tests/db/test_watchlist.py, which collide on basename under pytest's default import mode and broke whole-suite collection"

patterns-established:
  - "New route modules normalize all caller-supplied identifiers via one module-level _normalize() helper, called as the first statement in every endpoint that receives a ticker"

requirements-completed: [DATA-05, DATA-06, WLST-01, WLST-02, WLST-03]

coverage:
  - id: D1
    description: "app/db/watchlist.py exposes idempotent add_watchlist_ticker(), remove_watchlist_ticker(), and metadata-bearing get_watchlist_entries(), all persisted through the existing _connect()/DB_PATH helper (DATA-06)"
    requirement: "DATA-06"
    verification:
      - kind: unit
        ref: "backend/tests/db/test_watchlist.py::test_add_watchlist_ticker_persists, test_add_watchlist_ticker_is_idempotent, test_remove_watchlist_ticker_persists, test_get_watchlist_entries_returns_added_at"
        status: pass
    human_judgment: false
  - id: D2
    description: "POST /api/watchlist adds a recognized ticker case-insensitively and rejects an unrecognized one with 400, without persisting a write (WLST-01)"
    requirement: "WLST-01"
    verification:
      - kind: integration
        ref: "backend/tests/routes/test_watchlist.py::test_post_watchlist_adds_recognized_ticker, test_post_watchlist_normalizes_case, test_post_watchlist_rejects_unknown_ticker, test_post_watchlist_duplicate_reports_not_added"
        status: pass
    human_judgment: false
  - id: D3
    description: "DELETE /api/watchlist/{ticker} removes a ticker idempotently (second delete is a no-op 200, not a 404), case-insensitively (WLST-02)"
    requirement: "WLST-02"
    verification:
      - kind: integration
        ref: "backend/tests/routes/test_watchlist.py::test_delete_watchlist_removes_ticker, test_delete_watchlist_normalizes_case"
        status: pass
    human_judgment: false
  - id: D4
    description: "GET /api/watchlist returns every watched ticker joined with its latest PriceCache tick (or nulls if unpriced), sorted alphabetically, and a newly added ticker begins receiving prices from the existing update loop without a restart (WLST-03)"
    requirement: "WLST-03"
    verification:
      - kind: integration
        ref: "backend/tests/routes/test_watchlist.py::test_get_watchlist_returns_seeded_tickers, test_get_watchlist_joins_cached_prices, test_get_watchlist_uncached_ticker_has_null_price"
        status: pass
    human_judgment: false
  - id: D5
    description: "A ticker added via POST survives an app rebuild against the same SQLite file (DATA-06 persistence)"
    requirement: "DATA-06"
    verification:
      - kind: integration
        ref: "backend/tests/routes/test_watchlist.py::test_watchlist_add_survives_app_restart"
        status: pass
    human_judgment: false
  - id: D6
    description: "chat_messages table exists after startup with the exact six columns PLAN.md §7 specifies (id, user_id, role, content, actions, created_at), with actions nullable, and no unused Phase-3 read/write helpers (DATA-05)"
    requirement: "DATA-05"
    verification:
      - kind: unit
        ref: "backend/tests/db/test_chat_messages.py::test_init_db_creates_chat_messages_table, test_init_db_is_idempotent, test_actions_column_is_nullable"
        status: pass
    human_judgment: false
  - id: D7
    description: "Full backend test suite remains green and deterministic after all watchlist/chat_messages changes"
    verification:
      - kind: unit
        ref: "cd backend && uv run pytest -q (121 tests, run 3x for determinism)"
        status: pass
    human_judgment: false

duration: 11min
completed: 2026-09-16
status: complete
---

# Phase 1 Plan 03: Watchlist Mutation & chat_messages Schema Summary

Full read/write watchlist REST surface (add/remove/list-with-live-prices) plus the `chat_messages` table created for schema completeness, both self-initializing at app startup with zero new dependencies.

## Performance
- **Duration:** 11min
- **Started:** 2026-09-16T19:59:38Z
- **Completed:** 2026-09-16T20:10:24Z
- **Tasks:** 3 completed
- **Files modified:** 10 (7 created, 3 modified)

## Accomplishments
- Extended `app/db/watchlist.py` with idempotent `add_watchlist_ticker()`, `remove_watchlist_ticker()`, and a metadata-bearing `get_watchlist_entries()`, all reusing the existing `_connect()`/`DB_PATH` helper unchanged
- Built the full `GET`/`POST`/`DELETE /api/watchlist` REST surface in `app/routes/watchlist.py`, wired into `create_app()`, with case-insensitive ticker normalization applied consistently at the route boundary before validation or persistence
- Created the `chat_messages` table (schema only, per DATA-05) with the exact six columns PLAN.md §7 specifies, wired into `app/main.py`'s lifespan ahead of any background task creation
- Fixed a pytest module-basename collision (`tests/db/test_watchlist.py` vs. `tests/routes/test_watchlist.py`) by making the affected test directories real packages, without renaming either plan-locked file path

## Task Commits
1. **Task 1 RED: Add failing tests for watchlist add/remove/entries** - `4fcd1eb` (test)
1. **Task 1 GREEN: Implement persisted watchlist add/remove/entries** - `acd1f3c` (feat)
2. **Task 2 RED: Add failing route tests for watchlist endpoints** - `83505e3` (test)
2. **Task 2 GREEN: Implement watchlist REST endpoints** - `9f7d8ce` (feat)
3. **Task 3 RED: Add failing schema tests for chat_messages table** - `ca85229` (test)
3. **Task 3 GREEN: Create chat_messages table and wire startup init** - `5123852` (feat)

**Plan metadata:** commit follows this summary

_Note: no task required a REFACTOR commit — each GREEN implementation needed no follow-up cleanup._

## Files Created/Modified
- `backend/app/db/watchlist.py` - added `WatchlistEntry` dataclass, `add_watchlist_ticker`/`remove_watchlist_ticker`/`get_watchlist_entries`, updated module docstring
- `backend/app/routes/watchlist.py` - new router: `GET`/`POST`/`DELETE /api/watchlist`, `_normalize()` helper, Pydantic request/response models
- `backend/app/db/chat_messages.py` - `chat_messages` schema + idempotent `init_db()`, no read/write helpers (Phase 3's concern)
- `backend/app/main.py` - registers `watchlist_routes.router`, awaits `chat_messages.init_db()` before any `asyncio.create_task(...)`
- `backend/tests/db/test_watchlist.py` - 4 new tests for add/remove/entries
- `backend/tests/routes/test_watchlist.py` - 10 new route-level tests covering all three endpoints plus an app-restart persistence test
- `backend/tests/db/test_chat_messages.py` - 3 schema-introspection tests
- `backend/tests/__init__.py`, `backend/tests/db/__init__.py`, `backend/tests/routes/__init__.py` - empty package markers resolving the `test_watchlist.py` basename collision

## Decisions Made
- Used a POST-added, non-`DEFAULT_WATCHLIST` ticker (`ORCL`) rather than `AAPL` for the cached-price-join assertion, to avoid the same `run_update_loop` background-task race that Plan 01 documented and fixed for the BUY-path route tests.
- Resolved the `test_watchlist.py` basename collision via package `__init__.py` files rather than renaming either test file, preserving both plans' locked file paths exactly as specified.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Route test race between manually-seeded price and the background update loop**
- **Found during:** Task 2, initial `test_get_watchlist_joins_cached_prices` run
- **Issue:** The plan's `<behavior>` block specifies seeding `AAPL`'s price and asserting an exact match. `AAPL` is a member of `DEFAULT_WATCHLIST`, so `run_update_loop`'s already-in-flight first iteration can overwrite the manually-seeded price with a fresh simulator tick before the test's `GET` reads it — the exact race 01-01-SUMMARY.md documented for the BUY-path tests, reproduced here on the very first run (observed `189.99` vs. expected `190.0`).
- **Fix:** Rewrote the test to `POST /api/watchlist` a `TICKER_UNIVERSE` member not on `DEFAULT_WATCHLIST` (`ORCL`), then seed and assert on that ticker — `run_update_loop` only picks up a newly added ticker on its *next* 0.5s cycle, long after this synchronous test has finished.
- **Files modified:** `backend/tests/routes/test_watchlist.py`
- **Verification:** `tests/routes/test_watchlist.py` run 3 times consecutively after the fix — 10/10 passing each time, no flakiness observed
- **Commit:** `9f7d8ce`

**2. [Rule 3 - Blocking issue] pytest module basename collision across `tests/db/` and `tests/routes/`**
- **Found during:** Task 2, full-suite verification (`cd backend && uv run pytest -q`)
- **Issue:** The plan locks `backend/tests/routes/test_watchlist.py` as Task 2's new test file, but `backend/tests/db/test_watchlist.py` (extended in Task 1) already exists with the same basename. Neither `backend/tests/` nor any subdirectory had `__init__.py`, so pytest's default "prepend" import mode collects both files under the same bare module name `test_watchlist`, raising `import file mismatch` and aborting collection for the entire suite.
- **Fix:** Added empty `backend/tests/__init__.py`, `backend/tests/db/__init__.py`, and `backend/tests/routes/__init__.py`, making both directories real Python packages so pytest resolves fully-qualified module names (`tests.db.test_watchlist`, `tests.routes.test_watchlist`) instead of colliding basenames. No test file was renamed; both plans' locked paths are unchanged.
- **Files modified:** `backend/tests/__init__.py`, `backend/tests/db/__init__.py`, `backend/tests/routes/__init__.py` (all new, empty)
- **Verification:** `cd backend && uv run pytest -q` — 118 passed immediately after the fix, 121 passed after Task 3 was added; full suite run 3 times consecutively at plan end with no flakiness
- **Commit:** `9f7d8ce`

**3. [Rule 3 - Blocking issue] `strip().upper()` acceptance-criteria grep count included a docstring mention**
- **Found during:** Task 2, acceptance-criteria verification loop
- **Issue:** `grep -c 'strip().upper()' backend/app/routes/watchlist.py` returned 2, not the required 1 — the module docstring quoted the literal expression `` `.strip().upper()` `` in prose, alongside the one real implementation in `_normalize()`.
- **Fix:** Reworded the docstring to reference `_normalize` by name instead of quoting the literal expression, with no change to runtime behavior.
- **Files modified:** `backend/app/routes/watchlist.py`
- **Verification:** `grep -c 'strip().upper()' backend/app/routes/watchlist.py` returns `1`; `tests/routes/test_watchlist.py` still 10/10 passing
- **Commit:** `9f7d8ce`

**Total deviations:** 3 auto-fixed (1 Rule 1 — test-flakiness fix; 2 Rule 3 — blocking issues, one structural collision, one acceptance-criteria wording gap).
**Impact on plan:** None on the locked API contract, schema, or persistence behavior — all three deviations were test-infrastructure or documentation-wording fixes with zero change to the shipped endpoints' observable behavior.

## Issues Encountered
None beyond the deviations above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- The locked `GET`/`POST`/`DELETE /api/watchlist` contract (§ "Locked API contract" in `01-03-PLAN.md`) is implemented exactly as specified and ready for Phase 2's frontend to consume.
- `chat_messages` exists with PLAN.md §7's exact schema, ready for Phase 3's chat flow to add read/write logic with no further schema change.
- No blockers for Plan 04 (snapshots and reads) or later phases.

---
*Phase: 01-backend-trading-engine*
*Completed: 2026-09-16*

## Self-Check: PASSED

All 7 created files verified present on disk. All 6 task commit hashes
(`4fcd1eb`, `acd1f3c`, `83505e3`, `9f7d8ce`, `ca85229`, `5123852`) verified
present in git log.
