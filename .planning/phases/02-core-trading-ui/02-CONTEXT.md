# Phase 2: Core Trading UI - Context

**Gathered:** 2026-09-17
**Status:** Ready for planning

<domain>
## Phase Boundary

A user can watch live prices, place a market buy/sell order, and see cash/positions update in the browser — the core agentic trading loop (watch → trade → see it reflected) works end-to-end in a minimal Next.js frontend. In scope: watchlist panel (live prices, flash animation), trade bar, positions table, header (total value, cash, connection status dot), dark trading-terminal theme.

Out of scope for this phase (later phases): sparklines and the detailed per-ticker chart, the portfolio heatmap, the P&L history chart (all Phase 4); the AI chat panel (Phase 3); Docker packaging (Phase 5); automated test suites (Phase 6).

</domain>

<decisions>
## Implementation Decisions

The user deferred all gray-area choices to Claude ("You choose everything, I trust you") rather than working through them individually. The decisions below are Claude's calls, made to be consistent with `planning/PLAN.md` and the existing backend's conventions — not re-litigated, and downstream agents should treat them as locked unless they hit a concrete blocker.

### Trade bar UX
- **D-01:** Ticker field is a plain text input (uppercase-normalized client-side before submit), not a dropdown restricted to the watchlist — the backend's `execute_trade()` accepts any ticker `is_valid_ticker()` recognizes, not just watched ones, and PLAN.md §10 describes it as "a simple input area: ticker field, quantity field." — **Reversibility:** reversible — swapping to a dropdown later is a local component change with no API impact.
- **D-02:** Quantity field accepts decimals (`type="number" step="any"`, or a text input with numeric validation), since `positions.quantity` is `REAL` and the backend explicitly supports fractional shares (PLAN.md §7).
- **D-03:** No confirmation dialog on submit (per PLAN.md §2/§9 — zero-friction, instant fill). On response: success clears/resets the quantity field and the positions table + header refresh (see D-04); on error (400 with `detail` from `TradeRequest`/`execute_trade` validation, e.g. insufficient cash/shares), show the message inline near the trade bar, not a global toast — keeps it visible next to the action that caused it, no new UI dependency needed.

