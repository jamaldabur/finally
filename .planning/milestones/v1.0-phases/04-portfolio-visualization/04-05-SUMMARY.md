---
phase: 04-portfolio-visualization
plan: 05
subsystem: ui
tags: [react, recharts, accessibility, keyboard-navigation, css, tailwind]

# Dependency graph
requires:
  - phase: 04-01
    provides: Sparkline/MainChart/PnlHistoryChart/PortfolioHeatmap chart components and chartTheme constants
  - phase: 04-02
    provides: WatchlistRow's keyboard activation (role="button", tabIndex={0}, Enter/Space onKeyDown)
provides:
  - Sparkline opts out of Recharts' default accessibility layer (accessibilityLayer={false}), removing the second per-row tab stop that broke keyboard activation
  - One shared `.recharts-surface:focus-visible` CSS rule giving every remaining focusable chart an intentional on-theme ring
  - Recorded, gated decision that MainChart and PnlHistoryChart keep their focusable chart surface (keyboard tooltip access), while PortfolioHeatmap structurally has none
affects: [04-verification, 04-UAT]

# Actuals (#2632)
actuals:
  tokens: 1133
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Global `:focus-visible` styling for a third-party library's internal class name (`.recharts-surface`), matching the existing `.tabular-nums` precedent of one rule reaching every instance instead of a class threaded through each component"
    - "Deliberate accessibility-layer opt-out documented in the component's own module docblock rather than only in a planning doc, so a later reversal fails a grep gate instead of shipping silently"

key-files:
  created: []
  modified:
    - frontend/components/charts/Sparkline.tsx
    - frontend/app/globals.css
    - frontend/components/charts/MainChart.tsx

key-decisions:
  - "Sparkline opts out via accessibilityLayer={false} rather than tabIndex={-1} — the opt-out also removes role=\"application\" and Recharts' keydown middleware, not just the tab stop"
  - "MainChart and PnlHistoryChart deliberately KEEP their focusable chart surface — each is a standalone panel, and Recharts' keyboard middleware is the only route to the hover tooltip's values"
  - "PortfolioHeatmap needed verification, not an edit: Treemap renders through Surface (not RootSurface) and its props type does not accept accessibilityLayer, contradicting G-04-2a's artifact list"
  - "Focus ring implemented as one global .recharts-surface:focus-visible rule (2px solid var(--color-terminal-text), 2px offset) rather than per-component styling, using :focus-visible specifically so mouse clicks never paint the ring"

patterns-established:
  - "A chart component's decision to keep or opt out of Recharts' accessibility layer is recorded in its own docblock, guarded by a negative/positive grep in the plan's verify block, so the decision cannot be silently reversed later"

requirements-completed: [UI-02, UI-03]

