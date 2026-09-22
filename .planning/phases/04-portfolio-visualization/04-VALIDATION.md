---
phase: "4"
slug: "portfolio-visualization"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
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
| 04-05-01 | 05 | 3 (gap closure) | UI-02 / UI-03 | G-04-2a | Sparkline opts out of Recharts' keyboard layer (`accessibilityLayer={false}`); watchlist row remains the sole tab stop | structural + human-check (**confirmed live** — user verified Tab/Enter/Space traversal, ✅ 4831c6c) | `npm --prefix frontend run typecheck && lint && build` + grep for `accessibilityLayer={false}`/`role="img"`/absence of `tabIndex` | ✅ | ✅ green |
| 04-05-02 | 05 | 3 (gap closure) | UI-02 / UI-03 | G-04-2b | MainChart/PnlHistoryChart keep a focusable surface with a themed `:focus-visible` ring; PortfolioHeatmap confirmed structurally non-focusable | structural + human-check (deferred to end-of-phase UAT, SUMMARY coverage `D9`) | `npm --prefix frontend run typecheck && lint && build` + grep for the one focus-ring rule, correct token/offset, no accent hue | ✅ | ✅ green |
| 04-06-01 | 06 | 4 (gap closure) | UI-04 | G-04-3 | Heatmap label visibility gated on measured text extent (`labelFits`) against real tile insets, not a fixed-width constant | structural + human-check (deferred to end-of-phase UAT, SUMMARY coverage `D1`/`D3`) | `npm --prefix frontend run typecheck && lint && build` + grep for `labelFits`/`TILE_INSET`/`formatPercent`, absence of `PCT_MIN_WIDTH`/`TICKER_MIN_WIDTH`/truncation patterns | ✅ | ✅ green |
| 04-06-02 | 06 | 4 (gap closure) | UI-04 | G-04-3 | `PCT_MIN_HEIGHT` corrected to the real two-line label need; percentage visibility structurally requires ticker visibility (drop order can't invert) | structural | `npm --prefix frontend run typecheck && lint && build` + grep asserting `PCT_MIN_HEIGHT=36`/`TICKER_MIN_HEIGHT=26` and the `showPct`⇒`showTicker` dependency | ✅ | ✅ green |
| 04-07-01 | 07 | 5 (gap closure) | UI-05 | G-04-4 | Snapshot read bounded to a validated, most-recent window (`rowid DESC LIMIT` + reversed); route param validated `1..MAX_SNAPSHOT_LIMIT` via FastAPI `Query()` | **behavioral (TDD, RED→GREEN)** — real pytest coverage, not structural-only | `cd backend && uv run pytest tests/db/test_portfolio_snapshots.py tests/routes/test_portfolio.py -q` (9 new tests; full suite 224/224 green) | ✅ | ✅ green |
| 04-07-02 | 07 | 5 (gap closure) | UI-05 | G-04-4 | Frontend requests a bounded, display-sized window (`HISTORY_POINT_LIMIT=180`); all Plan 04-04 store invariants preserved | structural | `npm --prefix frontend run typecheck && lint && build` + grep for `limit`/`HISTORY_POINT_LIMIT`/preserved poll invariants | ✅ | ✅ green |
| 04-07-03 | 07 | 5 (gap closure) | UI-05 | G-04-4 | Portfolio Value line placed on a real time-scaled X axis (`type="number" scale="time"`) instead of categorical index spacing | structural + human-check (deferred to end-of-phase UAT, SUMMARY coverage `D3`) | `npm --prefix frontend run typecheck && lint && build` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Gap-closure addendum (04-05/06/07):** All seven gap-closure tasks carry at least the phase's
established structural gate (typecheck/lint/build + targeted greps), consistent with the Wave 0
decision above — no new gap relative to that already-accepted scope. **04-07-01 exceeds it**: its
TDD tracer task shipped genuine behavioral pytest coverage (backend snapshot windowing), the first
non-structural automated test in this phase. This does not by itself satisfy `nyquist_compliant`
phase-wide — the withheld frontend-behavioral gap below is unchanged by these three plans, none of
which added frontend test infrastructure.

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
| MainChart/PnlHistoryChart focus ring renders correctly, click vs. Tab focus distinction holds, arrow-key tooltip navigation works, heatmap never focuses | UI-02 / UI-03 / UI-04 | Visual rendering judgment; no browser available to the executor | `04-05-PLAN.md` Task 2 `<human-check>` (SUMMARY coverage `D9`, `human_judgment: true`) |
| Heatmap tile labels appear/degrade correctly across a 1920→1152px width range with 3+ real positions | UI-04 | Visual proportion judgment across a live-resized viewport; no browser available to the executor | `04-06-PLAN.md` Task 1/2 `<human-check>` (SUMMARY coverage `D1`/`D3`, `human_judgment: true`) |
| Portfolio Value line reads calmer/less busy with the accumulated 5-day history in the live `db/finally.db`, on a real time axis | UI-05 | Visual density/appearance judgment against live accumulated data; no browser available to the executor | `04-07-PLAN.md` Task 3 `<human-check>` (SUMMARY coverage `D3`, `human_judgment: true`) |

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

---

## Validation Audit 2026-09-22

Audited the three gap-closure plans (04-05, 04-06, 04-07) added after phase UAT (`04-UAT.md`:
G-04-2a/2b, G-04-3, G-04-4). All seven of their tasks carry at least the phase's established
structural gate; 04-07's TDD tracer task added genuine behavioral pytest coverage for the backend
snapshot-windowing logic — the first non-structural automated test in this phase.

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
| New behavioral coverage (bonus, not required) | 1 (04-07-01, backend snapshot windowing) |

`nyquist_compliant` remains `false`, unchanged: the four frontend-behavioral manual-only items
above (now seven, with three added by this audit) are still not covered by a frontend test
framework — none of the three gap-closure plans introduced one, consistent with the phase-wide
Phase 6/TEST-04 deferral already on record.
