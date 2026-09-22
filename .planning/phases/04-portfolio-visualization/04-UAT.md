---
status: diagnosed
phase: 04-portfolio-visualization
source: [04-VERIFICATION.md]
started: 2026-09-22T00:00:00Z
updated: 2026-09-22T02:20:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Sparklines fill progressively and match the row's change-% colour
expected: Open the app with the backend running and watch the watchlist for ~30s. Each row's sparkline starts as a flat muted baseline, then draws progressively with a ringed end dot, coloured to match the row's change-% text.
result: pass

### 2. Clicking or keyboard-activating a row shows the main chart
expected: Click a watchlist row, then Tab to another row and press Enter/Space. Main chart panel heading becomes the ticker; chart shows axes, hover crosshair and tooltip, end dot and end label; selected row tint shows; keyboard activation works.
result: issue
reported: "keyboard activation doesn't work, the little graph of stocks in watchlist is broken"
severity: major
note: Two distinct problems in one report. The sparkline complaint may be a regression of Test 1 (which the user passed earlier) or triggered by the click/selection interaction - unconfirmed until diagnosed.

### 3. Heatmap tiles render, sized by weight and coloured with the ±10% cap (HIGHEST RISK)
expected: Buy positions of differing sizes and P&L (include one beyond ±10%). Tiles are sized by market value; fill goes pale to vivid with a cap at 10%; labels drop percentage first, then ticker, on small tiles; hover tooltip shows weight and change. RISK: PortfolioHeatmap's Tile assumes Recharts 3.10.1 Treemap passes ticker and pct_change through as props to `content`; if it does not, every tile renders an empty <g/> and the heatmap is blank.
result: issue
reported: "I don't see % on all stocks in heatmap (I don't see it on NVDA)"
severity: major
note: Tiles DO render (Recharts prop-flattening risk did not materialise). Likely the by-design small-tile label drop (percentage dropped first below the 64x42 threshold) but that is unconfirmed until diagnosed.

### 4. P&L chart draws real snapshots after a trade
expected: Place a trade and watch the Portfolio Value panel. Chart shows >=2 snapshots with axes, tooltip and end label. The post-trade point appears only at the next 30s poll (known: review WR-01).
result: issue
reported: "the Portfolio Value graph is a little bit busy (maybe the line is bold, idk, fix it)"
severity: cosmetic

## Summary

total: 4
passed: 1
issues: 3
pending: 0
skipped: 0
blocked: 0

## Gaps

- gap_id: G-04-3
  truth: "Heatmap tiles show their P&L % (labels drop percentage first, then ticker, only on genuinely small tiles)"
  status: failed
  reason: "User reported: I don't see % on all stocks in heatmap (I don't see it on NVDA)"
  severity: major
  test: 3
  root_cause: "PortfolioHeatmap.tsx gates the % label on fixed PCT_MIN_WIDTH=64px / PCT_MIN_HEIGHT=42px rectangle thresholds that exceed the label's real rendered width (~42-54px at 10px/600 weight, measured via getComputedTextLength). At narrower viewports the panel's fixed h-60 height forces squarify into tall, narrow columns for low-weight holdings (e.g. a 60x158px NVDA tile at 27.5% weight), which fall in the dead band between fits-the-text and clears-the-gate. Implementation bug, not spec'd behaviour: 04-UI-SPEC.md conditions the drop on the label genuinely not fitting."
  artifacts:
    - path: "frontend/components/charts/PortfolioHeatmap.tsx"
      issue: "Fixed threshold constants (PCT_MIN_WIDTH=64, PCT_MIN_HEIGHT=42, TICKER_MIN_WIDTH=52) gate the % and ticker labels by rectangle size instead of measuring/estimating the text actually being drawn"
  missing:
    - "Gate the % (and ticker) label on an estimated or measured text-fit test (e.g. ~5.9px/char at this font+size vs width - 2*TILE_INSET) instead of a fixed-width/height rectangle threshold"
    - "Lower PCT_MIN_HEIGHT nearer the real single-line need (~36px, not 42px)"
  debug_session: ".planning/debug/heatmap-tile-pct-label-missing.md"