coverage:
  - id: D1
    description: "One Tab from a focused watchlist row moves focus to the NEXT row, not back into its own sparkline"
    requirement: "UI-03"
    verification:
      - kind: manual_procedural
        ref: "Task 1 tracer feedback gate human-check (blocking-human) — user response: approved"
        status: pass
    human_judgment: true
    rationale: "Keyboard focus traversal order across DOM elements can only be confirmed by an interactive session with the dev server running; verified via Task 1's blocking-human tracer gate and approved by the user in this continuation's prior_agent_state, not by an automated DOM test."
  - id: D2
    description: "Enter or Space on the newly focused row selects its ticker and the main chart heading changes to it"
    requirement: "UI-03"
    verification:
      - kind: manual_procedural
        ref: "Task 1 tracer feedback gate human-check (blocking-human) — user response: approved"
        status: pass
    human_judgment: true
    rationale: "Same interactive keyboard session as D1; no automated test asserts this end-to-end behavior."
  - id: D3
    description: "Sparkline's LineChart passes accessibilityLayer={false}; the chart root carries no tabindex/role=\"application\", so it is not focusable"
    requirement: "UI-02"
    verification:
      - kind: other
        ref: "grep -c 'accessibilityLayer={false}' frontend/components/charts/Sparkline.tsx (=1); negative grep for 'tabIndex' on the same file (exit 0)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Sparkline still exposes its trend to assistive technology via the wrapper's role=\"img\" and interpolated aria-label"
    requirement: "UI-02"
    verification:
      - kind: other
        ref: 'grep -c ''role="img"'' frontend/components/charts/Sparkline.tsx (=1)'
        status: pass
    human_judgment: false
  - id: D5
    description: "WatchlistRow's role=\"button\", tabIndex={0} and Enter/Space onKeyDown are unmodified by this plan"
    verification:
      - kind: other
        ref: "grep -cE 'role=\"button\"|tabIndex=\\{0\\}|onKeyDown' frontend/components/watchlist/WatchlistRow.tsx (=3)"
        status: pass
    human_judgment: false
  - id: D6
    description: "MainChart keeps Recharts' default focusable chart surface (passes no accessibility-layer prop); the decision and its rationale are recorded in the component's module docblock"
    verification:
      - kind: other
        ref: "negative grep for 'accessibilityLayer' in frontend/components/charts/MainChart.tsx (exit 0 — absent); npm run typecheck/lint/build all pass"
        status: pass
    human_judgment: false
  - id: D7
    description: "PortfolioHeatmap has no focusable chart surface to opt in or out of: Treemap renders through Surface (not RootSurface) and its props type does not accept accessibilityLayer at all — verified by reading recharts' own Treemap.d.ts/Treemap.js, not by editing the component"
    verification:
      - kind: other
        ref: "grep -n accessibilityLayer frontend/node_modules/recharts/types/chart/Treemap.d.ts (no match); negative grep for 'accessibilityLayer' in frontend/components/charts/PortfolioHeatmap.tsx (exit 0 — absent)"
        status: pass
    human_judgment: false
  - id: D8
    description: "One shared .recharts-surface:focus-visible rule in globals.css: 2px solid outline in var(--color-terminal-text), 2px outline-offset, :focus-visible (not bare :focus), no accent hue spent; pre-existing @theme tokens and .tabular-nums rule untouched"
    verification:
      - kind: other
        ref: "grep -c 'recharts-surface:focus-visible' globals.css (=1); grep for var(--color-terminal-text) and outline-offset within the rule; negative grep for accent-yellow/blue/purple in the rule; tabular-nums and theme-token counts unchanged"
        status: pass
    human_judgment: false
  - id: D9
    description: "Visually: the new focus ring reads intentional on the dark theme and appears only via keyboard focus (never on a mouse click), ArrowRight/ArrowLeft moves MainChart's tooltip while it is focused, and the Portfolio Heatmap never takes focus during Tab traversal"
    verification: []
    human_judgment: true
    rationale: "Requires an interactive keyboard/visual session (distinguishing click-focus from :focus-visible, judging whether the ring 'looks intentional', and confirming arrow-key tooltip movement) that cannot be asserted by grep, typecheck, lint, or build. Task 2 is type=\"auto\" (not a tracer/checkpoint), so per human_verify_mode=end-of-phase this check is deferred to the phase's end-of-phase UAT rather than blocking this plan's completion."

duration: ~15min (Task 2 portion, this continuation session)
completed: 2026-09-22
status: complete
---

# Phase 04 Plan 05: Watchlist keyboard focus and chart focus-ring decisions Summary

**Sparkline opts out of Recharts' keyboard-widget layer (accessibilityLayer={false}) so each watchlist row owns one tab stop again; MainChart/PnlHistoryChart deliberately keep theirs with a new shared on-theme `:focus-visible` ring, and PortfolioHeatmap is verified (not edited) to have no focusable surface at all.**

## Performance

- **Duration:** Task 1 completed in a prior session (tracer gate, approved); Task 2 (this continuation) ~15 min
- **Completed:** 2026-09-22
- **Tasks:** 2/2
- **Files modified:** 3 (`frontend/components/charts/Sparkline.tsx`, `frontend/app/globals.css`, `frontend/components/charts/MainChart.tsx`)

## Accomplishments

