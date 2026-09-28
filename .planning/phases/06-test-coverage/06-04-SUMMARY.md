---
phase: 06-test-coverage
plan: 04
subsystem: testing
tags: [vitest, react-testing-library, frontend, positions-table, formatting, heatmap, watchlist]
requires:
  - phase: 06-test-coverage
    provides: "Plan 06-02's test harness (stubFetch/deferred, renderWithProviders, StubEventSource, vitest config)"
provides:
  - "Positions table proof that the frontend displays compute_portfolio_view() figures verbatim in every state and never recomputes P&L/percent from a live SSE tick"
  - "Formatter (formatCurrency/formatSignedCurrency/formatPercent) sign and rounding contract, including negative zero and binary-rounding edge cases"
  - "Heatmap colour-scale arithmetic pinned at its exact cap (10%) and ink (5%) thresholds with hand-computed hex values"
  - "Watchlist row session-change percentage, sparkline trend label, and click/Enter ticker selection proof"
affects: [06-05]
actuals:
  tokens: 5753
  tasks: 2
  commits: 2
  plan_head_before: a4e882d4b96fe9ef62fc72fc3e4bcd732f510409
tech-stack:
  added: []
  patterns:
    - "position()/entry() fixture builders typed against the shared PositionView/WatchlistEntry types, spreading caller overrides last so the required discriminant field is never duplicated (TS2783)"
    - "Hand-computed mixColor arithmetic recorded as a comment beside each chartTheme assertion, so expected hex values can be independently re-verified without calling the function under test"
    - "Test-local probe component reading useChartSelection(), rendered beside the component under test, to assert on cross-context side effects (ticker selection) through screen.getByText rather than a direct hook read"
key-files:
  created:
    - frontend/components/positions/PositionsTable.test.tsx
    - frontend/lib/format.test.ts
    - frontend/components/charts/chartTheme.test.ts
    - frontend/components/watchlist/WatchlistRow.test.tsx
  modified: []
key-decisions:
  - "Task 1's literal 'UI_SOURCE_UNTOUCHED' verify command (scoped to include frontend/test-support and frontend/vitest.setup.ts against pre-phase baseline 726046a) is unsatisfiable as written for the same reason 06-03 already documented: those harness files were added by 06-02 and are new relative to 726046a regardless of this plan's actions. Substituted the semantically-equivalent check the plan's own <verification> section describes in prose (git status --short over the same path set), which correctly showed only new *.test.tsx files. Task 2's own copy of the grep-gate (scoped to only frontend/app/components/lib, no test-support/vitest.setup.ts) passed literally as written."
  - "Refresh test uses vi.useFakeTimers({ toFake: [\"setInterval\", \"clearInterval\"] }) plus a real-timer-backed waitFor (rather than a manual promise-flush inside act) to observe the periodic refresh's async fetch resolve, since setTimeout/microtasks stay real under that fake-timer scope"
requirements-completed: [TEST-04]
coverage:
  - id: D1
    description: "Positions table renders every server-computed column verbatim across all its states (tracer, loading, empty, error, loss, flat, unpriced, fractional, order, headers, periodic refresh), and a live SSE tick updates only the current-price cell, never the P&L/percent cells"
    requirement: TEST-04
    verification:
      - kind: unit
        ref: "frontend/components/positions/PositionsTable.test.tsx (11 tests)"
        status: pass
      - kind: other
        ref: "Non-vacuity check: recomputed the P&L cell from (price - avg_cost) * quantity in PositionsRow.tsx; the tracer and refresh cases failed as expected (2 of 11). Restored; file confirmed byte-identical to 726046a."
        status: pass
    human_judgment: false
  - id: D2
    description: "Currency/percent formatter sign and rounding rules (including negative zero and binary-rounding), the heatmap colour scale's exact 10% cap and 5% ink threshold with hand-computed mixColor values, and the watchlist row's session-change percentage, sparkline trend label, and click/Enter ticker selection"
    requirement: TEST-04
    verification:
      - kind: unit
        ref: "frontend/lib/format.test.ts (13 tests), frontend/components/charts/chartTheme.test.ts (22 tests), frontend/components/watchlist/WatchlistRow.test.tsx (10 tests)"
        status: pass
      - kind: other
        ref: "npm --prefix frontend run test (111 total), typecheck, and lint all exit 0; grep gate confirms 4 hard-coded hex values (#4adc7f/#3d8a5f/#945457) in chartTheme.test.ts"
        status: pass
      - kind: other
        ref: "Two non-vacuity checks: HEATMAP_CAP_PCT 10->20 broke 9 of 22 chartTheme cases; formatSignedCurrency's n>=0 -> n>0 broke both zero-sign format.test.ts cases. Both restored; files confirmed byte-identical to 726046a."
        status: pass
    human_judgment: false
