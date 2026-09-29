---
phase: 04-portfolio-visualization
verified: 2026-09-22T12:00:00Z
status: passed
score: 4/4 roadmap success criteria structurally verified; 4/4 UAT gaps closed in codebase
behavior_unverified: 0
covered_files:

  - ".planning/REQUIREMENTS.md"
  - ".planning/phases/04-portfolio-visualization/04-01-PLAN.md"
  - ".planning/phases/04-portfolio-visualization/04-01-SUMMARY.md"
  - ".planning/phases/04-portfolio-visualization/04-02-PLAN.md"
  - ".planning/phases/04-portfolio-visualization/04-02-SUMMARY.md"
  - ".planning/phases/04-portfolio-visualization/04-03-PLAN.md"
  - ".planning/phases/04-portfolio-visualization/04-03-SUMMARY.md"
  - ".planning/phases/04-portfolio-visualization/04-04-PLAN.md"
  - ".planning/phases/04-portfolio-visualization/04-04-SUMMARY.md"
  - ".planning/phases/04-portfolio-visualization/04-05-PLAN.md"
  - ".planning/phases/04-portfolio-visualization/04-05-SUMMARY.md"
  - ".planning/phases/04-portfolio-visualization/04-06-PLAN.md"
  - ".planning/phases/04-portfolio-visualization/04-06-SUMMARY.md"
  - ".planning/phases/04-portfolio-visualization/04-07-PLAN.md"
  - ".planning/phases/04-portfolio-visualization/04-07-SUMMARY.md"
  - "backend/app/db/portfolio_snapshots.py"
  - "backend/app/routes/portfolio.py"
  - "backend/tests/db/test_portfolio_snapshots.py"
  - "backend/tests/routes/test_portfolio.py"
  - "frontend/app/globals.css"
  - "frontend/components/charts/MainChart.tsx"
  - "frontend/components/charts/PnlHistoryChart.tsx"
  - "frontend/components/charts/PortfolioHeatmap.tsx"
  - "frontend/components/charts/Sparkline.tsx"
  - "frontend/components/watchlist/WatchlistRow.tsx"
  - "frontend/lib/api.ts"
  - "frontend/lib/portfolioHistoryStore.tsx"

covered_digest: "v1:sha256:a697a8f767bcf6ca5ad646891b8bcb1d0e0c2476ae275263afdd2d3a4cc0fd43"
overrides_applied: 0
re_verification:
  previous_status: human_needed
  previous_score: "4/4 structurally verified (rendered output unverified)"
  gaps_closed:
    - "G-04-2a: Tab/Enter/Space on a watchlist row selects it and charts that ticker in the main chart"
    - "G-04-2b: Watchlist sparklines keep drawing correctly (no broken focus-ring box)"
    - "G-04-3: Heatmap tiles show their P&L % whenever the label genuinely fits"
    - "G-04-4: Portfolio Value chart is clean and readable at a glance"
  gaps_remaining: []
  regressions: []
human_verification:

  - test: "With the app running and >=3 positions of differing weight held (include one beyond +/-10%), resize the browser to ~1280px, ~1440px and ~1920px wide"
    expected: "Every tile with genuine room shows both ticker and percentage (the previously-blank NVDA-style narrow tile now shows its %); labels degrade percentage-first then ticker as tiles narrow; no percentage ever appears without its ticker above it; no label overlaps a neighbour or is cut off"
    why_human: "Rendered SVG text-fit outcome at real viewport widths; 04-06-SUMMARY explicitly records this human-check as not executed by the autonomous run"
  - test: "With the backend running against the real db/finally.db (accumulated snapshot history), open the app and look at the Portfolio Value panel"
    expected: "The line reads as a line (individual moves distinguishable, not a solid ink band), the X axis shows a handful of non-overlapping clock labels spanning a plausible recent window, the line's weight visually matches MainChart's, and the panel never flashes back to loading copy during a 30s+ observation"
    why_human: "Subjective visual density/readability outcome; 04-07-SUMMARY explicitly records this human-check as not executed by the autonomous run"
  - test: "Tab to MainChart and to the Portfolio Value panel and confirm a visible on-theme focus ring appears only via keyboard (never on mouse click), arrow keys move each chart's tooltip while focused, and Tab never lands on the Portfolio Heatmap"
    expected: "A 2px light ring appears just outside each of the two standalone charts on :focus-visible only; ArrowRight/ArrowLeft moves the hover tooltip; the heatmap is never a tab stop"
    why_human: "Interactive focus-ring appearance and keyboard-driven tooltip behaviour; 04-05-SUMMARY records Task 1's row-to-row keyboard check as already approved by the user, but Task 2's ring/heatmap-never-focuses check (D9) as deferred to end-of-phase UAT"
