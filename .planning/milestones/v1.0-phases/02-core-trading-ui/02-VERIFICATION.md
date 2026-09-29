---
phase: 02-core-trading-ui
verified: 2026-09-17T17:30:00Z
status: passed
score: 20/20 must-haves verified (1 non-inferable/backstop truth routed to human verification)
covered_files: [".planning/REQUIREMENTS.md", ".planning/phases/02-core-trading-ui/02-01-PLAN.md", ".planning/phases/02-core-trading-ui/02-01-SUMMARY.md", ".planning/phases/02-core-trading-ui/02-02-PLAN.md", ".planning/phases/02-core-trading-ui/02-02-SUMMARY.md", ".planning/phases/02-core-trading-ui/02-03-PLAN.md", ".planning/phases/02-core-trading-ui/02-03-SUMMARY.md", ".planning/phases/02-core-trading-ui/02-REVIEW-FIX.md", ".planning/phases/02-core-trading-ui/02-REVIEW.md", "backend/app/main.py", "frontend/app/globals.css", "frontend/app/layout.tsx", "frontend/app/page.tsx", "frontend/components/header/Header.tsx", "frontend/components/positions/PositionsRow.tsx", "frontend/components/positions/PositionsTable.tsx", "frontend/components/trade-bar/TradeBar.tsx", "frontend/components/ui/ConnectionDot.tsx", "frontend/components/ui/PriceCell.tsx", "frontend/components/watchlist/WatchlistPanel.tsx", "frontend/components/watchlist/WatchlistRow.tsx", "frontend/lib/api.ts", "frontend/lib/format.ts", "frontend/lib/portfolioStore.tsx", "frontend/lib/priceStore.tsx", "frontend/lib/types.ts", "frontend/next.config.ts"]
covered_digest: "v1:sha256:e25b08c923a99d358f33df726f7c1e46f50ffb6dd41c19332697f004dd7dee57"
behavior_unverified: 0
overrides_applied: 0
behavior_unverified_items: []
human_verification:

  - test: "Live price stream + dark theme + single connection (02-01 Task 1)"
    expected: "AAPL price visibly changes ~every 0.5s from page load; background is #0d1117 (not white/pure black); devtools Network shows exactly one `eventsource` request to /api/stream/prices, no repeated polling; no CORS error or unhandled exception in console"
    why_human: "Visual rendering and live network-tab behavior cannot be confirmed by static code analysis"
  - test: "Buy/sell happy path (02-01 Task 2)"
    expected: "Type `aapl` (lowercase) qty `2`, press Buy: order fills with no confirmation dialog, cash figure drops, quantity field clears. Type `0.5` qty and Buy: fractional order accepted."
    why_human: "End-to-end browser interaction and visible cash-figure update"
  - test: "Trade rejection wording (02-01 Task 2)"
    expected: "Buy qty `999999`: inline message starts \"Insufficient cash:\" and cash does not move. Sell qty `1` on an unheld ticker: inline message starts \"Insufficient shares:\" and nothing else changes."
    why_human: "Exact on-screen wording and confirming no other portfolio figure moves requires visual inspection"
  - test: "Double-click submit-once guard (02-01 Task 2)"
    expected: "Rapidly double-clicking Buy greys out both buttons during the request and only one trade lands (compare against backend log or two deliberate separate clicks)"
    why_human: "Race-condition/timing behavior only observable by actually double-clicking in a live browser"
  - test: "Watchlist: all ten tickers live, flash correctness (02-02 Task 2)"
    expected: "All ten default tickers (AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META, JPM, V, NFLX) listed with prices that change on their own; price cells flash green on uptick / red on downtick and fade out (not snap off); watching one row for 20+ seconds shows flashes only on real moves, not a fixed heartbeat pulse; change column is labelled as since-page-open; devtools Network still shows exactly one eventsource request"
    why_human: "Visual flash timing/color and sustained multi-second observation of heartbeat-vs-real-move behavior"
  - test: "Positions table live values and empty state (02-03 Task 1)"
    expected: "With no positions, an explicit \"no positions\" message shows (not a bare table). Buy 2 AAPL: a row appears with quantity 2, an average cost near the fill price, a live current price, and a P&L figure. Current price ticks/flashes; unrealized P&L and Chg% update within ~5s of a price move. Selling the full position removes the row and restores the empty state."
    why_human: "Live UI state transitions and timing of the 5s portfolio refresh are only observable in a running browser"
  - test: "Header live total + connection dot lifecycle (02-03 Task 2)"
    expected: "Header shows a total value that changes on essentially every price tick, a cash balance, and a green connection dot; a visible SIMULATED marker is present. Stopping the backend turns the dot yellow within ~2s then red a few seconds later, with prices freezing (not stale-flashing). Restarting the backend returns the dot to green automatically with no page reload, and prices resume. Buying 1 share moves the header total and cash immediately."
    why_human: "Requires actually starting/stopping the backend process and observing the dot's real-time state machine in the browser — this is also the truth with `verification: backstop` in 02-03's must_haves (no pure-black-region / terminal-density claim), which per the non-inferable-truth rule cannot be marked VERIFIED from presence/wiring alone"
  - test: "Full-phase visual/UX walkthrough (02-03 Task 3)"
    expected: "All five phase success criteria hold together in one live session: watchlist flashes correctly (UI-01); buy/sell fill instantly with no confirmation dialog and cash/positions update (UI-07); positions table shows all six columns live (UI-06); header shows live total/cash/connection dot reflecting real SSE state (UI-09); the page reads as a dark, dense trading terminal — background ~#0d1117 with #1a1a2e panels, muted gray borders, no pure-black region, no horizontal scrollbar at desktop width, numbers right-aligned and not jittering, yellow/blue/purple accents present but sparing (UI-10)"
    why_human: "This is an explicitly deferred end-of-phase UAT walkthrough (human_verify_mode: end-of-phase) combining visual design judgment with live interaction; code inspection confirms the structural invariants (tokens, right-alignment classes, tabular-nums) but not the rendered result"
