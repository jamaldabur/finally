---
phase: 02-core-trading-ui
plan: 02
subsystem: ui
tags: [nextjs, react, typescript, sse, eventsource, tailwindcss-v4, trading]

requires:
  - phase: 02-core-trading-ui (plan 01)
    provides: "frontend scaffold, PriceStoreProvider/usePriceStore (single shared EventSource + firstPrices map), lib/api.ts fetch-wrapper shape, lib/format.ts, the D-08 page shell"
provides:
  - "components/ui/PriceCell.tsx — the one shared flash-on-real-change price cell, compares incoming price against a per-cell useRef of its own last rendered price (not the tick's previous_price), used by watchlist now and positions table in Plan 02-03"
  - "components/watchlist/WatchlistPanel.tsx + WatchlistRow.tsx — every backend-tracked ticker listed live from the shared SSE store, with a session-relative change percent"
  - "lib/api.ts: fetchWatchlist()"
  - "page.tsx: WatchlistPanel mounted above TradeBar in the left column, tracer AAPL readout removed"
affects: [02-03-header-connection-dot, 04-visualizations]

actuals:
  tokens: 2304
  tasks: 2
  commits: 2
  plan_head_before: 039f260ca8fded56411d597c1ffcca11019abbf3

tech-stack:
  added: []
  patterns:
    - "Flash trigger is per-cell render history (useRef), never the SSE tick's previous_price field — PriceCache.update() keeps the old previous_price on an unchanged heartbeat, so previous_price-based comparisons would flash forever after the first real move"
    - "components/ui/ holds primitives shared across feature folders (PriceCell now, ConnectionDot next) per D-12"

key-files:
  created:
    - frontend/components/ui/PriceCell.tsx
    - frontend/components/watchlist/WatchlistPanel.tsx
    - frontend/components/watchlist/WatchlistRow.tsx
  modified:
    - frontend/lib/api.ts
    - frontend/app/page.tsx

key-decisions:
  - "Task 1 (tdd=\"true\") executed as a standard type=\"auto\" task, same judgment call as 02-01's Task 2: no frontend test framework (Vitest/RTL) exists yet, its introduction is explicitly deferred to Phase 6 (TEST-04) per 02-VALIDATION.md, and the task's own <verify> block is entirely typecheck/grep automated checks with no test files listed"
  - "WatchlistRow computes change% as (price - firstPrice) / firstPrice * 100 using priceStore's firstPrices map, labelled \"Chg. since open\" in the panel header to avoid implying a market-day change, since the backend contract carries no daily open/previous close"

patterns-established:
  - "components/ui/PriceCell.tsx is the only flash implementation in the codebase — any future price cell (positions table) imports it rather than forking a second useRef+setTimeout flash"

requirements-completed: [UI-01]

coverage:
  - id: D1
    description: "The watchlist panel lists every ticker returned by GET /api/watchlist and each row's price updates on its own from the shared SSE stream"
    requirement: "UI-01"
    verification:
      - kind: unit
        ref: "npm --prefix frontend run typecheck"
        status: pass
      - kind: unit
        ref: "npm --prefix frontend run build && test -f frontend/out/index.html"
        status: pass
      - kind: unit
        ref: "grep -v '^\\s*//' frontend/components/watchlist/WatchlistRow.tsx | grep -c PriceCell (prints 3)"
        status: pass
    human_judgment: true
    rationale: "Confirming all ten default tickers render with live, self-updating prices in a real browser is the task's own <human-check> item #1, deferred to end-of-phase UAT per human_verify_mode: end-of-phase."
  - id: D2
    description: "A watchlist price cell flashes green on an uptick and red on a downtick, fading out within ~500ms, and flashes only on a real price move (not the 0.5s heartbeat re-broadcast of an unchanged price, even though that tick's previous_price still differs from its price)"
    requirement: "UI-01"
    verification:
      - kind: unit
        ref: "grep -v '^\\s*//' frontend/components/ui/PriceCell.tsx | grep -c useRef (prints 3)"
        status: pass
      - kind: unit
        ref: "grep -v '^\\s*//' frontend/components/ui/PriceCell.tsx | grep -cE duration-500 (prints 1)"
        status: pass
    human_judgment: true
    rationale: "Visually confirming the flash color/fade and that it stays silent on the heartbeat beat over a 20+ second watch is the task's own <human-check> items #2-#3, deferred to end-of-phase UAT."
  - id: D3
    description: "A watchlist entry whose price has never streamed (price null from GET /api/watchlist) renders an em-dash placeholder, shows no change percentage, and never flashes"
    requirement: "UI-01"
    verification:
      - kind: unit
        ref: "PriceCell.tsx: price === null returns before any flash-class logic (code inspection); WatchlistRow.tsx: changePct is null when price is null, rendered as an em-dash"
        status: pass
    human_judgment: false
  - id: D4
    description: "The watchlist panel opens no EventSource of its own — it reads the single connection created in Plan 02-01"
    requirement: "UI-01"
    verification:
      - kind: unit
        ref: "grep -rl 'new EventSource' frontend/app frontend/components frontend/lib (lists only frontend/lib/priceStore.tsx)"
        status: pass
      - kind: unit
        ref: "grep -rl 'fetch(' frontend/app frontend/components frontend/lib (lists only frontend/lib/api.ts)"
        status: pass
    human_judgment: false
  - id: D5
    description: "Watchlist prices render at exactly two decimal places and the change column is labelled as session-relative, not a market-day change"
    requirement: "UI-01"
    verification:
      - kind: unit
        ref: "PriceCell.tsx: price.toFixed(2); WatchlistPanel.tsx header span text: \"Chg. since open\" (code inspection)"
        status: pass
    human_judgment: true
    rationale: "Confirming the column label reads unambiguously in the rendered UI is the task's own <human-check> item #4, deferred to end-of-phase UAT."

