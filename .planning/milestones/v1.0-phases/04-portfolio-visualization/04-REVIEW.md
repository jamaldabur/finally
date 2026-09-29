---
phase: 04-portfolio-visualization
reviewed: 2026-09-22T00:00:00Z
depth: standard
files_reviewed: 11
files_reviewed_list:
  - frontend/components/charts/Sparkline.tsx
  - frontend/app/globals.css
  - frontend/components/charts/MainChart.tsx
  - frontend/components/charts/PortfolioHeatmap.tsx
  - backend/app/db/portfolio_snapshots.py
  - backend/app/routes/portfolio.py
  - backend/tests/db/test_portfolio_snapshots.py
  - backend/tests/routes/test_portfolio.py
  - frontend/lib/api.ts
  - frontend/lib/portfolioHistoryStore.tsx
  - frontend/components/charts/PnlHistoryChart.tsx
findings:
  critical: 0
  warning: 3
  info: 1
  total: 4
status: issues_found
---

# Phase 4: Code Review Report (Gap-Closure Plans 04-05, 04-06, 04-07)

**Reviewed:** 2026-09-22T00:00:00Z
**Depth:** standard
**Files Reviewed:** 11
**Status:** issues_found

## Summary

This review covers only what changed in these 11 files since commit `6f2466c` (the
prior 04-REVIEW.md baseline): the keyboard/focus-ring fix for the watchlist
sparkline (04-05), the treemap label-fit rewrite (04-06), and the
`portfolio_snapshots` windowing + time-scaled P&L X-axis work (04-07).

The three gap closures are each well-targeted at their root causes and are
backed by strong reasoning in their docblocks/commit comments — the heatmap
`labelFits()` rewrite in particular matches the measured glyph-width evidence
in `.planning/debug/heatmap-tile-pct-label-missing.md` closely, and the
`rowid`-based snapshot ordering correctly fixes the duplicate-`recorded_at`
tie-break bug with a test (`test_window_survives_duplicate_recorded_at`) that
actually forces the collision rather than hoping to get lucky. No critical
or security-relevant defects were found.

However, the P&L history windowing (04-07) introduced a new numeric,
time-scaled X axis without fully reconciling it against the very
duplicate-timestamp behavior the same plan's backend half explicitly
documents and tests as an expected occurrence — see WR-01 and WR-02 below.
The new `limit` parameter on `get_snapshots()`/`_get_snapshots_sync()` also
relies entirely on the route layer for its lower bound, which quietly
reopens the exact "unbounded response" gap (G-04-4) this work exists to
close, for any caller other than the one route — see WR-03.

## Warnings

### WR-01: Duplicate `recorded_at` timestamps produce a visual spike on the now-numeric X axis

**File:** `frontend/components/charts/PnlHistoryChart.tsx:81-131`
**Issue:** `backend/app/db/portfolio_snapshots.py` explicitly documents (and
`test_window_survives_duplicate_recorded_at` explicitly forces) the case
where two snapshots — e.g. the 30-second recorder tick and an
immediately-following post-trade insert — share one `recorded_at` string
because `datetime.now()`'s effective resolution can be coarser than
microseconds on some platforms. This is called out as a legitimate,
expected occurrence, not an edge case to eliminate.

`PnlHistoryChart` now plots on a `type="number" scale="time"` X axis keyed
on `recorded_at_ms = Date.parse(s.recorded_at)` (lines 81-84, 122-131). Two
adjacent points with an identical `recorded_at_ms` but different
`total_value` (exactly the scenario the backend fix anticipates) will sit at
the same X coordinate with different Y coordinates. Recharts' line generator
draws every point in array order regardless of X, so this renders as a
vertical (or near-vertical) segment — a visible spike that reads as an
instantaneous, discontinuous jump in portfolio value at a single instant,
when in fact the two points are sequential events that merely share a
timestamp string. `Sparkline.tsx`'s docblock shows the team is alert to this
class of problem elsewhere ("equal consecutive prices merge into one
recorded point"), but no analogous handling (e.g. a small synthetic offset,
or de-duplication/merge on the frontend, or a coarser recorded_at
granularity contract) exists here.
**Fix:** Either widen `recorded_at`'s effective resolution at the write site
(e.g. force microsecond-distinct timestamps, reverting part of the 04-07
rationale) or handle the collision on read — e.g. break ties for charting
purposes by nudging by array index (`recorded_at_ms + i * epsilon`) so two
same-timestamp points remain visually adjacent rather than overlapping:
```tsx
const chartData = snapshots.map((s, i) => ({
  ...s,
  // Guarantee strictly increasing X for charting only; does not change the
  // stored/returned recorded_at or reorder data.
  recorded_at_ms: Date.parse(s.recorded_at) + i,
}));
```

### WR-02: "No guard against a non-parseable timestamp" does not deliver the claimed "visible failure"

**File:** `frontend/components/charts/PnlHistoryChart.tsx:73-88`
**Issue:** The docblock/comment added in this diff states: "No guard around
a non-parseable timestamp: ... a chart that visibly fails on one is a better
outcome than one that quietly omits a recorded portfolio value." But the
code added in the same diff does not actually produce a visible failure for
a non-finite `recorded_at_ms`:
- `formatAxisTime` (line 86-88), added in this same diff, *does* guard with
  `Number.isFinite(ms) ? ... : ""` — silently blanking the tick label rather
  than failing visibly.
- A `NaN` value flowing into a `type="number"` axis with
  `domain={["dataMin", "dataMax"]}` will most likely either be silently
  skipped by Recharts' line/domain calculation (producing a quiet gap — the
  very "quietly omits" outcome the comment says is worse) or corrupt
  `dataMin`/`dataMax` into `NaN`, which manifests as a blank/broken chart
  with no visible error message, not a loud failure a user or developer
  could act on.

Either way, the actual failure mode is silent rather than the "visible
failure" the comment asserts is the deliberate tradeoff, so the comment is
misleading about what happens, and the current behavior is inconsistent (one
sibling function guards, the data pipeline feeding it does not).
**Fix:** Pick one behavior and make the comment match it: either guard
`recorded_at_ms` itself and drop/flag rows that fail to parse (matching
`formatTime`'s and `formatAxisTime`'s existing guard style), or add an
explicit, visible error state (e.g. render an alert banner) when any
snapshot's timestamp fails to parse, so the "visibly fails" claim is true in
practice.

### WR-03: `get_snapshots`/`_get_snapshots_sync` do not enforce their own `limit` lower bound

**File:** `backend/app/db/portfolio_snapshots.py:72-117`
**Issue:** The entire point of 04-07 Task 1 (closing gap G-04-4) is to stop
`portfolio_snapshots` reads from growing the response body without bound.
That bound is currently enforced only by `app/routes/portfolio.py`'s
`Query(default=DEFAULT_SNAPSHOT_LIMIT, ge=1, le=MAX_SNAPSHOT_LIMIT)` — the
DB function itself performs no validation on `limit` before splicing it into
`... LIMIT ?`. SQLite's own semantics for `LIMIT` make this a real gap, not
just defensive-programming pedantry: a `LIMIT` value of `0` returns zero
rows, and a **negative** `LIMIT` value means "no upper bound at all" (SQLite
returns every matching row). `get_snapshots()` is a public, exported,
directly-importable function (already called directly by several tests) —
any future direct caller (a background job, a chat-tool handler, an admin
script) that passes `limit=-1` or a miscomputed negative value would
silently get the entire unbounded table back, exactly reopening G-04-4,
with no error and no test coverage protecting against it.
**Fix:** Validate inside the DB layer itself, not only at the route:
```python
async def get_snapshots(
    user_id: str = DEFAULT_USER_ID, limit: int = DEFAULT_SNAPSHOT_LIMIT
) -> list[PortfolioSnapshot]:
    if limit < 1:
        raise ValueError(f"limit must be >= 1, got {limit}")
    return await asyncio.to_thread(_get_snapshots_sync, user_id, limit)
```

## Info

### IN-01: No automated regression coverage for the 04-05/04-06 frontend fixes

**File:** `frontend/components/charts/Sparkline.tsx`, `frontend/components/charts/PortfolioHeatmap.tsx`
**Issue:** Both the `accessibilityLayer={false}` keyboard-focus fix (04-05)
and the `labelFits()` glyph-metric rewrite (04-06) are verified only via the
manual/headless-Chrome debug sessions recorded in
`.planning/debug/keyboard-activation-watchlist-row.md` and
`.planning/debug/heatmap-tile-pct-label-missing.md`. Neither ships with a
runnable regression test, so a later refactor of either component (e.g.
someone re-adding `accessibilityLayer` for an unrelated reason, or tweaking
`TICKER_GLYPH_ADVANCE`/`PCT_GLYPH_ADVANCE`) has nothing automated to catch a
regression. This is consistent with the frontend having no test runner
configured project-wide (`frontend/package.json` has no `test` script and no
Vitest/Jest/RTL dependency), so it is not a new gap introduced by this diff
specifically — noted for awareness rather than as a defect unique to these
plans.
**Fix:** Out of scope for this diff given no frontend test infra exists yet;
worth tracking as a follow-up once frontend unit testing is set up (e.g. a
Vitest + Testing Library snapshot asserting `labelFits()`'s pure function
behavior at the documented boundary widths, and a DOM-level assertion that
`Sparkline`'s root has no `tabindex`).

---

_Reviewed: 2026-09-22T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