duration: 45min
completed: 2026-09-28
status: complete
---

# Phase 6 Plan 4: Positions Table, Display Formatting, and Heatmap Colour Scale Tests Summary

**Proved the positions table displays the backend's compute_portfolio_view() figures verbatim (never recomputing P&L from a live tick) and pinned formatter sign/rounding rules, the heatmap's 10%/5% colour thresholds, and the watchlist row's session-change percentage — all with hand-computed expected values, across four new test files and zero production code changes.**

## Performance
- **Duration:** ~45min
- **Started:** 2026-09-28
- **Completed:** 2026-09-28
- **Tasks:** 2/2
- **Files modified:** 4 (all created)

## Accomplishments
- `PositionsTable.test.tsx` (11 tests): tracer case proves a live SSE tick updates only the current-price cell while the Unrealized P&L and Chg % cells keep displaying the server's original `unrealized_pnl`/`pct_change` values; plus loading, empty, error, loss (red), flat (muted), unpriced (em-dash), fractional-quantity, row-order, header, and periodic-5s-refresh states — all read through `PortfolioProvider` via `renderWithProviders`, no mocking
- `format.test.ts` (13 tests): `formatCurrency`/`formatSignedCurrency`/`formatPercent` sign rules and `toFixed(2)` rounding, including negative zero rendering with a plus sign and the `3.00 -> 3.30` float-noise case (`9.999999999999996` displaying as `+10.00%`)
- `chartTheme.test.ts` (22 tests): `heatmapIntensity`'s cap behavior, `divergingFill` at the 9.9%/10%/10.01% boundary with hand-computed `mixColor` channel arithmetic recorded in comments, `mixColor` clamping (t > 1, t < 0, non-finite t), `tileTextColor`'s 4.99%/5% ink threshold, and `trendDirection`/`trendStroke`
- `WatchlistRow.test.tsx` (10 tests): pre-tick em-dash price/change state, session-change percentage colour and float-noise rounding, sparkline trend label ("AAPL trending up"/"down"), and click/Enter ticker selection proven through a test-local probe reading `useChartSelection()`
- Three non-vacuity checks performed and reverted across both tasks (see Deviations); all three touched files (`PositionsRow.tsx`, `chartTheme.ts`, `format.ts`) confirmed byte-identical to `726046a` after restoration
- Full frontend suite (111 tests across 10 files), `typecheck`, and `lint` all exit 0

## Task Commits
1. **Task 1: End-to-end positions table proof (GET to store to table to live price cell)** — `5cac1fc` (test)
2. **Task 2: Pin display arithmetic (formatters, heatmap colour scale, watchlist change percentage)** — `eb9997b` (test)

## Files Created/Modified
- `frontend/components/positions/PositionsTable.test.tsx` - 11 tests: tracer + loading/empty/error/loss/flat/unpriced/fractional/order/headers/refresh
- `frontend/lib/format.test.ts` - 13 tests: three formatters' sign rules, negative zero, binary rounding
- `frontend/components/charts/chartTheme.test.ts` - 22 tests: intensity cap, diverging fill boundary values, mixColor clamping, ink threshold, trend rule
- `frontend/components/watchlist/WatchlistRow.test.tsx` - 10 tests: pre-tick state, change percentage, float-noise rounding, sparkline labels, click/Enter selection

## Decisions Made
- Task 1's literal `UI_SOURCE_UNTOUCHED` verify command (including `frontend/test-support` and `frontend/vitest.setup.ts` in the diff against pre-phase baseline `726046a`) is unsatisfiable as written for the same reason documented in `06-03-SUMMARY.md`: those harness files are new relative to `726046a` by 06-02's design, not by any action of this plan. Ran the plan's own prose-described equivalent (`git status --short` over the same path set) instead, which correctly showed only the new `*.test.tsx` file as untracked. Task 2's own copy of the check (scoped to `frontend/app`/`components`/`lib` only) passed literally as written.
- The periodic-refresh test in `PositionsTable.test.tsx` uses `vi.useFakeTimers({ toFake: ["setInterval", "clearInterval"] })` plus a real-timer `waitFor` (rather than a manual `act(async () => ...)` flush) to observe the refresh's async fetch resolve, since only `setInterval`/`clearInterval` are faked and `setTimeout`-backed polling in `waitFor` still runs on real time.
- `position()`/`entry()` fixture builders spread caller overrides last without a separate explicit `ticker: overrides.ticker` line, avoiding a TS2783 "specified more than once" typecheck error while keeping `ticker` required via the `Pick<..., "ticker">` intersection type.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking verify script] Task 1's literal `UI_SOURCE_UNTOUCHED` automated verify command is unsatisfiable as written**
- **Found during:** Task 1 verification
- **Issue:** Same root cause as 06-03's documented deviation: the command diffs `frontend/test-support` and `frontend/vitest.setup.ts` (new files as of Plan 06-02) against pre-phase commit `726046a`, so it always contains non-`.test.` entries regardless of this plan's changes.
- **Fix:** Ran `git status --short -- frontend/app frontend/components frontend/lib frontend/test-support frontend/vitest.setup.ts`, confirming only the new test file was untracked (`??`) with no `M` entries — the invariant the plan's `<verification>` section actually describes.
- **Files modified:** None (verification-methodology substitution only)
- **Commit:** N/A (no code change)

**2. [Rule 3 - Blocking typecheck error] `position()`/`entry()` fixture builders triggered TS2783**
- **Found during:** Task 2 verification (`npm run typecheck`)
- **Issue:** Both `PositionsTable.test.tsx` and `WatchlistRow.test.tsx` built their fixture helpers with an explicit `ticker: overrides.ticker` property followed by `...overrides` in the same object literal — a redundant assignment TypeScript flags as "specified more than once, so this usage will be overwritten" (TS2783), since `overrides` (typed with a required `ticker` field via `Pick<T, "ticker">`) already carries it.
- **Fix:** Removed the explicit `ticker: overrides.ticker` line from both builders; `...overrides` alone already guarantees `ticker` is present and correctly typed.
- **Files modified:** `frontend/components/positions/PositionsTable.test.tsx`, `frontend/components/watchlist/WatchlistRow.test.tsx`
- **Verification:** `npm --prefix frontend run typecheck` exits 0; full suite still green (111 passed)
- **Commit:** `eb9997b` — the `WatchlistRow.test.tsx` fix landed with that file's own first commit; the `PositionsTable.test.tsx` fix amended a file already committed in Task 1 (`5cac1fc`), so its correction rides along in Task 2's commit as a follow-up edit to that file

### Non-vacuity checks (as required by the plan, not deviations)

**3. PositionsRow.tsx P&L recomputation (Task 1).** Temporarily changed the Unrealized P&L cell from `position.unrealized_pnl` to `(price - position.avg_cost) * position.quantity`. The tracer case's post-tick assertion and the periodic-refresh case both failed as expected (P&L read a value derived from the live price instead of the server's figure). Restored; all 11 tests passed again. File confirmed byte-identical to `726046a`.

**4. HEATMAP_CAP_PCT (Task 2).** Temporarily changed `chartTheme.ts`'s `HEATMAP_CAP_PCT` from `10` to `20`. 9 of 22 `chartTheme.test.ts` cases failed as expected (every cap-dependent intensity/fill/ink assertion). Restored; all 22 tests passed again. File confirmed byte-identical to `726046a`.

**5. formatSignedCurrency zero-sign comparison (Task 2).** Temporarily changed `format.ts`'s `n >= 0` to `n > 0` in `formatSignedCurrency`. Both zero-sign cases in `format.test.ts` failed as expected (`0` and `-0` rendered with a minus sign). Restored; all 13 tests passed again. File confirmed byte-identical to `726046a`.

**Total deviations:** 2 auto-fixed (one verify-script baseline substitution, one typecheck-driven fixture fix — neither touched application code) plus 3 planned non-vacuity checks executed and reverted. **Impact:** none on test content, coverage, or application behavior; all touched application files confirmed byte-identical to `726046a`.

## Issues Encountered
None beyond the two Rule 3 items documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness

Both frontend areas this plan owns (portfolio display calculations: positions table server-value fidelity, formatter/colour-scale arithmetic, watchlist session-change) are now locked by 45 new passing tests, on top of Plan 06-02's 27 and Plan 06-03's 28 — 111 total across 10 files. `npm --prefix frontend run test`, `typecheck`, and `lint` all exit 0. No non-test frontend file and no 06-02 harness file differs from its committed state. No blockers for Plan 06-05.

---
*Phase: 06-test-coverage*
*Completed: 2026-09-28*
