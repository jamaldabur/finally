---
phase: "4"
slug: "portfolio-visualization"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: true
created: "2026-09-21"
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | **None configured in `frontend/`** — no jest/vitest/@testing-library, and no `*.test.*`/`*.spec.*` outside `node_modules` [VERIFIED in 04-RESEARCH.md §Validation Architecture]. Consistent with Phase 2 and Phase 3, which also shipped frontend-only work with no frontend test files. |
| **Config file** | none — and none is installed this phase (see Wave 0 Requirements) |
| **Quick run command** | `npm --prefix frontend run typecheck && npm --prefix frontend run lint` |
| **Full suite command** | `npm --prefix frontend run typecheck && npm --prefix frontend run lint && npm --prefix frontend run build` |
| **Estimated runtime** | ~40-70 seconds for the full command (the `next build` static export dominates) |
| **Backend framework (unaffected)** | pytest 8.x, `backend/tests/` — this phase makes **no backend change**, so there is no backend test obligation. `GET /api/portfolio/history` is consumed as-is, unmodified since Phase 1. |

**Why no test framework is added this phase.** Introducing Vitest/Jest + React Testing Library
(plus `EventSource`/SSE fixtures and Recharts SVG assertions) is a substantial scope addition
beyond UI-02..05, and `TEST-04` already owns exactly that work in **Phase 6** per
`REQUIREMENTS.md`'s traceability table. Adding partial infrastructure now would be duplicated or
reworked there. This is the researcher's recommendation, accepted by the planner rather than
silently inherited.

**What replaces it.** Because no behavioural assertion is available, every task in this phase
carries a *structural* automated gate — `typecheck` + `lint` + `build` plus targeted greps that
assert the specific wiring, locked copy, and prohibited patterns each task is responsible for
(for example: exactly one `new EventSource(`, the 500-point cap constant both declared and
applied, the locked empty-state strings, no raw-HTML injection under `frontend/components/charts/`,
no curve interpolation on the snapshot line). Each `<automated>` command carries a `<fails_when>`
naming its failure signal. Rendered-pixel behaviour is covered by a per-task `<human-check>` and
by `/gsd-verify-work` at the phase gate.

---

## Sampling Rate