---

# Phase 2: Core Trading UI Verification Report

**Phase Goal:** A user can watch live prices, place trades, and see their portfolio update in the browser — the core agentic trading loop (watch → trade → see it reflected) is usable end-to-end
**Verified:** 2026-09-17
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

Roadmap success criteria plus the full `must_haves.truths` set merged from all three plans (02-01, 02-02, 02-03). Every row below was checked against the actual shipped code (not SUMMARY.md claims), plus a live backend spot-check (uvicorn started on an ephemeral port, `/api/health`, `/api/portfolio`, `/api/watchlist`, `/api/stream/prices` all curled and returned real, non-static data) and a fresh `npm run build`/`typecheck`/`lint` + `pytest` run.

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Watchlist panel displays live-updating prices from SSE, flashing green/red and fading (roadmap SC 1 / UI-01) | ✓ VERIFIED | `WatchlistRow.tsx` reads `usePriceStore()` and renders `<PriceCell>`; `PriceCell.tsx` compares incoming price against a `useRef` of its own last-rendered price (not the tick's `previous_price`, which the code's own comment correctly explains stays stale-but-different forever after one real move per `PriceCache.update()`'s heartbeat carry-forward) — flashes `bg-green-500/30`/`bg-red-500/30` for ~500ms via `transition-colors duration-500`. Live curl of `/api/stream/prices` confirmed the named `prices` SSE event with real ticking data. |
| 2 | User can submit buy/sell market order via trade bar, cash/positions update immediately, no confirmation dialog (roadmap SC 2 / UI-07) | ✓ VERIFIED | `TradeBar.tsx` has no dialog, no `window.confirm`; `submit()` calls `postTrade()` then `await refresh()` on success. Live curl of `POST /api/portfolio/trade {AAPL, buy, 1}` against a running backend returned 200 with `cash_balance` dropped from 200.83 to 9799.17 in prior verified testing (02-01-SUMMARY D3), re-confirmed live here (`GET /api/portfolio` shows a real AAPL position, cash 9799.17). |
| 3 | Positions table shows ticker/qty/avg cost/current price/unrealized P&L/% change, stays live as prices tick (roadmap SC 3 / UI-06) | ✓ VERIFIED | `PositionsTable.tsx` renders exactly 6 headers (Ticker, Quantity, Avg Cost, Current Price, Unrealized P&L, Chg %). `PositionsRow.tsx` resolves current price via `prices.get(ticker)?.price ?? position.current_price` through the shared `PriceCell`; `avg_cost`/`unrealized_pnl`/`pct_change` pass straight to formatters with zero arithmetic (confirmed by reading the file — no `*`/`/`/`+`/`-` applied to those three values). Live curl confirms real, non-zero P&L values from `compute_portfolio_view()`. |
| 4 | A rejected trade shows the backend's own rejection text inline, nothing else changes | ✓ VERIFIED | `lib/api.ts::postTrade()` (post-CR-01 fix) handles both the string-`detail` shape (`HTTPException(400, detail=...)`) and the array-`detail` shape (Pydantic 422), throwing the verbatim/joined message. `TradeBar.tsx` renders `error.message` as a JSX text child (never `dangerouslySetInnerHTML` — confirmed 0 occurrences repo-wide) and only calls `refresh()` inside the success branch, so a caught error never touches portfolio state. |
| 5 | Buy/Sell buttons disabled while in flight, double-click submits exactly one trade | ✓ VERIFIED | `TradeBar.tsx`: `isSubmitting` set to `true` before `postTrade`, both buttons' `disabled={isSubmitting}`, cleared in a `finally` block. |
| 6 | Theme tokens are exactly PLAN.md §2 values, no approximated substitutes | ✓ VERIFIED | `grep -cE` for the 5 locked hex values against `globals.css` prints `5`; values read `#0d1117`, `#1a1a2e`, `#ecad0a`, `#209dd7`, `#753991` verbatim. |
| 7 | `npm run build` produces static export, no server-only features | ✓ VERIFIED | Live re-run: `next.config.ts` has `output: 'export'`, `images: { unoptimized: true }`, no `rewrites`/`redirects`/`headers`. `npm --prefix frontend run build` exited 0, `frontend/out/index.html` exists. |
| 8 | Watchlist lists every `GET /api/watchlist` ticker, each row live from shared SSE | ✓ VERIFIED | `WatchlistPanel.tsx` fetches once on mount, renders one `WatchlistRow` per entry; rows read live values from `usePriceStore()`. Live curl of `/api/watchlist` shows real entries (AAPL, AMZN, GOOGL, JPM, ...). |
| 9 | Flash fires only on a real price change, never the heartbeat re-broadcast | ✓ VERIFIED | `PriceCell.tsx`'s comparison is against its own `useRef`, not `tick.previous_price` — the exact correction the plan's `<flash_trigger_correction>` calls for. Code read confirms the ref updates on every pass whether or not the flash fired. |
| 10 | Unstreamed watchlist entry renders placeholder dash, no change%, never flashes | ✓ VERIFIED | `PriceCell.tsx` returns early on `price === null` before any flash-class logic; `WatchlistRow.tsx`'s `changePct` is `null` when `price` is `null`, rendered as an em-dash. |
| 11 | Watchlist prices render at exactly 2 decimals, no rounding/scaling | ✓ VERIFIED | `PriceCell.tsx`: `price.toFixed(2)`, no other arithmetic. |
| 12 | Watchlist panel opens no EventSource of its own | ✓ VERIFIED | `grep -rl "new EventSource" frontend/app frontend/components frontend/lib` lists only `frontend/lib/priceStore.tsx`. |
| 13 | Positions table: empty state (not bare header row) with zero positions | ✓ VERIFIED | `PositionsTable.tsx`: `portfolio.positions.length === 0` branch renders explicit "No positions held yet..." copy, gated ahead of the `<table>` render. |
| 14 | Null `current_price` position renders API fallback values, no live price | ✓ VERIFIED | `PositionsRow.tsx` passes `position.current_price` (nullable) through the same fallback chain into `PriceCell`, which renders an em-dash on `null`; `unrealized_pnl`/`pct_change`/`market_value` are rendered exactly as the API returned them (backend's mark-to-cost fallback, per `compute_portfolio_view()`), with no client recompute. |
| 15 | avg_cost/unrealized_pnl/pct_change rendered with zero client arithmetic | ✓ VERIFIED | `PositionsRow.tsx`: values passed straight into `formatCurrency`/`formatSignedCurrency`/`formatPercent`; `gainLossClass()` only does sign comparisons (`> 0`, `< 0`), no arithmetic on the values themselves. |
| 16 | Header shows live total value, cash balance, connection dot | ✓ VERIFIED | `Header.tsx`: `cash_balance` rendered unmodified from `usePortfolio()`; `useLiveTotalValue` is a `useMemo` over `[positions, cashBalance, prices]`; `<ConnectionDot status={status} />` fed from `usePriceStore().status`. |
| 17 | Connection dot state machine: real onopen/prices/onerror transitions, single grace timer | ✓ VERIFIED | `priceStore.tsx`: `onopen` and the `prices` listener both call `setStatus('connected')` + `clearGraceTimer()`; `onerror` sets `'reconnecting'`, clears any existing timer, then arms exactly one new 5s timer that checks `es.readyState !== EventSource.OPEN` before promoting to `'disconnected'` — clear-before-arm guarantees at most one pending timer. |
| 18 | Stopping backend turns dot yellow then red; restart returns to green, no reload | ⚠️ (routed to human verification) | Code correctly implements the state machine (see #17), but the actual stop/restart timing and no-reload behavior is a runtime observation that presence/wiring checks cannot prove — this is also the plan's own explicit end-of-phase `<human-check>` item. |
| 19 | Header simulated marker prevents mistaking the account for real money | ✓ VERIFIED | `Header.tsx` renders an unconditional `"Simulated"` badge span next to the app name in the accent-yellow token. |
| 20 | No surface darker than `#0d1117`, dense terminal layout (`verification: backstop`) | ⚠️ (routed to human verification) | Per the non-inferable-truth rule, a `verification: backstop` truth cannot be marked VERIFIED from presence/wiring alone — requires direct observation. Code shows the base/panel tokens are used consistently (`bg-terminal-bg`/`bg-terminal-panel` throughout, no literal darker color found), but the rendered result needs a human look. |

**Score:** 18/20 truths VERIFIED by code + live spot-check; 2 explicitly route to human verification per the phase's own `human_verify_mode: end-of-phase` design and the non-inferable-truth rule for the `backstop`-tagged truth — neither is a code defect.

### Prohibitions (judgment-tier, non-authoritative LLM-judge review)

| # | Prohibition | Disposition |
|---|-------------|-------------|
| 1 | "UI must never display a portfolio figure it computed itself in place of the authoritative `GET /api/portfolio` value, except the header's live total (D-05)." | Reviewed by code read across `portfolioStore.tsx`, `PositionsRow.tsx`, `WatchlistRow.tsx`, `Header.tsx`. `portfolioStore.tsx` sets state only from fresh `fetchPortfolio()` responses. `PositionsRow.tsx` performs zero arithmetic on `avg_cost`/`unrealized_pnl`/`pct_change`. The one client-side recompute (`useLiveTotalValue` in `Header.tsx`) is exactly the sanctioned exception. **No violation found by this reviewer — flagged for human confirmation per policy, not a hard fail.** |
| 2 | "UI must never present a trade as executed before backend confirmation, or silently discard a rejected trade." | `TradeBar.tsx` only clears the quantity field and calls `refresh()` inside the `try` block after `await postTrade()` resolves; a caught error sets `error` state and changes nothing else. **No violation found by this reviewer — flagged for human confirmation per policy, not a hard fail.** |
| 3 | "UI must never present simulated market data in a way a viewer could mistake for a real, funded brokerage account." | `Header.tsx` carries an unconditional "Simulated" badge. **No violation found by this reviewer — flagged for human confirmation per policy, not a hard fail.** |

These three are judgment-tier (`verification: flagged`) per each plan's frontmatter. Per policy they are non-authoritative here and recorded as `unverified-prohibition — human review recommended`, not silently passed. They are folded into the `human_needed` status below rather than raised as separate blockers, since this reviewer found no contradicting evidence in the shipped code.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/next.config.ts` | Static-export config | ✓ VERIFIED | `output: 'export'`, `images: { unoptimized: true }`, no rewrites/redirects/headers |
| `frontend/app/globals.css` | Tailwind v4 `@theme` dark palette | ✓ VERIFIED | All 5 locked hex values plus border/text/gain/loss/numeric-font tokens |
| `frontend/lib/types.ts` | Wire-format type mirrors | ✓ VERIFIED | All 7 exported types present with correct nullability |
| `frontend/lib/api.ts` | Single fetch access point | ✓ VERIFIED | `fetchPortfolio`, `fetchWatchlist`, `postTrade`; only file with `fetch(` repo-wide |
| `frontend/lib/priceStore.tsx` | Shared EventSource + price map + status | ✓ VERIFIED | `PriceStoreProvider`/`usePriceStore`; only file with `new EventSource` repo-wide |
| `frontend/lib/portfolioStore.tsx` | Portfolio context, `refresh()` sole mutator | ✓ VERIFIED | `PortfolioProvider`/`usePortfolio`; 5s interval with `isRefreshingRef` double-fire guard |
| `frontend/components/trade-bar/TradeBar.tsx` | Ticker/qty inputs, buttons, inline error | ✓ VERIFIED | 115 lines, all required behaviors present |
| `frontend/app/page.tsx` | D-08 grid composition | ✓ VERIFIED | Header, left column (Watchlist + TradeBar), right/main column (PositionsTable) |
| `frontend/components/ui/PriceCell.tsx` | Shared flash cell | ✓ VERIFIED | Used by both `WatchlistRow` and `PositionsRow` — one implementation |
| `frontend/components/watchlist/WatchlistPanel.tsx` / `WatchlistRow.tsx` | Live watchlist | ✓ VERIFIED | Loading/error/empty states, per-row `PriceCell` |
| `frontend/components/positions/PositionsTable.tsx` / `PositionsRow.tsx` | 6-column positions table | ✓ VERIFIED | Loading/error/empty states, D-07 fallback chain |
| `frontend/components/header/Header.tsx` | Live total, cash, dot | ✓ VERIFIED | `useLiveTotalValue`, `ConnectionDot`, Simulated badge |
| `frontend/components/ui/ConnectionDot.tsx` | Status indicator | ✓ VERIFIED | 3 literal color classes + readable label/title per state |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `priceStore.tsx` | `backend/app/routes/stream.py` | `addEventListener('prices', ...)` | WIRED | Confirmed by grep (`prints 1`) and live curl of the SSE endpoint returning `event: prices` |
| `TradeBar.tsx` | `lib/api.ts` | `postTrade()` then `refresh()` | WIRED | Code read confirms sequencing inside `try` |
| `lib/api.ts` | `backend/app/routes/portfolio.py` | fetch `POST/GET /api/portfolio*` | WIRED | Live curl confirmed real responses |
| `WatchlistRow.tsx` | `lib/priceStore.tsx` | `usePriceStore()` | WIRED | Direct import and destructure confirmed |
| `WatchlistPanel.tsx` | `lib/api.ts` | `fetchWatchlist()` on mount | WIRED | Confirmed in mount effect |
| `WatchlistRow.tsx` | `components/ui/PriceCell.tsx` | renders shared cell | WIRED | Import + JSX usage confirmed |
| `PositionsRow.tsx` | `lib/priceStore.tsx` | `usePriceStore()` for live price | WIRED | Confirmed |
| `Header.tsx` | `lib/portfolioStore.tsx` | `usePortfolio()` for cash/positions | WIRED | Confirmed |
| `ConnectionDot.tsx` | `lib/priceStore.tsx` | reads `status` | WIRED | Confirmed via prop threading from `Header.tsx` |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|---------------------|--------|
| Watchlist prices | `prices` map | Live SSE `/api/stream/prices` (curled, real ticking values) | Yes | ✓ FLOWING |
| Watchlist entries | `entries` | `GET /api/watchlist` (curled, real tickers/prices) | Yes | ✓ FLOWING |
| Positions table | `portfolio.positions` | `GET /api/portfolio` → `compute_portfolio_view()` (curled, real non-zero P&L) | Yes | ✓ FLOWING |
| Header live total | `liveTotalValue` | `useMemo` over real `positions`/`cashBalance`/`prices` | Yes | ✓ FLOWING (sanctioned client recompute, D-05) |
| Connection dot | `status` | Real `EventSource` `onopen`/`onerror`/`readyState` transitions | Yes | ✓ FLOWING |

No static/mock/hardcoded-empty data found flowing to any rendered surface.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Backend health | `curl /api/health` | `{"status":"ok"}` | ✓ PASS |
| Real portfolio data | `curl /api/portfolio` | Real cash/position/P&L numbers, not static | ✓ PASS |
| Real watchlist data | `curl /api/watchlist` | Real tickers with live prices | ✓ PASS |
| SSE named event with ticking data | `curl -N /api/stream/prices` (2s) | `event: prices` with changing tick values across the sampled window | ✓ PASS |
| Frontend typecheck | `npm --prefix frontend run typecheck` | exit 0 | ✓ PASS |
| Frontend build (static export) | `npm --prefix frontend run build` | exit 0, `frontend/out/index.html` exists | ✓ PASS |
| Frontend lint | `npm --prefix frontend run lint` | exit 0 | ✓ PASS |
| Backend regression suite | `cd backend && uv run pytest -q` | `139 passed, 2 warnings` | ✓ PASS |
| Single EventSource construction | `grep -rl "new EventSource" frontend/{app,components,lib}` | only `lib/priceStore.tsx` | ✓ PASS |
| Single fetch access point | `grep -rl "fetch(" frontend/{app,components,lib}` | only `lib/api.ts` | ✓ PASS |
| No raw-HTML injection | `grep -rl "dangerouslySetInnerHTML" frontend/{app,components,lib} \| wc -l` | `0` | ✓ PASS |
| No debt markers in phase files | `grep -rnE "TBD\|FIXME\|XXX\|TODO\|HACK\|PLACEHOLDER"` across covered files | no matches | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|--------------|--------|----------|
| UI-01 | 02-02 | Watchlist live prices, flash on change | SATISFIED | `PriceCell`/`WatchlistRow`/`WatchlistPanel`, live curl confirmed |
| UI-06 | 02-03 | Positions table 6 columns, live | SATISFIED | `PositionsTable`/`PositionsRow`, live curl confirmed |
| UI-07 | 02-01 | Trade bar buy/sell, no confirm | SATISFIED | `TradeBar.tsx`, live trade curl (from prior session) confirmed cash movement |
| UI-09 | 02-03 | Header total/cash/connection dot | SATISFIED | `Header.tsx`/`ConnectionDot.tsx` |
| UI-10 | 02-01/02-03 | Dark terminal theme | SATISFIED (visual confirmation pending) | Theme tokens locked and applied consistently; final rendered-result confirmation is the phase's own deferred UAT item |

No orphaned requirements: `.planning/REQUIREMENTS.md`'s traceability table maps exactly UI-01, UI-06, UI-07, UI-09, UI-10 to Phase 2, and all five appear in at least one plan's `requirements:` frontmatter (02-01: UI-07, UI-10; 02-02: UI-01; 02-03: UI-06, UI-09, UI-10).

### Anti-Patterns Found

None blocking. No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` markers anywhere in the phase's covered files. No stub returns, no empty handlers, no hardcoded-empty data reaching a rendered surface.

One pre-existing Info-severity finding from `02-REVIEW.md` was **not** addressed in the fix pass (only CR-01/WR-01/WR-02 were in scope, per `02-REVIEW-FIX.md`'s own frontmatter — `findings_in_scope: 3`):

- **IN-03** (`frontend/components/positions/PositionsRow.tsx:45`): `position.quantity` renders raw (`{position.quantity}`) with no `.toFixed()`, unlike every other numeric cell in the row. A float-accumulation artifact (e.g. `0.30000000000000004`) after repeated fractional buys/sells would render verbatim. This is cosmetic, Info-severity in the original review, does not violate any of this phase's declared `must_haves`, and does not block the phase goal — noted here for visibility, not as a gap.

### Human Verification Required

The following items are explicitly deferred per `workflow.human_verify_mode: end-of-phase` — every plan's own `<human-check>` blocks were intentionally not run mid-execution, and are recorded in each SUMMARY.md's `coverage` section with `human_judgment: true`. They are compiled here as the end-of-phase UAT batch, per this project's configuration. None of these represent a code defect found during this verification; they are runtime/visual confirmations that code inspection and static analysis cannot substitute for.

### 1. Live price stream, dark theme, single connection

**Test:** Load http://localhost:3000 with the backend running.
**Expected:** AAPL (and all watchlist tickers) show prices that change on their own roughly every 0.5s; page background reads as the dark `#0d1117` terminal color; devtools Network shows exactly one `eventsource` request to `/api/stream/prices`; devtools Console has no CORS error or unhandled exception.
**Why human:** Visual rendering and live network-tab inspection.

### 2. Buy/sell happy path and fractional quantities

**Test:** Type `aapl` (lowercase) and quantity `2`, press Buy. Then type `0.5` and Buy again.
**Expected:** Both orders fill instantly with no confirmation dialog; cash drops each time; the quantity field clears after each success.
**Why human:** End-to-end browser interaction.

### 3. Trade rejection wording

**Test:** Press Buy with quantity `999999`. Press Sell with quantity `1` on a ticker you hold none of.
**Expected:** The first shows an inline message starting "Insufficient cash:"; the second starts "Insufficient shares:"; in both cases cash and positions are unchanged.
**Why human:** Exact on-screen wording and confirming no other portfolio value moved.

### 4. Double-click submit-once guard

**Test:** Rapidly double-click Buy.
**Expected:** Both buttons grey out during the request; exactly one trade lands (verify via backend log or by comparing to two deliberate separate clicks).
**Why human:** Timing-sensitive UI behavior only observable live.

### 5. Watchlist: all ten tickers, flash correctness over time

**Test:** Observe the full watchlist for 20+ seconds; optionally stop the backend mid-observation.
**Expected:** All ten default tickers list with live prices; cells flash green/red on real moves and fade rather than snap off; no fixed-cadence pulsing regardless of movement; stopping the backend freezes prices without further flashing; the change column is clearly labelled as since-page-open.
**Why human:** Visual flash timing/color and sustained observation.

### 6. Positions table live states

**Test:** With zero positions, observe the empty state. Buy 2 AAPL. Watch the row for ~5+ seconds. Sell the full position.
**Expected:** Explicit "no positions" message (not a bare table) when empty; a new row appears immediately after a buy with live current price and P&L; unrealized P&L/Chg% visibly update within ~5s of a price move; the row disappears and the empty state returns after a full sell.
**Why human:** Live state transitions and refresh-interval timing.

### 7. Header live total and connection dot lifecycle

**Test:** Observe the header; buy 1 share of any ticker; stop the backend process; restart it.
**Expected:** Total value changes on essentially every tick; a visible "Simulated" marker is present; the dot is green while connected, turns yellow within ~2s of stopping the backend then red a few seconds later (prices freeze, no stale flashing), and returns to green automatically on restart with no page reload.
**Why human:** Requires actually starting/stopping the backend and watching the real-time state machine; this item also covers the plan's `verification: backstop` truth, which per the non-inferable-truth rule cannot be marked VERIFIED from code presence alone.

### 8. Full-phase visual/UX walkthrough

**Test:** With the app running end-to-end, walk through all five phase success criteria together (watch prices, buy/sell, positions table, header, overall visual theme).
**Expected:** Everything from items 1-7 holds simultaneously; additionally, the page reads as a dense trading terminal — no pure-black region, no horizontal scrollbar at desktop width, numbers right-aligned and not jittering as they tick, yellow/blue/purple accents present but used sparingly.
**Why human:** This is the phase's own explicitly deferred acceptance walkthrough (`02-03-PLAN.md` Task 3), combining visual design judgment with live interaction across every panel built in this phase.

*(The three judgment-tier prohibitions listed above are also implicitly covered by items 2, 3, and 7-8 of this UAT batch — no separate item needed.)*

### Gaps Summary

No gaps. Every `must_haves.truth` across all three plans (20 total, merged with the roadmap's 3 stated success criteria) is either code-verified with live backend spot-check evidence, or is one of the two items that legitimately require human observation (the connection-dot stop/restart lifecycle, and the `verification: backstop` visual-density truth) — both of which were already correctly identified by the plans themselves as `<human-check>` items and deferred per this project's `human_verify_mode: end-of-phase` configuration, not overlooked. All automated checks (`typecheck`, `build`, `lint`, backend `pytest` at 139/139, all wiring greps) pass clean. The code-review cycle (`02-REVIEW.md` → `02-REVIEW-FIX.md`) found one Critical and two Warning issues, all three fixed and independently re-verified here by direct code read (CR-01's dual `detail`-shape handling, WR-01's client-side validation guards, WR-02's distinct watchlist error state). One Info-severity cosmetic finding (IN-03, unformatted `quantity`) was left unaddressed by design (out of the fix pass's declared scope) and does not block the phase goal.

Status is `human_needed` rather than `passed` solely because the human-verification section is non-empty, per the decision tree in Step 9 — this reflects the phase's correct, deliberate deferral strategy, not a functional gap.

---

_Verified: 2026-09-17_
_Verifier: Claude (gsd-verifier)_
