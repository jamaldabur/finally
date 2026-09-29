---
phase: 05-docker-packaging-deployment
plan: 03
subsystem: infra
tags: [docker, dockerignore, dotenv-leak, lifespan-shutdown, asyncio, powershell, bash, launcher-scripts]

requires:
  - phase: 05-docker-packaging-deployment
    provides: "Plan 05-01's Dockerfile/HEALTHCHECK/bind-mount contract and Plan 05-02's start/stop scripts, both amended here without changing their shape"
provides:
  - "A .dockerignore that excludes every dotenv variant at every depth and re-includes the committed .env.example templates, proven by inspecting what Docker actually received rather than by grepping the Dockerfile"
  - "A lifespan shutdown that awaits both background tasks before releasing the market source's shared HTTP client"
  - "A start_mac.sh readiness poll whose every curl attempt is time-bounded"
  - "A start_windows.ps1 that reports every failure as a plain stderr line with a real exit 1, never a PowerShell error-record dump"
affects: [06-testing-e2e]

actuals:
  tokens: 26000
  tasks: 3
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Layer-evidence verification: prove a build-context exclusion by inspecting what the daemon actually received (whole-context probe, target-stage probe, runtime-image probe), not by grepping the Dockerfile text"
    - "asyncio.gather(..., return_exceptions=True) to drain cancelled background tasks before releasing a resource they share"

key-files:
  created: []
  modified:
    - .dockerignore
    - backend/app/main.py
    - backend/tests/test_main.py
    - scripts/start_mac.sh
    - scripts/start_windows.ps1

key-decisions:
  - "Live round-trip proof required closing the browser tab that start_windows.ps1 -Build auto-opens (D-08) before invoking stop_windows.ps1 — its open SSE connection (GET /api/stream/prices never returns while the client stays connected) otherwise blocks uvicorn's graceful shutdown past docker stop's 10s grace period, producing exit code 137 (SIGKILLed) instead of a clean 'Application shutdown complete.' This is a pre-existing characteristic of the long-lived SSE stream, not a regression from this plan's asyncio.gather fix or from WR-02/WR-03 — the loop-error grep and rc from stop_windows.ps1 were both clean regardless, only the shutdown_complete log line depended on no held-open connection. Closing the tab is a verification-harness step only; no script, route, or Dockerfile line changed."

requirements-completed: [DEPLOY-01, DEPLOY-03]

coverage:
  - id: D1
    description: "CR-01 closed: .dockerignore now excludes **/.env and **/.env.*, re-includes !**/.env.example, and the Dockerfile is byte-identical — verified by a whole-context probe, a --target frontend-build probe, and a runtime-image probe, each seeded with four empty sentinel dotenv files and anchored by a positive control"
    requirement: "DEPLOY-01"
    verification:
      - kind: integration
        ref: "docker build -q -f - . (whole-context probe): find /ctx -name '.env*' -> exactly /ctx/.env.example, /ctx/frontend/.env.example"
        status: pass
      - kind: integration
        ref: "docker build --target frontend-build (stage probe): find /app/frontend ... -> exactly /app/frontend/.env.example, /app/frontend/package.json"
        status: pass
      - kind: integration
        ref: "docker build -t finally:latest . (runtime probe): find /app ... -> exactly /app/app/main.py"
        status: pass
      - kind: integration
        ref: "smoke run of rebuilt finally:latest: GET /api/health -> {\"status\":\"ok\"}, GET / -> doctype html"
        status: pass
    human_judgment: false
  - id: D2
    description: "WR-01 closed: lifespan shutdown now awaits asyncio.gather(update_task, snapshot_task, return_exceptions=True) before source.stop(), locked by a test that failed against the old cancel-then-stop ordering"
    requirement: "DEPLOY-01"
    verification:
      - kind: unit
        ref: "backend/tests/test_main.py::test_lifespan_awaits_background_tasks_before_stopping_source (observed RED before the fix on `assert fake.in_flight_at_stop is False` -> got True; GREEN after)"
        status: pass
      - kind: unit
        ref: "uv run --directory backend pytest -q (full suite)"
        status: pass
    human_judgment: false
  - id: D3
    description: "WR-02 closed: every readiness curl in start_mac.sh now carries --max-time 2, matching start_windows.ps1's -TimeoutSec 2"
    requirement: "DEPLOY-03"
    verification:
      - kind: other
        ref: "bash -n scripts/start_mac.sh; curl_calls=1 bounded=1 structural gate"
        status: pass
    human_judgment: false
  - id: D4
    description: "WR-03 closed: all five start_windows.ps1 failure paths write via [Console]::Error.WriteLine(...) instead of Write-Error, so the intended message prints and exit 1 is reached; proven from a temp copy with no .env, and exercised live in a full -Build / stop round trip on the rebuilt image"
    requirement: "DEPLOY-03"
    verification:
      - kind: integration
        ref: "temp-copy run with no .env: rc=1, template_named=1, error_record_lines=0"
        status: pass
      - kind: integration
        ref: "live start_windows.ps1 -Build / stop_windows.ps1 round trip: rc=0 both, health {\"status\":\"ok\"}, shutdown_complete=1, loop_errors=0, exit code 0, db/finally.db intact"
        status: pass
    human_judgment: false

