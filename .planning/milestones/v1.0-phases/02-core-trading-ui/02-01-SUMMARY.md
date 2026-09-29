---
phase: 02-core-trading-ui
plan: 01
subsystem: ui
tags: [nextjs, react, typescript, tailwindcss-v4, sse, eventsource, fastapi-cors, trading]

requires:
  - phase: 01-backend-trading-engine
    provides: "GET /api/portfolio, POST /api/portfolio/trade, GET /api/stream/prices (named `prices` SSE event), execute_trade()'s verbatim rejection strings"
provides:
  - "frontend/ Next.js 16 App Router + TypeScript + Tailwind v4 project, static-export build (output: 'export')"
  - "Shared single EventSource price store (PriceStoreProvider/usePriceStore) feeding all price-dependent UI"
  - "Portfolio context (PortfolioProvider/usePortfolio) — refresh() is the only way portfolio state changes"
  - "Single fetch access point (lib/api.ts: fetchPortfolio, postTrade) surfacing the backend's 400 detail verbatim"
  - "Trade bar: real buy/sell market orders for any ticker, decimal quantities, inline backend error text, double-click-safe"
  - "PLAN.md §2 dark terminal palette as Tailwind v4 @theme tokens"
  - "Dev-only CORS middleware on the FastAPI backend scoped to http://localhost:3000"
affects: [02-02-watchlist-positions, 02-03-header-connection-dot, 03-ai-chat, 04-visualizations]

actuals:
  tokens: 69267
  tasks: 3
  commits: 2
  plan_head_before: 07e529e97ccd293a37f001fa11739f78083f5993

tech-stack:
  added: ["next@16.3.5", "react@19.3.0", "react-dom@19.3.0", "tailwindcss@4.3.3", "@tailwindcss/postcss@4.3.3", "typescript@6.0.3 (downgraded from pinned 7.0.2, see deviations)", "eslint-config-next@16.3.5", "@types/react@19.3.0", "@types/node@22.20.3"]
  patterns:
    - "Single shared EventSource behind a React context (D-05) — no component opens its own SSE connection"
    - "Single fetch access point (lib/api.ts) — no component calls fetch() directly"
    - "Backend is sole authority for portfolio math (D-04) — the store only ever sets state from a fresh GET /api/portfolio response, never derives/patches locally"
    - "Mount-only data fetch written as an inline effect IIFE with a cancellation flag, decoupled from the exported refresh() callback, to satisfy eslint-plugin-react-hooks 7.1.1's set-state-in-effect rule"

key-files:
  created:
    - frontend/lib/types.ts
    - frontend/lib/format.ts
    - frontend/lib/priceStore.tsx
    - frontend/lib/api.ts
    - frontend/lib/portfolioStore.tsx
    - frontend/components/trade-bar/TradeBar.tsx
    - frontend/app/layout.tsx
    - frontend/app/page.tsx
    - frontend/app/globals.css
    - frontend/next.config.ts
  modified:
    - backend/app/main.py (dev-only CORSMiddleware)
    - backend/tests/test_main.py (CORS header assertion)

key-decisions:
  - "typescript downgraded from the plan's pinned 7.0.2 to 6.0.3 — eslint-config-next@16.3.5's bundled typescript-eslint@8.70.0 requires typescript >=4.8.4 <6.1.0"
  - "Root .gitignore's lib/ pattern negated for frontend/lib/ so the app's lib module isn't accidentally excluded"
  - "portfolioStore.tsx's mount effect is a self-contained async IIFE rather than calling the exported refresh() callback, to satisfy the new react-hooks/set-state-in-effect lint rule without restructuring the public API"

patterns-established:
  - "lib/api.ts is the only file permitted to call fetch() against the backend; lib/priceStore.tsx is the only file permitted to construct an EventSource"
  - "Trade bar and any future mutation UI must refetch GET /api/portfolio after a successful write rather than constructing a local position update"

requirements-completed: [UI-07, UI-10]

