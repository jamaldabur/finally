---
status: diagnosed
trigger: "G-04-4 (UAT test 4): the Portfolio Value graph is a little bit busy (maybe the line is bold, idk, fix it)"
created: 2026-09-22T02:00:00Z
updated: 2026-09-22T09:20:00Z
---

## Current Focus

hypothesis: CONFIRMED — the "busy"/"bold" look is series over-density, not any styling
  property. 2094 snapshots are rendered into a ~126px-tall x ~190-430px-wide plot
  area (5-11 points per horizontal pixel), so adjacent 2px strokes merge into a
  band 4-5x thicker than the nominal stroke.
test: (complete) Measured live `GET /api/portfolio/history`; computed plot-area
  geometry by hand from the component's own Tailwind classes and Recharts margins;
  ran a differential against MainChart.tsx (byte-identical chart config, 500-point
  cap, no user complaint).
expecting: (met) Ranked candidates, each labelled spec'd value vs implementation
  choice.
next_action: (none — goal is find_root_cause_only; no fix applied, no source
  files modified)

reasoning_checkpoint:
  hypothesis: "The Portfolio Value chart reads as busy/bold because nothing in the
    path windows, caps, or downsamples the snapshot series: the backend query has no
    LIMIT, the route has no limit, the store passes rows through untouched, and the
    component plots every row. 2094 points into a ~190-430px-wide plot is 5-11
    points/px, which renders the 2px stroke as a 7.5-10.8px-tall band of ink per
    pixel column."
  confirming_evidence:
    - "Live endpoint returns 2094 snapshots spanning 7222 minutes (5.0 days)."
    - "Measured ink extent in a single 1px column: median 7.5px (plotW=432) to
      10.8px (plotW=192), p90 ~27-28px — vs a 2px nominal stroke on a 126px plot."
    - "1373 of 2092 interior points (65.6%) reverse direction — near-maximal zigzag."
    - "MainChart.tsx has identical stroke/axes/tooltip/end-label/animation config but
      is capped at PRICE_HISTORY_LIMIT=500 in a ~2x taller, ~3x wider panel
      (~0.5 points/px, 10-24x less dense) and drew no busyness complaint."
  falsification_test: "If stroke width were the cause, MainChart (same
    CHART_STROKE_WIDTH=2 from the same chartTheme.ts constant) would read equally
    bold. It does not — Test 2's complaints were keyboard activation and sparklines,
    never main-chart busyness. That refutes strokeWidth as the cause."
  fix_rationale: "(not applied — diagnose-only mode)"
  blind_spots: "Plot width is computed from Tailwind classes, not measured in a
    browser; the 190-430px range covers 1440px-1920px viewports. The exact Recharts
    auto-domain nice-tick bounds were approximated by the data range, which shifts
    the px-per-dollar figure slightly but not the density conclusion."
  candidate_causes:
    - "data: unbounded, never-windowed snapshot series (2094 rows, 5 days) — PRIMARY"
    - "code: no cap/downsample at any of the four layers that could apply one"
    - "code: categorical X axis distorts time across 17 session gaps"
    - "config: Y-axis domain=['auto','auto'] fits 5 days of range into 126px"
  and_gate: "yes — density (data) is necessary but the small 240px panel (code/layout
    choice) is what makes it fatal. MainChart proves density alone at 500 points in a
    288px full-width panel is fine; the P&L panel combines 4x the points with ~1/2
    the height and ~1/3 the width. Both conditions must hold."

## Symptoms

expected: Chart shows >=2 snapshots with axes, tooltip and end label, with a clean,
  restrained look consistent with the dark data-dense terminal style (04-UI-SPEC.md).
actual: User reported: "the Portfolio Value graph is a little bit busy (maybe the line
  is bold, idk, fix it)". Subjective cosmetic complaint; need concrete properties.
errors: None reported
reproduction: UAT test 4 - place a trade and watch the Portfolio Value panel
started: Discovered during UAT right after phase 04 execution (plan 04-04)

## Eliminated

- hypothesis: Grid lines contribute to the busy look
  evidence: No <CartesianGrid> element is rendered at all in PnlHistoryChart.tsx
  timestamp: 2026-09-22T02:00:00Z

- hypothesis: The line's stroke width is too heavy (the user's own guess)
  evidence: CHART_STROKE_WIDTH=2 is the UI-SPEC's spec'd value ("Line | 2px stroke")
    and is the single shared constant in chartTheme.ts used by MainChart too.
    MainChart renders at 2px and drew no busyness complaint. The line only *appears*
    bold because 5-11 points/px merge adjacent strokes into a 7.5-10.8px ink band.
  timestamp: 2026-09-22T09:15:00Z

- hypothesis: Visible dots/markers on every point make it busy
  evidence: The `dot` render function returns an empty `<g key=.../>` for every
    index !== lastIndex, so only the final marker is visible. Zero intermediate
    markers are drawn. (It does create 2094 throwaway <g> elements — a perf cost,
    not a visual one.)
  timestamp: 2026-09-22T09:15:00Z

- hypothesis: Tooltip/cursor contributes to the static busy look
  evidence: <Tooltip> renders only on hover (returns null when !active); the cursor
    line likewise. Neither is present in the resting view the user described.
  timestamp: 2026-09-22T09:15:00Z

- hypothesis: Chart animation adds visual churn
  evidence: CHART_ANIMATION_ACTIVE=false, passed as isAnimationActive on the Line.
  timestamp: 2026-09-22T09:15:00Z

- hypothesis: The sibling diagnosis's Recharts 3 accessibilityLayer focus outline
    has visual bearing here
  evidence: grep for `accessibilityLayer|tabIndex` across frontend/components/charts
    returns no matches. PnlHistoryChart passes neither prop, so no focus-outline
    surface exists on this chart, focused or not.
  timestamp: 2026-09-22T09:18:00Z

## Evidence

- timestamp: 2026-09-22T02:00:00Z
  checked: PnlHistoryChart.tsx full source
  found: No <CartesianGrid> element is rendered at all.
  implication: Grid lines are NOT a contributor to the busy look. Eliminated as a
    candidate before testing it further.

- timestamp: 2026-09-22T09:05:00Z
  checked: Live GET http://localhost:8000/api/portfolio/history (read-only)
  found: 2094 snapshots, spanning 2026-09-17T08:47Z to 2026-09-22T09:09Z
    (7222 minutes = 5.0 days). Values $9843.68-$10223.19 (range $379.51, 3.78% of
    mid). 1373 of 2092 interior points (65.6%) reverse direction. Only 6 points
    (0.3%) fall in the last 60 minutes; 1691 (80.8%) in the last 24h.
  implication: The series is 5 days of accumulated history, not "the trade I just
    placed". The post-trade change the UAT test asks the user to look at occupies
    0.3% of the horizontal axis.

- timestamp: 2026-09-22T09:06:00Z
  checked: backend/app/db/portfolio_snapshots.py::_get_snapshots_sync,
    backend/app/routes/portfolio.py::get_portfolio_history,
    frontend/lib/portfolioHistoryStore.tsx, PnlHistoryChart.tsx
  found: Four sequential layers, none of which windows or thins the series. SQL is
    `SELECT ... ORDER BY recorded_at` with no LIMIT; the route maps 1:1; the store's
    own docstring says it "never sorts, filters, thins, or synthesises points"; the
    component passes `snapshots` straight to <LineChart data=...>.
  implication: There is no cap anywhere. The rendered point count grows without
    bound for the life of the volume-mounted db/finally.db, so this gets strictly
    worse every day the app runs.

- timestamp: 2026-09-22T09:08:00Z
  checked: Rendered plot geometry, computed by hand from the component's own classes
  found: Panel `h-60` (240px) - `p-4` (32px) - h2 text-sm (20px) - `mt-3` (12px)
    = 176px container. LineChart margin {top:20,bottom:0}; XAxis default height 30.
    => plot area 126px tall. Width: YAxis width={72} + right margin 16 subtracted
    from a panel that is one of two `flex-1` siblings in the centre column
    => ~192px (1440px viewport) to ~432px (1920px viewport).
  implication: 2094 points into 192-432px = 4.85-10.91 points per horizontal pixel;
    x-step is 0.09-0.21px, i.e. every data point is sub-pixel.

- timestamp: 2026-09-22T09:09:00Z
  checked: Ink density per 1px column (max-min of the values falling in each pixel
    column, scaled by 126px / $379.51 = 1px per $3.01)
  found: Median vertical ink extent in a single 1px column: 10.8px at plotW=192,
    7.5px at plotW=432. p90: 28.4px / 27.3px (22% of total plot height).
  implication: THE SMOKING GUN. The 2px stroke renders as a 7.5-10.8px-tall band in
    a typical pixel column — 4-5x its nominal weight — and up to ~28px at p90. The
    user's "maybe the line is bold" is an accurate perception of the symptom with
    the wrong cause attached: the stroke is 2px as spec'd; the *series* is too dense.

