---
phase: 06-test-coverage
plan: 02
subsystem: testing
tags: [vitest, react-testing-library, jsdom, frontend, sse, price-flash]
requires:
  - phase: 02-core-trading-ui
    provides: PriceCell (flash trigger via useRef), priceStore.tsx (SSE connection-status state machine), Header.tsx (live total fallback chain)
provides:
  - Vitest 5 + React Testing Library test runner for frontend/ (jsdom environment, tsconfig-paths alias resolution)
  - Hand-rolled StubEventSource test double (D-04) with CONNECTING/OPEN/CLOSED statics and open()/emit()/emitPrices()/fail() helpers
  - Hand-rolled fetchStub/deferred test double (D-05) with default mount-time routes for portfolio/watchlist/chat/history
  - renderWithProviders() wrapping the real five-provider layout.tsx nesting
  - 27 passing frontend unit tests proving the price-flash contract, the SSE store's event/connection-status machine, and the header's live total
  - .dockerignore hardened against test code reaching the Docker build context
affects: [06-03, 06-04]
actuals:
  tokens: 119548
  tasks: 3
  commits: 2
  plan_head_before: acc141892b711906669b50e01f7a30153356242a
tech-stack:
  added: ["vitest@5.0.2", "vite@8.3.1", "@vitejs/plugin-react@6.1.1", "jsdom@30.1.1", "@testing-library/react@16.3.3", "@testing-library/dom@10.4.2", "@testing-library/jest-dom@7.0.1", "vite-tsconfig-paths@6.1.1"]
  patterns:
    - "Stub-class test doubles (StubEventSource, stubFetch) instead of mocking libraries, mirroring the backend's StubSource/_FakeRequest convention"
    - "renderWithProviders() reproduces app/layout.tsx's exact provider nesting verbatim rather than a reduced test-only tree"
key-files:
  created:
    - frontend/vitest.config.mts
    - frontend/vitest.setup.ts
    - frontend/test-support/eventSourceStub.ts
    - frontend/test-support/fetchStub.ts
    - frontend/test-support/renderWithProviders.tsx
    - frontend/components/ui/PriceCell.test.tsx
    - frontend/lib/priceStore.test.tsx
    - frontend/components/header/Header.test.tsx
  modified:
    - frontend/package.json
    - frontend/package-lock.json
    - .dockerignore
key-decisions:
  - "All eight pinned devDependencies (four flagged SUS purely on latest-release-date heuristic) installed exactly as evaluated at the Task 1 checkpoint after the human typed \"approved\" — no substitution needed, npm ls vite showed a single deduped 8.3.1"
  - "StubEventSource.emit() only delivers to listeners registered for the exact event type, and to onmessage only when that type is literally \"message\" — matches real browser EventSource routing and makes a test that fires the wrong event type fail loudly instead of silently passing"
  - "fetchStub keys routes by \"<METHOD> <pathname>\", ignoring query strings, so GET /api/portfolio/history matches regardless of its ?limit= query without special-casing"
requirements-completed: [TEST-04]
coverage:
  - id: D1
    description: "Vitest + RTL test runner bootstrap (jsdom environment, @vitejs/plugin-react, vite-tsconfig-paths, setup file, test/test:watch scripts)"
    requirement: TEST-04
    verification:
      - kind: unit
        ref: "npm --prefix frontend run test (27 passed)"
        status: pass
      - kind: other
        ref: "npm --prefix frontend run typecheck / lint / build all exit 0"
        status: pass
    human_judgment: false
  - id: D2
    description: "Price-flash trigger and 500ms fade timing proven against the real PriceCell component, including the unchanged-heartbeat no-reflash contract and the re-armed-timer boundary"
    requirement: TEST-04
    verification:
      - kind: unit
        ref: "frontend/components/ui/PriceCell.test.tsx (8 tests)"
        status: pass
    human_judgment: false
  - id: D3
    description: "SSE store (priceStore.tsx) named-event handling, first-price/history de-duplication, and the 5s disconnect-grace connection-status state machine"
    requirement: TEST-04
    verification:
      - kind: unit
        ref: "frontend/lib/priceStore.test.tsx (13 tests)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Header's live total value (three-level fallback chain, float-noise precision) and cash rendering through the real provider tree"
    requirement: TEST-04
    verification:
      - kind: unit
        ref: "frontend/components/header/Header.test.tsx (6 tests)"
        status: pass
    human_judgment: false
  - id: D5
    description: "Test code and test-support modules never reach the Docker build context"
    requirement: TEST-04
    verification:
      - kind: other
        ref: ".dockerignore ends with six test-exclusion patterns; grep gate confirms no application module imports test-support"
        status: pass
    human_judgment: false