duration: 24min
completed: 2026-09-17
status: complete
---

# Phase 2 Plan 2: Watchlist Panel and Shared Flash Price Cell Summary

**Every backend-tracked ticker now lists live in the left column via one shared `PriceCell` primitive that flashes green/red only on a real price move (never the 0.5s heartbeat), with a session-relative change percentage.**

## Performance

- **Duration:** 24 min
- **Started:** 2026-09-17T09:08:04Z
- **Completed:** 2026-09-17T09:32:00Z (approx.)
- **Tasks:** 2
- **Files modified:** 5 (3 created, 2 modified)

## Accomplishments
- Built `components/ui/PriceCell.tsx`, the single shared flash-on-real-change price cell: compares the incoming price against a `useRef` of its own last rendered price — deliberately NOT against the SSE tick's `previous_price` field, per the plan's `<flash_trigger_correction>` and `PriceCache.update()`'s heartbeat carry-forward behavior (backend/app/market/cache.py)
- Built `WatchlistPanel.tsx` (mount-time `fetchWatchlist()` for the ticker list + pre-stream prices, loading/empty states) and `WatchlistRow.tsx` (ticker + live `PriceCell` + session-relative change% from `priceStore`'s `firstPrices` map)
- Added `fetchWatchlist()` to `lib/api.ts` following the existing `fetchPortfolio`/`postTrade` fetch-wrapper shape exactly
- Mounted `<WatchlistPanel />` above `<TradeBar />` in `page.tsx`'s left column, removing Plan 02-01's single-AAPL tracer readout
- Confirmed exactly one `EventSource` construction (`lib/priceStore.tsx`) and exactly one `fetch(` call site (`lib/api.ts`) across the whole `frontend/app`, `frontend/components`, `frontend/lib` tree

## Task Commits

Each task was committed atomically:

1. **Task 1: PriceCell — the one flash-on-real-change primitive** - `d44a29f` (feat)
2. **Task 2: Watchlist panel — every tracked ticker, live, in the left column** - `7aa7b49` (feat)

**Plan metadata:** commit pending (this SUMMARY + STATE.md/ROADMAP.md/REQUIREMENTS.md docs commit, made immediately after this file)

## Files Created/Modified
- `frontend/components/ui/PriceCell.tsx` - shared flash-on-real-change price cell (em-dash on null, green/red flash fading over ~500ms)
- `frontend/components/watchlist/WatchlistPanel.tsx` - fetches the watchlist once on mount, renders one row per ticker, loading/empty states
- `frontend/components/watchlist/WatchlistRow.tsx` - ticker + `PriceCell` + session-relative change%
- `frontend/lib/api.ts` - adds `fetchWatchlist()`
- `frontend/app/page.tsx` - mounts `<WatchlistPanel />` above `<TradeBar />`, removes the tracer AAPL readout

## Decisions Made
- Task 1's `tdd="true"` attribute was executed as a standard `type="auto"` task (see key-decisions above) — same documented precedent as 02-01's Task 2, since no frontend test framework exists this phase and none is planned until Phase 6 (TEST-04)
- Change percentage guards `firstPrice !== 0` before dividing, to avoid a `NaN`/`Infinity` edge case the plan didn't explicitly call out but which Rule 1 (bug prevention) covers
- Used `entry.ticker` (already uppercase per the backend's `_normalize()`) as the React key and display value directly — no client-side re-normalization needed since `GET /api/watchlist` always returns canonical uppercase tickers

## Deviations from Plan

None - plan executed exactly as written. The Task 1 TDD-attribute handling is a documented process note (see key-decisions), not a Rule 1-4 deviation — it follows the same judgment 02-01 already established and recorded.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `PriceCell` is ready for Plan 02-03's positions table to import directly — no fork needed
- The D-08 left column (watchlist above trade bar) is now fully populated; the right/main column remains open for Plan 02-03's positions table
- End-of-phase UAT must still exercise this plan's `<human-check>` items (all ten default tickers listed and updating, flash color/fade timing, 20+ second no-heartbeat-flash watch, change-column label clarity, single `eventsource` network request) — recorded above as coverage entries D1-D2 and D5 with `human_judgment: true`
- Backend untouched by this plan — no regression risk to the Phase 1 test suite

---
*Phase: 02-core-trading-ui*
*Completed: 2026-09-17*

## Self-Check: PASSED

All created files verified present on disk (`frontend/components/ui/PriceCell.tsx`, `frontend/components/watchlist/WatchlistPanel.tsx`, `frontend/components/watchlist/WatchlistRow.tsx`, this SUMMARY.md). Both task commits (`d44a29f`, `7aa7b49`) confirmed present in `git log --oneline --all`.