duration: 30min
completed: 2026-09-23
status: complete
---

# Phase 5 Plan 3: Dotenv build-context leak closed with layer evidence, shutdown now awaits its background tasks, and both launchers fail cleanly Summary

**`.dockerignore` now excludes every dotenv variant at every depth (proven by three sentinel-seeded layer probes, not a Dockerfile grep); `lifespan` shutdown awaits both cancelled background tasks before releasing the market source's shared client; `start_mac.sh`'s readiness curl is time-bounded; and `start_windows.ps1` reports every failure as a plain stderr line with a real exit 1, proven live end to end.**

## Performance
- **Duration:** ~30min
- **Started:** 2026-09-23T19:08Z (approx, per prior STATE.md session marker)
- **Completed:** 2026-09-23T19:31Z
- **Tasks:** 3 completed
- **Files modified:** 5

## Accomplishments
- Closed CR-01 (Phase 5's only failed must-have): `.dockerignore` broadened from a single root-anchored `.env` line to `**/.env` / `**/.env.*` / `!**/.env.example`, verified against what Docker's daemon actually received at three points (whole build context, the `frontend-build` stage the gap named, and the shipped runtime image), each seeded with four empty sentinel dotenv files and anchored by a positive control so a broken probe can never silently pass.
- Closed WR-01: `lifespan`'s shutdown now runs `await asyncio.gather(update_task, snapshot_task, return_exceptions=True)` between the two `cancel()` calls and `await source.stop()`, locked by a TDD-authored regression test that demonstrably failed against the old ordering.
- Closed WR-02 and WR-03: `start_mac.sh`'s readiness `curl` is capped at 2 seconds per attempt; `start_windows.ps1`'s five failure paths write via `[Console]::Error.WriteLine(...)` instead of `Write-Error`, so `exit 1` is reachable again instead of dead code under `$ErrorActionPreference = "Stop"`.
- Re-verified the whole Phase 5 round trip end to end on the rebuilt image carrying all three fixes: `start_windows.ps1 -Build` comes up healthy, `stop_windows.ps1` shuts it down cleanly (`Application shutdown complete`, exit code 0, no background-loop errors), and `db/finally.db` survives untouched.

## Task Commits
1. **Task 1: End-to-end "no dotenv file reaches any image layer"** - `a3c0739` (fix)
2. **Task 2 (RED): failing test for shutdown ordering** - `14e8bdb` (test)
2. **Task 2 (GREEN): await background tasks before source.stop()** - `1fabcbc` (fix)
3. **Task 3: bounded curl + PowerShell stderr fixes, live round trip** - `efdc476` (fix)

**Plan metadata:** committed alongside this SUMMARY (see final `docs(05-03): ...` commit)

_Note: Task 2 is TDD (RED then GREEN), matching the plan's own commit guidance — 2 commits for that task._

## Files Created/Modified
- `.dockerignore` - three-line dotenv exclusion/re-include block replacing the single root-anchored `.env` line; header comment extended to explain the `**/` root-anchoring difference from `.gitignore`, the two whole-directory Dockerfile copies it protects, and why it also keeps `next build` hermetic inside the image
- `backend/app/main.py` - `lifespan`'s shutdown section gains `await asyncio.gather(update_task, snapshot_task, return_exceptions=True)` before `await source.stop()`, with an explanatory comment
- `backend/tests/test_main.py` - new `_ParkedSource(MarketDataSource)` fake and `test_lifespan_awaits_background_tasks_before_stopping_source`; new imports `asyncio`, `threading`, `app.market.base.MarketDataSource`
- `scripts/start_mac.sh` - readiness `curl` gains `--max-time 2`; step-9 comment updated with the per-attempt cap and worst-case bound
- `scripts/start_windows.ps1` - five `Write-Error` calls replaced with `[Console]::Error.WriteLine(...)`; one explanatory comment added above the `.env` guard

## Decisions Made
- See `key-decisions` in frontmatter: closing the auto-opened browser tab before the round trip's `stop_windows.ps1` call was a verification-harness choice, not a code change — no script, route, or Dockerfile line was touched to make this work.

## Deviations from Plan
None - plan executed exactly as written. All five files modified are exactly the five declared in `files_modified`; the Dockerfile, `scripts/stop_mac.sh`, and `scripts/stop_windows.ps1` all have zero diff against HEAD (`SCOPE_HELD` verified); no `docker builder prune`/`system prune`/`image prune` was run; no top-level `docker-compose.yml` was created.

## Issues Encountered
- The live `-Build` / `stop` round trip's first attempt exited the container with code 137 (SIGKILLed by `docker stop`'s 10s grace timeout) instead of a clean shutdown, because `start_windows.ps1`'s D-08 auto-opened browser held an open `GET /api/stream/prices` SSE connection — uvicorn's graceful shutdown waits for in-flight connections to finish, and an infinite SSE generator never finishes on its own. This is a pre-existing characteristic of the SSE route (`backend/app/routes/stream.py`, out of this plan's declared file scope), not something introduced by the `asyncio.gather` fix: the loop-error grep was already clean (`loop_errors=0`) on that first attempt, and `rc=0` from `stop_windows.ps1` itself (PowerShell's own exit code, not the container's). Closing the browser window before re-running the round trip produced a fully clean shutdown (`shutdown_complete=1`, `loop_errors=0`, container exit code 0). Not fixed here (would require touching `stream.py` or the stop script's `docker stop` timeout, both out of this plan's scope) — flagged below as a residual observation for a future phase, not a WR item this plan owns.

## User Setup Required
None - Docker Desktop was already running for the entire plan (confirmed via `docker info` before Tasks 1 and 3, per each task's `<precondition>`); no `05-USER-SETUP.md` was generated since the condition was already satisfied throughout.

## Additional Verification Detail (per plan's `<output>` contract)

**Step 0 existence results (Task 1):** `ROOT_ENV_PRESENT` and `FRONTEND_DEV_ENV_PRESENT` both printed — the project-root `.env` and `frontend/.env.development.local` were present before any edit, and `LOCAL_ENV_FILES_INTACT` confirmed both still exist, untouched, after cleanup.

**Inventory gate full output** (`git status --porcelain --ignored=matching --untracked-files=all`, filtered to dotenv paths, with all four sentinels on disk):
```
.env
.env.gsdprobe
backend/app/.env.gsdprobe
frontend/.env.development.local
frontend/.env.gsdprobe.local
frontend/gsdprobe/.env
```
All four sentinels (`.env.gsdprobe`, `frontend/.env.gsdprobe.local`, `frontend/gsdprobe/.env`, `backend/app/.env.gsdprobe`) present alongside the two real local dotenv files.

**Probe outputs (names only):**
- Whole-context probe: `/ctx/.env.example`, `/ctx/frontend/.env.example`
- `frontend-build` stage probe: `/app/frontend/.env.example`, `/app/frontend/package.json`
- Runtime image probe: `/app/app/main.py`

**WR-01 test's failing assertion before the fix:**
```
>       assert fake.in_flight_at_stop is False
E       assert True is False
E        +  where True = <tests.test_main._ParkedSource object at 0x...>.in_flight_at_stop
```
Full file run at that point: `1 failed, 6 passed`. After the fix: `7 passed`; full backend suite: `228 passed` (was 227 before this plan).

**WR-03 temp-copy output after the fix** (directory tree with no `.env`):
```
Error: .env not found at <temp>\.env
Copy .env.example to .env and fill in OPENROUTER_API_KEY before starting FinAlly.
rc=1
template_named=1
error_record_lines=0
```
For contrast, 05-REVIEW.md's plan-time reproduction of the pre-fix behavior recorded a PowerShell error-record block (`FullyQualifiedErrorId`/`CategoryInfo`/position lines) also with `rc=1` — same exit code, but with the terminating-error dump this fix eliminates. This plan did not re-run the pre-fix reproduction against the now-fixed script (that would require reverting the fix first); the review's plan-time record stands as the "before" evidence.

**Round trip shutdown log evidence** (after closing the auto-opened browser tab):
```
INFO:     Shutting down
INFO:     Waiting for application shutdown.
INFO:     Application shutdown complete.
INFO:     Finished server process [1]
```
`stop_windows.ps1` rc=0; container final state: `exited ExitCode=0`; `docker logs finally | grep -c 'Traceback\|loop iteration failed'` = 0; `db/finally.db` present and intact (`DATA_INTACT`).

**T-05-01 residual:** build-cache entries from pre-fix builds on this development machine may still hold the old `frontend-build` layer containing `frontend/.env.development.local`. They are local-only (never pushed to a registry, no cache export configured in this project) and owned by the same user who owns the source file. The user may purge them at their own discretion with `docker builder prune`; this plan did not run that command.

**Bash launch path:** still unexercised live on this Windows/Git-Bash machine (carried forward from 05-02's Edge Coverage — Git Bash path translation prevents a live `docker run` invocation from this shell). WR-02's `start_mac.sh` fix was verified by syntax (`bash -n`) and structural gates (every non-comment `curl` call carries `--max-time 2`) only.

**IN-01 deferral:** No `PYTHONUNBUFFERED=1` in the Dockerfile remains deferred, as planned — info-level with no functional defect, and fixing it would require editing the `Dockerfile`, which this plan keeps byte-identical so Task 1's layer evidence stays attributable to `.dockerignore` alone. Available as a one-line `/gsd-quick` follow-up at any time.

## Next Phase Readiness
Phase 5's tenth must-have (no secret enters a Docker image layer via the build context) is now closed with layer-inspection evidence, and all three 05-REVIEW.md warnings (WR-01/WR-02/WR-03) are fixed with a gate each. Phase 5 can now re-verify at 10/10. Phase 6 (testing/E2E) inherits: a `finally:latest` image that starts, serves, and shuts down cleanly under the idempotent launcher scripts; a backend suite at 228 passing tests; and the still-open, explicitly out-of-scope observation that a client holding an SSE connection open blocks a fully graceful `docker stop` within its default 10s grace period — worth a look if Phase 6's E2E infra needs deterministic clean shutdowns between test runs.

---
*Phase: 05-docker-packaging-deployment*
*Completed: 2026-09-23*

## Self-Check: PASSED
All claimed files (05-03-SUMMARY.md) and commits (a3c0739, 14e8bdb, 1fabcbc, efdc476) verified present.
