---
phase: 04-portfolio-visualization
plan: 06
subsystem: ui
tags: [recharts, treemap, heatmap, svg, text-fit, gap-closure]

# Dependency graph
requires:
  - phase: 04-portfolio-visualization
    provides: PortfolioHeatmap.tsx treemap component with diverging fill and drop-order label rules (04-03)
provides:
  - "labelFits() text-fit gate replacing fixed-width rectangle thresholds in the heatmap tile renderer"
  - "Corrected PCT_MIN_HEIGHT (36, derived) and a structural percentage-requires-ticker drop order"
affects: [04-portfolio-visualization, ui-review]

# Actuals (#2632)
actuals:
  tokens: 1170
  tasks: 2
  commits: 2

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Text-fit label gating: gate SVG label visibility on `label.length * measuredGlyphAdvance` vs. inset-adjusted tile width, not a fixed rectangle constant"
    - "Structural drop-order dependency: a lower-priority label's visibility boolean is AND-ed with the higher-priority label's own visibility boolean, so spec'd drop order holds regardless of relative string lengths"

key-files:
  created: []
  modified:
    - frontend/components/charts/PortfolioHeatmap.tsx

key-decisions:
  - "Per-glyph advance constants (7 for ticker, 6 for percentage) pinned to the TOP of the measured live ranges (6.0-7.0px / 5.1-5.7px) rather than the middle, per plan: an estimate erring low would let text overflow its tile, which the UI-SPEC forbids outright"
  - "labelFits() is a plain arithmetic estimate, not a DOM measurement (getComputedTextLength + ref + re-render) — the plan explicitly rejected the measure-then-redraw approach as disproportionate to the defect; enforced by a negative grep"
  - "PCT_MIN_HEIGHT corrected 42 -> 36 with its derivation now recorded in comment (inset + second baseline + 10px glyph descender); TICKER_MIN_HEIGHT deliberately left at 26 since no observed tile ever failed on it"
  - "showPct now requires showTicker as a structural AND, not just a stricter numeric threshold — closes the theoretical case where a short percentage could clear its own bar while a longer ticker on the same tile misses its own"

patterns-established:
  - "When a spec defines an ordered fallback (drop A before B), encode the order as a boolean AND-chain between the two visibility flags rather than relying on the two threshold pairs happening to stay in the right relative order"

requirements-completed: [UI-04]

coverage:
  - id: D1
    description: "Heatmap tile labels are gated by labelFits() (measured-glyph text-fit test) instead of fixed TICKER_MIN_WIDTH/PCT_MIN_WIDTH pixel constants; the reported 60x158px 27.5%-weight tile now shows its percentage"
    requirement: "UI-04"
    verification:
      - kind: other
        ref: "grep -c labelFits frontend/components/charts/PortfolioHeatmap.tsx (== 3, both gates + definition) and ! grep -qE PCT_MIN_WIDTH|TICKER_MIN_WIDTH (constants removed)"
        status: pass
      - kind: other
        ref: "npm --prefix frontend run typecheck && lint && build"
        status: pass
    human_judgment: true
    rationale: "The actual visual claim (a specific narrow tile now shows its percentage at real browser widths) needs a running app and human eyes on the rendered SVG; the plan's own <verify> block specifies this as a human-check step, not an automatable one."
  - id: D2
    description: "PCT_MIN_HEIGHT corrected from 42 to 36 with its vertical-need derivation recorded in comment; TICKER_MIN_HEIGHT unchanged at 26 with the reason recorded"
    requirement: "UI-04"
    verification:
      - kind: other
        ref: "grep -nE 'PCT_MIN_HEIGHT[[:space:]]*=[[:space:]]*36' and 'TICKER_MIN_HEIGHT[[:space:]]*=[[:space:]]*26' in PortfolioHeatmap.tsx"
        status: pass
    human_judgment: false
  - id: D3
    description: "Percentage visibility is structurally dependent on ticker visibility (showPct = showTicker && ...), so the UI-SPEC's percentage-then-ticker drop order cannot be inverted by a short percentage clearing its own bar on a tile whose longer ticker misses its own"
    requirement: "UI-04"
    verification:
      - kind: other
        ref: "code inspection: `const showPct = showTicker && labelFits(pctLabel, ...) && height >= PCT_MIN_HEIGHT;` in PortfolioHeatmap.tsx Tile()"
        status: pass
    human_judgment: true
    rationale: "Structural correctness is verifiable by reading the boolean expression, but the plan's <verify> block also asks a human to step through six browser widths (1920 down to 1152px) and visually confirm the degrade order and that no percentage ever appears without its ticker — that is a rendering judgment call, not something a grep can assert."
  - id: D4
    description: "No regression to tile geometry, diverging fill, contrast-switching ink colour, tooltip content, or the four loading/error/empty/populated state branches"
    requirement: "UI-04"
    verification:
      - kind: other
        ref: "negative greps for current_price|avg_cost|quantity (no re-derivation), dangerouslySetInnerHTML (none), plus positive greps for divergingFill|tileTextColor (>=2), Weight (>=1), and the three state-branch strings"
        status: pass
    human_judgment: false

