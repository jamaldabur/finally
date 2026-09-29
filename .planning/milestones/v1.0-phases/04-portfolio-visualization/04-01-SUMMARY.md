---
phase: 04-portfolio-visualization
plan: 01
subsystem: frontend
tags: [recharts, sparkline, sse, price-history]
requires: []
provides:
  - priceHistory buffer in usePriceStore()
  - chartTheme shared constants and trend rule
  - Sparkline component in every watchlist row
affects: [04-02, 04-03, 04-04]
tech-stack:
  added: [recharts ^3.10.1]
  patterns: [single shared SSE handler feeds all chart state; one trend rule in chartTheme]
key-files:
  created:
    - frontend/components/charts/chartTheme.ts
    - frontend/components/charts/Sparkline.tsx
  modified:
    - frontend/lib/priceStore.tsx
    - frontend/components/watchlist/WatchlistRow.tsx
    - frontend/package.json
    - frontend/package-lock.json
decisions:
  - priceHistory lives inside PriceStoreProvider (no second provider)
  - Zero-point baseline is a plain div, not a Recharts render
metrics:
  tasks: 2
  completed: 2026-09-22
status: complete
commits: 2
plan_head_before: 840dcecb880a8da81f479c841c93cc3804248a92
actuals:
  tokens: 6000
  tasks: 2
  commits: 2
requirements: [UI-02]
---

# Phase 4 Plan 1: Watchlist Sparklines Summary

Live per-row sparklines using Recharts, fed by a 500-point-capped price-history buffer accumulated inside the app's single shared SSE handler.

## Tasks

| Task | Commit | Result |
| ---- | ------ | ------ |
| 1 (tracer) | f2b0c1f | recharts installed, chartTheme, priceHistory buffer, Sparkline, row wiring |
| 2 | 6f94bd0 | flat baseline (0 pts), marker-only (1 pt), end dot with surface ring, role=img/aria-label |

## Verification

typecheck, lint and build pass; `frontend/out/index.html` is emitted; exactly one `new EventSource(`. The human-check (visual watch of live rows) was not performed by this agent and remains for UAT.

## Deviations from Plan

**1. [Rule 1 - Bug] Overflow allowed on the LineChart** - the end dot (radius 4 + 2px ring) lies on the data extreme and would be clipped by the 20px SVG with zero margin; added `style={{ overflow: "visible" }}` while keeping zero margin. File: Sparkline.tsx. Commit 6f94bd0.

## Known Stubs

None.

## Threat Flags

None.

## Self-Check: PASSED
