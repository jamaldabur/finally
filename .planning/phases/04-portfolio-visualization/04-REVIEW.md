---
phase: 04-portfolio-visualization
reviewed: 2026-09-22T00:00:00Z
depth: standard
files_reviewed: 14
files_reviewed_list:
  - frontend/app/layout.tsx
  - frontend/app/page.tsx
  - frontend/components/charts/chartTheme.ts
  - frontend/components/charts/MainChart.tsx
  - frontend/components/charts/PnlHistoryChart.tsx
  - frontend/components/charts/PortfolioHeatmap.tsx
  - frontend/components/charts/Sparkline.tsx
  - frontend/components/watchlist/WatchlistRow.tsx
  - frontend/lib/api.ts
  - frontend/lib/chartSelection.tsx
  - frontend/lib/portfolioHistoryStore.tsx
  - frontend/lib/priceStore.tsx
  - frontend/lib/types.ts
  - frontend/package.json
findings:
  critical: 0
  warning: 5
  info: 4
  total: 9
status: issues_found
---

# Phase 4: Code Review Report

**Reviewed:** 2026-09-22
**Depth:** standard
**Files Reviewed:** 14 (types.ts and package.json had nothing to flag)
**Status:** issues_found

## Summary

No security problems or crashes were found. The main defects are behavioural: the P&L chart goes stale after a trade, and both line charts plot irregularly spaced points at even spacing on the x-axis. Selection state is also never reconciled with the watchlist.

## Warnings

### WR-01: P&L chart does not update after a trade (external contract gap)

**File:** `frontend/lib/portfolioHistoryStore.tsx:89-94`
**Issue:** PLAN.md §7 says a snapshot is recorded immediately after each trade. The history store only polls every 30s and exposes `refresh`, but nothing calls it after a manual trade (TradeBar) or an assistant trade (chatStore). The chart therefore lags up to 30s behind the trade, and the "check back after your first trade" empty-state copy is misleading. Portfolio state refreshes immediately, so the UI is inconsistent.
**Fix:** After a successful trade in the trade flow and in chatStore, call `usePortfolioHistory().refresh()`. This works with the current provider nesting, because `PortfolioHistoryProvider` sits inside `ChatProvider`. Chat would need the provider moved above it, or the refresh triggered from a shared effect that watches the portfolio snapshot.

### WR-02: Line charts use a category x-axis, so irregular timestamps are drawn evenly spaced

**File:** `frontend/components/charts/PnlHistoryChart.tsx:90-97`, `frontend/components/charts/MainChart.tsx:81-88`
**Issue:** `XAxis dataKey="recorded_at"` and `dataKey="timestamp"` default to a category axis. Snapshots include immediate post-trade points that fall between the 30s ticks. `priceStore` also drops unchanged prices, so main-chart points are irregular in time too. Both charts distort the time axis, which contradicts the "drawn exactly as recorded" claim in the file header.
**Fix:** Map each point to a numeric time (`t: Date.parse(...)`) and use `<XAxis type="number" dataKey="t" scale="time" domain={["dataMin","dataMax"]} />`. Keep `tickFormatter` working on the number.

### WR-03: Selected ticker is not cleared when it is removed from the watchlist

**File:** `frontend/lib/chartSelection.tsx:22-29`, `frontend/components/charts/MainChart.tsx:46-48`
**Issue:** The selection is plain state and is never reconciled with the watchlist. Removing the selected ticker (manually or via chat) leaves the main chart showing a symbol that is no longer watched. Its price history stays in the buffer, so the chart still renders.
**Fix:** Clear the selection when the ticker disappears, for example in WatchlistPanel's remove handler with `if (selectedTicker === t) setSelectedTicker(null)`. Alternatively, have MainChart treat a selection missing from the watchlist as null.

### WR-04: Unguarded `JSON.parse` in the SSE handler

**File:** `frontend/lib/priceStore.tsx:84-85`
**Issue:** A malformed `prices` payload throws inside the event listener. The exception is uncaught, and every later event depends on the same path. `payload.ticks` is also assumed to exist without a check.
**Fix:** Wrap the parse in try/catch and return early on failure. Check `Array.isArray(payload?.ticks)` before iterating.

### WR-05: History refresh can set state after unmount and duplicates the fetch logic

**File:** `frontend/lib/portfolioHistoryStore.tsx:48-87`
**Issue:** `refresh` has no cancellation guard, so an in-flight interval fetch calls `setState` after unmount. The mount effect is a second copy of the same logic and does not use `isRefreshingRef`. A mount fetch and an interval `refresh` can therefore overlap, and the older response can overwrite the newer one.
**Fix:** Have both paths share one guarded function with a `mountedRef` check, or a request-sequence counter that discards stale responses.

## Info

### IN-01: Legend labels hardcode the 10% cap

**File:** `frontend/components/charts/PortfolioHeatmap.tsx:105-107`
**Issue:** The labels are literal `−10%`/`+10%` while `HEATMAP_CAP_PCT` exists (and is used in the aria-label). They will drift if the cap is changed.
**Fix:** Render `−{HEATMAP_CAP_PCT}%` and `+{HEATMAP_CAP_PCT}%`.

### IN-02: Tile text contrast flips abruptly at intensity 0.5

**File:** `frontend/components/charts/chartTheme.ts:84-86`
**Issue:** The switch to dark ink at 0.5 is a guessed threshold, so mid-range fills may have poor contrast with the light ink.
**Fix:** Choose the ink from the computed luminance of the mixed fill (WCAG contrast).

### IN-03: Duplicated error-parsing block in the API client

**File:** `frontend/lib/api.ts:63-69`, `99-105`
**Issue:** `postTrade` and `postChatMessage` carry identical detail-parsing logic. A `detail` that is a non-string, non-array object would produce a bad `Error` message.
**Fix:** Extract a shared `throwApiError(res)` helper and coerce with `String(...)`.

### IN-04: Watchlist change % is session-relative while the header says "daily"

**File:** `frontend/components/watchlist/WatchlistRow.tsx:26-31`
**Issue:** `firstPrices` is the first price seen in the session, so the percentage resets on every page load. PLAN.md §10 asks for "daily change %". The header comment discloses the limitation, but a ticker added mid-session starts at 0%.
**Fix:** Document this as an accepted limitation, or have the backend expose a session or day open price.

---

_Reviewed: 2026-09-22_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
