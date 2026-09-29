---
phase: 01-backend-trading-engine
plan: 02
subsystem: backend-trading-engine
tags: [fastapi, sqlite, asyncio, trade-execution, tdd]

requires:
  - phase: 01-01
    provides: "execute_trade(), TradeResult, _apply_buy seam, positions.upsert_position, POST /api/portfolio/trade contract"
provides:
  - "positions.delete_position() — epsilon-tolerant row deletion when a sell fully closes a position"
  - "service._apply_sell() — the sell half of execute_trade(), average-cost-preserving, epsilon-tolerant sufficiency guard"
  - "backend/tests/portfolio/test_service.py — direct execute_trade() unit tests including lock-serialization proof"
  - "Route-level sell and rejection-branch coverage in backend/tests/routes/test_portfolio.py"
affects: [01-03-watchlist-mutation, 01-04-snapshots-and-reads, phase-02-frontend, phase-03-chat]

actuals:
  tokens: 3984
  tasks: 3
  commits: 4
  plan_head_before: 9b93fab

tech-stack:
  added: []
  patterns:
    - "_apply_sell() mirrors _apply_buy() exactly: same lock scope, same TradeResult shape, avg_cost carried through unchanged on a sell"
    - "Epsilon tolerance added to the HELD side (never subtracted from the requested side) of the sufficiency comparison, so a float-imprecise sell-all succeeds rather than spuriously rejecting"

key-files:
  created:
    - backend/tests/portfolio/test_service.py
  modified:
    - backend/app/db/positions.py
    - backend/app/portfolio/service.py
    - backend/tests/routes/test_portfolio.py

key-decisions:
  - "Task 2's rejection-branch tests and Task 3's service-level tests were written after Task 1's GREEN implementation was already complete, and passed immediately rather than driving new code — the epsilon-tolerant sufficiency guard is not separable from a correct sell implementation (Task 1 could not pass its own tests without it). Documented as a deviation from strict per-task RED-then-GREEN below rather than silently treated as normal."

patterns-established:
  - "Sell-path rejection message: 'Insufficient shares: {ticker} sell of {quantity} exceeds held {held}' — held renders as 0 (not 0.0) when there is no position row"

requirements-completed: [PORT-02, PORT-03, PORT-04]

coverage:
  - id: D1
    description: "Market sell order — instant fill at cached price, credits cash, leaves avg_cost unchanged, deletes the position row when fully closed (PORT-02)"
    requirement: "PORT-02"
    verification:
      - kind: integration
        ref: "backend/tests/routes/test_portfolio.py::test_sell_credits_cash_and_reduces_position"
        status: pass
      - kind: integration
        ref: "backend/tests/routes/test_portfolio.py::test_sell_all_closes_position"
        status: pass
      - kind: integration
        ref: "backend/tests/routes/test_portfolio.py::test_sell_fractional_remainder_keeps_row"
        status: pass
      - kind: integration
        ref: "backend/tests/routes/test_portfolio.py::test_sell_records_trade_row"
        status: pass
      - kind: unit
        ref: "backend/tests/portfolio/test_service.py::test_sell_does_not_change_avg_cost"
        status: pass
    human_judgment: false
  - id: D2
    description: "Buy rejected with 400 when cost exceeds cash balance, zero state change (PORT-03, hardened from Plan 01)"
    requirement: "PORT-03"
    verification:
      - kind: integration
        ref: "backend/tests/routes/test_portfolio.py::test_rejected_buy_leaves_no_partial_write"
        status: pass
      - kind: unit
        ref: "backend/tests/portfolio/test_service.py::test_buy_insufficient_cash_returns_error_result"
        status: pass
    human_judgment: false
  - id: D3
    description: "Sell rejected with 400 when quantity exceeds held shares (including no-position case), epsilon-tolerant so a float-imprecise sell-all still succeeds (PORT-04)"
    requirement: "PORT-04"
    verification:
      - kind: integration
        ref: "backend/tests/routes/test_portfolio.py::test_sell_more_than_held_is_rejected"
        status: pass
      - kind: integration
        ref: "backend/tests/routes/test_portfolio.py::test_sell_with_no_position_is_rejected"
        status: pass
      - kind: integration
        ref: "backend/tests/routes/test_portfolio.py::test_sell_all_with_float_imprecision_succeeds"
        status: pass
      - kind: unit
        ref: "backend/tests/portfolio/test_service.py::test_sell_insufficient_shares_returns_error_result"
        status: pass
    human_judgment: false
  - id: D4
    description: "The portfolio lock actually serializes concurrent trades against shared cash_balance, preventing a double-spend rather than both requests reading the same pre-trade balance"
    verification:
      - kind: unit
        ref: "backend/tests/portfolio/test_service.py::test_concurrent_trades_are_serialized_by_the_lock"
        status: pass
    human_judgment: false
  - id: D5
    description: "execute_trade() normalizes ticker case and rejects unknown tickers uniformly for both sides"
    verification:
      - kind: unit
        ref: "backend/tests/portfolio/test_service.py::test_lowercase_ticker_is_normalized"
        status: pass
      - kind: unit
        ref: "backend/tests/portfolio/test_service.py::test_unknown_ticker_returns_error_result"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-09-16
status: complete
---

# Phase 1 Plan 02: Backend Trading Engine — SELL Path & State-Preserving Rejections Summary

Market SELL order execution with epsilon-tolerant position closing, plus a dedicated service-level test module proving average-cost math and that the portfolio lock genuinely serializes concurrent trades rather than merely existing.

## Performance
- **Duration:** 25min
- **Started:** 2026-09-16 (session start)
- **Completed:** 2026-09-16
- **Tasks:** 3 completed
- **Files modified:** 4 (1 created, 3 modified)

## Accomplishments
- Added `positions.delete_position()` (parameterized `DELETE`, `?` placeholders for both `user_id` and `ticker`) and `service._apply_sell()`, dispatched from `execute_trade()` on `side == "sell"` — mirrors `_apply_buy()` exactly: same `async with lock:` scope, same `TradeResult` shape, `avg_cost` carried through unchanged (average-cost accounting never re-bases on a sell)
- Proved both rejection branches (`Insufficient cash: `, `Insufficient shares: `) are write-free and epsilon-tolerant — a sell-all expressed as `0.30000000000000004` (three summed `0.1` buys) succeeds rather than spuriously triggering PORT-04, and a rejected buy/sell leaves cash, positions, and trades byte-for-byte unchanged
- Created `backend/tests/portfolio/test_service.py`, calling `execute_trade()` directly against real `PriceCache`/`SimulatorMarketDataSource`/`asyncio.Lock` objects (no mocks, no TestClient) — including a genuine concurrency proof: two `asyncio.gather`-fired buys sharing one lock produce exactly one `executed` and one `error` result, with final cash reflecting exactly one fill (4000.0, not 10000.0 or -2000.0)
- Full backend suite: 104 tests passing (up from 89 at the end of Plan 01)

## Task Commits
1. **Task 1 RED: Add failing route tests for sell path** - `1d5001c` (test)
1. **Task 1 GREEN: Implement market SELL path** - `1091828` (feat)
2. **Task 2: Add rejection-branch tests for sell and buy paths** - `fbb61a7` (test)
3. **Task 3: Add service-level test module for execute_trade()** - `470344f` (test)

**Plan metadata:** commit follows this summary

_Note: Tasks 2 and 3 produced no separate GREEN/feat commit — see Deviations below._

## Files Created/Modified
- `backend/app/db/positions.py` - `delete_position()`: parameterized `DELETE FROM positions WHERE user_id = ? AND ticker = ?`, returns whether a row was actually removed
- `backend/app/portfolio/service.py` - `_apply_sell()` (sufficiency guard, epsilon-tolerant close, avg_cost preserved, cash credited, trade row inserted), dispatched from `execute_trade()`; `NotImplementedError` placeholder removed
- `backend/tests/routes/test_portfolio.py` - 10 new tests: 4 happy-path sell tests (Task 1) + 4 rejection-branch tests + `test_rejected_buy_leaves_no_partial_write` (Task 2)
- `backend/tests/portfolio/test_service.py` - new module, 7 tests covering avg-cost math, both rejection shapes, ticker normalization, unknown-ticker rejection, and lock serialization (Task 3)

## Decisions Made
- Kept `held` unformatted (not zero-padded/rounded) in the `Insufficient shares: ` message per the plan's explicit instruction — money is rounded to 2 decimals, share counts are not, so fractional holdings read correctly in the error text.
- No change was needed to `app/routes/portfolio.py` — `TradeResponse.position` was already typed `PositionRecord | None` from Plan 01, so a closed position's `position: null` serializes correctly with zero route changes, confirming Plan 01's layering was right (per the plan's own stated purpose).

## Deviations from Plan

### Process Note (not a Rule 1-4 auto-fix)

**Tasks 2 and 3's tests passed immediately in RED, without driving new implementation.**
- **Found during:** Task 2 (writing `test_sell_more_than_held_is_rejected` and siblings) and Task 3 (writing the full `test_service.py` module)
- **What happened:** Per tdd.md's error-handling guidance ("Test doesn't fail in RED: feature may already exist... investigate"), I ran each new test set before assuming a GREEN step was needed. All 4 Task 2 tests and all 7 Task 3 tests passed on first run.
- **Why:** Task 1's `_apply_sell()` could not itself pass Task 1's own sell tests without an epsilon-tolerant sufficiency guard already in place (a sell of more shares than held, or of a nonexistent position, has to be rejected for the happy-path tests' state assertions to hold at all). The rejection logic and the epsilon tolerance are therefore not separable into a later task's "GREEN" — they were load-bearing for Task 1's own correctness. Task 3's service-level tests exercise the same `execute_trade()` that Task 1 and Task 2's route tests already exercise end-to-end via HTTP; nothing in Task 3's behavior list required code `execute_trade()` didn't already have (including the lock, which Plan 01 built and this plan never had reason to touch).
- **Verification:** Ran each new test file/subset individually before committing, confirmed non-error, behavior-correct passes (not collection errors or vacuous zero-test runs) — `uv run pytest tests/routes/test_portfolio.py -q -x` (14 passed) and `uv run pytest tests/portfolio/test_service.py -q -x` (7 passed) — then the full suite (104 passed) before each commit.
- **Impact:** None on scope, contract, or test coverage — every behavior the plan specified for Tasks 2 and 3 has a passing, correctly-targeted test. Only the commit shape differs from the plan's literal "RED then GREEN" per task (each of Tasks 2 and 3 produced a single `test(...)` commit with no paired `feat(...)`, since there was nothing left to implement).

**Total deviations:** 1 process note (no code-behavior deviation; Rules 1-4 do not apply — no bug, no missing functionality, no blocker, no architectural change).
**Impact:** None on the locked API contract, schema, or service-layer behavior.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `execute_trade()` now fully covers both `buy` and `sell` with a single validated, structured-result path — ready for Phase 3's chat flow to call unchanged, per the plan's stated success criteria.
- PORT-02, PORT-03, PORT-04 are all complete with passing tests selectable by the `-k` expressions recorded in `01-VALIDATION.md`.
- No blockers for Plan 03 (watchlist mutation) or Plan 04 (snapshots and reads), both of which depend only on Plan 01's schema/service shape, which this plan left unchanged.

---
*Phase: 01-backend-trading-engine*
*Completed: 2026-09-16*

## Self-Check: PASSED

All 4 created/modified files verified present on disk with the described content. All 4 task commit hashes (`1d5001c`, `1091828`, `fbb61a7`, `470344f`) verified present in `git log`.
