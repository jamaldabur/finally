---
status: diagnosed
trigger: "keyboard activation doesn't work, the little graph of stocks in watchlist is broken"
created: 2026-09-22T01:00:00Z
updated: 2026-09-22T01:45:00Z
audit_acknowledged:
  milestone: v1.0
  at: 2026-09-29
  status: diagnosed
---

## Current Focus

hypothesis: CONFIRMED — each `WatchlistRow` contains a second, unintended tab stop (its own Recharts sparkline `<svg tabindex="0" role="application">`), so one Tab from a selected row lands inside the *same* row rather than on the next row; Enter/Space there re-selects the already-selected ticker and appears to do nothing.
test: live-browser reproduction of the exact UAT flow (click row 1, Tab, Enter, Space, Tab, Enter) against the running `next dev` + FastAPI pair, reading `document.activeElement` and the main chart heading after every keystroke
expecting: after the first Tab, activeElement is the sparkline svg and the chart heading stays on the already-selected ticker; only the SECOND Tab reaches the next row
next_action: none — diagnose-only mode; root cause established, returning to orchestrator

reasoning_checkpoint:
  hypothesis: "Recharts 3.x defaults `accessibilityLayer` to true, which makes every chart's root <svg> surface focusable (tabindex=0, role=application). Sparkline renders such a chart INSIDE the focusable WatchlistRow, so each row owns two tab stops. Tabbing from a row therefore moves focus to that row's own sparkline, not the next row, and Enter/Space there re-fires setSelectedTicker for the ticker that is already selected — a visual no-op the user reads as 'keyboard activation doesn't work'."
  confirming_evidence:
    - "Live DOM tab-stop enumeration: stops alternate row/svg/row/svg for all 10 rows — 0 AAPL row, 1 recharts-surface, 2 AMZN row, 3 recharts-surface, ..."
    - "Live keystroke replay: after click on AAPL, Tab -> activeElement = svg[role=application,cls=recharts-surface]; Enter -> heading still AAPL; Space -> heading still AAPL; second Tab -> activeElement = div[role=button]; Enter -> heading becomes AMZN"
    - "recharts 3.10.1 source: es6/chart/CartesianChart.js:24 `accessibilityLayer: true` in defaultCartesianChartProps; es6/container/RootSurface.js:45 `tabIndex = hasAccessibilityLayer ? 0 : undefined` and :50 `role = 'application'`; es6/chart/CategoricalChart.js:22/33 always passes a non-null `otherAttributes` so the branch is always taken"
    - "No component in frontend/components passes accessibilityLayer or tabIndex to a Recharts chart (grep: only WatchlistRow.tsx:36 tabIndex={0})"
  falsification_test: "If a single Tab from a focused row landed on the NEXT row's div (not an svg), or if the sparkline svg carried no tabindex, the hypothesis would be dead. Both were checked live and both went the other way."
  fix_rationale: "N/A this session (goal: find_root_cause_only). The causal lever is the extra focusable descendant, not the row's key handler — the handler is correct and does fire."
  blind_spots:
    - "Not verified in the production static export, only in `next dev`. The tabindex comes from Recharts' runtime default, not a dev-only path, so it is expected to be identical — but unverified."
    - "Not verified in Firefox/Safari. Chromium (153) was used. SVG tabindex focusability is standard in all modern engines."
    - "Whether the user was tabbing forward only; Shift+Tab has the mirror-image problem (lands on the previous row's sparkline) but was not replayed."
  candidate_causes:
    - "code: Sparkline.tsx renders a Recharts LineChart inside the focusable row without disabling the chart's own accessibility/focus layer (PRIMARY)"
    - "config/dependency: recharts 3.x flipped `accessibilityLayer` to default true (it defaulted false in 2.x), so a chart that was a passive graphic under the 2.x mental model is now an interactive widget (CONTRIBUTING — this is why nobody wrote a defence against it)"
    - "data: the sparkline only mounts a chart once >=1 price point has streamed, so the extra tab stop does not exist at t=0 (CONTRIBUTING — explains why an immediate post-load tab test passes and the defect only shows after prices arrive)"
    - "environment: dev vs static export — RULED OUT by source; the tabIndex is emitted by recharts' shipped runtime, not by a dev-only code path"
  and_gate: "Yes, weakly — three conditions coincide: (1) recharts 3.x default accessibilityLayer=true, (2) the chart is a DOM *descendant* of the focusable row rather than a sibling, and (3) at least one price point has arrived so the chart is mounted. Condition (2) is what turns a merely-extra tab stop into one that swallows the activation: Enter on it bubbles back to the SAME row's handler and re-selects the already-selected ticker, producing zero visible change instead of an obvious wrong-target error. Removing any one of the three restores correct single-Tab behaviour; (1) is the practical fix point."

## Symptoms