duration: 55min
completed: 2026-09-28
status: complete
---

# Phase 6 Plan 2: Frontend Test Harness Bootstrap + Price-Flash/SSE/Header Proof Summary

**Bootstrapped Vitest 5 + React Testing Library from a zero-test-infrastructure frontend, then proved the price-flash, SSE connection-status, and live-total-value contracts against the real components through hand-rolled EventSource/fetch stubs — no mocking libraries, no UI code changed.**

## Performance
- **Duration:** ~55min (across two dispatches; this continuation covered Tasks 2-3)
- **Started:** 2026-09-28 (continuation dispatch)
- **Completed:** 2026-09-28
- **Tasks:** 3/3 (Task 1 checkpoint approved by human in a prior dispatch; Tasks 2-3 executed in this dispatch)
- **Files modified:** 11 (8 created, 3 modified)

## Checkpoint: Task 1 Package Legitimacy (carried forward)

Task 1 was a `gate="blocking-human"` package-legitimacy checkpoint. A prior dispatch presented the evidence table for all eight frontend test devDependencies (four flagged `SUS`/`too-new` purely because their most recent release was published within the last ~3 weeks — `vitest`, `jsdom`, `@testing-library/dom`, and the planner's own `vite@8.3.1` pin — each cross-checked against 60M+/week downloads and an official GitHub source repo). No package was installed during that task. The human then typed **"approved"**, authorizing installation of all eight packages exactly as evaluated, with no rejection and no substitution. This dispatch resumed from that approval and proceeded directly to Task 2's install step — this is normal checkpoint flow, not a deviation.

## Accomplishments
- Installed all eight pinned devDependencies with a single `npm install --save-dev --save-exact` command; no ERESOLVE conflicts; `npm ls vite` confirmed one deduped `vite@8.3.1` across `@vitejs/plugin-react`, `vite-tsconfig-paths`, and `vitest`'s own `@vitest/mocker` dependency
- Added `"test": "vitest run"` (single run, never watch — required by the validation strategy) and `"test:watch": "vitest"` to `frontend/package.json`
- Built `frontend/vitest.config.mts` (P-02: `.mts` extension, per the bundled Next.js Vitest guide and the project's ESM-only plugin versions) and `frontend/vitest.setup.ts` (jest-dom matchers, RTL `cleanup()`, per-test `EventSource`/`ResizeObserver` stub installation)
- Built `StubEventSource` (D-04, P-04): statics `CONNECTING`/`OPEN`/`CLOSED`, an `instances` registry with `reset()`/`latest()`, and test helpers `open()`, `emit()`, `emitPrices()`, `fail()`, `close()` matching the app's real named-`prices`-event SSE contract
- Proved the price-flash contract end-to-end against the real `PriceCell` component: null/first-price rendering, up/down flash colors, no re-flash on an unchanged heartbeat, the 499ms/500ms fade boundary, and the re-armed-timer boundary at 300ms+500ms=800ms
- Built `fetchStub`/`deferred` (D-05) and `renderWithProviders` (the exact five-provider `layout.tsx` nesting) as shared test-support for 06-03/06-04
- Proved the SSE store's named-event handling, first-price/history de-duplication, and the full 5s disconnect-grace connection-status state machine (4999/5000ms boundary, re-armed single timer across an error burst, recovery mid-window) against the real `priceStore.tsx`
- Proved the header's three-level current-price fallback chain, live recompute on ticks, connection label, and the `$9000.40` float-noise precision case against the real `Header.tsx`
- Appended six test-exclusion patterns to `.dockerignore` (P-05) so no test file, test-support module, or Vitest config reaches the production Docker image
- Ran and confirmed three non-vacuity checks (see Deviations/Issues below) — all mutations caused the expected test failures, and all three touched files (`PriceCell.tsx`, `priceStore.tsx`, `Header.tsx`) are byte-identical to commit `726046a` after restoration

## Task Commits
1. **Task 1: Package legitimacy checkpoint** — no commit (checkpoint only, no files modified; approved by human in prior dispatch)
2. **Task 2: End-to-end price-flash proof (npm script → Vitest → jsdom → PriceCell)** — `6e93a06` (feat)
3. **Task 3: SSE store + header live total proof, Docker exclusion** — `bd7b078` (feat)

## Files Created/Modified
- `frontend/vitest.config.mts` - Vitest config: jsdom env, both plugins, setup file, include/exclude globs
- `frontend/vitest.setup.ts` - jest-dom matchers, RTL cleanup, EventSource/ResizeObserver stub wiring
- `frontend/test-support/eventSourceStub.ts` - `StubEventSource` hand-rolled test double (D-04)
- `frontend/test-support/fetchStub.ts` - `stubFetch`/`deferred` hand-rolled test double (D-05)
- `frontend/test-support/renderWithProviders.tsx` - RTL render wrapped in the real provider nesting
- `frontend/components/ui/PriceCell.test.tsx` - 8 tests: flash trigger + timing
- `frontend/lib/priceStore.test.tsx` - 13 tests: SSE event handling + connection-status machine
- `frontend/components/header/Header.test.tsx` - 6 tests: live total + cash rendering
- `frontend/package.json` - added `test`/`test:watch` scripts and 8 exact-pinned devDependencies
- `frontend/package-lock.json` - lockfile updated for the 8 new devDependencies (dominates diff size)
- `.dockerignore` - appended 6 test-exclusion patterns (P-05)

## Decisions Made
- All eight packages installed exactly as evaluated at the Task 1 checkpoint; no version substitution was needed (no ERESOLVE conflict occurred)
- `StubEventSource.emit()` delivers strictly to listeners registered for the exact event `type` string, mirroring real browser `EventSource` routing (a test firing the wrong event type fails loudly by simply not reaching the handler, rather than silently appearing to pass)
- `fetchStub` keys routes by `"<METHOD> <pathname>"` only, deliberately dropping the query string from the key, so `GET /api/portfolio/history?limit=180` matches a `GET /api/portfolio/history` route registration without special-casing

## Deviations from Plan

### Non-vacuity checks (as required by the plan, not deviations)

**1. PriceCell flash timeout (Task 2).** Temporarily changed `PriceCell.tsx`'s `setTimeout(..., 500)` to `5000`. Confirmed the 499ms/500ms boundary test and the re-armed-timer test both failed (flash class still present when the test expected it cleared). Restored to `500`; all 8 tests passed again. File confirmed byte-identical to `726046a`.

**2. priceStore disconnect grace window (Task 3).** Temporarily changed `priceStore.tsx`'s `DISCONNECT_GRACE_MS` from `5000` to `4000`. Confirmed the "reports disconnected only after the 5s grace window" test failed (status was already `disconnected` at the 4999ms check-point, one test out of 13 failed). Restored to `5000`; all 13 tests passed again. File confirmed byte-identical to `726046a`.

**3. Header fallback chain (Task 3).** Temporarily changed `Header.tsx`'s `position.current_price ?? position.avg_cost` fallback to `position.current_price ?? 0`. Confirmed both the `$10300.00` fallback-total test and the downstream `$10400.00` live-recompute test failed (computed totals were $100 lower, matching ORCL's dropped `avg_cost * quantity` term). Restored the original fallback; all 6 tests passed again. File confirmed byte-identical to `726046a`.

None of the three touched files needed re-fixing beyond the restore — each mutation produced exactly the expected failure, confirming the corresponding tests are not vacuously passing.

**Total deviations:** 0 (three planned non-vacuity checks executed and passed as designed; not counted as deviations). **Impact:** none — plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness

The shared frontend test harness (`vitest.config.mts`, `vitest.setup.ts`, `StubEventSource`, `stubFetch`/`deferred`, `renderWithProviders`) is in place and proven by 27 passing tests across three files. Plans 06-03 and 06-04 can import these test-support modules directly rather than re-deriving stubs. `npm --prefix frontend run test`, `typecheck`, `lint`, and `build` all exit 0. No non-test file under `frontend/app`, `frontend/components`, or `frontend/lib` differs from commit `726046a`. No blockers.

---
*Phase: 06-test-coverage*
*Completed: 2026-09-28*
