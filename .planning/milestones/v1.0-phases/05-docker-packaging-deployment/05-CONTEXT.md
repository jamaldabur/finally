# Phase 5: Docker Packaging & Deployment - Context

**Gathered:** 2026-09-22
**Status:** Ready for planning

<domain>
## Phase Boundary

A user can start the entire application with a single command and have their data persist across restarts. In scope: a multi-stage Dockerfile (Node build stage → Python runtime stage) producing one image that serves the Next.js static export and all `/api/*` routes on port 8000; a volume-mounted SQLite database that survives container restarts; idempotent start/stop scripts for macOS/Linux (bash) and Windows (PowerShell); a committed `.env.example`.

Out of scope for this phase (later/other phases or explicitly non-goals): automated test suites including `test/docker-compose.test.yml` (Phase 6); cloud deployment / Terraform (PLAN.md §11 stretch goal, not core v1); any change to backend business logic, frontend UI, or the LLM integration — this phase only packages what Phases 1-4 already built.

</domain>

<decisions>
## Implementation Decisions

The user deferred all gray-area choices to Claude ("You decide, choose the best") rather than working through them individually — the same pattern as Phase 2. The decisions below are Claude's calls, made to be consistent with `planning/PLAN.md` and the existing codebase's conventions, and downstream agents should treat them as locked unless they hit a concrete blocker.

### SQLite persistence
- **D-01:** Use a **bind mount** of the repo's own `db/` directory to `/app/db` inside the container (e.g. `-v "<absolute-path-to-repo>/db:/app/db"`), not an opaque named Docker volume. — **Reversibility:** reversible — switching to a named volume later is a one-line script change with no code impact. — **Rationale:** PLAN.md §4 explicitly designates the top-level `db/` directory as "the runtime volume mount target" with a committed `.gitkeep` and gitignored `finally.db`, which only makes sense if `db/` is the literal bind-mount source the user can inspect/back up directly. This resolves a literal inconsistency in PLAN.md itself: §4's directory structure implies a bind mount, while §11's example `docker run` command uses a named volume (`finally-data`). §4 is the more detailed and specific of the two, so it wins. `backend/app/db/watchlist.py`'s existing `FINALLY_DB_PATH` env var (default `<repo-root>/db/finally.db`) already assumes this exact layout — no backend code changes needed.
- **D-02:** Both start scripts resolve `db/`'s **absolute path** before mounting (`$(cd "$(dirname "$0")/.." && pwd)/db` in bash; `(Resolve-Path (Join-Path $PSScriptRoot "..\db")).Path` in PowerShell) rather than a bare relative `./db`, and create the directory first if missing (`mkdir -p` / `New-Item -Force`). — **Rationale:** Docker Desktop on Windows (this user's platform) is sensitive to relative-path bind mounts depending on the shell's working directory at invocation time; resolving to an absolute path up front avoids silent mount failures.

### Dev-only CORS middleware
- **D-03:** Leave `backend/app/main.py`'s `CORSMiddleware` (scoped to `http://localhost:3000`) in place unconditionally — do not strip it or gate it behind an env var for the Docker image. — **Reversibility:** reversible — removing it later is a 5-line diff with no external contract. — **Rationale:** In the single-container deployment the frontend and backend are always same-origin, so no browser ever sends a cross-origin request matching `localhost:3000`; the middleware is inert there. It's scoped to exactly one hardcoded origin with no credentials, so the security surface is negligible. Adding conditional logic (env var, build-time strip) to remove a no-op would add complexity and a new failure mode (accidentally breaking local `next dev` against the packaged backend) for zero functional benefit at this project's demo scale.

### Static frontend serving
- **D-04:** FastAPI mounts the built frontend (`frontend/out/`, copied into the image at `static/`) via Starlette's `StaticFiles(directory="static", html=True)`, mounted at `/` **after** all `/api/*` routers are registered — so API routes always take precedence and `html=True` serves `index.html` at `/`. — **Rationale:** PLAN.md §3 states this exact architecture ("FastAPI serves the static frontend files and all API routes on port 8000"); the frontend is a single page (`frontend/app/page.tsx` is the only route), so no SPA-fallback/catch-all routing is needed beyond `StaticFiles(html=True)`'s built-in `index.html` serving.
- **D-05:** Frontend Docker build stage uses `npm ci` (not `npm install`) against the committed `package-lock.json`, matching the reproducible-install intent of the backend's `uv sync`/lockfile convention. — **Reversibility:** reversible.

### Start/stop script behavior
- **D-06:** `start_mac.sh`/`start_windows.ps1` build the image only if it doesn't already exist, or if an explicit `--build` flag is passed — exactly as PLAN.md §11 specifies. Fixed image tag `finally:latest`, fixed container name `finally`.
- **D-07:** Re-running `start` while the named container is already running is a **no-op**: detect it (`docker ps --filter name=finally`), print the existing URL, and exit 0 — do not error, and do not restart. Re-running `stop` when the container isn't running is also a no-op that exits 0 with a friendly message ("FinAlly is not running"), satisfying the idempotency requirement (DEPLOY-03) without surprising the user either way.
- **D-08:** Start scripts attempt to **auto-open the browser** to `http://localhost:8000` on a successful start (`open` on macOS, `Start-Process` on Windows), best-effort and non-fatal if it fails (e.g. a headless/CI environment) — never blocks or errors the script. — **Rationale:** PLAN.md §11 lists this as optional ("Optionally opens the browser"); for a capstone demo whose whole pitch is an "impressive fluid demo experience" (PLAN.md §9), auto-opening is the more in-character default. `stop_mac.sh`/`stop_windows.ps1` never touch the volume/data per PLAN.md §11 ("Does NOT remove the volume").
- **D-09:** Scripts validate that a project-root `.env` exists before running the container and print a clear error pointing at `.env.example` if it's missing, rather than silently starting a container with no `OPENROUTER_API_KEY` and letting chat fail opaquely later.

### docker-compose.yml
- **D-10:** Do **not** create a top-level `docker-compose.yml` in this phase. — **Rationale:** PLAN.md §11 itself calls it "an optional convenience wrapper," and none of DEPLOY-01 through DEPLOY-04 in REQUIREMENTS.md reference it — the raw Dockerfile plus start/stop scripts fully satisfy every Phase 5 success criterion. `test/docker-compose.test.yml` (Phase 6, E2E-only) is a separate, already-scoped file this decision doesn't affect. Keeping scope tight here avoids building an artifact nothing in this milestone consumes.

### Container health check
- **D-11:** Dockerfile includes a `HEALTHCHECK` instruction hitting the existing `GET /api/health` endpoint via Python's stdlib (`CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"`), not `curl` — the `python:3.12-slim` base image doesn't ship `curl` by default and this avoids adding a package just for the health probe.

### Claude's Discretion
Per the user's "you choose everything" response, all of Phase 5's implementation gray areas (volume mount strategy, CORS middleware fate, static-serving mechanics, and start/stop script UX details) were left to Claude's judgment rather than individually discussed. The decisions above are the record of those calls; anything not explicitly pinned down here (e.g. exact shell-script error message wording, precise Dockerfile layer-caching order beyond the two stages PLAN.md already specifies) remains open for the researcher/planner to decide.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Product spec
- `planning/PLAN.md` §3 — Architecture overview (single container, single port, FastAPI serves static export + API)
- `planning/PLAN.md` §4 — Directory structure (`db/` as the runtime volume mount target with `.gitkeep`; `scripts/`, `Dockerfile`, `docker-compose.yml` locations)
- `planning/PLAN.md` §5 — Environment variables (`OPENROUTER_API_KEY`, `MASSIVE_API_KEY`, `LLM_MOCK`) and their behavior
- `planning/PLAN.md` §11 — Docker & Deployment: multi-stage Dockerfile stages, example `docker run` command, start/stop script responsibilities, idempotency requirement

