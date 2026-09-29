---
status: complete
phase: 02-core-trading-ui
source: [02-VERIFICATION.md]
started: 2026-09-17T17:35:00Z
updated: 2026-09-17T17:54:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Live price stream, dark theme, single connection
expected: AAPL (and all watchlist tickers) show prices that change on their own roughly every 0.5s; page background reads as the dark #0d1117 terminal color; devtools Network shows exactly one eventsource request to /api/stream/prices; devtools Console has no CORS error or unhandled exception.
result: pass

### 2. Buy/sell happy path and fractional quantities
expected: Type "aapl" (lowercase) and quantity 2, press Buy — order fills instantly with no confirmation dialog, cash drops, quantity field clears. Type 0.5 and Buy again — fractional order accepted.
result: pass

### 3. Trade rejection wording
expected: Buy quantity 999999 — inline message starts "Insufficient cash:" and cash does not move. Sell quantity 1 on a ticker held none of — message starts "Insufficient shares:" and nothing else changes.
result: pass

### 4. Double-click submit-once guard
expected: Rapidly double-clicking Buy greys out both buttons during the request and only one trade lands (compare against backend log or two deliberate separate clicks).
result: pass

### 5. Watchlist: all ten tickers, flash correctness over time
expected: All ten default tickers (AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META, JPM, V, NFLX) listed with live prices; cells flash green on uptick / red on downtick and fade out (not snap off); watching one row for 20+ seconds shows flashes only on real moves, not a fixed heartbeat pulse; change column labelled as since-page-open; devtools Network still shows exactly one eventsource request.
result: pass

### 6. Positions table live states
expected: With no positions, an explicit "no positions" message shows (not a bare table). Buy 2 AAPL — a row appears with quantity 2, an average cost near the fill price, a live current price, and a P&L figure; current price ticks/flashes; unrealized P&L and Chg% update within ~5s of a price move. Selling the full position removes the row and restores the empty state.
result: pass

### 7. Header live total and connection dot lifecycle
expected: Header shows a total value that changes on essentially every price tick, a cash balance, and a green connection dot; a visible "Simulated" marker is present. Stopping the backend turns the dot yellow within ~2s then red a few seconds later, with prices freezing (not stale-flashing). Restarting the backend returns the dot to green automatically with no page reload, and prices resume. Buying 1 share moves the header total and cash immediately.
result: pass

### 8. Full-phase visual/UX walkthrough
expected: All five phase success criteria hold together in one live session — watchlist flashes correctly (UI-01); buy/sell fill instantly with no confirmation dialog and cash/positions update (UI-07); positions table shows all six columns live (UI-06); header shows live total/cash/connection dot reflecting real SSE state (UI-09); the page reads as a dark, dense trading terminal — background ~#0d1117 with #1a1a2e panels, muted gray borders, no pure-black region, no horizontal scrollbar at desktop width, numbers right-aligned and not jittering, yellow/blue/purple accents present but sparing (UI-10).
result: pass

## Summary

total: 8
passed: 8
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps
