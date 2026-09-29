---
phase: 04-portfolio-visualization
plan: 07
subsystem: ui
tags: [fastapi, sqlite, recharts, nextjs, portfolio-snapshots, x-axis, gap-closure]

# Dependency graph
requires:
  - phase: 04-portfolio-visualization
    provides: "04-04's Portfolio Value line chart (PnlHistoryChart.tsx), portfolioHistoryStore.tsx and fetchPortfolioHistory() — the four-layer path this plan bounds"
  - phase: 01-backend-trading-engine
    provides: "01-04's original portfolio_snapshots schema/writer (append-only, never-pruned, 30s recorder + on-trade insert)"
provides:
  - "A bounded, most-recent-first snapshot read (DEFAULT_SNAPSHOT_LIMIT=500, MAX_SNAPSHOT_LIMIT=2000) selected by rowid rather than recorded_at"
  - "A validated `limit` query parameter on GET /api/portfolio/history, enforced via FastAPI Query bounds"
  - "A frontend-owned display bound (HISTORY_POINT_LIMIT=180) mirroring priceStore.tsx's PRICE_HISTORY_LIMIT precedent"
  - "A time-scaled X axis on the Portfolio Value chart (type=\"number\", scale=\"time\", explicit dataMin/dataMax domain)"
affects: [portfolio-visualization, testing]

# Actuals (#2632)
actuals:
  tokens: 5153
  tasks: 3
  commits: 4

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "rowid-based ORDER BY ... DESC LIMIT ? + reversed() for a most-recent, oldest-first window — now used identically by both chat_messages.py and portfolio_snapshots.py for tables where two writers can share a timestamp"
    - "Frontend-owned display bound sent as a request parameter (HISTORY_POINT_LIMIT mirroring PRICE_HISTORY_LIMIT) rather than a client-side trim, so the bound also caps the wire payload"
    - "Numeric time-scale X axis: a one-to-one recorded_at_ms projection used only for placement, domain explicitly pinned to [dataMin, dataMax] to avoid Recharts' zero-based numeric-axis default"

key-files:
  created: []
  modified:
    - backend/app/db/portfolio_snapshots.py
    - backend/app/routes/portfolio.py
    - backend/tests/db/test_portfolio_snapshots.py
    - backend/tests/routes/test_portfolio.py
    - frontend/lib/api.ts
    - frontend/lib/portfolioHistoryStore.tsx
    - frontend/components/charts/PnlHistoryChart.tsx

key-decisions:
  - "Selection is by SQLite rowid, not recorded_at text — the 30-second recorder and an on-trade insert can share an identical ISO timestamp, which would make a descending sort on the timestamp column pick an arbitrary subset at the window boundary. Mirrors the pre-existing chat_messages.py fix for the identical tie condition."
  - "The bound is a server-side window (SQL LIMIT + validated route parameter), not a client-side trim or a downsample — the smallest of the three options and the only one that also stops the response body from growing without limit, converting T-04-12 from accepted to mitigated."
  - "HISTORY_POINT_LIMIT=180 is derived, not picked: the panel's measured plot width (190-430px) at MainChart's proven ~0.46 points/px density lands at 180 points, versus the 5-11 points/px that produced the busy/bold complaint."
  - "No new copy announces the visible window — the time-scaled X axis makes the ~90-minute span legible from its own tick labels."

patterns-established:
  - "A numeric Recharts XAxis using scale=\"time\" always needs an explicit domain=[\"dataMin\",\"dataMax\"] — the default numeric domain begins at zero, which would crush any epoch-millisecond series against the right edge."

requirements-completed: [UI-05]

coverage:
  - id: D1
    description: "GET /api/portfolio/history returns a bounded, most-recent window of snapshots, oldest-first, with a validated limit query parameter (default 500, max 2000); no snapshot row is ever pruned"
    requirement: "UI-05"
    verification:
      - kind: unit
        ref: "backend/tests/db/test_portfolio_snapshots.py::test_get_snapshots_limit_returns_most_recent_oldest_first"
        status: pass
      - kind: unit
        ref: "backend/tests/db/test_portfolio_snapshots.py::test_get_snapshots_limit_above_row_count_returns_all"
        status: pass
      - kind: unit
        ref: "backend/tests/db/test_portfolio_snapshots.py::test_get_snapshots_limit_one_returns_most_recent_only"
        status: pass
      - kind: unit
        ref: "backend/tests/db/test_portfolio_snapshots.py::test_window_survives_duplicate_recorded_at"
        status: pass
      - kind: unit
        ref: "backend/tests/db/test_portfolio_snapshots.py::test_get_snapshots_default_limit_is_the_declared_constant"
        status: pass
      - kind: integration
        ref: "backend/tests/routes/test_portfolio.py::test_get_portfolio_history_explicit_limit_returns_most_recent"
        status: pass
      - kind: integration
        ref: "backend/tests/routes/test_portfolio.py::test_get_portfolio_history_zero_limit_is_422"
        status: pass
      - kind: integration
        ref: "backend/tests/routes/test_portfolio.py::test_get_portfolio_history_negative_limit_is_422"
        status: pass
      - kind: integration
        ref: "backend/tests/routes/test_portfolio.py::test_get_portfolio_history_over_max_limit_is_422"
        status: pass
    human_judgment: false
  - id: D2
    description: "Frontend requests a bounded, display-sized window (HISTORY_POINT_LIMIT=180) at both mount and every 30s refresh, mirroring PRICE_HISTORY_LIMIT, with no client-side sort/filter/slice added"
    requirement: "UI-05"
    verification:
      - kind: other
        ref: "npm --prefix frontend run typecheck && npm --prefix frontend run lint && npm --prefix frontend run build"
        status: pass
      - kind: other
        ref: "grep -c HISTORY_POINT_LIMIT frontend/lib/portfolioHistoryStore.tsx (3 occurrences: declaration + both call sites)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Portfolio Value chart's X axis is time-scaled (type=\"number\", scale=\"time\", explicit dataMin/dataMax domain) instead of categorical, so session gaps read as gaps and the density fix visibly resolves the reported busy/bold line"
    requirement: "UI-05"
    verification:
      - kind: other
        ref: "npm --prefix frontend run typecheck && npm --prefix frontend run lint && npm --prefix frontend run build"
        status: pass
      - kind: other
        ref: "targeted greps in 04-07-PLAN.md Task 3 <verify> — scale=\"time\", type=\"number\", explicit domain, recorded_at_ms present, CHART_STROKE_WIDTH untouched, no hardcoded strokeWidth, no legend/curve interpolation, no aggregation, no accessibilityLayer, all four locked panel states intact"
        status: pass
    human_judgment: true
    rationale: "This gap was originally reported as a subjective visual complaint (\"the graph is a little bit busy\"); confirming the fix actually reads as a clean, readable line against the live db/finally.db (with its 5 days of accumulated history) requires a browser and human eyes, which this executor does not have. The plan's own <verify> block reserves this exact confirmation for a <human-check> against the running app."

# Metrics
duration: 15min
completed: 2026-09-22
status: complete
---

# Phase 4 Plan 7: Portfolio Value Chart Density Fix Summary

