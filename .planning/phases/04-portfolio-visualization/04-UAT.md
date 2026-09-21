---
status: complete
phase: 04-portfolio-visualization
source: [04-VERIFICATION.md]
started: 2026-09-22T00:00:00Z
updated: 2026-09-22T00:50:00Z
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
  artifacts: []
  missing: []

- gap_id: G-04-4
  truth: "Portfolio Value chart is clean and readable at a glance"
  status: failed
  reason: "User reported: the Portfolio Value graph is a little bit busy (maybe the line is bold, idk, fix it)"
  severity: cosmetic
  test: 4
  artifacts: []
  missing: []

- gap_id: G-04-2a
  truth: "Tab/Enter/Space on a watchlist row selects it and charts that ticker in the main chart"
  status: failed
  reason: "User reported: keyboard activation doesn't work"
  severity: major
  test: 2
  artifacts: []
  missing: []

- gap_id: G-04-2b
  truth: "Watchlist sparklines keep drawing correctly (Test 1 passed earlier; reported broken while testing row selection)"
  status: failed
  reason: "User reported: the little graph of stocks in watchlist is broken"
  severity: major
  test: 2
  artifacts: []
  missing: []