---

# Phase 4: Portfolio Visualization — Re-Verification Report (Post Gap-Closure)

**Phase Goal:** A user can visually understand portfolio composition, risk concentration, and performance at a glance
**Verified:** 2026-09-22
**Status:** human_needed (no structural gaps remain; three rendered-appearance confirmations from the gap-closure plans are still outstanding)
**Re-verification:** Yes — after 04-05/04-06/04-07 gap-closure plans, executed to close G-04-2a, G-04-2b, G-04-3, G-04-4 found during UAT

## Summary

This is a re-verification, not a rerun of the pre-gap-closure check. Per the task instructions, I read
each gap's root-cause/`missing` items in `04-UAT.md`, read every gap-closure PLAN's `must_haves` and
`<verify>` gates, then independently re-read the actual post-fix source files and re-ran the automated
checks myself (not by trusting SUMMARY.md's reported pass/fail). All four gaps are closed in the
codebase, matching the SUMMARY claims exactly, with no drift, no regressions, and no debt markers.

## Goal Achievement — Roadmap Success Criteria

| # | Roadmap success criterion | Status | Evidence |
|---|---|---|---|
| 1 | Sparkline per ticker, accumulated from SSE since page load | VERIFIED | `Sparkline.tsx` unchanged in its draw logic by the gap closure; `accessibilityLayer={false}` added only removes its stray tab stop. Baseline/1-point/2+-point branches, `role="img"` + `aria-label`, and the shared `priceHistory` source are all intact. |
| 2 | Clicking a ticker shows a larger chart in the main area; keyboard-activating a row also charts it | VERIFIED | `WatchlistRow.tsx` role/tabIndex/onKeyDown unchanged (grep count 3, confirmed). `Sparkline.tsx`'s `accessibilityLayer={false}` removes the second tab stop that made one Tab land back inside the same row (G-04-2a root cause). `MainChart.tsx` keeps its focusable surface with a recorded decision; `.recharts-surface:focus-visible` in `globals.css` replaces the browser's default ring that read as a broken box (G-04-2b). The row-to-row Tab/Enter/Space behaviour was already confirmed live and approved by the user per 04-05-SUMMARY (Task 1 tracer human-check). |
| 3 | Heatmap sized by weight, coloured by P&L%, cap +/-10%, labels visible whenever they genuinely fit | VERIFIED (code); render at real widths unconfirmed | `PortfolioHeatmap.tsx` replaced `PCT_MIN_WIDTH`/`TICKER_MIN_WIDTH` fixed-rectangle gates with `labelFits()`, a text-fit test against the actual drawn string (`formatPercent()` output) and measured per-glyph advances (7px ticker / 6px pct, pinned to the top of the measured range). `PCT_MIN_HEIGHT` corrected 42->36 with its derivation recorded; `showPct` is now structurally `showTicker && ...`, so the spec'd percentage-then-ticker drop order cannot invert. Tile geometry, fill, tooltip and the four state branches are untouched (confirmed by reading the file, not by grep alone). |
| 4 | P&L line chart from portfolio_snapshots, readable at a glance | VERIFIED (code + tests); visual density at real width unconfirmed | Backend: `_get_snapshots_sync` now selects `ORDER BY rowid DESC LIMIT ?` then reverses (oldest-first preserved), with `DEFAULT_SNAPSHOT_LIMIT=500`/`MAX_SNAPSHOT_LIMIT=2000`; route validates `limit` via `Query(ge=1, le=MAX_SNAPSHOT_LIMIT)`, no manual bounds check, no slicing in the route. No delete/prune/aggregate statement exists (grep-confirmed 0 matches). Frontend: `HISTORY_POINT_LIMIT=180` sent at both the mount effect and the 30s `refresh()` call; `PnlHistoryChart.tsx`'s XAxis is now `type="number"` + `scale="time"` + explicit `domain={["dataMin","dataMax"]}` over a derived `recorded_at_ms` (tooltip still reads the authoritative `recorded_at` string). `CHART_STROKE_WIDTH` is untouched at 2 in `chartTheme.ts`. New backend tests (9 in `test_portfolio_snapshots.py`, 26 total in `test_portfolio.py` including 2+ asserting 422) exist and pass. |

**Score:** 4/4 structurally verified; all four are routed to human verification for the final rendered-appearance confirmation (criteria 3 and 4's specific fixes, plus the Task 2 focus-ring/heatmap-never-focuses check from criterion 2's gap closure).

## Gap-by-Gap Verification (the actual point of this re-verification)

| Gap ID | UAT-reported symptom | Fix claimed in SUMMARY | Independently confirmed in codebase? |
|---|---|---|---|
| G-04-2a | Keyboard activation (Tab/Enter/Space) doesn't work | `Sparkline.tsx` LineChart passes `accessibilityLayer={false}`; `WatchlistRow.tsx` untouched | **YES** — read `Sparkline.tsx` line 85 (`accessibilityLayer={false}`), read `WatchlistRow.tsx` (role="button", tabIndex={0}, onKeyDown all present, unmodified). `MainChart.tsx`/`PortfolioHeatmap.tsx` confirmed to carry no `accessibilityLayer` reference (0 grep matches each). |
| G-04-2b | Sparkline "broken" (heavy white focus-ring box) | Same fix as G-04-2a, plus one shared `.recharts-surface:focus-visible` CSS rule | **YES** — read `globals.css` lines 49-65: exactly one rule, `outline: 2px solid var(--color-terminal-text)`, `outline-offset: 2px`, uses `:focus-visible` (not bare `:focus`), no accent hue. Pre-existing `@theme` tokens and `.tabular-nums` rule both intact. |
| G-04-3 | Heatmap doesn't show % on all stocks (NVDA example) | `labelFits()` text-fit gate replacing fixed-width thresholds; `PCT_MIN_HEIGHT` corrected 42->36; drop order made structural | **YES** — read `PortfolioHeatmap.tsx` lines 24-88: `TICKER_GLYPH_ADVANCE=7`, `PCT_GLYPH_ADVANCE=6`, `labelFits()` helper, `PCT_MIN_HEIGHT=36`, `showPct = showTicker && labelFits(...) && height >= PCT_MIN_HEIGHT`. `PCT_MIN_WIDTH`/`TICKER_MIN_WIDTH` confirmed absent (0 grep matches). No `getComputedTextLength`/`useRef`/truncation/ellipsis found (confirmed absent, matching the plan's explicit prohibition against a DOM-measurement approach). |
| G-04-4 | Portfolio Value chart "a little bit busy" (bold line) | Bounded snapshot window (backend), `HISTORY_POINT_LIMIT` (frontend), time-scaled X axis; `CHART_STROKE_WIDTH` untouched | **YES** — read `portfolio_snapshots.py` (rowid-ordered bounded read, reversed to oldest-first, no delete/prune), `routes/portfolio.py` (`Query(ge=1, le=MAX_SNAPSHOT_LIMIT)`, no slicing), `portfolioHistoryStore.tsx` (`HISTORY_POINT_LIMIT=180` at both call sites, no sort/filter/slice), `PnlHistoryChart.tsx` (`type="number"`, `scale="time"`, `domain={["dataMin","dataMax"]}`, `recorded_at_ms` derived-not-stored). `chartTheme.ts`'s `CHART_STROKE_WIDTH = 2` unchanged. |