duration: 12min
completed: 2026-09-22
status: complete
---

# Phase 4 Plan 6: Heatmap Tile Label Text-Fit Gate Summary

**Replaced the heatmap's fixed-pixel label thresholds with a measured-glyph text-fit test (`labelFits()`), corrected `PCT_MIN_HEIGHT` to its derived value, and made the percentage-then-ticker drop order structural — closing G-04-3 where a 27.5%-weight tile showed no percentage despite having room for it.**

## Performance

- **Duration:** 12 min
- **Started:** 2026-09-22T13:30:00+03:00 (approx, from prior commit timestamp)
- **Completed:** 2026-09-22T13:38:10+03:00
- **Tasks:** 2 completed
- **Files modified:** 1

## Accomplishments
- Deleted `TICKER_MIN_WIDTH`/`PCT_MIN_WIDTH` fixed-pixel width gates and replaced both with a shared `labelFits()` helper that compares the actual string's length (times a measured per-glyph advance) against the tile's inset-adjusted width — closing the reported failure where a 60x158px tile at 27.5% weight showed its ticker but no percentage.
- Sourced the two per-glyph advance constants (7 for ticker glyphs, 6 for percentage glyphs) from the live `getComputedTextLength()` measurements already captured in the debug session, pinned to the top of each measured range so the estimate can only err toward an early drop, never an overflow.
- Corrected `PCT_MIN_HEIGHT` from an unexplained 42 to a derived 36 (inset + second-line baseline + glyph descender), and made the percentage's visibility structurally require the ticker's visibility so the spec'd drop order (percentage first, then ticker) can never be inverted by a short percentage clearing a bar a longer ticker misses.

## Task Commits

Each task was committed atomically:

1. **Task 1: Gate each label on the text it is actually drawing, not on a rectangle** - `08db830` (fix)
2. **Task 2: Keep the drop rule honest at the narrow end — right height, right order** - `aa736c0` (fix)

**Plan metadata:** (this commit, docs)

## Files Created/Modified
- `frontend/components/charts/PortfolioHeatmap.tsx` - Replaced fixed-width label gates with `labelFits()` text-fit test; corrected `PCT_MIN_HEIGHT`; made percentage visibility structurally depend on ticker visibility

## Decisions Made
- Per-glyph advance constants pinned to the top of the measured range (7px ticker, 6px percentage), not the middle, per the plan's explicit reasoning: under-reporting risks overflow, which the UI-SPEC forbids; over-reporting only costs an occasional early (but still spec-compliant) drop.
- Kept `TICKER_MIN_HEIGHT` at 26 unchanged — the debug session found no tile ever failed on it, and the plan explicitly flagged changing it as unjustified churn.
- Split the plan's two tasks into two separate commits even though both touch the same file and same `Tile()` function, per the executor's per-task atomic-commit contract — Task 1 left `PCT_MIN_HEIGHT` at its pre-existing 42 and the two visibility booleans independent; Task 2 then applied the height correction and the structural dependency on top.

## Deviations from Plan

None — plan executed exactly as written. Both tasks' acceptance criteria and automated `<verify>` checks (typecheck, lint, build, and all grep assertions) passed on the first attempt with no auto-fixes needed.

The plan's `<human-check>` verify steps (visually confirming label appearance/degradation across six browser viewport widths with a running backend and live positions) were not executed in this autonomous run — they require an interactively running app and human visual judgment, which this executor context does not provide. These are captured in the `coverage:` block above with `human_judgment: true` for `/gsd-verify-work` to route to the user.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness

The heatmap's label visibility logic is now text-fit-driven with a corrected, derived height threshold and a structurally-enforced drop order. `frontend/components/charts/PortfolioHeatmap.tsx`'s tile geometry, fill, tooltip, and the four state branches (loading/error/empty/populated) are unchanged and re-verified by negative/positive greps.

Remaining human verification: confirm at real browser widths (1920 down through 1152px, per the plan's human-check steps) that (a) the originally-reported NVDA-style tile now shows its percentage, and (b) the degrade order (percentage first, then ticker) holds visually with no overlap or mid-character clipping. Ready for 04-07.

---
*Phase: 04-portfolio-visualization*
*Completed: 2026-09-22*

## Self-Check: PASSED

- FOUND: frontend/components/charts/PortfolioHeatmap.tsx
- FOUND: SUMMARY.md (this file)
- FOUND: commit 08db830 (Task 1)
- FOUND: commit aa736c0 (Task 2)
