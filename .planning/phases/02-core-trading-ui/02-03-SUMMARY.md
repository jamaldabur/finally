---
phase: 02-core-trading-ui
plan: 03
subsystem: ui
tags: [nextjs, react, typescript, sse, eventsource, tailwindcss-v4, trading]

requires:
  - phase: 02-core-trading-ui (plans 01, 02)
    provides: "frontend scaffold, PriceStoreProvider/usePriceStore, PortfolioProvider/usePortfolio, lib/api.ts, PriceCell, WatchlistPanel/WatchlistRow, the D-08 page shell, TradeBar"
provides:
  - "components/positions/PositionsTable.tsx + PositionsRow.tsx — six-column positions table (ticker, quantity, avg cost, current price, unrealized P&L, % change), live current price via the D-07 fallback chain, loading/error/empty states"
  - "lib/portfolioStore.tsx: 5-second refresh() interval with an in-flight ref guard, cleaned up on unmount"
  - "components/ui/ConnectionDot.tsx — shared green/yellow/red connection primitive with a readable label per state"
  - "lib/priceStore.tsx: completed D-06 grace-timer state machine (single graceTimer ref, cleared on open/every tick, armed once per error, readyState-checked before flipping to disconnected)"
  - "components/header/Header.tsx — live total value (useLiveTotalValue, the one sanctioned client-side recompute), cash balance, connection dot, visible SIMULATED marker"
  - "globals.css: --color-gain/--color-loss tokens and --font-numeric family, applied site-wide to every element already carrying tabular-nums via a single .tabular-nums { font-family } rule"
affects: [03-ai-chat, 04-visualizations]

actuals:
  tokens: 5241
  tasks: 3
  commits: 3
  plan_head_before: b8a1c31f1e5b4a88a8d78005bad6bd362fc9fdb2

tech-stack:
  added: []
  patterns:
    - "Positions table resolves current_price through the identical SSE-then-API-then-avg_cost fallback chain the header's useLiveTotalValue uses — the two never disagree"
    - "avg_cost/unrealized_pnl/pct_change render straight from GET /api/portfolio through a formatter, with zero arithmetic in the row component — the backend's round-once convention is never re-derived client-side (D-04)"
    - "Grace-timer connection status: a single useRef timer handle, always cleared before being re-armed, so interleaved error/recovery events can never leave the dot stuck red while the stream is live (D-06)"
    - "Numeric-cell typography is applied globally via a plain-CSS `.tabular-nums { font-family: var(--font-numeric) }` rule rather than threading a second utility class through every numeric JSX element"

key-files:
  created:
    - frontend/components/positions/PositionsTable.tsx
    - frontend/components/positions/PositionsRow.tsx
    - frontend/components/header/Header.tsx
    - frontend/components/ui/ConnectionDot.tsx
  modified:
    - frontend/lib/portfolioStore.tsx
    - frontend/lib/priceStore.tsx
    - frontend/app/page.tsx
    - frontend/app/globals.css
    - frontend/components/trade-bar/TradeBar.tsx

key-decisions:
  - "PositionsRow and WatchlistRow both color gain/loss with literal Tailwind classes (text-green-400/text-red-400) rather than immediately migrating to the new --color-gain/--color-loss tokens — WatchlistRow.tsx and PriceCell.tsx are outside this plan's files_modified scope (established in Plans 02-01/02-02), so the new tokens are defined for future consumers (Phase 4) without touching files this plan doesn't own"
  - "The single monospace numeric family is applied via a global `.tabular-nums { font-family: var(--font-numeric) }` CSS rule in globals.css instead of a second utility class threaded through PositionsRow/WatchlistRow JSX — reaches every numeric cell (including WatchlistRow, out of this plan's file scope) with a globals.css-only change"
  - "portfolioStore's 5s interval and the TradeBar/mount-effect refresh calls share one isRefreshingRef guard, so an in-flight refresh from any source is never double-fired by the interval, not just interval-vs-interval overlap"

patterns-established:
  - "components/ui/ holds ConnectionDot alongside PriceCell — shared primitives usable by any future panel (Phase 3 chat, Phase 4 chart/heatmap) without forking"