coverage:
  - id: D1
    description: "A live, self-updating AAPL price renders in the browser from the real backend SSE stream (single shared EventSource, named `prices` event)"
    requirement: "UI-10"
    verification:
      - kind: automated_ui
        ref: "npm --prefix frontend run build && test -f frontend/out/index.html"
        status: pass
      - kind: unit
        ref: "grep -v '^\\s*//' frontend/lib/priceStore.tsx | grep -c \"addEventListener('prices'\""
        status: pass
    human_judgment: true
    rationale: "Live-price ticking, dark-theme rendering, and single-connection network behavior require a browser walkthrough to confirm visually — completed and approved by the user during Task 1's tracer feedback gate (see Deviations/Issues section)."
  - id: D2
    description: "PLAN.md §2 dark terminal palette exists as Tailwind v4 @theme tokens (#0d1117, #1a1a2e, #ecad0a, #209dd7, #753991)"
    requirement: "UI-10"
    verification:
      - kind: unit
        ref: "grep -cE '^\\s*--color-[a-z-]+:\\s*(#0d1117|#1a1a2e|#ecad0a|#209dd7|#753991)\\s*;' frontend/app/globals.css"
        status: pass
    human_judgment: false
  - id: D3
    description: "A user can submit a buy or sell market order for any recognized ticker at any positive decimal quantity, no confirmation dialog, cash updates on success"
    requirement: "UI-07"
    verification:
      - kind: unit
        ref: "npm --prefix frontend run typecheck"
        status: pass
      - kind: unit
        ref: "npm --prefix frontend run build"
        status: pass
      - kind: manual_procedural
        ref: "curl POST /api/portfolio/trade {ticker:AAPL,side:buy,quantity:1} against running backend — verified 200 with trade/cash_balance/position, cash_balance dropped 200.83 to 9799.17"
        status: pass
    human_judgment: true
    rationale: "Double-click submit-once behavior, fractional-quantity UX, and the exact on-screen wording of rejected trades are UI/interaction checks the task's own <human-check> block defers to end-of-phase UAT per human_verify_mode: end-of-phase."
  - id: D4
    description: "A rejected trade (insufficient cash / insufficient shares) shows the backend's own rejection text inline next to the trade bar, and nothing else on screen changes"
    requirement: "UI-07"
    verification:
      - kind: manual_procedural
        ref: "curl POST /api/portfolio/trade {ticker:AAPL,side:buy,quantity:999999} against running backend — verified 400 with detail 'Insufficient cash: AAPL x999999.0 at 200.82 costs 200819799.18, available 9799.17'; lib/api.ts throws Error(detail) verbatim, TradeBar renders error.message as JSX text"
        status: pass
    human_judgment: true
    rationale: "Confirming the exact string renders inline in the DOM (not just that the backend returns it) and that no other portfolio figure moves is a visual/UI check, deferred to end-of-phase UAT alongside D3."
  - id: D5
    description: "Buy and Sell buttons disable while a request is in flight so a double-click submits exactly one trade"
    requirement: "UI-07"
    verification:
      - kind: unit
        ref: "TradeBar.tsx: isSubmitting state set before postTrade, cleared in finally block, both buttons' disabled prop bound to it — confirmed by code inspection per acceptance criteria"
        status: pass
    human_judgment: true
    rationale: "Actually double-clicking in a live browser and confirming exactly one POST lands is the task's own <human-check> item #5, deferred to end-of-phase UAT."

duration: 19min (Task 2 continuation session; Task 1 ran in a prior session separated by a human tracer-feedback checkpoint)
completed: 2026-09-17
status: complete
---

# Phase 2 Plan 1: Frontend Scaffold, Live SSE Price, and Real Trade Execution Summary

**Next.js 16 App Router + Tailwind v4 dark-terminal frontend streaming live AAPL prices over a shared EventSource, with a working buy/sell trade bar that posts real market orders and surfaces the backend's own rejection text inline.**

## Performance

- **Duration:** ~19 min for Task 2 (this continuation session); Task 1 (scaffold + tracer) ran in a prior session, paused at a tracer feedback gate for human browser verification, then resumed here
- **Started:** 2026-09-17T08:46:18Z (Task 1 commit) — see note above on the two-session split
- **Completed:** 2026-09-17T09:06:07Z
- **Tasks:** 3 (Task 0 package-legitimacy gate, Task 1 tracer, Task 2 trade bar)
- **Files modified:** 20 (15 created, 5 modified across both tasks; Task 2 alone touched 5: 3 created, 2 modified)