### Live data & refresh flow
- **D-04:** After a trade executes, the frontend refetches `GET /api/portfolio` immediately (rather than optimistic local updates) — `compute_portfolio_view()` is the single source of truth for cash/positions/P&L math (rounding, avg cost, etc.), so re-deriving it client-side would duplicate backend logic and risk drifting from it. — **Reversibility:** reversible — optimistic updates can be layered on top later without changing the API contract.
- **D-05:** A single shared SSE connection (one `EventSource` for `/api/stream/prices`, opened once — e.g. via a React context/provider or a top-level hook) feeds all price-dependent UI: watchlist rows, and the header's live total value (recomputed client-side from cached position quantities/avg cost + latest SSE prices, so it updates every tick without polling `/api/portfolio` on each tick).
- **D-06:** Connection status dot: green while the `EventSource` is open and receiving events, yellow after an `onerror` fires (browser is auto-retrying — native `EventSource` reconnect behavior per PLAN.md §6), red if no reconnection succeeds after a short grace window. Exact thresholds are left to the executor/planner to tune.
- **D-07:** Positions table rows resolve `current_price` from the same shared SSE price store the watchlist uses (falling back to `GET /api/portfolio`'s `current_price` field when the ticker's price hasn't streamed yet, e.g. right after page load) rather than issuing separate polling requests.

### Layout & panel arrangement
- **D-08:** Single page, header pinned at top (portfolio total value, cash balance, connection dot — full width). Below the header: a left column with the watchlist panel stacked above the trade bar, and a right/main column with the positions table. This leaves an obvious main-content slot for the Phase 4 chart/heatmap and an obvious side slot for the Phase 3 chat panel, so those phases extend the layout instead of reworking it.
- **D-09:** Dark theme per PLAN.md §2: background ~`#0d1117`/`#1a1a2e`, accent yellow `#ecad0a`, blue `#209dd7`, purple `#753991` for submit/buy-type actions. Price flash: brief green/red background on the changed price cell, fading via CSS transition over ~500ms, triggered only when `price !== previous_price` from a given SSE tick (never on an unchanged heartbeat resend — PLAN.md §6).

### Frontend scaffolding
- **D-10:** Next.js App Router with `output: 'export'` (static export), TypeScript, Tailwind CSS — all explicitly named in PLAN.md §3/§10/§11.
- **D-11:** Frontend naming/style is idiomatic TypeScript/React (camelCase functions/variables, PascalCase components), not a mirror of the backend's Python snake_case — PLAN.md §4 treats `frontend/` and `backend/` as independent, loosely-coupled projects ("frontend knows nothing about Python").
- **D-12:** Components organized by feature (`components/watchlist/`, `components/trade-bar/`, `components/positions/`, `components/header/`), with shared primitives (buttons, status dot, etc.) under `components/ui/`. Exact file layout beyond this grouping is left to the planner/researcher.

### Claude's Discretion
Per the user's "you choose everything" response, essentially all of Phase 2's implementation gray areas (trade bar UX, live-data refresh strategy, layout arrangement, and frontend scaffolding conventions) were left to Claude's judgment rather than individually discussed. The decisions above are the record of those calls; anything not explicitly pinned down here (e.g. exact Tailwind config structure, precise flash-animation timing curve, specific component prop shapes) remains open for the researcher/planner to decide.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Product spec
- `planning/PLAN.md` §2 — Visual design (colors, price flash, connection dot, layout density)
- `planning/PLAN.md` §6 — Market data / SSE streaming contract (event shape, `previous_price` carry-forward semantics, heartbeat vs. real change)
- `planning/PLAN.md` §8 — API endpoint table (`/api/portfolio`, `/api/portfolio/trade`, `/api/watchlist`)
- `planning/PLAN.md` §10 — Frontend design (required panels, `EventSource` usage, charting library note, Tailwind)

### Backend contracts this phase consumes (already implemented in Phase 1)
- `backend/app/routes/portfolio.py` — `GET /api/portfolio` (`PortfolioResponse`: `cash_balance`, `positions[]` with `ticker/quantity/avg_cost/current_price/market_value/unrealized_pnl/pct_change`, `positions_value`, `total_value`, `total_unrealized_pnl`), `POST /api/portfolio/trade` (`TradeRequest{ticker, side, quantity}` → `TradeResponse{trade, cash_balance, position}`, 400 on validation error with `detail` message)
- `backend/app/routes/watchlist.py` — `GET /api/watchlist` (`WatchlistResponse{watchlist: [{ticker, price, previous_price, direction, timestamp}]}`, price fields nullable if not yet streamed)
- `backend/app/routes/stream.py` — `GET /api/stream/prices`: SSE with a **named event `prices`** (not the default `message` event — the frontend's `EventSource` must use `addEventListener('prices', ...)`), payload `{"ticks": [{ticker, price, previous_price, timestamp, direction}, ...]}` covering all tracked tickers per tick, broadcast every 0.5s

### Codebase maps
- `.planning/codebase/STACK.md` — confirms frontend stack is still fully unbuilt (Next.js/Tailwind/charting library are planned-only, no existing code to reconcile with)
- `.planning/codebase/STRUCTURE.md` — `frontend/` directory doesn't exist yet; will be a fresh self-contained Next.js project per PLAN.md §4 boundaries

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None on the frontend — `frontend/` does not exist yet, this is a greenfield build.
- Backend is complete for this phase's needs: `GET /api/portfolio`, `POST /api/portfolio/trade`, `GET /api/watchlist`, `GET /api/stream/prices` are all implemented and tested (Phase 1, 73+ backend tests passing).

### Established Patterns
- Backend consistently normalizes tickers to uppercase before validation/persistence (`_normalize()` in `watchlist.py`) — frontend should also uppercase ticker input before submit to avoid round-tripping a case mismatch through a 400.
- SSE `previous_price` only changes when the underlying price actually changes (heartbeats resend the last known price unchanged) — frontend flash-trigger logic must compare `price !== previous_price` from the tick, not "did I receive an event."

### Integration Points
- All frontend API calls are same-origin `/api/*` — no CORS setup needed (PLAN.md §3/§10).
- `POST /api/portfolio/trade` is the only mutation this phase needs; its 400 response `detail` string is the exact text to surface as the trade-bar error (e.g. "insufficient cash", "insufficient shares" — exact wording lives in `backend/app/portfolio/service.py` if the planner wants to confirm copy).

</code_context>

<specifics>
## Specific Ideas

No specific requirements beyond what's captured in Implementation Decisions above — the user explicitly deferred all Phase 2 gray areas to Claude's judgment.

</specifics>

<deferred>
## Deferred Ideas

None — no scope-creep suggestions came up during this discussion; the user deferred implementation choices rather than proposing new capabilities.

</deferred>

---

*Phase: 02-core-trading-ui*
*Context gathered: 2026-09-17*