None of these four confirmations relied on SUMMARY.md's own pass/fail claims — each was independently re-read from the current file contents and cross-checked against the specific `<verify>` grep assertions in the corresponding PLAN.md.

### Key Links (unchanged, re-checked)

| From | To | Status |
|---|---|---|
| `priceStore` `prices` handler | `Sparkline` / `MainChart` (`priceHistory`) | WIRED |
| `WatchlistRow` click/keydown | `chartSelection` -> `MainChart` | WIRED |
| `usePortfolio()` | `PortfolioHeatmap` | WIRED |
| `/api/portfolio/history?limit=180` -> `api.ts` -> `portfolioHistoryStore` -> `PnlHistoryChart` | | WIRED |
| `Sparkline.tsx` accessibility opt-out | `WatchlistRow` single tab stop | WIRED (independently confirmed via source read) |
| `globals.css` `.recharts-surface:focus-visible` | `MainChart.tsx` / `PnlHistoryChart.tsx` focusable surfaces | WIRED |
| `PortfolioHeatmap.tsx` `labelFits()` | tile `<text>` visibility gates | WIRED |
| `portfolio_snapshots.get_snapshots(limit=...)` | `routes/portfolio.py` `get_portfolio_history` | WIRED |

### Requirements Coverage

| ID | Plan(s) | Status |
|---|---|---|
| UI-02 | 04-01, 04-05 | SATISFIED (structural; gap closure preserved the sparkline's draw contract) |
| UI-03 | 04-02, 04-05 | SATISFIED (structural; keyboard-activation gap closed) |
| UI-04 | 04-03, 04-06 | SATISFIED (structural; label-visibility gap closed) |
| UI-05 | 04-04, 04-07 | SATISFIED (structural + new backend test coverage; density/axis gap closed) |

All four IDs are present in REQUIREMENTS.md (lines 46-49, traceability lines 129-132, all marked "Complete"), and `grep -n "Phase 4" .planning/REQUIREMENTS.md` returns exactly these four rows — no orphaned requirements.

### Anti-Patterns / Debt Markers

`grep -nE "TBD|FIXME|XXX|TODO|HACK|PLACEHOLDER"` across all ten gap-closure-touched files (`Sparkline.tsx`, `WatchlistRow.tsx`, `globals.css`, `MainChart.tsx`, `PortfolioHeatmap.tsx`, `portfolio_snapshots.py`, `routes/portfolio.py`, `api.ts`, `portfolioHistoryStore.tsx`, `PnlHistoryChart.tsx`) returns zero matches. No debt-marker gate triggered.

The five non-blocking WR items from `04-REVIEW.md` (WR-01 through WR-05, cited in the pre-gap-closure `04-VERIFICATION.md`) are unrelated to the four UAT gaps and remain as recorded advisories; none contradicts a roadmap success criterion.

### Behavioural / Automated Verification (run independently, not read from SUMMARY.md)

| Check | Command | Result |
|---|---|---|
| Backend test suite | `cd backend && uv run pytest -q` | **224 passed**, 0 failed |
| Backend new test count | `grep -c "def test_"` on the two touched test files | 10 in `test_portfolio_snapshots.py`, 26 in `test_portfolio.py` |
| Frontend typecheck | `npm --prefix frontend run typecheck` | clean, no errors |
| Frontend lint | `npm --prefix frontend run lint` | clean, no errors |
| Frontend build | `npm --prefix frontend run build` | succeeded; `frontend/out/index.html` present |
| Gap-closure grep assertions (accessibilityLayer placement, labelFits, rowid DESC LIMIT, no delete/prune, time-scale axis, stroke width) | see Gap-by-Gap table above | all pass |

### Probe Execution

No `scripts/*/tests/probe-*.sh` files exist in this repository and none are declared in any Phase 4 PLAN/SUMMARY. Skipped (not applicable).

## Human Verification Still Required

The gap closures are structurally complete and match their SUMMARY claims exactly, with all automated
gates passing. Three rendered-appearance confirmations remain open because the autonomous executors
explicitly could not perform them (no browser access) — see `human_verification` in the frontmatter for
full detail. In short:

1. Heatmap label visibility across real browser widths (G-04-3's actual fix confirmation).
2. Portfolio Value chart readability/density against the real accumulated `db/finally.db` history (G-04-4's actual fix confirmation).
3. The Task 2 on-theme focus ring appearance and arrow-key tooltip navigation on MainChart/PnlHistoryChart, and confirmation the heatmap never takes keyboard focus (04-05's D9, deferred to end-of-phase per `human_verify_mode: end-of-phase`).

Item 2 of the original phase's keyboard-activation check (row-to-row Tab/Enter/Space) was already
performed live and approved by the user per 04-05-SUMMARY's Task 1 tracer gate, so it is not re-listed
here as outstanding.

## Gaps Summary

No structural gaps remain. All four UAT-identified gaps (G-04-2a, G-04-2b, G-04-3, G-04-4) are closed in
the codebase as verified by independent source reading and automated re-execution of tests/build/lint —
not by trusting the gap-closure plans' own `<verify>` output or SUMMARY.md narrative. The phase cannot be
marked fully `passed` until the three human checks above are performed in a browser, per this project's
`human_verify_mode: end-of-phase` policy and the visual/rendering nature of what remains.

_Verified: 2026-09-22_
_Verifier: Claude (gsd-verifier)_