requirements-completed: [UI-06, UI-09, UI-10]

coverage:
  - id: D1
    description: "The positions table shows one row per held position with ticker, quantity, average cost, current price, unrealized P&L, and percent change, and the current price column ticks live from the shared SSE stream"
    requirement: "UI-06"
    verification:
      - kind: unit
        ref: "npm --prefix frontend run typecheck"
        status: pass
      - kind: unit
        ref: "npm --prefix frontend run build && test -f frontend/out/index.html"
        status: pass
      - kind: unit
        ref: "grep -v '^\\s*//' frontend/components/positions/PositionsRow.tsx | grep -c PriceCell (prints 3)"
        status: pass
    human_judgment: true
    rationale: "Confirming a live position appears with a ticking current price and updating P&L in a real browser is the task's own <human-check> items #2-#3, deferred to end-of-phase UAT per human_verify_mode: end-of-phase."
  - id: D2
    description: "With zero positions, the positions table renders an explicit empty state rather than a bare header row; buying then fully selling a position returns to that empty state"
    requirement: "UI-06"
    verification:
      - kind: unit
        ref: "PositionsTable.tsx: portfolio.positions.length === 0 branch renders explicit copy before the table element is ever mounted (code inspection)"
        status: pass
    human_judgment: true
    rationale: "Confirming the empty-state message (not a bare table) actually renders before any trade, and reappears after a full sell, is the task's own <human-check> items #1 and #4, deferred to end-of-phase UAT."
  - id: D3
    description: "avg_cost, unrealized_pnl and pct_change render straight from GET /api/portfolio with no client-side arithmetic, and unrealized_pnl/pct_change are colored green/red/neutral by sign"
    requirement: "UI-06"
    verification:
      - kind: unit
        ref: "PositionsRow.tsx: gainLossClass(value) compares value > 0 / < 0 only, formatCurrency/formatSignedCurrency/formatPercent receive avg_cost/unrealized_pnl/pct_change unmodified (code inspection)"
        status: pass
    human_judgment: false
  - id: D4
    description: "The header shows a live total value updating on every price tick, the cash balance, and a connection dot fed from the real SSE status"
    requirement: "UI-09"
    verification:
      - kind: unit
        ref: "npm --prefix frontend run typecheck"
        status: pass
      - kind: unit
        ref: "npm --prefix frontend run build && test -f frontend/out/index.html"
        status: pass
      - kind: unit
        ref: "grep -v '^\\s*//' frontend/components/header/Header.tsx | grep -c useMemo (prints 2)"
        status: pass
    human_judgment: true
    rationale: "Confirming the total value visibly changes on essentially every price tick and the dot reads green while the stream is live is the task's own <human-check> item #1, deferred to end-of-phase UAT."
  - id: D5
    description: "The connection dot reflects real EventSource transitions: green on open/every tick, yellow after an error, red only after a 5s grace window with no live connection, and returns to green automatically on reconnect — with at most one grace timer pending at a time"
    requirement: "UI-09"
    verification:
      - kind: unit
        ref: "grep -v '^\\s*//' frontend/lib/priceStore.tsx | grep -c EventSource.OPEN (prints 1)"
        status: pass
      - kind: unit
        ref: "priceStore.tsx: clearGraceTimer() called at the top of onopen, the prices listener, and onerror (before re-arming) — code inspection confirms at most one timer handle is ever live"
        status: pass
    human_judgment: true
    rationale: "Actually stopping and restarting the backend process to watch the dot walk green -> yellow -> red -> green with no page reload is the task's own <human-check> items #3-#4, deferred to end-of-phase UAT."
  - id: D6
    description: "A visible SIMULATED marker sits beside the portfolio total so the terminal cannot be mistaken for a funded brokerage account"
    requirement: "UI-09"
    verification:
      - kind: unit
        ref: "Header.tsx: a literal 'Simulated' badge span renders unconditionally next to the app name (code inspection)"
        status: pass
    human_judgment: true
    rationale: "Confirming the marker is actually visible and legible in the rendered header is the task's own <human-check> item #2, deferred to end-of-phase UAT."
  - id: D7
    description: "No surface in the rendered UI is darker than the #0d1117 base background, the layout reads as a dense trading terminal, numeric columns are right-aligned and tabular, and the full watch-trade-reflect loop works end to end"
    requirement: "UI-10"
    verification:
      - kind: unit
        ref: "npm --prefix frontend run lint"
        status: pass
      - kind: unit
        ref: "grep -cE '^\\s*--color-[a-z-]+:\\s*(#0d1117|#1a1a2e|#ecad0a|#209dd7|#753991)\\s*;' frontend/app/globals.css (prints 5)"
        status: pass
      - kind: integration
        ref: "cd backend && uv run pytest -q (139 passed)"
        status: pass
      - kind: unit
        ref: "grep -rl 'new EventSource' frontend/app frontend/components frontend/lib (lists only lib/priceStore.tsx); grep -rl 'fetch(' (lists only lib/api.ts); grep -rl setFlashClass (lists only components/ui/PriceCell.tsx)"
        status: pass
    human_judgment: true
    rationale: "This is the task's own full-phase walkthrough <human-check> — all five phase success criteria confirmed together in a live browser — explicitly deferred to end-of-phase UAT per human_verify_mode: end-of-phase; this plan's automated checks can confirm the theme tokens and structural invariants but not the rendered visual result."

