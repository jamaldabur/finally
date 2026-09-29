---
phase: 04-portfolio-visualization
plan: 03
subsystem: frontend
tags: [recharts, treemap, heatmap, diverging-fill]
requires: [04-02]
provides:
  - PortfolioHeatmap component in centre column side-by-side row
  - mixColor / divergingFill / tileTextColor / HEATMAP_CAP_PCT in chartTheme
affects: [04-04]
key-files:
  created:
    - frontend/components/charts/PortfolioHeatmap.tsx
  modified:
    - frontend/components/charts/chartTheme.ts
    - frontend/app/page.tsx
decisions:
  - Diverging formula uses hex twins of the CSS tokens (interpolation needs channel values)
  - Label thresholds 52x26 (ticker) and 64x42 (percent), tunable at UAT
metrics:
  tasks: 2
  completed: 2026-09-22
status: complete
commits: 2
plan_head_before: 4a4875b5d006b8bc5696ebef3b0bd47304979a82
actuals:
  tokens: 6000
  tasks: 2
  commits: 2
requirements: [UI-04]
---

# Phase 4 Plan 3: Portfolio Heatmap Summary

Recharts treemap sizing each position tile by server `market_value` and filling it via one shared diverging formula capped at +/-10%, with weighted hover tooltip, loss-to-gain legend strip and loading/error/empty states.

## Tasks

| Task | Commit | Result |
| ---- | ------ | ------ |
| 1 (tracer) | bbffc41 | diverging helpers, tiles, side-by-side row in page.tsx |
| 2 | 8cfea76 | whole-or-nothing labels, tooltip, legend from mixColor, four-branch shell |

## Verification

typecheck, lint, build pass; `frontend/out/index.html` emitted. The visual human-check was not performed by this agent and remains for UAT (including whether Recharts injects tile geometry through the JSX `content` element as expected, and the label thresholds).

## Deviations from Plan

None - plan executed as written.

## Known Stubs

None.

## Threat Flags

None.

## Self-Check: PASSED
