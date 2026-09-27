---
phase: "06"
slug: "test-coverage"
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-09-27"
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

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 0 | TEST-03 | — | N/A | unit | `pytest tests/routes/test_watchlist.py::test_post_watchlist_empty_ticker_is_422 -x` | ❌ W0 | ⬜ pending |
| 06-01-02 | 01 | 0 | TEST-04 | — | N/A | infra | `npm run test -- --run` (bootstrap only) | ❌ W0 | ⬜ pending |
| 06-01-03 | 01 | 0 | TEST-05 | — | N/A | infra | `docker compose -f test/docker-compose.test.yml config` (bootstrap only) | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

*Full per-task rows are finalized once the planner assigns concrete task IDs; this table seeds Wave 0's known infrastructure gaps.*

---

## Wave 0 Requirements

- [ ] `frontend/vitest.config.ts` + `frontend/vitest.setup.ts` — Vitest bootstrap, covers TEST-04's entire test-runner prerequisite
- [ ] `frontend/lib/test-support/eventSourceStub.ts` (or equivalent) — shared EventSource stub, covers any SSE-dependent TEST-04 test (jsdom has no native `EventSource`)
- [ ] `frontend/package.json` `"test"` script — currently absent entirely
- [ ] `test/package.json` + `test/playwright.config.ts` — E2E bootstrap, covers TEST-05's entire test-runner prerequisite
- [ ] `test/docker-compose.test.yml` — E2E container orchestration, covers TEST-05's infra requirement
- [ ] `backend/tests/routes/test_watchlist.py::test_post_watchlist_empty_ticker_is_422` (or similarly named) — the one identified backend gap for TEST-03

---

## Manual-Only Verifications

*All phase behaviors have automated verification — this phase's entire purpose is closing that gap. No manual-only items expected; the planner should flag any that turn out to be unavoidable.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (frontend infra, E2E infra, the one backend gap)
- [ ] No watch-mode flags (Vitest `--run`, Playwright non-watch, pytest has no watch mode)
- [ ] Feedback latency < 180s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