expected: Click a watchlist row, then Tab to another row and press Enter/Space. Main chart panel heading becomes the ticker; chart shows axes, hover crosshair and tooltip, end dot and end label; selected row tint shows; keyboard activation works.
actual: "keyboard activation doesn't work, the little graph of stocks in watchlist is broken" (sparkline half tracked separately as G-04-2b)
errors: none reported
reproduction: Test 2 in .planning/phases/04-portfolio-visualization/04-UAT.md
started: discovered during UAT immediately after phase 04 execution (plan 04-02 introduced role=button/tabIndex=0 on WatchlistRow)
environment: `next dev` on :3000 (dev build, React StrictMode) against FastAPI on :8000, real browser. Not the static export.

## Eliminated

- hypothesis: "The row's onKeyDown handler is wrong (missing key, wrong casing, missing preventDefault)"
  evidence: Handler tests `event.key === "Enter" || event.key === " "`, calls preventDefault then setSelectedTicker — correct. Live replay proves it DOES fire and select correctly once focus is genuinely on a row div (step 6: Enter on the AMZN row changed the heading to AMZN).
  timestamp: 2026-09-22T01:25:00Z

- hypothesis: "ChartSelectionContext / provider wiring is broken so setSelectedTicker never reaches MainChart"
  evidence: Mouse click on the same row selects and charts the ticker through the identical setSelectedTicker call; keyboard Enter on a row div also works (step 6). The state channel is sound.
  timestamp: 2026-09-22T01:25:00Z

- hypothesis: "Rows remount on every 500ms SSE tick (unstable key / inline component), destroying focus"
  evidence: WatchlistPanel.tsx:88 keys rows by `entry.ticker` (stable); WatchlistRow is a module-level component. Live replay held focus across many seconds of streaming ticks — activeElement survived between keystrokes.
  timestamp: 2026-09-22T01:30:00Z

- hypothesis: "Dev-only artefact (React StrictMode double-mount, or Next dev overlay swallowing keys)"
  evidence: The tabindex is emitted by recharts' own shipped runtime (es6/container/RootSurface.js), gated only on the accessibilityLayer root prop — no dev/prod branch. StrictMode affects mount-time effects only, and focus persisted across ticks.
  timestamp: 2026-09-22T01:35:00Z

- hypothesis: "The sparklines themselves are failing to render (G-04-2b as an independent rendering bug)"
  evidence: Differential screenshots of the same AAPL row: unfocused = correct red line with end marker; sparkline-focused = same line plus a heavy white rounded-rect focus ring that visually reads as an empty broken box. Live DOM: 12 recharts-surface elements present, first sparkline path has 13 points, svg box 114x20. The drawing is fine — the *focus ring* is what looks broken.
  timestamp: 2026-09-22T01:40:00Z

## Evidence

- timestamp: 2026-09-22T01:00:00Z
  checked: frontend/components/watchlist/WatchlistRow.tsx
  found: row div has role="button", tabIndex={0}, onClick -> setSelectedTicker, onKeyDown handling "Enter" and " " with preventDefault. Between the ticker span and the price cells it renders `<Sparkline ticker={entry.ticker} />` as a descendant.
  implication: handler body is correct; the row's own children are the place to look for focus interference.

- timestamp: 2026-09-22T01:00:00Z
  checked: frontend/lib/chartSelection.tsx
  found: plain React context over useState<string | null>. No memoization issue that affects correctness.
  implication: selection plumbing is sound; not the cause.

- timestamp: 2026-09-22T01:05:00Z
  checked: frontend/components/watchlist/WatchlistPanel.tsx
  found: rows keyed by `entry.ticker`; WatchlistRow is a stable module-level component; the panel refetches only on `watchlistRevision`.
  implication: no per-tick remount, so focus loss by remount is excluded.

- timestamp: 2026-09-22T01:10:00Z
  checked: frontend/components/charts/Sparkline.tsx
  found: renders `<ResponsiveContainer><LineChart ...>` once `series.length > 0`; passes no `accessibilityLayer`, no `tabIndex`, no `role` to the chart. Wrapper div carries role="img".
  implication: the chart is left on Recharts' defaults — and it is nested inside the focusable row.

- timestamp: 2026-09-22T01:12:00Z
  checked: frontend/node_modules/recharts/es6/chart/CartesianChart.js, container/RootSurface.js, chart/CategoricalChart.js, context/accessibilityContext.js (recharts 3.10.1, pinned ^3.10.1 in package.json)
  found: CartesianChart.js:24 `accessibilityLayer: true` in defaultCartesianChartProps. useAccessibilityLayer() returns `state.rootProps.accessibilityLayer ?? true`. RootSurface.js:40-51 — when otherAttributes is non-null and no numeric tabIndex was supplied, `tabIndex = hasAccessibilityLayer ? 0 : undefined` and `role = 'application'`. CategoricalChart.js:22/33 always supplies `otherAttributes: svgPropertiesNoEvents(others)` (an object, never null).
  implication: EVERY Recharts cartesian chart in this app emits a focusable `<svg tabindex="0" role="application">` unless it opts out. For Sparkline that svg is a descendant of the row.

- timestamp: 2026-09-22T01:14:00Z
  checked: frontend/node_modules/recharts/es6/chart/RechartsWrapper.js:269-275, 352
  found: the wrapper div attaches onFocus/onBlur/onKeyDown that dispatch focusAction/blurAction/keyDownAction into Recharts' redux store (keyboardEventsMiddleware handles ArrowLeft/ArrowRight/Enter for its own tooltip cursor).
  implication: Recharts intends the chart to be an interactive keyboard widget — it is behaving as designed; the app just never asked it not to.