- gap_id: G-04-4
  truth: "Portfolio Value chart is clean and readable at a glance"
  status: failed
  reason: "User reported: the Portfolio Value graph is a little bit busy (maybe the line is bold, idk, fix it)"
  severity: cosmetic
  test: 4
  root_cause: "Series over-density, not stroke width. No layer (SQL query, route, store, component) windows or caps portfolio_snapshots, so all ~2094 accumulated rows (5 days, unbounded and growing) are drawn into a ~126px-tall plot area - 5-11 data points per horizontal pixel, sub-pixel x-step. The near-vertical adjacent segments of the 2px stroke merge into an ink band 7.5-10.8px tall, which reads as bold/busy even though CHART_STROKE_WIDTH=2 is the spec'd value (proven correct by MainChart.tsx, which shares every style constant but caps at PRICE_HISTORY_LIMIT=500 and draws cleanly). Secondary: XAxis has no type=\"number\"/scale=\"time\", so Recharts defaults to a categorical axis that spaces all 2094 points evenly by index, collapsing real time gaps and squeezing the last hour (what UAT asks the user to look at) into ~0.3% of the width. Ruled out: CartesianGrid (not rendered), intermediate dot markers (none), tooltip/cursor, animation (already off), and the sibling accessibilityLayer/focus-outline finding (no accessibilityLayer/tabIndex usage in this file)."
  artifacts:
    - path: "backend/app/db/portfolio_snapshots.py"
      issue: "_get_snapshots_sync has no LIMIT - the snapshot table is never pruned per PLAN.md and grows unbounded"
    - path: "backend/app/routes/portfolio.py"
      issue: "get_portfolio_history maps every row 1:1 with no windowing parameter"
    - path: "frontend/lib/portfolioHistoryStore.tsx"
      issue: "Passes all snapshots straight through by design (no thinning), unlike priceStore.tsx's PRICE_HISTORY_LIMIT=500 precedent"
    - path: "frontend/components/charts/PnlHistoryChart.tsx"
      issue: "Renders every row with a categorical (not time-scaled numeric) XAxis"
  missing:
    - "Bound the rendered/returned point count (e.g. a windowed/limited query or downsampling to ~1 point per 2-3px), mirroring the existing PRICE_HISTORY_LIMIT=500 precedent"
    - "Switch XAxis to type=\"number\" with a time dataKey and scale=\"time\" so real time gaps are honest"
  debug_session: ".planning/debug/portfolio-value-chart-busy.md"

- gap_id: G-04-2a
  truth: "Tab/Enter/Space on a watchlist row selects it and charts that ticker in the main chart"
  status: failed
  reason: "User reported: keyboard activation doesn't work"
  severity: major
  test: 2
  root_cause: "Recharts 3.x makes every cartesian chart a focusable widget by default (accessibilityLayer defaults true, emitting <svg tabindex=\"0\" role=\"application\">). Sparkline.tsx never opts out, and its chart is a DOM descendant of the focusable WatchlistRow, so every row owns two tab stops: the row, then its own sparkline. After clicking a row, one Tab lands on that same row's sparkline (not the next row); Enter/Space there re-selects the already-selected ticker with no visible change. Same class of defect (own stray tabindex=0 surface) exists in MainChart.tsx, PnlHistoryChart.tsx and PortfolioHeatmap.tsx. Confirmed by live tab-stop enumeration (headless Chromium): stops alternate row/sparkline/row/sparkline for all 10 watchlist rows."
  artifacts:
    - path: "frontend/components/charts/Sparkline.tsx"
      issue: "LineChart renders without opting out of Recharts' default accessibilityLayer, making it a second focusable element nested inside the already-interactive WatchlistRow"
    - path: "frontend/components/watchlist/WatchlistRow.tsx"
      issue: "role=button/tabIndex=0 row whose own click/keydown handler is correct; the descendant sparkline steals the next Tab (no change needed here beyond verifying the fix)"
    - path: "frontend/components/charts/MainChart.tsx"
      issue: "Same default accessibilityLayer applies; standalone panel so less harmful but same class of defect"
    - path: "frontend/components/charts/PnlHistoryChart.tsx"
      issue: "Same default accessibilityLayer applies (also implicated in G-04-4's ranked candidates as visually neutral there)"
    - path: "frontend/components/charts/PortfolioHeatmap.tsx"
      issue: "Same default accessibilityLayer applies"
  missing:
    - "Pass accessibilityLayer={false} (or explicit tabIndex={-1}) to the LineChart in Sparkline.tsx so the watchlist row is the only tab stop"
    - "Decide deliberately whether MainChart/PnlHistoryChart/PortfolioHeatmap keep a focusable chart surface; if so, give it a visible focus style that works on the dark theme"
  debug_session: ".planning/debug/keyboard-activation-watchlist-row.md"

- gap_id: G-04-2b
  truth: "Watchlist sparklines keep drawing correctly (Test 1 passed earlier; reported broken while testing row selection)"
  status: failed
  reason: "User reported: the little graph of stocks in watchlist is broken"
  severity: major
  test: 2
  root_cause: "Same root cause as G-04-2a, not an independent rendering defect. What the user saw as 'broken' is the sparkline's own default browser focus ring: when Tab lands on the sparkline's <svg role=\"application\"> (see G-04-2a), it renders a heavy white outline:auto ring tightly around the 114x20 chart, which reads as an empty white-outlined box. The underlying draw is healthy (confirmed via live DOM: 12 recharts-surface elements, a correct 13-point path in the correct 114x20 box) - it is only ever visibly wrong while that element holds keyboard focus. Fixing G-04-2a (removing the sparkline as a tab stop) closes this gap by the same mechanism; recommend one fix and one verification for both."
  artifacts:
    - path: "frontend/components/charts/Sparkline.tsx"
      issue: "Same as G-04-2a - the focusable chart surface both steals the tab stop and grows a default focus outline around itself while focused"
  missing:
    - "Same fix as G-04-2a (accessibilityLayer={false} / tabIndex={-1}) - verify the outline disappears once the sparkline is no longer focusable"
  debug_session: ".planning/debug/keyboard-activation-watchlist-row.md"

- gap_id: G-04-2b
  truth: "Watchlist sparklines keep drawing correctly (Test 1 passed earlier; reported broken while testing row selection)"
  status: failed
  reason: "User reported: the little graph of stocks in watchlist is broken"
  severity: major
  test: 2
  artifacts: []
  missing: []