**Bounded the portfolio_snapshots read to a validated most-recent window (rowid-ordered, 500/2000 limits) and switched the Portfolio Value chart's X axis to a real time scale, closing G-04-4's series-over-density and categorical-axis root causes without touching the 2px stroke the user initially suspected.**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-09-22T13:40:38+03:00 (previous plan's completion commit)
- **Completed:** 2026-09-22T13:51:28+03:00
- **Tasks:** 3
- **Files modified:** 7

## Accomplishments
- `get_snapshots(limit=...)` now selects the most recent rows via `ORDER BY rowid DESC LIMIT ?` and reverses to oldest-first, surviving a duplicate `recorded_at` timestamp between the 30-second recorder and an on-trade insert — mirroring the project's existing `chat_messages.py` fix for the identical tie condition
- `GET /api/portfolio/history?limit=N` validates N via FastAPI `Query(ge=1, le=MAX_SNAPSHOT_LIMIT)`, rejecting out-of-range values with 422 before the handler runs; no `HTTPException` added, no slicing performed in the route
- Frontend `portfolioHistoryStore.tsx` now requests `HISTORY_POINT_LIMIT=180` at both mount and every 30-second refresh, stopping the response body's unbounded growth at the source while preserving every Plan 04-04 invariant (interval, in-flight guard, two-effect split, once-only loading flag, no sort/filter/slice)
- `PnlHistoryChart.tsx`'s X axis is now `type="number"` + `scale="time"` with an explicit `domain={["dataMin","dataMax"]}` over a derived `recorded_at_ms` projection, so the 17 session gaps in the live record (one of 2.75 days) draw to scale instead of collapsing to even index spacing
- Zero rows deleted, pruned or aggregated anywhere — the fix bounds only what a read returns, per PLAN.md §7's never-pruned design

## Task Commits

Each task was committed atomically:

1. **Task 1: Bound the read at the source** - `a20a401` (test, RED) → `4489359` (feat, GREEN)
2. **Task 2: Ask for only as many points as the panel can honestly draw** - `77148f9` (feat)
3. **Task 3: Put the line on a real time axis** - `c370094` (fix)

_TDD task (Task 1) had two commits: test → feat, per RED→GREEN discipline._

## Files Created/Modified
- `backend/app/db/portfolio_snapshots.py` - `DEFAULT_SNAPSHOT_LIMIT`/`MAX_SNAPSHOT_LIMIT` constants; `_get_snapshots_sync`/`get_snapshots` now take a `limit`, select by `rowid DESC`, reverse to oldest-first
- `backend/app/routes/portfolio.py` - `GET /api/portfolio/history` gains a `Query`-validated `limit` parameter, passed straight through to `get_snapshots`
- `backend/tests/db/test_portfolio_snapshots.py` - 5 new tests covering the windowed read, duplicate-timestamp survival, and the declared default
- `backend/tests/routes/test_portfolio.py` - 4 new tests covering default/explicit/zero/negative/over-max limit behavior
- `frontend/lib/api.ts` - `fetchPortfolioHistory` now takes a required `limit` and sends it as a query parameter
- `frontend/lib/portfolioHistoryStore.tsx` - declares `HISTORY_POINT_LIMIT=180` (derived, commented), passes it at both call sites, updated docblock
- `frontend/components/charts/PnlHistoryChart.tsx` - `recorded_at_ms` projection, time-scaled `XAxis`, updated docblock; tooltip still reads the authoritative `recorded_at` string

## Decisions Made
- Selection by `rowid` rather than `recorded_at` (see key-decisions in frontmatter) — a deliberate widening of the fix beyond what the density complaint alone required, closing 01-REVIEW.md's WR-03 concern for reads as a side effect.
- Server-side window over client-side trim or downsample (see key-decisions) — closes T-04-12 (DoS via unbounded read) as a side effect of the density fix.
- `HISTORY_POINT_LIMIT=180` derived from measured plot geometry and `MainChart.tsx`'s proven density regime, not picked arbitrarily.
- No new UI copy announcing the visible window — the time axis's own tick labels make the ~90-minute span self-evident.

## Deviations from Plan

None - plan executed exactly as written. All `must_haves.truths`, prohibitions, and negative/positive greps in the plan's `<verify>` blocks pass as specified.

## Issues Encountered
None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Phase complete, ready for verification. The remaining item on this plan's own `<verify>` block is a `<human-check>` against the running app with the real `db/finally.db` (5 days of accumulated snapshots) — confirming the line now visually reads as a clean line rather than a band, and that it matches `MainChart.tsx`'s weight side by side. This executor has no browser access to perform that check; it is flagged as `human_judgment: true` (D3) in this summary's coverage block for `/gsd-verify-work` to route to UAT.

No blockers for phase closure. All backend tests pass (224/224); frontend typecheck/lint/build all pass.

---
*Phase: 04-portfolio-visualization*
*Completed: 2026-09-22*

## Self-Check: PASSED

All 7 modified files confirmed present on disk; all 4 task commits (`a20a401`, `4489359`, `77148f9`, `c370094`) confirmed in git history.
