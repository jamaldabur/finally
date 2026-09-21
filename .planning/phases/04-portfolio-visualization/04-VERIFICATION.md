---
phase: 04-portfolio-visualization
verified: 2026-09-22T00:00:00Z
status: human_needed
score: 4/4 roadmap success criteria structurally verified (rendered output unverified)
behavior_unverified: 0
gaps: []
human_verification:
  - test: "Open the app with the backend running; watch the watchlist for ~30s"
    expected: "Each row's sparkline starts as a flat muted baseline, then draws progressively with a ringed end dot, coloured to match the row's change-% text"
    why_human: "Rendered pixels; no frontend test framework exists (Phase 6 owns TEST-04)"
  - test: "Click a watchlist row, then press Tab/Enter/Space on another row"
    expected: "Main chart panel heading becomes the ticker; the chart shows axes, hover crosshair and tooltip, end dot and end label; selected row tint shows; keyboard activation works"
    why_human: "Interaction and visual layout"
  - test: "Buy positions of differing sizes and P&L (including one beyond +/-10%)"
    expected: "Heatmap tiles are sized by market value; fill goes pale to vivid with a cap at 10%; labels drop percentage first, then ticker, on small tiles; hover tooltip shows weight and change"
    why_human: "Recharts 3.10.1 Treemap custom `content` receives flattened data fields (ticker, pct_change) — this is assumed by Tile and cannot be confirmed without rendering. If the props are not flattened, every tile renders an empty <g/> and the heatmap is blank"
  - test: "Place a trade and watch the Portfolio Value panel"
    expected: "Chart shows >=2 snapshots with axes, tooltip and end label. Expect the post-trade point to appear only at the next 30s poll (see WR-01)"
    why_human: "Needs live snapshots and rendering"
---

# Phase 4: Portfolio Visualization Verification Report

**Phase Goal:** A user can visually understand portfolio composition, risk concentration, and performance at a glance
**Status:** human_needed (no structural gaps; nothing viewed in a browser)
**Re-verification:** No

## Goal Achievement

| # | Roadmap success criterion | Status | Evidence |
|---|---|---|---|
| 1 | Sparkline per ticker, accumulated from SSE since page load | VERIFIED (structural) | `lib/priceStore.tsx` appends to `priceHistory` inside the single `prices` listener; skips equal-price ticks, caps at 500, arrival order kept, no back-fill. `Sparkline.tsx` handles 0/1/2+ points and takes trend colour from `trendDirection(firstPrices, latest)`, the same source as the row's change-%. Mounted in `WatchlistRow.tsx`. |
| 2 | Clicking a ticker shows a larger chart in the main area | VERIFIED (structural) | `WatchlistRow` is `role=button`, `tabIndex=0`, with click/Enter/Space calling `setSelectedTicker`. `MainChart.tsx` reads `chartSelection` and the same `priceHistory`. It has empty, waiting (<2 points) and full states, with axes, tooltip, end dot and end label. Mounted in `app/page.tsx`. |
| 3 | Heatmap sized by weight, coloured by P&L%, cap +/-10% | VERIFIED (structural), render unconfirmed | `PortfolioHeatmap.tsx` uses Recharts `Treemap` with `dataKey="market_value"` and server `pct_change`. `chartTheme.divergingFill` uses `min(abs(pct),10)/10` and `mixColor` clamps t. Empty, loading and error states present; legend shows -10%/0%/+10%; SVG-only tiles. See human item 3 on Treemap prop flattening. |
| 4 | P&L line chart from portfolio_snapshots | VERIFIED (structural) | `fetchPortfolioHistory()` in `lib/api.ts` hits `/api/portfolio/history`. `portfolioHistoryStore` polls every 30s with the loading flag lowered once and no sort or resample. `PnlHistoryChart.tsx` shows the <2 copy, a loading state, and an error state with `role="alert"`, and otherwise the chart with a trend colour. The provider is mounted in `layout.tsx`. |

**Score:** 4/4 structurally verified; 0 behaviour-unverified truths flagged, but all rendered-appearance claims are routed to human verification.

### Key Links

| From | To | Status |
|---|---|---|
| `priceStore` `prices` handler | `Sparkline` / `MainChart` (`priceHistory`) | WIRED |
| `WatchlistRow` click | `chartSelection` -> `MainChart` | WIRED |
| `usePortfolio()` | `PortfolioHeatmap` | WIRED |
| `/api/portfolio/history` -> `api.ts` -> `portfolioHistoryStore` -> `PnlHistoryChart` | | WIRED |
| Providers in `layout.tsx`; all charts mounted in `page.tsx` | | WIRED |

Single EventSource: only `priceStore.tsx` constructs one (other grep hits are comments). No `dangerouslySetInnerHTML` under `components`. No TODO/FIXME/XXX/TBD in charts, lib or app.

### Data-Flow

All four surfaces read from real sources (the SSE-fed store, `GET /api/portfolio`, `GET /api/portfolio/history`). No hardcoded or static data was found. FLOWING.

### Requirements Coverage

| ID | Plan | Status |
|---|---|---|
| UI-02 | 04-01 | SATISFIED (structural) |
| UI-03 | 04-02 | SATISFIED (structural) |
| UI-04 | 04-03 | SATISFIED (structural; see human item 3) |
| UI-05 | 04-04 | SATISFIED (structural) |

All four IDs are present in REQUIREMENTS.md (lines 46-49, traceability lines 129-132), and none is orphaned.

### Anti-Patterns / Review Warnings (non-blocking, advisory)

Code review 04-REVIEW.md reports 0 critical and 5 warnings. I confirmed by reading the code that these are real:

- **WR-01:** The P&L chart is not refreshed after a trade; it updates only on the 30s poll. This is a UX lag, not a criterion failure, because the data still comes from `portfolio_snapshots`.
- **WR-02:** The x-axes are category axes, so irregular timestamps are drawn evenly spaced. Both `PnlHistoryChart` and `MainChart` are affected.
- **WR-03:** The selected ticker is not cleared when it is removed from the watchlist.
- **WR-04:** `JSON.parse` in the SSE handler is unguarded.
- **WR-05:** The history store has a possible race and set-state-after-unmount.

None of these blocks the four success criteria. They are recommended for a follow-up fix. The WR-02 issue makes "over time" a partly distorted time axis.

### Behavioural Spot-Checks

Skipped: no frontend test framework exists. The orchestrator reported that typecheck, lint, `next build` and backend pytest (214 passed) all pass.

## Gaps Summary

There are no structural gaps. The phase goal is delivered in code, but no rendering has been observed. The four human items above must be confirmed in a browser before the phase is signed off, with particular attention to the Recharts 3 Treemap `content` props.

Note: `covered_files` and `covered_digest` (via `verification.fingerprint`) were not generated in this run.

_Verified: 2026-09-22_
_Verifier: Claude (gsd-verifier)_