- timestamp: 2026-09-22T09:10:00Z
  checked: Differential vs MainChart.tsx + frontend/lib/priceStore.tsx
  found: MainChart uses the same chartTheme constants (2px stroke, r=4 dot, 2px
    ring, animation off), the same type="linear", the same domain={["auto","auto"]},
    the same TICK_STYLE/AXIS_LINE, the same tooltip shape and the same end-label
    code. Its only differences: PRICE_HISTORY_LIMIT=500 caps its series, and it
    renders in a full-width `h-72` panel (~234px plot height, ~1090px plot width)
    => ~0.46 points/px. UAT Test 2 complained about keyboard activation and
    sparklines, never about the main chart being busy.
  implication: Every styling property is held constant between a chart that reads
    fine and one that reads busy. Density is the only variable that differs
    (10-24x), which isolates it as the cause and exonerates stroke width, axes,
    tooltip, end label, animation and colour.

- timestamp: 2026-09-22T09:11:00Z
  checked: Session gaps in the snapshot series vs Recharts XAxis default type
  found: 17 gaps >5 minutes, including one of 3956 minutes (2.75 days) at index 108.
    XAxis is declared `dataKey="recorded_at"` with no `type="number"`; Recharts
    defaults XAxis to type="category", so all 2094 points are spaced evenly by
    index regardless of elapsed time.
  implication: Secondary defect. Time is badly distorted — the 108 points before the
    2.75-day gap get the same horizontal real estate as the 108 most recent, and the
    last hour compresses to ~1px. This is an accuracy bug that compounds the
    unreadability, distinct from the density cause.

- timestamp: 2026-09-22T09:12:00Z
  checked: Y-axis configuration against measured deltas
  found: domain={["auto","auto"]} fits the full 5-day $379.51 range into 126px
    => 1px = $3.01. Median point-to-point |delta| is $0.81 = 0.27px (sub-pixel);
    p90 is $80.97 = 26.9px. Tick labels use formatCurrency => "$10030.52" (9 chars,
    no thousands separator, 2 decimals) at the default tickCount of 5 over 126px
    (~31px apart), inside width={72}.
  implication: The symptoms' "auto-domain amplifies a tiny change into a jagged
    swing" hypothesis is only partly right — routine 30s ticks are sub-pixel and are
    NOT amplified. What the auto domain does do is spend the whole 126px on 5 days
    of range, so recent movement is squashed. Contributing amplifier, not the cause.
    Separately the 72px y-axis consumes 17-37% of the panel's width for 5 nearly
    identical 9-character strings.

- timestamp: 2026-09-22T09:13:00Z
  checked: End-label placement in the dot render function
  found: <text x={cx} y={cy-12} textAnchor="end"> — the label is anchored at the
    last point and extends LEFT, across the right edge of the plot, with no
    collision avoidance.
  implication: At 5-11 points/px a ~60px-wide label sits directly on top of roughly
    300-650 data points of the densest part of the line. Minor contributor; it only
    reads as clutter *because* of the density beneath it.

## Resolution

root_cause: >
  Series over-density in the Portfolio Value panel: nothing in the four-layer path
  (SQL -> route -> store -> component) windows, caps, or downsamples
  `portfolio_snapshots`, so all 2094 accumulated rows (5 days, unbounded and
  growing) are drawn into a plot area only ~126px tall by ~190-430px wide. At
  4.85-10.91 points per horizontal pixel the 2px stroke merges into a 7.5-10.8px
  ink band per pixel column (p90 ~28px, 22% of plot height), which is exactly the
  "bold"/"busy" appearance reported. The stroke width the user suspected is the
  UI-SPEC's spec'd 2px and is not at fault — MainChart.tsx proves it, using
  byte-identical chart configuration at 500 capped points and reading fine.
  Secondary compounding defect: XAxis defaults to type="category", so 17 session
  gaps (one of 2.75 days) are collapsed to even index spacing and the last hour of
  activity — the thing UAT Test 4 asks the user to look at — occupies 0.3% of the
  width.
fix: (not applied — diagnose-only mode)
verification: (not applicable — diagnose-only mode)
files_changed: []