- timestamp: 2026-09-22T01:20:00Z
  checked: live page http://localhost:3000 via Chrome DevTools Protocol (headless chromium 153), after ~9s of SSE, enumerating `a[href],button,input,select,textarea,[tabindex]:not([tabindex="-1"])` in DOM order
  found: tab stops alternate exactly — 0 `<div role=button tabindex=0>` "AAPL...", 1 `<svg role=application tabindex=0 class="recharts-surface">`, 2 `<div role=button>` "AMZN...", 3 `<svg role=application>`, ... through all 10 rows (20 stops), then the trade inputs/buttons, then stop 24 the Portfolio Value chart's own `<svg role=application tabindex=0>`.
  implication: CONFIRMED — 2 tab stops per row, the second being the row's own sparkline. 10 extra unwanted tab stops in the watchlist alone, plus one per standalone chart panel.

- timestamp: 2026-09-22T01:28:00Z
  checked: live keystroke replay of the UAT flow (real CDP mouse + key events), reading the chart heading and document.activeElement after each step
  found: |
    STEP 1 click AAPL row  -> heading "AAPL", activeElement div[role=button]
    STEP 2 Tab             -> activeElement svg[role=application,cls=recharts-surface]   (still inside the AAPL row)
    STEP 3 Enter           -> heading STILL "AAPL"   <-- the reported failure
    STEP 4 Space           -> heading STILL "AAPL"   <-- the reported failure
    STEP 5 Tab (2nd)       -> activeElement div[role=button]  (the AMZN row)
    STEP 6 Enter           -> heading "AMZN"          (works)
  implication: exact reproduction of "keyboard activation doesn't work". It is not dead — it needs TWO Tabs per row, and the first Enter/Space after one Tab is a silent no-op because it re-selects the ticker that is already selected.

- timestamp: 2026-09-22T01:40:00Z
  checked: differential screenshots of the AAPL row — unfocused vs row-focused vs sparkline-focused (CDP Page.captureScreenshot, same clip)
  found: unfocused = clean red sparkline with end marker. Row-focused = a white ring around the WHOLE row (a good, legible focus indicator). Sparkline-focused = a heavy white rounded-rect ring drawn tightly around the 114x20 sparkline, which reads as an empty white-outlined box. Computed style on the focused svg: `outline: auto 5px`.
  implication: RELATES TO G-04-2b — the same extra tab stop is the most likely cause of "the little graph of stocks in watchlist is broken". The user saw it while performing the Tab test in Test 2; the sparkline drawing itself is provably correct (13-point path, correct colour, end dot) the moment focus leaves it.

- timestamp: 2026-09-22T01:42:00Z
  checked: .planning/phases/04-portfolio-visualization/04-02-PLAN.md lines 305-311
  found: the plan's automated gate was `grep -c "tabIndex"` on WatchlistRow.tsx (passes trivially), and its human check said "Tab to a watchlist row and press Enter" — tabbing INTO the watchlist from outside lands on a row and works. Only tabbing BETWEEN rows (what 04-UAT Test 2 asks for) exposes the defect.
  implication: the gap was invisible to both gates by construction, not by oversight in execution.

## Resolution

root_cause: |
  Recharts 3.x turns every cartesian chart into a focusable keyboard widget by default
  (`defaultCartesianChartProps.accessibilityLayer = true` in
  node_modules/recharts/es6/chart/CartesianChart.js:24), which makes
  container/RootSurface.js render the chart's root element as
  `<svg tabindex="0" role="application">`. `frontend/components/charts/Sparkline.tsx`
  renders such a chart and never opts out, and that chart is a DOM *descendant* of the
  focusable `WatchlistRow` div. Every watchlist row therefore contains two tab stops:
  the row itself and, immediately after it, the row's own sparkline.

  Consequence for the user's exact flow: after clicking a row, one Tab moves focus to
  THAT row's sparkline rather than to the next row. Enter/Space there bubbles back to
  the same row's onKeyDown and calls setSelectedTicker with the ticker that is already
  selected — so nothing changes on screen and keyboard activation appears dead. A second
  Tab reaches the next row, where Enter/Space works correctly.

  Contributing conditions (AND-gate): the chart must be a descendant of the focusable
  row (otherwise the stray stop would be an obvious wrong-target rather than a silent
  no-op), and at least one price point must have streamed (Sparkline renders a plain
  div, with no tab stop, while `series.length === 0`).

  Related to G-04-2b: when that sparkline svg takes focus, Chrome paints its `outline: auto`
  ring tightly around the 114x20 chart, producing an empty white-outlined box where the
  mini graph was. Differential screenshots show the sparkline renders correctly the
  instant focus leaves it, so the same extra tab stop most likely explains the
  "little graph ... is broken" half of the same report.

fix: not applied (goal: find_root_cause_only)
verification: not applicable — diagnose-only session
files_changed: []