## Accomplishments
- Scaffolded `frontend/` as a Next.js 16 App Router + TypeScript + Tailwind v4 project with `output: 'export'` from day one, plus a `typecheck` script
- Wired one real end-to-end slice: FastAPI SSE (`/api/stream/prices`, named `prices` event) → single shared `EventSource` (`PriceStoreProvider`/`usePriceStore`) → live-updating AAPL readout, confirmed working in the browser by the user
- Locked in the PLAN.md §2 dark palette as Tailwind v4 `@theme` tokens (`#0d1117`, `#1a1a2e`, `#ecad0a`, `#209dd7`, `#753991`, plus a muted border/text token pair)
- Built the full trade bar: free-text ticker (client-side uppercased), decimal-quantity input, purple Buy/Sell buttons, disabled-while-submitting guard, and inline rendering of the backend's verbatim 400 `detail` string
- Added `lib/api.ts` (the app's single `fetch` access point) and `lib/portfolioStore.tsx` (`PortfolioProvider`/`usePortfolio`), both verified against the running backend via direct `curl` calls to `POST /api/portfolio/trade` and `GET /api/portfolio`
- Wired live cash balance and total portfolio value into the header via `formatCurrency`, sourced unmodified from `GET /api/portfolio` (no client-side derivation)
- Added a dev-only `CORSMiddleware` to the FastAPI backend, scoped to `http://localhost:3000`, with a backend test asserting the CORS header on `/api/health`

## Task Commits

Each task was committed atomically:

1. **Task 1: End-to-end "watch a live price" — scaffold, theme, shared SSE store, one streaming ticker** - `2c40546` (feat)
2. **Task 2: Trade bar — buy and sell any ticker for real, with the backend's own rejection text inline** - `ac918b5` (feat)

_Task 0 was a `checkpoint:human-verify` gate with no code changes — the user reviewed the six `[SUS]`-flagged npm packages and responded "approved" before any install._

**Plan metadata:** commit pending (this SUMMARY + STATE.md/ROADMAP.md/REQUIREMENTS.md docs commit, made immediately after this file)

## Files Created/Modified

**Task 1** (see `2c40546`): `frontend/package.json`, `frontend/package-lock.json`, `frontend/tsconfig.json`, `frontend/next.config.ts`, `frontend/postcss.config.mjs`, `frontend/eslint.config.mjs`, `frontend/.gitignore`, `frontend/.env.example`, `frontend/app/layout.tsx`, `frontend/app/page.tsx`, `frontend/app/globals.css`, `frontend/lib/types.ts`, `frontend/lib/format.ts`, `frontend/lib/priceStore.tsx`, `backend/app/main.py`, `backend/tests/test_main.py`

**Task 2** (`ac918b5`):
- `frontend/lib/api.ts` — `fetchPortfolio()`, `postTrade()`; the single place any component reaches the backend, throws the backend's verbatim `detail` on a 400
- `frontend/lib/portfolioStore.tsx` — `PortfolioProvider`/`usePortfolio`; `refresh()` is the only way portfolio state ever changes
- `frontend/components/trade-bar/TradeBar.tsx` — ticker/quantity inputs, Buy/Sell buttons, inline error, disabled-while-submitting
- `frontend/app/layout.tsx` — nests `PortfolioProvider` inside `PriceStoreProvider`
- `frontend/app/page.tsx` — adds `<TradeBar />` to the left column, live cash/total value in the header

## Decisions Made
- Kept the tracer's fixed AAPL readout in `page.tsx` rather than removing it, per the plan's own instruction ("remove only if the watchlist region is not yet present" — it isn't; Plan 02-02 replaces it)
- Used `type="button"` (not `type="submit"`) for both Buy and Sell so click handling is unambiguous and doesn't require managing native form-submit semantics for two competing actions
- Kept `refresh()` as the exported `usePortfolio()` API but wrote the mount-time initial fetch as its own inline effect (see deviation below) rather than changing the public shape of `PortfolioProvider`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `frontend/.gitignore`'s `lib/` pattern swallowed `frontend/lib/`**
- **Found during:** Task 1
- **Issue:** The generated `.gitignore` from `create-next-app` (or the root `.gitignore`) had a `lib/` pattern that also matched `frontend/lib/`, which is this project's own source directory, not a build artifact
- **Fix:** Added `!frontend/lib/` / `!frontend/lib/**` negation lines to the root `.gitignore`
- **Files modified:** `.gitignore`
- **Committed in:** `2c40546` (Task 1 commit)

**2. [Rule 3 - Blocking] `typescript` downgraded from the plan's pinned 7.0.2 to 6.0.3**
- **Found during:** Task 1
- **Issue:** `eslint-config-next@16.3.5`'s bundled `typescript-eslint@8.70.0` requires `typescript >=4.8.4 <6.1.0`; the plan's pinned `typescript@7.0.2` is incompatible and would break `npm run lint`
- **Fix:** Pinned `typescript@6.0.3` instead; confirmed `typecheck` and `lint` both pass clean
- **Files modified:** `frontend/package.json`, `frontend/package-lock.json`
- **Committed in:** `2c40546` (Task 1 commit)

**3. [Rule 1 - Bug] `eslint-plugin-react-hooks@7.1.1`'s `set-state-in-effect` rule flagged `portfolioStore.tsx`'s mount fetch**
- **Found during:** Task 2, `npm --prefix frontend run lint`
- **Issue:** `useEffect(() => { refresh(); }, [refresh])` — calling the exported `refresh()` callback (a `useCallback` that eventually calls `setState`) directly from an effect body triggered `react-hooks/set-state-in-effect: "Avoid calling setState() directly within an effect"`, a new rule shipped in this `eslint-config-next@16.3.5`/`eslint-plugin-react-hooks@7.1.1` combination
- **Fix:** Rewrote the mount effect as a self-contained async IIFE with its own `cancelled` guard that calls `fetchPortfolio()` and sets state directly, rather than delegating through the `refresh` function reference. `refresh()` itself is unchanged and remains the only way `TradeBar` (or any future consumer) re-fetches portfolio state after a mutation.
- **Files modified:** `frontend/lib/portfolioStore.tsx`
- **Verification:** `npm --prefix frontend run lint` exits 0; `npm --prefix frontend run typecheck` and `npm --prefix frontend run build` re-confirmed clean afterward
- **Committed in:** `ac918b5` (Task 2 commit)

---

**Total deviations:** 3 auto-fixed (1 bug — gitignore, 1 blocking — typescript version, 1 bug — lint rule). All three were necessary to reach a green build/lint/typecheck; none changed the plan's architecture or scope.
**Impact on plan:** No scope creep. All fixes are contained to tooling/config and one internal-only restructuring of a `useEffect` body; the public `usePortfolio()`/`PortfolioProvider` contract described in the plan is unchanged.

## Issues Encountered

**Process note on Task 2's `tdd="true"` frontmatter attribute:** Task 2 carried `tdd="true"`, and this project's `workflow.tdd_mode` config is unset/false, so the hard blocking TDD gate did not apply — per the executor's own instructions, RED→GREEN→REFACTOR discipline was still supposed to apply as a quality practice. However, `02-VALIDATION.md`'s Wave 0 Gaps section explicitly documents that no frontend test framework (Vitest/RTL) exists this phase, that installing one is out of scope (`TEST-04` is Phase 6 scope), and that "the planner should not add a testing-framework task to this phase." Task 2's own `<files>` list contains no test files, and its `<verify>` block is entirely typecheck/build/lint/grep automated checks plus a `<human-check>` block explicitly designed to ride through to end-of-phase UAT — consistent with this being a plan-authored, deliberate exception to strict TDD for this specific phase rather than an oversight. Given this explicit, documented conflict between the frontmatter attribute and the phase's own validation strategy, Task 2 was executed as a standard `type="auto"` task: implementation was verified via its own `<automated>` verify commands (`typecheck`, `build`, `lint`, the `dangerouslySetInnerHTML`/`toUpperCase()` grep checks) plus live `curl` calls against the running backend to confirm the exact request/response contract, rather than committing separate RED/GREEN test-file changes against a framework this phase deliberately does not install. The five `<human-check>` items (double-click-once, insufficient-cash wording, insufficient-shares wording, fractional buy, and the general buy/sell flow) are recorded above as coverage entries D3–D5 with `human_judgment: true`, deferred to end-of-phase UAT per `human_verify_mode: end-of-phase` — no mid-plan checkpoint was raised for them, matching the continuation instructions.

## User Setup Required

None — no external service configuration required. `NEXT_PUBLIC_API_BASE_URL` is already documented in `frontend/.env.example` (Task 1) and `frontend/.env.development.local` (git-ignored) is already in place locally.

## Next Phase Readiness

- `frontend/lib/api.ts`, `frontend/lib/priceStore.tsx`, and `frontend/lib/portfolioStore.tsx` are the stable foundation Plan 02-02 (watchlist, positions table) and Plan 02-03 (header, connection dot) build on directly — no rework needed
- The D-08 page shell's left column (watchlist above trade bar) and right/main column (positions table) slots are still open exactly as designed; `<TradeBar />` now occupies the bottom of the left column
- End-of-phase UAT must still exercise the five `<human-check>` items from Task 1 (visual/network confirmation) and Task 2 (double-click, insufficient-cash/shares wording, fractional buy) — none were skipped, all are recorded as `human_judgment: true` coverage entries above, not silently dropped
- Backend regression suite (`cd backend && uv run pytest -q`) still passes at 139/139 after this plan's CORS addition — no Phase 1 regression

---
*Phase: 02-core-trading-ui*
*Completed: 2026-09-17*

## Self-Check: PASSED

All created files verified present on disk (`frontend/lib/api.ts`, `frontend/lib/portfolioStore.tsx`, `frontend/components/trade-bar/TradeBar.tsx`, `frontend/app/layout.tsx`, `frontend/app/page.tsx`, this SUMMARY.md). Both task commits (`2c40546`, `ac918b5`) confirmed present in `git log --oneline --all`.
