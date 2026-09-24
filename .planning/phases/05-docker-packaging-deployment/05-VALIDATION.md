---
phase: "5"
slug: "docker-packaging-deployment"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-09-22"
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.0+ / pytest-asyncio 0.24+ (`backend/pyproject.toml`) for application code; docker CLI + `bash -n`/PowerShell live invocation for packaging and launcher behavior (no CI-wired docker-build test harness exists yet — deferred to Phase 6's E2E infrastructure per 05-02-SUMMARY.md) |
| **Config file** | `backend/pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run --directory backend pytest -q` |
| **Full suite command** | `uv run --directory backend pytest -q` (no separate slow/full split — 228 tests, all fast) |
| **Estimated runtime** | ~20s (measured: 228 passed in 20.37s) |

---

## Sampling Rate

- **After every task commit:** `uv run --directory backend pytest -q` for tasks touching `backend/`; the task's own `<verify>` block (docker build/run, launcher invocation, structural grep) for packaging/script tasks
- **After every plan wave:** Full backend suite + the wave's live docker/launcher round trip as specified in that plan's task `<verify>` blocks
- **Before `/gsd-verify-work`:** Full suite must be green — confirmed 228/228 passing at this audit
- **Max feedback latency:** ~20s (pytest) / ~1-3min (docker build + live round trip)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 1 | DEPLOY-01, DEPLOY-02 | — | N/A | integration | `docker build -t finally:latest .` then `curl :8000/api/health`, `curl :8000/`, `curl :8000/api/portfolio`; SQLite round-trip across `docker rm -f finally` + fresh `docker run` against the same `db/` bind mount | N/A — live command, codified in 05-01-PLAN.md Task 1 `<verify>` | ✅ green |
| 05-01-02 | 01 | 1 | (static-mount robustness, DEPLOY-01) | — | N/A | unit | `uv run --directory backend pytest tests/test_main.py -k static_mount -q` | ✅ `backend/tests/test_main.py` | ✅ green |
| 05-01-03 | 01 | 1 | DEPLOY-04 | — | N/A | structural | grep per-variable assertions on `.env.example` (no high-entropy token) + `git check-ignore .env.example` (exit 1) | N/A — live command, codified in 05-01-PLAN.md Task 3 `<verify>` | ✅ green |
| 05-02-01 | 02 | 2 | DEPLOY-03 | T-05-08 | Argument validation before any docker call | integration + structural | `bash -n scripts/start_mac.sh scripts/stop_mac.sh`; structural greps (`set -euo pipefail`, anchored `name=^`, `.env.example`, `--max-time 2`); live idempotent start/stop round trip via Git Bash on Windows | N/A — live command, codified in 05-02-PLAN.md Task 1 `<verify>` | ✅ green (see Manual-Only: the actual `docker run` launch path via `start_mac.sh` itself was not exercised on this host) |
| 05-02-02 | 02 | 2 | DEPLOY-03 | T-05-08 | Idempotent start/stop, rebuild-only-on-`-Build` | integration | `powershell -File scripts/start_windows.ps1 [-Build]` / `scripts/stop_windows.ps1` live round trip against Docker Desktop; container count, `StartedAt` timestamp, and `db/finally.db` checked across the sequence | N/A — live command, codified in 05-02-PLAN.md Task 2 `<verify>` | ✅ green |
| 05-03-01 | 03 | 3 | DEPLOY-01 | CR-01 | No dotenv content reaches any image layer | integration | Sentinel-seeded `docker build -q -f - .` (whole context), `--target frontend-build` (stage probe), full runtime-image probe; each greps the resulting layer for stray `.env*` files | N/A — live command, codified in 05-03-PLAN.md Task 1 `<verify>` | ✅ green |
| 05-03-02 | 03 | 3 | DEPLOY-01 | WR-01 | Shutdown awaits in-flight background tasks before releasing the market-data client | unit (TDD) | `uv run --directory backend pytest tests/test_main.py::test_lifespan_awaits_background_tasks_before_stopping_source -q` (RED observed pre-fix, GREEN after) | ✅ `backend/tests/test_main.py` | ✅ green |
| 05-03-03 | 03 | 3 | DEPLOY-03 | WR-02, WR-03 | Bounded readiness probes; failures print a plain message, never a raw error-record dump | structural + integration | `bash -n scripts/start_mac.sh`; grep for `--max-time 2`; temp-copy run with no `.env` (checks `[Console]::Error.WriteLine` usage, zero `Write-Error` lines); live `-Build`/stop round trip on the rebuilt image | N/A — live command, codified in 05-03-PLAN.md Task 3 `<verify>` | ✅ green |
| 05-04-01 | 04 | 4 | DEPLOY-03 | WR-04 (gap) | Unrecognised `start_windows.ps1` argument rejected with usage + exit 1 before any docker call | integration | Docker-free temp-copy matrix (`-File` and in-session, accept/reject sets) + live repro of VERIFICATION.md's exact three reproductions (`--build`, `--totally-bogus-flag`, `--i-am-not-a-real-flag`) against the running container, confirming container ID/`StartedAt` unchanged | N/A — live command, codified in 05-04-PLAN.md Task 1 `<verify>` | ✅ green |
| 05-04-02 | 04 | 4 | DEPLOY-03 | WR-04 (gap) | Unrecognised `stop_windows.ps1` argument rejected before contacting Docker; bare stop stays idempotent | integration | Live sequence: rejected stop while running (container untouched), bare stop ×2 (idempotent), rejected stop while stopped, `db/finally.db` intact throughout | N/A — live command, codified in 05-04-PLAN.md Task 2 `<verify>` | ✅ green |
| 05-04-03 | 04 | 4 | DEPLOY-03 (doc correction) | WR-04 (gap) | N/A — documentation task | structural | grep/awk `PLACEMENT_OK` + content-term check + `HISTORY_UNTOUCHED` gate on `05-REVIEW.md` (original WR-04 text and frontmatter preserved, correction appended) | N/A — live command, codified in 05-04-PLAN.md Task 3 `<verify>` | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

*Full backend suite confirmed at this audit: `uv run --directory backend pytest -q` → 228 passed, 2 warnings (deprecation notices only), 20.37s.*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. `backend/pyproject.toml` already pins pytest 8.0+/pytest-asyncio 0.24+ and `backend/tests/` was already populated by prior phases (market data, portfolio, LLM, routes). No new test framework install was needed — the two genuinely new automated regression tests this phase added (static-mount guard, lifespan shutdown ordering) were written as part of their own TDD tasks (05-01 Task 2, 05-03 Task 2), not as a separate Wave 0 step.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| The bash launcher pair's actual container-launch path (`start_mac.sh` invoking `docker run` for the first time, not idempotency/argument/`.env`-guard behavior, all of which *were* live-verified) | DEPLOY-03 | This development environment is Windows. Git Bash path translation would mangle the bind-mount source path before Docker Desktop's Linux daemon receives it, so the live `docker run` launch via `start_mac.sh` itself has never been exercised end-to-end (05-02-SUMMARY.md D5, 05-03-PLAN.md's own Edge Coverage note both name this same gap) | On a real macOS or Linux host (or once Phase 6's E2E infrastructure exists): run `./scripts/start_mac.sh` from a clean checkout, confirm `curl http://localhost:8000/api/health` returns `{"status":"ok"}`, then `./scripts/stop_mac.sh` and confirm the container stops cleanly and `db/finally.db` persists |

---

## Validation Sign-Off

- [x] All tasks have an automated verify command (docker build/run, `curl`, `pytest`, structural grep/awk) — see Per-Task Verification Map. None rely solely on unassisted human eyeballing.
- [x] Sampling continuity: no 3 consecutive tasks without automated verify — every task in the table carries a concrete, reproducible command.
- [x] Wave 0 covers all MISSING references — none were MISSING; existing `backend/tests/` infrastructure and the two new TDD tests cover the application-code requirements, and packaging/launcher requirements are covered by the live, documented commands in each plan's own `<verify>` blocks.
- [x] No watch-mode flags — `pytest -q` is one-shot; no `--watch`/`-w` anywhere in the phase's test commands.
- [x] Feedback latency < 60s for the automatable subset (pytest ~20s); docker-build/live-round-trip checks run in the 1-3 minute range, appropriate for infrastructure-level verification, not per-commit sampling.
- [x] `nyquist_compliant: true` set in frontmatter.

**Approval:** approved 2026-09-24 (retroactive audit — phase 05 was already complete with all four plans summarized and 05-VERIFICATION.md at 14/14 must-haves; this validation pass reconstructed the map from each plan's SUMMARY.md `coverage:` blocks and PLAN.md `<verify>` blocks, and re-ran the full backend suite to confirm current green state).

## Validation Audit 2026-09-24

| Metric | Count |
|--------|-------|
| Gaps found | 1 (bash launcher's live `docker run` path — pre-existing, self-disclosed since 05-02, not new) |
| Resolved | 0 (requires a non-Windows host or Phase 6 E2E infra; out of scope for this audit) |
| Escalated | 1 (recorded in Manual-Only Verifications above) |
