---
phase: "02"
slug: "core-trading-ui"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-09-17"
---

# Phase 02 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | None configured yet for `frontend/` — greenfield. Vitest/React Testing Library are explicitly Phase 6 scope (`TEST-04` per REQUIREMENTS.md traceability), not this phase. |
| **Config file** | none — see Wave 0 |
| **Quick run command** | n/a — manual browser verification for this phase |
| **Full suite command** | n/a |
| **Estimated runtime** | n/a (manual walkthrough, not timed) |

---

## Sampling Rate

- **After every task commit:** Manual browser check against the running `next dev` + backend `uv run uvicorn` pair (no automated frontend test runner exists yet)
- **After every plan wave:** Full manual walkthrough of the phase's 5 success criteria (watchlist flash, buy/sell, positions table, header, dark theme)
- **Before `/gsd-verify-work`:** All 5 PLAN.md-listed success criteria visually/functionally confirmed
- **Max feedback latency:** n/a — this phase uses manual verification, not an automated sampling cadence. Formal automated frontend tests land in Phase 6 (`TEST-04`); do not add a testing-framework task to this phase.

---

## Per-Task Verification Map

Task/Plan/Wave columns are seeded TBD — plans do not exist yet at research time; the planner assigns concrete task IDs when it consumes this file.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | UI-01 | — | Watchlist flashes green/red only on real SSE price change (`price !== previous_price`), never on unchanged heartbeat resend | manual (browser) | — | ❌ Wave 0 | ⬜ pending |
| TBD | TBD | TBD | UI-06 | — | Positions table shows ticker/quantity/avg_cost/current_price/unrealized_pnl/pct_change, staying live | manual (browser) | — | ❌ Wave 0 | ⬜ pending |
| TBD | TBD | TBD | UI-07 | V5 (input validation, defense-in-depth only) | Trade bar buy/sell submits and reflects cash/position update, no confirmation dialog | manual (browser) | — | ❌ Wave 0 | ⬜ pending |
| TBD | TBD | TBD | UI-09 | — | Header shows live total value, cash, connection dot reflecting SSE state | manual (browser) | — | ❌ Wave 0 | ⬜ pending |
| TBD | TBD | TBD | UI-10 | — | Dark trading-terminal theme renders per PLAN.md §2 (colors, density) | manual (visual review) | — | ❌ Wave 0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

No test-framework installation is required this phase. Automated frontend testing (Vitest/React Testing Library) is explicitly Phase 6 scope (`TEST-04` per REQUIREMENTS.md traceability) — the planner must not add a testing-framework task here; this phase is verified by manual browser walkthrough against the 5 PLAN.md success criteria instead.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Watchlist flashes green/red on real SSE price change, not on heartbeat resend | UI-01 | No frontend test framework yet (deferred to Phase 6/`TEST-04`); requires a live SSE stream + visual observation | Run `next dev` + backend `uv run uvicorn`; watch watchlist rows during price ticks; confirm flash triggers only when `price !== previous_price`, never on an unchanged heartbeat |
| Positions table live fields | UI-06 | Same — visual/live-data verification, no framework yet | Execute a trade; confirm the table updates ticker/quantity/avg_cost/current_price/unrealized_pnl/pct_change |
| Trade bar buy/sell, no confirmation dialog | UI-07 | Same | Submit a buy and a sell order; confirm cash/position update immediately with no confirmation dialog, and that a 400 validation error (e.g. insufficient cash/shares) surfaces inline near the trade bar |
| Header live total value, cash, connection dot | UI-09 | Same | Observe the header while prices tick and while toggling the backend's SSE availability (stop/restart it) to see the dot move green → yellow → red per D-06's thresholds |
| Dark trading-terminal theme | UI-10 | Visual/design review, not a scriptable assertion | Compare the rendered UI against PLAN.md §2: background `#0d1117`/`#1a1a2e`, accent yellow `#ecad0a`, blue `#209dd7`, purple `#753991` for submit/buy actions |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies — N/A this phase; manual verification is the documented, intentional strategy (see RESEARCH.md § Validation Architecture)
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify — N/A, no automated tests this phase
- [ ] Wave 0 covers all MISSING references — N/A, no Wave 0 test-framework work needed
- [ ] No watch-mode flags — N/A
- [ ] Feedback latency < {N}s — N/A (manual verification, not timed sampling)
- [ ] `nyquist_compliant: true` set in frontmatter — remains `false` until `/gsd-validate-phase` confirms

**Approval:** pending
