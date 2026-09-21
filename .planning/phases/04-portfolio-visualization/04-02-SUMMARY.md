---
phase: 04-portfolio-visualization
plan: 02
subsystem: frontend
tags: [recharts, main-chart, selection, watchlist]
requires: [04-01]
provides:
  - useChartSelection() / ChartSelectionProvider
  - MainChart component in centre column
affects: [04-03, 04-04]
tech-stack:
  added: []
  patterns: [selection as innermost context; centre column as stacked bordered panels]
key-files:
  created:
    - frontend/lib/chartSelection.tsx
    - frontend/components/charts/MainChart.tsx
  modified:
    - frontend/app/layout.tsx
    - frontend/app/page.tsx
    - frontend/components/watchlist/WatchlistRow.tsx
decisions:
  - Selection is a context mounted innermost in layout
  - Main chart has no loading/error state (synchronous client state)
metrics:
  tasks: 2
  completed: 2026-09-22
status: complete
commits: 2
plan_head_before: 3cb0b805963e5a55fc94ceaa1185d6272759cdb5
actuals:
  tokens: 5000
  tasks: 2
  commits: 2
requirements: [UI-03]
---

# Phase 4 Plan 2: Main Chart Summary

Clicking (or Enter/Space on) a watchlist row selects the ticker and draws its accumulated series from the shared priceHistory buffer in a larger Recharts chart with axes, tooltip crosshair, end dot with surface ring and a neutral-coloured end price label.

## Tasks

| Task | Commit | Result |
| ---- | ------ | ------ |
| 1 (tracer) | 8b66844 | selection context, MainChart, clickable row, stacked centre column |
| 2 | 374797c | three locked states, axes/tooltip/end marker/label, keyboard activation |

## Verification

typecheck, lint, build pass; `frontend/out/index.html` emitted. The human-check (visual, hover, keyboard) was not performed by this agent and remains for UAT, including axis-band clipping inside h-72.

## Deviations from Plan

None - plan executed as written.

## Known Stubs

None.

## Threat Flags

None.

## Self-Check: PASSED