- **After every task commit:** `npm --prefix frontend run typecheck && npm --prefix frontend run lint`, plus that task's greps
- **After every plan wave:** `npm --prefix frontend run typecheck && npm --prefix frontend run lint && npm --prefix frontend run build`, plus the wave's `<human-check>` walkthrough against a running backend
- **Before `/gsd-verify-work`:** full command green and the static export present at `frontend/out/index.html`
- **Max feedback latency:** ~70 seconds (no task in this phase is more than one command away from a red signal)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | UI-02 | T-04-02 / T-04-SC | Buffer bounded at 500 points per ticker; only the audited `recharts` package is installed, pinned in the committed lockfile | structural (typecheck/lint/build + grep) | `npm --prefix frontend run typecheck && npm --prefix frontend run lint && npm --prefix frontend run build` | ✅ | ⬜ pending |
| 04-01-02 | 01 | 1 | UI-02 | T-04-01 | Accessible name built by interpolation; no raw-HTML injection anywhere under `frontend/components/charts/` | structural + human-check | `grep -rl "dangerouslySetInnerHTML" frontend/components/charts \| wc -l` | ✅ | ⬜ pending |
| 04-02-01 | 02 | 2 | UI-03 | T-04-05 | Chart trend colour derives only from the shared `trendDirection()` against `firstPrices`, so it cannot contradict the row's own figure | structural | `npm --prefix frontend run typecheck && npm --prefix frontend run lint && npm --prefix frontend run build` | ✅ | ⬜ pending |
| 04-02-02 | 02 | 2 | UI-03 | T-04-04 | All chart text rendered as JSX/prop-driven text; no raw-HTML injection | structural + human-check | `grep -rl "dangerouslySetInnerHTML" frontend/components/charts \| wc -l` | ✅ | ⬜ pending |
| 04-03-01 | 03 | 3 | UI-04 | T-04-07 | Tile geometry and fill read only server-computed `market_value`/`pct_change`; component never touches a per-share price, cost basis, or quantity | structural | `! grep -vE "^\s*(//\|\*\|/\*)" frontend/components/charts/PortfolioHeatmap.tsx \| grep -qE "current_price\|avg_cost\|quantity"` | ✅ | ⬜ pending |
| 04-03-02 | 03 | 3 | UI-04 | T-04-08 | Tile labels and tooltip text are SVG/JSX children; no truncation hiding a value; no raw-HTML injection | structural + human-check | `npm --prefix frontend run typecheck && npm --prefix frontend run lint && npm --prefix frontend run build` | ✅ | ⬜ pending |
| 04-04-01 | 04 | 4 | UI-05 | T-04-10 | Store applies no sort/filter/slice/reverse to recorded snapshots; one shared 30s poll | structural | `! grep -vE "^\s*(//\|\*\|/\*)" frontend/lib/portfolioHistoryStore.tsx \| grep -qE "\.sort\(\|\.filter\(\|\.slice\(\|\.reverse\("` | ✅ | ⬜ pending |
| 04-04-02 | 04 | 4 | UI-05 | T-04-10 / T-04-11 | No curve interpolation on the snapshot line (no drawn value between recorded points); no raw-HTML injection | structural + human-check | `! grep -vE "^\s*(//\|\*\|/\*)" frontend/components/charts/PnlHistoryChart.tsx \| grep -qE "Legend\|type=\"(monotone\|basis\|natural\|cardinal)\""` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Sampling continuity:** every one of the eight tasks carries at least one runnable `<automated>`
command with a `<fails_when>` sibling — there is no run of three consecutive tasks without an
automated gate, and no task relies on a `MISSING — Wave 0` sentinel.

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements.* No test scaffold is missing and none is
created: the `typecheck` / `lint` / `build` scripts already exist in `frontend/package.json`
(lines 9-10) and are the commands Phase 2 and Phase 3 verified against. Behavioural frontend
tests are deliberately deferred to **Phase 6 / TEST-04**, per the justification above — this is a
recorded phase-scope decision, not an unfilled gap.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Sparkline draws, extends, and colour-matches its row's change-% figure; 0-point and 1-point rows do not blank or reflow | UI-02 | Requires a live SSE stream and rendered pixels; no frontend test framework exists this phase | `04-01-PLAN.md` Task 2 `<human-check>` — watch the watchlist for ~1 minute from first paint |
| Clicking/keyboard-activating a row swaps the main chart; axis labels are not clipped inside `h-72` | UI-03 | Rendered-geometry question with no prior chart in the codebase to measure against (04-RESEARCH.md Open Question 2, Pitfall 3) | `04-02-PLAN.md` Task 2 `<human-check>` steps 2 and 6 |
| Tile area tracks holding size; fill pales/saturates with P&L and caps at ±10%; labels drop in order; no React DOM warnings from the SVG tree | UI-04 | Visual proportion and colour judgement; DOM-warning check needs a browser console | `04-03-PLAN.md` Task 2 `<human-check>` steps 2-8 |
| P&L line renders only after 2 snapshots; panel never flashes loading copy on the 30s refresh; panels are equal width and height | UI-05 | Requires elapsed wall-clock time against a running backend | `04-04-PLAN.md` Task 2 `<human-check>` steps 1, 5 and 6 |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (none exist — no sentinel used)
- [x] No watch-mode flags
- [x] Feedback latency < 70s
- [ ] `nyquist_compliant: true` set in frontmatter — **withheld**: the automated layer in this
      phase is structural (type/lint/build + targeted greps), not behavioural. Every UI-02..05
      behaviour is sampled, but four of them are sampled by a human check rather than by an
      assertion, so the phase is honestly PARTIAL until Phase 6 / TEST-04 lands frontend test
      infrastructure. Do not flip this flag without real component tests.

**Approval:** pending
