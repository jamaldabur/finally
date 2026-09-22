---
status: testing
phase: 04-portfolio-visualization
source: [04-VERIFICATION.md]
started: 2026-09-22T14:30:00Z
updated: 2026-09-22T14:30:00Z
---

## Current Test

number: 1
name: Heatmap tile label visibility across real browser widths (G-04-3 fix confirmation)
expected: |
  With the app running and >=3 positions of differing weight held (include one beyond +/-10%),
  resize the browser to ~1280px, ~1440px and ~1920px wide. Every tile with genuine room shows
  both ticker and percentage (the previously-blank NVDA-style narrow tile now shows its %);
  labels degrade percentage-first then ticker as tiles narrow; no percentage ever appears
  without its ticker above it; no label overlaps a neighbour or is cut off.
awaiting: user response

## Tests

### 1. Heatmap tile label visibility across real browser widths (G-04-3 fix confirmation)
expected: With the app running and >=3 positions of differing weight held (include one beyond +/-10%), resize the browser to ~1280px, ~1440px and ~1920px wide. Every tile with genuine room shows both ticker and percentage (the previously-blank NVDA-style narrow tile now shows its %); labels degrade percentage-first then ticker as tiles narrow; no percentage ever appears without its ticker above it; no label overlaps a neighbour or is cut off.
result: [pending]

### 2. Portfolio Value chart readability against real accumulated history (G-04-4 fix confirmation)
expected: With the backend running against the real db/finally.db (accumulated snapshot history), open the app and look at the Portfolio Value panel. The line reads as a line (individual moves distinguishable, not a solid ink band), the X axis shows a handful of non-overlapping clock labels spanning a plausible recent window, the line's weight visually matches MainChart's, and the panel never flashes back to loading copy during a 30s+ observation.
result: [pending]

### 3. Chart focus ring appearance and keyboard tooltip navigation (04-05 Task 2 / D9 confirmation)
expected: Tab to MainChart and to the Portfolio Value panel and confirm a visible on-theme focus ring appears only via keyboard (never on mouse click), arrow keys move each chart's tooltip while focused, and Tab never lands on the Portfolio Heatmap. A 2px light ring appears just outside each of the two standalone charts on :focus-visible only; ArrowRight/ArrowLeft moves the hover tooltip; the heatmap is never a tab stop.
result: [pending]

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps
