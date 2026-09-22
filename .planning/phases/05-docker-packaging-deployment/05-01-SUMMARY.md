---
phase: 05-docker-packaging-deployment
plan: 01
subsystem: infra
tags: [docker, fastapi, staticfiles, dockerfile, uv, sqlite, deployment]

requires:
  - phase: 01-04-backend-trading-engine
    provides: complete FastAPI backend (all API routes, watchlist/portfolio/chat, FINALLY_DB_PATH mechanism)
  - phase: 02-frontend
    provides: Next.js static export (output "export", producing frontend/out/)
provides:
  - "A committed multi-stage Dockerfile producing one image that serves the Next.js static export and every /api/* route on port 8000"
  - "A guarded StaticFiles mount in backend/app/main.py that never breaks a checkout without a built frontend"
  - "A .dockerignore keeping secrets, user data, and dependency trees out of every image layer"
  - "A committed, placeholder-only .env.example documenting all three PLAN.md §5 environment variables"
affects: [05-02-startup-scripts, phase-06-testing]

actuals:
  tokens: 2610
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Guarded StaticFiles mount (is_dir() check around app.mount, not check_dir=False) so a frontend-less checkout never breaks create_app()"
    - "Two-stage Docker build (node:20-slim -> python:3.12-slim) with COPY --from= carrying only the compiled frontend/out/ into the runtime image"
    - "uv binary acquired via COPY --from=ghcr.io/astral-sh/uv:<pinned-tag> /uv /bin/uv on a literal python:3.12-slim base, rather than a uv-vendored base image"

key-files:
  created:
    - Dockerfile
    - .dockerignore
    - .env.example
  modified:
    - backend/app/main.py
    - backend/tests/test_main.py

key-decisions:
  - "P-01 resolved with no substitution: ghcr.io/astral-sh/uv:0.10.9 (the locally installed uv version) pulled and built successfully — the exact pinned tag from RESEARCH.md Open Question 2 worked as specified"
  - "First docker build measured at 150s (2m30s) end-to-end from an empty layer cache — well under the ~10 minute foreground timeout risk RESEARCH.md flagged; run in the background regardless per the plan's own guidance, and it finished without needing a re-run"
  - "Bind-mount host path form that works on this Windows/Docker-Desktop-WSL2 machine: resolve the repo root via `pwd -W` under Git Bash (not bare `pwd`, which yields an MSYS-style /c/... path Docker Desktop does not translate the same way), then pass `-v \"$D/db:/app/db\"` with MSYS_NO_PATHCONV=1 set to stop Git Bash from mangling the container-side /app/db path into a Windows path. Plan 05-02's scripts should use this exact `pwd -W` + MSYS_NO_PATHCONV=1 pattern for the bash script's Windows/Git-Bash path, alongside D-02's PowerShell Resolve-Path form for native PowerShell invocation."

requirements-completed: [DEPLOY-01, DEPLOY-02, DEPLOY-04]

coverage:
  - id: D1
    description: "One docker build from the repo root produces a single image serving both the Next.js static export and every /api/* route on port 8000"
    requirement: DEPLOY-01
    verification:
      - kind: integration
        ref: "docker build -t finally:latest . (150s, ended with 'naming to docker.io/library/finally:latest')"
        status: pass
      - kind: integration
        ref: "curl http://localhost:8000/api/health -> {\"status\":\"ok\"}; curl http://localhost:8000/ -> doctype html; curl http://localhost:8000/api/portfolio -> 200"
        status: pass
    human_judgment: false
  - id: D2
    description: "SQLite persists via the db/ bind mount, proven by a data round-trip across container destruction and replacement, not by the presence of a -v flag"
    requirement: DEPLOY-02
    verification:
      - kind: integration
        ref: "POST /api/watchlist {ticker:CSCO} -> added:true; docker rm -f finally; fresh docker run against same host db/; GET /api/watchlist contains CSCO"
        status: pass
    human_judgment: false
  - id: D3
    description: ".env.example is committed, documents OPENROUTER_API_KEY/MASSIVE_API_KEY/LLM_MOCK with placeholder-only values, and is not gitignored"
    requirement: DEPLOY-04
    verification:
      - kind: unit
        ref: "grep assertions on .env.example (per-variable assignment + no high-entropy token) plus git check-ignore .env.example (exit 1)"
        status: pass
    human_judgment: false
  - id: D4
    description: "The guarded static mount cannot break a frontend-less checkout, provably serves the index, and never shadows /api/*"
    verification:
      - kind: unit
        ref: "backend/tests/test_main.py::test_create_app_skips_static_mount_when_directory_absent, ::test_static_mount_serves_index_when_directory_present, ::test_api_route_wins_over_static_mount"
        status: pass
    human_judgment: false

duration: ~25min
completed: 2026-09-22
status: complete
---

# Phase 5 Plan 1: Docker Packaging Tracer Summary

**One `docker build` now produces a single FastAPI+Next.js image on port 8000 with SQLite persisting through a bind mount, proven by a live build-run-persist round trip, not just static file presence.**

## Performance
- **Duration:** ~25min
- **Started:** 2026-09-22T15:41:36Z (STATE.md session start)
- **Completed:** 2026-09-22T15:55:05Z
- **Tasks:** 3 completed
- **Files modified:** 5 (2 created infra files beyond Dockerfile/.dockerignore/.env.example, 2 backend files edited)

## Accomplishments
- Multi-stage `Dockerfile` (node:20-slim → python:3.12-slim) builds and runs end-to-end: one image serves the Next.js static export and all `/api/*` routes on port 8000
- SQLite persistence proven by an actual round-trip (add ticker → destroy container → fresh container → ticker still present), not merely the presence of a `-v` flag
- `backend/app/main.py` gained a guarded `StaticFiles` mount that can never break a checkout without a built frontend (Starlette's eager `check_dir` would otherwise raise `RuntimeError`)
- `.env.example` committed with placeholder-only values for all three PLAN.md §5 variables, verified not gitignored

## Task Commits
1. **Task 1: End-to-end "one command runs the whole app and keeps my data"** - `80250bf` (feat)
2. **Task 2: Prove the static mount cannot break a frontend-less checkout, and cannot shadow an API route** - `e66cfa0` (test)
3. **Task 3: Commit the environment template users copy** - `5fec63f` (docs)

_Task 2 is a single `test(05-01):` commit rather than a separate test→feat pair: the mount behavior it locks was already implemented by Task 1, so GREEN required no new production code — only the RED→GREEN cycle for Test 2 (index-serving) was independently confirmed by temporarily removing the `index.html` write and observing a genuine 404 failure before restoring the correct version, per the plan's own TDD guidance for this task._

## Files Created/Modified
- `Dockerfile` - Two-stage build; pins `node:20-slim`, `python:3.12-slim`, and `ghcr.io/astral-sh/uv:0.10.9`; sets `FINALLY_DB_PATH=/app/db/finally.db`; stdlib `HEALTHCHECK` against `/api/health`
- `.dockerignore` - Excludes `node_modules`, `.venv`, `__pycache__`, `.git`, `.planning`, `.claude`, `frontend/out`, `db/*.db`, `db/*.db-journal`, the project env file, and `*.log`
- `.env.example` - Documents `OPENROUTER_API_KEY`, `MASSIVE_API_KEY`, `LLM_MOCK` with placeholder-only values
- `backend/app/main.py` - Adds `STATIC_DIR` module constant (`parents[1]`), guarded `app.mount("/", StaticFiles(...), name="static")` as the last statement of `create_app()`, and updates the `CORSMiddleware` comment to record the D-03 answer
- `backend/tests/test_main.py` - Three new tests locking the absent-directory guard, index serving, and API-over-static precedence

## Decisions Made
- P-01 (uv acquisition strategy): resolved as specified, no tag substitution needed — `ghcr.io/astral-sh/uv:0.10.9` pulled and worked on the first build
- First `docker build` duration measured at 150s from a cold cache, informing Plan 05-02's own build-timeout sizing
- Bind-mount host path form on this Windows/Git-Bash/Docker-Desktop-WSL2 machine: `pwd -W` (not bare `pwd`) plus `MSYS_NO_PATHCONV=1` on the `docker run` invocation — recorded for Plan 05-02's bash script to reuse directly

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None. The Docker daemon was confirmed running (precondition met) before any build/run step; the first `docker build` succeeded without needing a re-run despite the plan's warning about foreground timeouts (it was run as a background command per the plan's own guidance).

## User Setup Required
None - no external service configuration required (Docker Desktop was already confirmed running before dispatch).

## Next Phase Readiness
Plan 05-02 (start/stop scripts) can now build directly on: image tag `finally:latest`, container name `finally`, published port `8000`, bind-mount target `/app/db`, and the `pwd -W` + `MSYS_NO_PATHCONV=1` path-resolution pattern proven on this machine. No blockers.

---
*Phase: 05-docker-packaging-deployment*
*Completed: 2026-09-22*
