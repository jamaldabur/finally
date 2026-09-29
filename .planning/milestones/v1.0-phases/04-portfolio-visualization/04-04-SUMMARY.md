---
phase: 04-portfolio-visualization
plan: 04
subsystem: frontend
tags: [recharts, line-chart, polling, portfolio-history]
requires: [04-03]
provides:
  - PortfolioHistoryProvider / usePortfolioHistory (single 30s poll)
  - fetchPortfolioHistory() and SnapshotResponse/PortfolioHistoryResponse types
  - PnlHistoryChart Portfolio Value panel completing the centre-column row
affects: []
key-files:
  created:
    - frontend/lib/portfolioHistoryStore.tsx
    - frontend/components/charts/PnlHistoryChart.tsx
  modified:
    - frontend/lib/types.ts
    - frontend/lib/api.ts
    - frontend/app/layout.tsx
    - frontend/app/page.tsx
decisions:
  - History store passes backend snapshots through untouched (no sort/filter/interpolation)
  - Zero and one snapshot share the not-enough-history copy
metrics:
  tasks: 2
  completed: 2026-09-22
status: complete
commits: 2
plan_head_before: 62889fc
actuals:
  tokens: 6500
  tasks: 2
  commits: 2
requirements: [UI-05]
---

# Phase 4 Plan 4: Portfolio Value History Chart Summary

Portfolio Value line chart fed by a single 30-second polling provider over `GET /api/portfolio/history`, drawing recorded snapshots as-is with axes, tooltip, end dot and neutral end label, plus loading/error/not-enough-history states.

## Tasks

| Task | Commit | Result |
| ---- | ------ | ------ |
| 1 (tracer) | 7bd3aa3 | types, fetchPortfolioHistory, provider in layout, minimal line, panel in page.tsx row |
| 2 | 4d13bae | four-branch state shell, axes, tooltip, end marker and label |

## Verification

typecheck, lint, build pass; `frontend/out/index.html` emitted; no raw-HTML injection under charts. The visual human-check (states, tooltip, 2-minute no-flash watch, backend-down error) was not performed by this agent and remains for UAT.

## Deviations from Plan

None - plan executed as written.

## Known Stubs

None.

## Threat Flags

None.

## Self-Check: PASSED
