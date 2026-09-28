---
phase: "06"
slug: "test-coverage"
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-09-27"
validated: "2026-09-28"
---

# Phase 06 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
>
> This phase is unusual: TEST-04/05's own deliverable *is* the test framework this section would normally audit against. The gaps below are therefore this phase's actual Wave 1 scope, not separate infrastructure debt.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Backend framework** | pytest 8.0+ / pytest-asyncio 0.24+ (already configured, `backend/pyproject.toml`) |
| **Backend config file** | `backend/pyproject.toml` `[tool.pytest.ini_options]` |
| **Backend quick run** | `cd backend && uv run pytest` |
| **Backend full suite** | `cd backend && uv run pytest -v` (228 existing tests + gap-closure additions) |
| **Frontend framework** | Vitest 5.0.2 (not yet configured — this phase's deliverable) |
| **Frontend config file** | `frontend/vitest.config.ts` (to be created) |
| **Frontend quick run** | `cd frontend && npm run test -- --run <file>` |
| **Frontend full suite** | `cd frontend && npm run test -- --run` |
| **E2E framework** | Playwright 1.63.0 (not yet configured — this phase's deliverable) |
| **E2E config file** | `test/playwright.config.ts` (to be created) |
| **E2E run command** | `docker compose -f test/docker-compose.test.yml up --build --abort-on-container-exit` |
| **Estimated runtime** | ~40s backend, ~10s frontend unit, ~2-3min E2E (Docker build + suite) |

---

## Sampling Rate

- **After every task commit:** backend — `pytest -x` on the touched module; frontend — `npm run test -- --run <touched file>`
- **After every plan wave:** backend full suite (`uv run pytest`); frontend full suite (`npm run test -- --run`)
- **Before `/gsd-verify-work`:** Full backend suite green + full frontend suite green + full Playwright E2E suite green (via Compose)
- **Max feedback latency:** ~180s (E2E Docker build is the long pole)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| 06-01-01 | 01 | 1 | TEST-03 | unit | `pytest backend/tests/routes/test_watchlist.py -x` (empty/whitespace ticker 422/400) | ✅ green |
| 06-01-02 | 01 | 1 | TEST-01/02/03 | unit | `pytest backend/tests/portfolio/test_service.py -x` (sell-at-loss) + full-suite audit, 231 passed | ✅ green |
| 06-02-01 | 02 | 1 | TEST-04 | infra+unit | `npm --prefix frontend run test` — Vitest/RTL bootstrap, PriceCell flash (8 tests) | ✅ green |
| 06-02-02 | 02 | 1 | TEST-04 | unit | `npm --prefix frontend run test` — priceStore/Header via real providers (19 tests) | ✅ green |
| 06-03-01 | 03 | 2 | TEST-04 | unit | `npm --prefix frontend run test` — WatchlistPanel CRUD/read-states (8 tests) | ✅ green |
| 06-03-02 | 03 | 2 | TEST-04 | unit | `npm --prefix frontend run test` — ActionBadge (9) + ChatPanel (11 tests) | ✅ green |
| 06-04-01 | 04 | 2 | TEST-04 | unit (tracer) | `npm --prefix frontend run test` — PositionsTable displays backend figures verbatim | ✅ green |
| 06-04-02 | 04 | 2 | TEST-04 | unit | `npm --prefix frontend run test` — format/chartTheme/WatchlistRow (45 tests total this plan) | ✅ green |
| 06-05-01 | 05 | 2 | TEST-05 | checkpoint | package-legitimacy human-verify (`@playwright/test`) — approved | ✅ approved |
| 06-05-02 | 05 | 2 | TEST-05 | infra+e2e | `npm --prefix test run e2e` — Playwright/Docker bootstrap, fresh-start spec | ✅ green |
| 06-05-03 | 05 | 2 | TEST-05 | e2e | `npm --prefix test run e2e` — SSE reconnect (unreachable-at-load) | ✅ green |
| 06-06-01 | 06 | 3 | TEST-05 | e2e | `npm --prefix test run e2e` — trade bar lifecycle (buy/sell/rejections) | ✅ green |
| 06-06-02 | 06 | 3 | TEST-05 | e2e | `npm --prefix test run e2e` — chat-driven watchlist + mocked chat trades | ✅ green |
| 06-06-03 | 06 | 3 | TEST-05 | e2e | `npm --prefix test run e2e` — sparklines/main chart/heatmap/P&L | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Known environment limitation (not a coverage gap — WINDOWS.md #1, open):** `test/specs/06-sse-reconnect.spec.ts`'s live-drop scenario (`context.setOffline`) cannot observe a status transition away from "Connected" under this Chromium/CDP environment — the emulation blocks new connections but doesn't interrupt an already-open, continuously-streaming SSE connection. Root-caused and verified deterministic (30s isolated diagnostic + 2 full E2E runs). The requirement (SSE resilience) remains automated-verified: the suite's other reconnect test (`page.route` abort, unreachable-at-load) independently proves the same `EventSource` retry/reconnect capability and passes reliably every run. Accepted as an environment constraint per this phase's own plan-level contingency instructions, not weakened or skipped.

---

## Wave 0 Requirements

- [x] `frontend/vitest.config.mts` + `frontend/vitest.setup.ts` — Vitest bootstrap, covers TEST-04's entire test-runner prerequisite (06-02)
- [x] `frontend/test-support/eventSourceStub.ts` — shared EventSource stub, covers any SSE-dependent TEST-04 test (06-02)
- [x] `frontend/package.json` `"test"` script — added by 06-02
- [x] `test/package.json` + `test/playwright.config.ts` — E2E bootstrap, covers TEST-05's entire test-runner prerequisite (06-05)
- [x] `test/docker-compose.test.yml` — E2E container orchestration, covers TEST-05's infra requirement (06-05, extended by 06-06)
- [x] `backend/tests/routes/test_watchlist.py::test_post_watchlist_empty_ticker_is_422` + `test_post_watchlist_whitespace_ticker_is_400` — the identified backend gaps for TEST-03 (06-01)

---

## Manual-Only Verifications

*None.* Every phase behavior has automated verification. The one checkpoint gate (06-02 Task 1, 06-05 Task 1 — package-legitimacy `gate="blocking-human"`) is a pre-install human confirmation, not a test-coverage gap; both were approved with a documented evidence table and are recorded in their plans' SUMMARY.md files.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (frontend infra, E2E infra, the one backend gap) — all satisfied
- [x] No watch-mode flags (Vitest `--run` via `npm run test`, Playwright non-watch, pytest has no watch mode)
- [x] Feedback latency < 180s (backend ~ a few seconds, frontend unit ~10s, E2E ~2-3min Docker build + suite — within the estimated envelope)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** validated 2026-09-28 — all 5 requirements (TEST-01–05) have passing automated tests: 231 backend (pytest), 160 frontend unit (Vitest/RTL across 06-02/06-03/06-04), 13 E2E (Playwright across 06-05/06-06). One environment-specific test limitation is documented above and in WINDOWS.md #1 (open, non-blocking — underlying capability independently proven by a passing sibling test). One unrelated latent production bug was found during E2E work and logged separately as WINDOWS.md #2 (open, out of this phase's scope per its P-07 boundary).

## Validation Audit 2026-09-28

| Metric | Count |
|--------|-------|
| Gaps found | 0 (all 5 requirements were already covered by passing tests from the 6 executed plans) |
| Resolved | — |
| Escalated | 0 |
| Environment limitations documented | 1 (WINDOWS.md #1, non-blocking) |