duration: ~11min
completed: 2026-09-17
status: complete
---

# Phase 2 Plan 3: Positions Table, Header, and Terminal Finish Summary

**Positions table (six live-authoritative columns), a header with a client-recomputed live total value and a truthful grace-windowed connection dot, and a terminal-wide density/token pass completing Phase 2's watch-trade-reflect loop.**

## Performance

- **Duration:** ~11 min
- **Started:** 2026-09-17T16:50:10Z
- **Completed:** 2026-09-17T17:00:48Z
- **Tasks:** 3
- **Files modified:** 9 (4 created, 5 modified)

## Accomplishments
- Built `PositionsTable.tsx`/`PositionsRow.tsx`: six required columns (Ticker, Quantity, Avg Cost, Current Price, Unrealized P&L, Chg %), an explicit empty state keyed on `positions.length`, a loading state, and current price resolved through the same D-07 fallback chain (`prices.get(ticker)?.price ?? position.current_price`) rendered via the shared `PriceCell`
- Added a 5-second `refresh()` interval to `portfolioStore.tsx`, guarded by an `isRefreshingRef` so no in-flight fetch (interval- or trade-triggered) is ever double-fired, cleaned up on unmount
- Completed the D-06 connection-status state machine in `priceStore.tsx`: a single `graceTimer` ref, cleared on `onopen` and every `prices` event, armed exactly once per `onerror`, checking `EventSource.OPEN` before promoting to `'disconnected'`
- Built `ConnectionDot.tsx` (green/yellow/red, readable label per state, literal complete Tailwind classes) and `Header.tsx` (`cash_balance` unmodified from `usePortfolio()`, `useLiveTotalValue` — the phase's one sanctioned client-side recompute — memoized over positions/cash/prices, plus a visible `SIMULATED` marker per T-02-10)
- Extended `globals.css` with `--color-gain`/`--color-loss` tokens and a `--font-numeric` family, applied to every already-`tabular-nums` element site-wide via one CSS rule, without needing to touch `WatchlistRow.tsx`/`PriceCell.tsx` (outside this plan's file scope)
- Confirmed exactly one `EventSource` construction, one `fetch(` call site, and one flash implementation repo-wide; confirmed all five PLAN.md §2 locked palette hex values remain unchanged; backend regression suite still 139/139 passing

## Task Commits

Each task was committed atomically:

1. **Task 1: Positions table — live current price, server-authoritative P&L** - `9121e72` (feat)
2. **Task 2: Header — live total value, cash balance, and a connection dot that tells the truth** - `6fe8051` (feat)
3. **Task 3: Terminal finish — density, palette, and the full-phase walkthrough** - `25e57d3` (feat)

**Plan metadata:** commit pending (this SUMMARY + STATE.md/ROADMAP.md/REQUIREMENTS.md docs commit, made immediately after this file)

## Files Created/Modified
- `frontend/components/positions/PositionsTable.tsx` - six-column table with loading/error/empty states
- `frontend/components/positions/PositionsRow.tsx` - one row; live price via D-07 fallback through `PriceCell`, no arithmetic on avg_cost/unrealized_pnl/pct_change
- `frontend/lib/portfolioStore.tsx` - 5s `refresh()` interval, `isRefreshingRef` double-fire guard
- `frontend/app/page.tsx` - mounts `PositionsTable` in the main column (Task 1), then `Header` at the top (Task 2)
- `frontend/lib/priceStore.tsx` - completed D-06 grace-timer state machine
- `frontend/components/ui/ConnectionDot.tsx` - shared green/yellow/red status primitive
- `frontend/components/header/Header.tsx` - live total value, cash, connection dot, SIMULATED marker
- `frontend/app/globals.css` - `--color-gain`/`--color-loss`/`--font-numeric` tokens, global `.tabular-nums` font-family rule
- `frontend/components/trade-bar/TradeBar.tsx` - density tightening (`mb-3`/`gap-3` -> `mb-2`/`gap-2`) to match the rhythm already used in `WatchlistPanel`/`PositionsTable`

## Decisions Made
- Kept `PositionsRow`'s gain/loss coloring as literal `text-green-400`/`text-red-400` (matching `WatchlistRow`'s already-established convention) rather than the new `--color-gain`/`--color-loss` tokens, since migrating `WatchlistRow.tsx` itself is outside this plan's `files_modified` scope — the tokens are defined and ready for Phase 4's heatmap to consume
- Applied the single numeric font family via a global `.tabular-nums { font-family: var(--font-numeric) }` CSS rule rather than a second utility class threaded through JSX, so it reaches `WatchlistRow.tsx`'s numeric cells too without touching that file
- Used one `isRefreshingRef` guard shared by `portfolioStore`'s interval and its exported `refresh()` — the interval calls the same guarded function `TradeBar` calls post-trade, so any in-flight fetch (from either source) blocks a second one

## Deviations from Plan

None — plan executed exactly as written. `PositionsRow.tsx` and `WatchlistPanel.tsx`/`Header.tsx` were already fully compliant with Task 3's density/token requirements as built in Tasks 1-2 (dim-text headers, muted borders, tabular-nums, right-aligned numerics), so Task 3's diff is scoped to `globals.css` (new tokens) and a minor `TradeBar.tsx` rhythm tightening — not a deviation, the plan's own acceptance criteria for Task 3 are satisfied by the combination of Tasks 1-2's output and this token addition.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 2's full watch-trade-reflect loop is code-complete: watchlist streams live prices (Plan 02-02), the trade bar executes real orders (Plan 02-01), the positions table shows server-authoritative P&L with a live price column (this plan), and the header shows a live total value with a truthful connection dot (this plan)
- `ConnectionDot.tsx` and the `--color-gain`/`--color-loss`/`--font-numeric` tokens are ready for Phase 3 (chat panel) and Phase 4 (chart/heatmap) to consume directly — no fork needed
- End-of-phase UAT must still exercise every `<human-check>` item recorded above as coverage entries D1-D7 with `human_judgment: true`, including Task 3's full five-criteria walkthrough (UI-01, UI-06, UI-07, UI-09, UI-10 together) and stopping/restarting the backend to watch the connection dot walk green → yellow → red → green
- Backend regression suite (`cd backend && uv run pytest -q`) still passes at 139/139 after this plan — no regression across the whole phase

---
*Phase: 02-core-trading-ui*
*Completed: 2026-09-17*

## Self-Check: PASSED

All created files verified present on disk (`frontend/components/positions/PositionsTable.tsx`, `frontend/components/positions/PositionsRow.tsx`, `frontend/components/header/Header.tsx`, `frontend/components/ui/ConnectionDot.tsx`, this SUMMARY.md). All three task commits (`9121e72`, `6fe8051`, `25e57d3`) confirmed present in `git log --oneline --all`.
