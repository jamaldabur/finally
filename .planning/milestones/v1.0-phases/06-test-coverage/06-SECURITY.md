---
phase: "06"
slug: "test-coverage"
status: verified
threats_open: 0
asvs_level: 1
security_block_on: high
register_authored_at_plan_time: true
created: "2026-09-28"
---

# Phase 06 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| test process -> SQLite file | Backend tests write real SQLite files; the autouse `isolated_db` fixture is the only thing keeping them off the developer's portfolio database | test data only |
| test author -> application code | A failing test creates pressure to "fix" the code under test; every plan in this phase forbids changing `backend/app`, `frontend/app`/`components`/`lib`, or committed E2E specs' targets | none (write-forbidden boundary) |
| npm/pip install -> developer machine + CI | Eight frontend devDependencies (06-02) and `@playwright/test` (06-05) are new supply-chain entries, four+one flagged `SUS` by the automated too-new heuristic | package code |
| E2E container -> host/production resources | Playwright runs against the real built Docker image; must never touch the developer's `db/finally.db`, published ports, or a real LLM provider | portfolio data, API keys, network |
| production image build -> test artifacts | `.dockerignore` must keep all frontend/E2E test code and harness modules out of the shipped image | none (exclusion boundary) |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-06-01 | Tampering | backend/app under test | medium | mitigate | `git diff --name-only 726046a -- backend/app` gated empty on every task; independently confirmed empty by orchestrator spot-check | closed |
| T-06-02 | Tampering | developer's db/finally.db | medium | mitigate | New tests reuse the `client` fixture and `_init_tables()` helper under conftest.py's autouse `isolated_db` (per-test tmp_path db) | closed |
| T-06-03 | Repudiation | backend test-suite integrity | low | mitigate | Full-suite gate requires ≥231 passed, 0 skipped/xfailed; per-file test-count gate catches a removed pre-existing test. Confirmed: 231 passed | closed |
| T-06-SC (06-02) | Tampering | npm installs (vitest, vite, jsdom, @testing-library/dom + 4 OK-verdict packages) | high | mitigate | Blocking-human legitimacy checkpoint (evidence table: official repo, tens-to-hundreds of millions weekly downloads, years-old packages); exact version pins; committed lockfile. Checkpoint approved by human | closed |
| T-06-04 | Tampering | production image and static bundle | medium | mitigate | `.dockerignore` excludes test files/harness/`test/`; independently confirmed via 06-02's commit adding six exclusion patterns | closed |
| T-06-01b | Tampering | frontend/app, components, lib | medium | mitigate | Byte-identical-to-`726046a` gate on every task; non-vacuity mutations reverted and reconfirmed | closed |
| T-06-06 | Repudiation | frontend test integrity | low | mitigate | Mutation checks prove new tests fail when guarded behavior changes; module-level mocking forbidden by grep gate | closed |
| T-06-07 | Information Disclosure | committed test fixtures | low | accept | Fixtures contain only ticker symbols and round-number prices — no credential, key, or personal data | closed (accepted) |
| T-06-08 | Tampering | ActionBadge reason rendering | low | mitigate | Test asserts a reason containing markup renders as literal text with no element created (locks Phase 3's T-03-16 escaping) | closed |
| T-06-01c | Tampering | frontend/app, components, lib + 06-02 harness | medium | mitigate | Byte-identical gate on every task | closed |
| T-06-06b | Repudiation | frontend test integrity | low | mitigate | Mutation checks on WatchlistPanel revision dep, ActionBadge alert role, chatStore rollback | closed |
| T-06-09 | Tampering (displayed-figure integrity) | PositionsRow P&L cells | medium | mitigate | Tracer proves a live SSE tick cannot change P&L/percent cells | closed |
| T-06-01d | Tampering | frontend/app, components, lib + 06-02 harness | medium | mitigate | Byte-identical gate; 3 files independently confirmed unchanged from baseline | closed |
| T-06-06c | Repudiation | frontend test integrity | low | mitigate | Hard-coded expected colors/strings (deriving from code-under-test forbidden); mutation checks prove discrimination | closed |
| T-06-02 (06-05) | Tampering | user's db/finally.db and finally-data volume | high | mitigate | Named throwaway `e2e-db` volume only, project-namespaced `finally-e2e`; gate proves no volume survives. **Independently verified** via `grep` on `test/docker-compose.test.yml`: `volumes: - e2e-db:/app/db`, no bind mount to `db/`, no `finally-data` reference | closed |
| T-06-03 (06-05) | Information Disclosure | OPENROUTER_API_KEY | high | mitigate | No env file, no provider key reaches either container; `LLM_MOCK: "true"` asserted. **Independently verified** via `grep`: no `env_file` directive, no `OPENROUTER` string anywhere in compose file, `LLM_MOCK: "true"` present, `MASSIVE_API_KEY: ""` explicit | closed |
| T-06-05 | Denial of Service | user's running FinAlly container | medium | mitigate | No published host port, no fixed container name, no `finally` image tag; project name namespaces every resource. **Independently verified** via `grep`: no `ports:`, `container_name:`, or shared `image:` tag found in compose file | closed |
| T-06-SC (06-05) | Tampering | @playwright/test and Playwright base image | high | mitigate | Blocking-human legitimacy checkpoint (official microsoft/playwright repo, ~73M weekly downloads, long-established); exact npm pin + Docker image tag lockstep. **Independently verified**: `test/package.json` pins `"@playwright/test": "1.63.0"`, `test/Dockerfile.playwright` uses `mcr.microsoft.com/playwright:v1.63.0-noble` — versions match exactly. Checkpoint approved by human | closed |
| T-06-06d | Repudiation | E2E result integrity | medium | mitigate | `retries: 0`, `forbidOnly` under CI, negative grep for focused/skipped/fixme specs; the live-drop reconnect assertion was left unweakened per explicit plan instruction when it could not be satisfied in this environment (documented in WINDOWS.md #1, not silently passed) | closed |
| T-06-07b | Information Disclosure | committed E2E files | low | mitigate | Grep gate rejects key-shaped strings anywhere in the harness; fixtures contain only ticker symbols and prices | closed |
| T-06-10 | Elevation of Privilege | runner container isolation | low | mitigate | Chromium's shared-memory need met via `shm_size`, not host IPC namespace; no host networking | closed |
| T-06-11 | Repudiation | chat spec phrases (D-07) | medium | mitigate | Every phrase asserted against `build_mock_response` directly before the browser run; watchlist spec grep-gated for the "to my watchlist" keyword | closed |
| T-06-01e | Tampering | backend/app and frontend application source | medium | mitigate | Byte-identical-to-`726046a` gate on every task; specs locate by role/label/text only (negative grep for test ids) | closed |
| T-06-06e | Repudiation | E2E result integrity | medium | mitigate | Negative grep rejects focused/skipped/fixme specs and fixed sleeps; retries stay 0; heatmap colour oracle is an independent restatement, not a read-back | closed |
| T-06-02b | Tampering | user's database | high | mitigate | Inherited from 06-05: throwaway `e2e-db` volume; Task 3 re-checks no `finally-e2e` volume survives after this plan's runs. Suite verified stable across 2 consecutive full runs | closed |

*Status: open · closed · open — below `high` threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above `workflow.security_block_on` (`high`) count toward `threats_open`*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-06-01 | T-06-07 | Committed test fixtures contain only ticker symbols and round-number prices — no credential, key, or personal data. No mitigation beyond code review needed. | plan-time disposition (06-02), confirmed at phase close | 2026-09-28 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-09-28 | 24 | 24 | 0 | Orchestrator (L1 grep-depth verification — ASVS level 1; register authored at plan time across all 6 plans' `<threat_model>` blocks; short-circuit rule applied, no auditor subagent spawned since `threats_open: 0`) |

**Verification method:** Cross-referenced each plan's STRIDE register against (1) the executing agent's own SUMMARY.md self-check evidence (byte-identical-to-baseline diffs, mutation-test results, full-suite pass counts) and (2) independent orchestrator-run `grep`/`Read` checks against the actual committed files for the five `high`-severity threats (T-06-02, T-06-03, T-06-05, and both T-06-SC package-legitimacy checkpoints), since those are the ones at or above the `high` block threshold.

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-09-28