### Requirements
- `.planning/REQUIREMENTS.md` — DEPLOY-01 through DEPLOY-04 (traceability table maps all four to Phase 5, currently Pending)

### Backend contracts this phase packages (already implemented, Phases 1-4)
- `backend/app/main.py` — `create_app()` factory; lifespan wires DB init, market data loop, portfolio snapshot loop; **existing CORS middleware and its inline comment are the direct source of decision D-03**
- `backend/app/db/watchlist.py:29-33` — `FINALLY_DB_PATH` env var and its default (`<repo-root>/db/finally.db`), the exact path this phase's volume mount must satisfy
- `backend/app/routes/health.py` — `GET /api/health`, the endpoint decision D-11's HEALTHCHECK targets
- `backend/pyproject.toml` — confirms `uv` + Hatchling as the Python build backend for the Dockerfile's Python stage

### Frontend build target
- `frontend/next.config.ts` — `output: 'export'` static export config (produces `frontend/out/`), with an explicit comment warning against adding rewrites/redirects/headers under static export
- `frontend/app/page.tsx` — the app's only route (confirms no SPA-fallback routing complexity beyond `StaticFiles(html=True)`)
- `frontend/package.json` — `npm run build` is the export-producing script; lockfile present for `npm ci`

### Codebase maps
- `.planning/codebase/CONCERNS.md` §"Unfinished Deployment Setup" — enumerates exactly what's missing (Dockerfile, compose files, scripts) and flags the untested `/app/db` volume mount as a known risk this phase must close
- `.planning/codebase/STRUCTURE.md` — target directory layout for `scripts/`, `Dockerfile`, `docker-compose.yml`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/routes/health.py` — `GET /api/health` already returns `{"status": "ok"}`, ready to back the Dockerfile `HEALTHCHECK` (D-11) with no changes.
- `backend/app/db/watchlist.py`'s `FINALLY_DB_PATH` env var mechanism already supports being pointed at a container path (`/app/db/finally.db`) without any backend code changes — the Dockerfile just needs to set `FINALLY_DB_PATH=/app/db/finally.db` (or rely on the default plus a matching `WORKDIR`).
- `backend/app/main.py`'s `load_dotenv(..., override=False)` already reads a project-root `.env` — consistent with PLAN.md §11's `--env-file .env` docker run flag; no new env-loading code needed.

### Established Patterns
- Backend fully commits to `uv` for dependency management (`backend/uv.lock` present) — the Dockerfile's Python stage should use `uv sync --frozen` (or equivalent) for a reproducible install, mirroring the frontend's `npm ci` decision (D-05).
- All prior phases favor "no new config surface unless PLAN.md already implies one" (e.g. Phase 2's D-01 kept the ticker field a plain input rather than adding a dropdown-restriction config) — this phase's decisions follow the same instinct (D-03's CORS call, D-10's compose-skip).

### Integration Points
- `backend/app/main.py:create_app()` is the single place the Dockerfile's runtime stage needs to serve: it already returns a fully-wired `app` with all routers included; the Docker image only needs to (1) copy `frontend/out/` to a `static/` directory the app can mount, and (2) add the `StaticFiles` mount described in D-04 — this is the one actual code change this phase requires in `backend/app/main.py`.
- The 3 backend route modules (`portfolio`, `watchlist`, `chat`) plus `health` and `stream` are all registered in `create_app()` already — nothing about the Docker packaging changes their behavior.

</code_context>

<specifics>
## Specific Ideas

No specific requirements beyond what's captured in Implementation Decisions above — the user explicitly deferred all Phase 5 gray areas to Claude's judgment, consistent with Phase 2's precedent.

</specifics>

<deferred>
## Deferred Ideas

None — no scope-creep suggestions came up during this discussion; the user deferred implementation choices rather than proposing new capabilities.

</deferred>

---

*Phase: 05-docker-packaging-deployment*
*Context gathered: 2026-09-22*
