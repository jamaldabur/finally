---
status: testing
phase: 04-portfolio-visualization
source: [04-VERIFICATION.md]
started: 2026-09-22T00:00:00Z
updated: 2026-09-22T00:00:00Z
---

## Current Test

number: 1
name: Sparklines fill progressively and match the row's change-% colour
expected: |
  Each row's sparkline starts as a flat muted baseline, then draws progressively with a ringed end dot, coloured to match the row's change-% text
awaiting: user response

## Tests

### 1. Sparklines fill progressively and match the row's change-% colour
expected: Open the app with the backend running and watch the watchlist for ~30s. Each row's sparkline starts as a flat muted baseline, then draws progressively with a ringed end dot, coloured to match the row's change-% text.
result: [pending]

### 2. Clicking or keyboard-activating a row shows the main chart
expected: Click a watchlist row, then Tab to another row and press Enter/Space. Main chart panel heading becomes the ticker; chart shows axes, hover crosshair and tooltip, end dot and end label; selected row tint shows; keyboard activation works.
result: [pending]

### 3. Heatmap tiles render, sized by weight and coloured with the ±10% cap (HIGHEST RISK)
expected: Buy positions of differing sizes and P&L (include one beyond ±10%). Tiles are sized by market value; fill goes pale to vivid with a cap at 10%; labels drop percentage first, then ticker, on small tiles; hover tooltip shows weight and change. RISK: PortfolioHeatmap's Tile assumes Recharts 3.10.1 Treemap passes ticker and pct_change through as props to `content`; if it does not, every tile renders an empty <g/> and the heatmap is blank.
result: [pending]

### 4. P&L chart draws real snapshots after a trade
expected: Place a trade and watch the Portfolio Value panel. Chart shows >=2 snapshots with axes, tooltip and end label. The post-trade point appears only at the next 30s poll (known: review WR-01).
result: [pending]

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0
blocked: 0

## Gaps