- Closed G-04-2a/G-04-2b's shared root cause: Recharts 3.x defaults every cartesian chart to a focusable keyboard widget, and the watchlist sparkline — a DOM descendant of the already-focusable row — was giving each row two tab stops instead of one.
- `Sparkline.tsx`'s `LineChart` now passes `accessibilityLayer={false}`, removing the stray tab stop and its `role="application"` while keeping the wrapper's `role="img"` + interpolated `aria-label` for assistive tech.
- Recorded (not just implied) the decision that `MainChart` and `PnlHistoryChart` keep Recharts' default focusable surface, since each is a standalone panel and arrow-key tooltip navigation is the only keyboard route to their plotted values.
- Verified — via `recharts`' own `Treemap.d.ts`/`Treemap.js` source, not by editing the component — that `PortfolioHeatmap` never had a focusable surface to begin with: `Treemap` renders through `Surface`, not `RootSurface`, and its props type doesn't even accept the opt-out prop.
- Added one shared `.recharts-surface:focus-visible` rule in `globals.css` (2px solid `var(--color-terminal-text)`, 2px offset) replacing the browser's default `outline: auto` ring that read as a broken empty box during UAT, using `:focus-visible` so a mouse click never paints it.

## Task Commits

Each task was committed atomically:

1. **Task 1: Give each watchlist row back its single tab stop — one path, row to row** - `4831c6c` (fix) — completed in a prior session; tracer feedback gate approved by user before this continuation began.
2. **Task 2: Decide and record which charts stay focusable, and give them a ring worth seeing** - `984d42e` (feat)

**Plan metadata:** (this commit, following SUMMARY/STATE/ROADMAP/REQUIREMENTS updates)

## Files Created/Modified

- `frontend/components/charts/Sparkline.tsx` - Opts its `LineChart` out of Recharts' accessibility layer (`accessibilityLayer={false}`); docblock records why (Task 1, prior session)
- `frontend/app/globals.css` - Adds the shared `.recharts-surface:focus-visible` rule (2px solid `var(--color-terminal-text)`, 2px offset), preceded by a comment explaining the one-rule-reaches-every-instance rationale (same pattern as `.tabular-nums`)
- `frontend/components/charts/MainChart.tsx` - Docblock records the deliberate keep-focusable decision and points at the global CSS rule; no JSX change — "keeping the default" means passing nothing

## Decisions Made

- `accessibilityLayer={false}` chosen over `tabIndex={-1}` for the sparkline: the opt-out removes `role="application"` and Recharts' keydown middleware too, not just the tab stop (planner assumption 1, confirmed correct).
- MainChart and PnlHistoryChart keep their focusable chart surface; PortfolioHeatmap needs no code change since `Treemap` structurally never emits a focusable root (verified against `recharts`' own type declarations and ES6 source).
- The focus ring is one global CSS rule targeting Recharts' internal `.recharts-surface` class, matching the project's existing `.tabular-nums` precedent, rather than a class threaded through each chart component.
- `PnlHistoryChart.tsx` intentionally not touched in this plan (owned by sibling gap-closure plan 04-07 in the same wave); the decision needs no code there since "keep the default" means passing nothing, and the global CSS rule reaches it regardless.

## Deviations from Plan

None - plan executed exactly as written (Task 1 in a prior session, Task 2 in this continuation).

## Issues Encountered

- The plan's `<task_commit_protocol>` plan-commit ledger (`gsd-plan-head-before-04-05`) was not found on disk at the start of this continuation session — the prior agent's session apparently did not persist it, or the persisted file was not carried forward. Reconstructed it from `git log` as the parent of Task 1's commit (`4831c6c^` = `df03505`), which correctly measures both of this plan's commits (`COMMITS_ACTUAL=2`) for the `actuals.commits` field below.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Both reported keyboard-activation defects (G-04-2a, G-04-2b) are closed at the code level and gated by automated greps; the remaining interactive confirmations (D1, D2 — already approved by the user for Task 1; D9 — Task 2's visual/keyboard check) are either already signed off or deferred to end-of-phase UAT per `human_verify_mode: end-of-phase`.
- No blockers for sibling wave-5 plans (04-06, 04-07); `PnlHistoryChart.tsx` was deliberately left untouched here for 04-07 to modify without a file conflict.

---
*Phase: 04-portfolio-visualization*
*Completed: 2026-09-22*

## Self-Check: PASSED

- FOUND: frontend/components/charts/Sparkline.tsx
- FOUND: frontend/app/globals.css
- FOUND: frontend/components/charts/MainChart.tsx
- FOUND: .planning/phases/04-portfolio-visualization/04-05-SUMMARY.md
- FOUND commit: 4831c6c
- FOUND commit: 984d42e
