# Phase 5: Docker Packaging & Deployment - Research

**Researched:** 2026-09-22
**Domain:** Docker multi-stage builds, Next.js static export deployment, uv-managed Python container packaging, idempotent shell/PowerShell scripting
**Confidence:** MEDIUM

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**SQLite persistence**
- **D-01:** Use a **bind mount** of the repo's own `db/` directory to `/app/db` inside the container (e.g. `-v "<absolute-path-to-repo>/db:/app/db"`), not an opaque named Docker volume. `backend/app/db/watchlist.py`'s existing `FINALLY_DB_PATH` env var (default `<repo-root>/db/finally.db`) already assumes this exact layout — no backend code changes needed.
- **D-02:** Both start scripts resolve `db/`'s **absolute path** before mounting (`$(cd "$(dirname "$0")/.." && pwd)/db` in bash; `(Resolve-Path (Join-Path $PSScriptRoot "..\db")).Path` in PowerShell) rather than a bare relative `./db`, and create the directory first if missing (`mkdir -p` / `New-Item -Force`). Docker Desktop on Windows is sensitive to relative-path bind mounts depending on the shell's working directory at invocation time.

**Dev-only CORS middleware**
- **D-03:** Leave `backend/app/main.py`'s `CORSMiddleware` (scoped to `http://localhost:3000`) in place unconditionally — do not strip it or gate it behind an env var for the Docker image. In single-container deployment frontend and backend are same-origin, so the middleware is inert but harmless.

**Static frontend serving**
- **D-04:** FastAPI mounts the built frontend (`frontend/out/`, copied into the image at `static/`) via Starlette's `StaticFiles(directory="static", html=True)`, mounted at `/` **after** all `/api/*` routers are registered — so API routes always take precedence and `html=True` serves `index.html` at `/`.
- **D-05:** Frontend Docker build stage uses `npm ci` (not `npm install`) against the committed `package-lock.json`.

**Start/stop script behavior**
- **D-06:** `start_mac.sh`/`start_windows.ps1` build the image only if it doesn't already exist, or if an explicit `--build` flag is passed. Fixed image tag `finally:latest`, fixed container name `finally`.
- **D-07:** Re-running `start` while the named container is already running is a **no-op**: detect it, print the existing URL, exit 0. Re-running `stop` when not running is also a no-op that exits 0 ("FinAlly is not running").
- **D-08:** Start scripts attempt to **auto-open the browser** to `http://localhost:8000` on successful start, best-effort and non-fatal. `stop_mac.sh`/`stop_windows.ps1` never touch the volume/data.
- **D-09:** Scripts validate that a project-root `.env` exists before running the container and print a clear error pointing at `.env.example` if missing.

**docker-compose.yml**
- **D-10:** Do **not** create a top-level `docker-compose.yml` in this phase. `test/docker-compose.test.yml` (Phase 6, E2E-only) is unaffected.

**Container health check**
- **D-11:** Dockerfile includes a `HEALTHCHECK` instruction hitting `GET /api/health` via Python's stdlib (`CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"`), not `curl` — `python:3.12-slim` doesn't ship `curl`.

### Claude's Discretion
Per the user's "you choose everything" response, all of Phase 5's implementation gray areas (volume mount strategy, CORS middleware fate, static-serving mechanics, start/stop script UX details) were left to Claude's judgment. Anything not explicitly pinned down above (exact shell-script error message wording, precise Dockerfile layer-caching order beyond the two stages PLAN.md specifies) remains open for this research/the planner to fill in.

### Deferred Ideas (OUT OF SCOPE)
None — no scope-creep suggestions came up during the discussion; the user deferred implementation choices rather than proposing new capabilities.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DEPLOY-01 | App builds as a multi-stage Docker image (Node build stage → Python runtime stage), serving frontend + API on a single port (8000) | Dockerfile skeleton in Code Examples; Standard Stack; Architecture Patterns |
| DEPLOY-02 | SQLite database persists via a Docker volume mount at `db/` | D-01/D-02 (locked); confirmed `FINALLY_DB_PATH` mechanism already supports it (verified below) |
| DEPLOY-03 | Idempotent start/stop scripts exist for macOS/Linux (bash) and Windows (PowerShell) | Code Examples: bash/PowerShell idempotency patterns |
| DEPLOY-04 | `.env.example` is committed, documenting `OPENROUTER_API_KEY`, `MASSIVE_API_KEY`, `LLM_MOCK` | Code Examples: `.env.example` template; confirmed file does not yet exist |
</phase_requirements>

## Summary

Phase 5 packages the already-complete backend (FastAPI, `uv`-managed, 224 passing tests) and frontend (Next.js 16.3.5 static export, already builds successfully into `frontend/out/`) into a single multi-stage Docker image, plus idempotent bash/PowerShell start/stop scripts and a committed `.env.example`. No backend business logic, frontend UI, or LLM integration changes — this is packaging-only work as CONTEXT.md's `<domain>` explicitly bounds it.

The technical shape is well-established and low-risk: a Node 20 build stage runs `npm ci && npm run build` to produce `frontend/out/`, a Python 3.12 runtime stage runs `uv sync --frozen` to install backend dependencies, `COPY --from=` pulls the built frontend into a `static/` directory the FastAPI app already knows how to serve (once the one required code change — mounting `StaticFiles(directory="static", html=True)` after the existing routers in `backend/app/main.py` — is made). Every other piece needed for DEPLOY-02 (the `FINALLY_DB_PATH` env var, defaulting to `<repo-root>/db/finally.db`) and DEPLOY-04's env vars (`OPENROUTER_API_KEY`, `MASSIVE_API_KEY`, `LLM_MOCK`, all already read by `main.py`/`factory.py`) is already implemented and requires zero backend code changes — only a Dockerfile, two shell scripts, two PowerShell scripts, and one `.env.example` file are net-new deliverables, plus the single `StaticFiles` mount line.

One research finding worth flagging prominently: a web search surfaced claims that FastAPI 0.141.1 (the exact version this project has pinned) ships a native `app.frontend()` SPA-serving helper that would make D-04's manual `StaticFiles(html=True)` mount unnecessary. This claim was **investigated and refuted** by reading the actual installed package source (`backend/.venv/Lib/site-packages/fastapi/applications.py` and `staticfiles.py`) — no such method exists in the installed version. D-04's manual mount-after-routers approach is confirmed as the only available approach in this exact version and should proceed as locked; see Common Pitfalls for the full account.

**Primary recommendation:** Build the Dockerfile as a two-stage `node:20-slim` → `python:3.12-slim` image using `npm ci`/`uv sync --frozen` with `--mount=type=cache` layer-caching, add the required `StaticFiles(html=True)` mount as the one backend code change, write bash/PowerShell scripts around `docker ps --filter name=finally --filter status=running -q` for idempotent state detection, and commit a straightforward `.env.example` — no exotic patterns needed, this whole phase is applying well-documented, standard Docker/uv/Next.js patterns to an already-working app.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Multi-stage image build (Node → Python) | Build/CI (Dockerfile) | — | Docker build-time concern; no runtime code owns this |
| Static frontend serving (`frontend/out/` → `/`) | API / Backend (FastAPI `StaticFiles` mount) | CDN/Static (conceptually, but not present here — single container per PLAN.md §3) | PLAN.md §3 explicitly assigns "FastAPI serves the static frontend files and all API routes on port 8000" — no separate static tier exists in this architecture |
| SQLite persistence across restarts | Database / Storage (bind mount) | Backend (`FINALLY_DB_PATH` env var read) | Storage tier owns durability; backend tier owns the path contract that must match the mount target |
| Container lifecycle (start/stop/idempotency) | Host / Ops (shell scripts) | — | Outside the application's own runtime; a host-level wrapper around `docker` CLI |
| Environment variable documentation | Host / Ops (`.env.example`) | Backend (`load_dotenv` consumer) | The template is a deploy-time artifact; the consumer is `backend/app/main.py`'s existing `load_dotenv` call |
| Container health signaling | API / Backend (`GET /api/health`, already implemented) | Host / Ops (`HEALTHCHECK` instruction that calls it) | The health logic lives in the backend; the Docker instruction is just a probe wrapper around the existing endpoint |

## Standard Stack

### Core
| Library / Tool | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Docker multi-stage builds | Docker Engine 29.7.2 (confirmed installed locally) [VERIFIED: `docker --version` output this session] | Produces one final image without carrying Node.js/npm into the runtime layer | Standard technique for polyglot builds (build-tool in one language, runtime in another) — avoids bloating the production image with a full Node toolchain |
| `node:20-slim` base image (build stage) | Node 20.x | Runs `npm ci && npm run build` for the frontend | PLAN.md §11 explicitly specifies "Stage 1: Node 20 slim" [VERIFIED: planning/PLAN.md §11, quoted: "Stage 1: Node 20 slim"]. The installed `next@16.3.5` package declares `"engines": { "node": ">=20.9.0" }` [VERIFIED: `frontend/node_modules/next/package.json`, read this session, quoted: `"engines": {\n    "node": ">=20.9.0"\n  }`] — any current `node:20-slim` tag (which tracks the latest 20.x patch) satisfies this. |
| `python:3.12-slim` base image (runtime stage) | Python 3.12.x | Runs the FastAPI app via `uv sync --frozen` + `uvicorn` | `backend/pyproject.toml` declares `requires-python = ">=3.12"` [VERIFIED: `backend/pyproject.toml:5`, quoted: `requires-python = ">=3.12"`]. D-11 (locked) specifically calls out that `python:3.12-slim` lacks `curl`, motivating the stdlib-based `HEALTHCHECK`. |
| `uv` | 0.10.9 (confirmed installed locally) [VERIFIED: `uv --version` output this session] | Installs backend Python dependencies reproducibly from `uv.lock` inside the image | Project already commits to `uv` end-to-end (`backend/uv.lock` present); official `uv` Docker guide's two-step `sync --no-install-project` then `sync` pattern is the documented, cache-friendly approach [CITED: docs.astral.sh/uv/guides/integration/docker/] |
| `npm ci` | npm 11.0.0 (locally installed) [VERIFIED: `npm --version` output this session] | Reproducible install from `frontend/package-lock.json`, which exists in the repo [VERIFIED: `ls frontend/package-lock.json` succeeded this session] | D-05 (locked); matches the project's existing lockfile-based reproducibility convention for the backend (`uv.lock`) |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Starlette `StaticFiles` (re-exported as `fastapi.staticfiles.StaticFiles`) | Bundled with `starlette==1.6.0` / `fastapi==0.141.1` [VERIFIED: `backend/uv.lock`, quoted: `name = "starlette"` / `version = "1.6.0"` and `name = "fastapi"` / `version = "0.141.1"`] | Serves `frontend/out/` (copied to `static/`) as the single-page app, `html=True` for `index.html` fallback at `/` | D-04 (locked) — this is the only viable approach in the pinned FastAPI version; see Common Pitfalls for why a newer native alternative does NOT exist here |
| `python-dotenv` | Already a backend dependency [VERIFIED: `backend/pyproject.toml:12`, quoted: `"python-dotenv>=1.2.3"`] | `backend/app/main.py`'s existing `load_dotenv(..., override=False)` call already reads project-root `.env` — no new code needed for env var loading inside the container | Already wired; Dockerfile/scripts just need to ensure `--env-file .env` (or equivalent) reaches the container per PLAN.md §11 |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Manual `StaticFiles(html=True)` mount (D-04, locked) | `app.frontend()` (a purported FastAPI-native SPA helper) | **Does not exist** in the installed `fastapi==0.141.1` — investigated and refuted by reading `backend/.venv/Lib/site-packages/fastapi/applications.py` (no `frontend` method) and `staticfiles.py` (a one-line re-export of Starlette's `StaticFiles`, nothing else). See Common Pitfalls. D-04 stands as written. |
| Bind mount (D-01, locked) | Named Docker volume (`docker volume create`) | Named volumes are opaque to the host filesystem, harder for a course student to inspect/back up directly; PLAN.md §4 explicitly designs `db/` as an inspectable bind-mount target with a committed `.gitkeep`. D-01's rationale in CONTEXT.md already resolves this in favor of the bind mount. |
| `docker-compose.yml` for production convenience | Raw `docker run` + wrapper scripts | D-10 (locked) explicitly defers compose; not revisited here. |

**Installation:** No new Python or npm packages are introduced by this phase — see Package Legitimacy Audit below for why.

**Version verification:** All versions in the table above were confirmed via direct inspection of `backend/uv.lock`, `frontend/node_modules/next/package.json`, and local tool version checks (`docker --version`, `uv --version`, `node --version`, `npm --version`) run this session — not via registry lookups, since no new packages are being added.

## Package Legitimacy Audit

**Not applicable in the traditional sense.** This phase adds zero new pip/npm dependencies — it packages the exact dependency sets already locked in `backend/uv.lock` and `frontend/package-lock.json` from prior phases (Phases 1-4), which were already subject to legitimacy review when those dependencies were introduced. The only "new" external inputs are Docker base image tags (`node:20-slim`, `python:3.12-slim`), which are official Docker Hub / Docker-maintained images, not registry packages, and are not subject to the npm/PyPI slopsquatting vector this gate exists to catch.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| *(none — no new packages introduced this phase)* | — | — | — | — | — | N/A |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────────── docker build ───────────────────────────────┐
│                                                                              │
│  Stage 1: node:20-slim (builder)          Stage 2: python:3.12-slim (final)│
│  ┌─────────────────────────┐              ┌──────────────────────────────┐ │
│  │ COPY frontend/package*.json│            │ COPY backend/pyproject.toml   │ │
│  │ RUN npm ci                │            │      backend/uv.lock          │ │
│  │ COPY frontend/ .           │            │ RUN uv sync --frozen          │ │
│  │ RUN npm run build          │──out/────▶ │      --no-install-project     │ │
│  │   → produces frontend/out/ │  COPY      │ COPY backend/app/ ./app/      │ │
│  └─────────────────────────┘  --from=     │ RUN uv sync --frozen          │ │
│                                 builder    │ COPY --from=builder /out ./static/│
│                                            │ HEALTHCHECK CMD python -c ... │ │
│                                            │ CMD uvicorn app.main:app      │ │
│                                            └──────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────┬─┘
                                                                             │
                                                                     docker run
                                                                             │
                                                                             ▼
┌────────────────────────────── running container (port 8000) ──────────────┐
│                                                                              │
│  Browser ──HTTP──▶  uvicorn (app.main:app)                                 │
│                        │                                                    │
│                        ├─▶ /api/health, /api/stream/*, /api/portfolio/*,   │
│                        │   /api/watchlist/*, /api/chat  (routers, checked   │
│                        │   FIRST — D-04)                                   │
│                        │                                                    │
│                        └─▶ StaticFiles("/","./static", html=True)          │
│                            (checked LAST — serves frontend/out/ contents,  │
│                             index.html at "/")                             │
│                                                                              │
│  Background tasks (already implemented, unchanged): market data update      │
│  loop, portfolio snapshot loop — write to PriceCache / SQLite               │
│                                                                              │
│  SQLite: /app/db/finally.db  ◀── bind mount ──▶  <repo>/db/finally.db      │
│  (host filesystem — survives container restart/removal, D-01)              │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────┘

Host-level lifecycle (outside the container):
  scripts/start_mac.sh / start_windows.ps1
    ├─ check .env exists (D-09) → error + point to .env.example if missing
    ├─ check image "finally:latest" exists → build if missing or --build passed (D-06)
    ├─ check container "finally" already running → no-op + print URL if so (D-07)
    ├─ resolve db/ to absolute path (D-02) → mkdir -p if missing
    ├─ docker run -v <abs db path>:/app/db -p 8000:8000 --env-file .env --name finally finally:latest
    └─ best-effort auto-open http://localhost:8000 (D-08)

  scripts/stop_mac.sh / stop_windows.ps1
    ├─ check container "finally" running → no-op + friendly message if not (D-07)
    └─ docker stop finally (volume/data untouched, D-08)
```

### Recommended Project Structure
```
finally/
├── Dockerfile                  # Multi-stage: node:20-slim → python:3.12-slim
├── .dockerignore                # NEW — exclude node_modules, .venv, __pycache__, db/*.db, .git, test/
├── .env.example                  # NEW — OPENROUTER_API_KEY, MASSIVE_API_KEY, LLM_MOCK
├── scripts/
│   ├── start_mac.sh              # NEW
│   ├── stop_mac.sh               # NEW
│   ├── start_windows.ps1         # NEW
│   └── stop_windows.ps1          # NEW
├── backend/
│   └── app/main.py               # ONE code change: add StaticFiles(html=True) mount after routers
└── db/
    └── .gitkeep                  # already exists — bind-mount target, unchanged
```

### Pattern 1: Two-stage Dockerfile with `COPY --from=`
**What:** Build the frontend in a throwaway Node stage; copy only the compiled `out/` directory into the final Python image.
**When to use:** Any time a build toolchain (Node) is not needed at runtime (a static export served by a different runtime, here Python/FastAPI).
**Example:**
```dockerfile
# Source: Docker multi-stage build docs + PLAN.md §11 (Stage 1: Node 20 slim, Stage 2: Python 3.12 slim)
FROM node:20-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build
# produces /app/frontend/out (D-05, next.config.ts's output: 'export')

FROM python:3.12-slim AS runtime
WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock ./
RUN --mount=from=ghcr.io/astral-sh/uv,source=/uv,target=/bin/uv \
    uv sync --frozen --no-install-project
COPY backend/app ./app
RUN --mount=from=ghcr.io/astral-sh/uv,source=/uv,target=/bin/uv \
    uv sync --frozen
COPY --from=frontend-build /app/frontend/out ./static
ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```
Note: the `--mount=from=ghcr.io/astral-sh/uv,...` line is one way to get the `uv` binary into a plain `python:3.12-slim` image without a separate install step (BuildKit mount syntax); an equally valid alternative is `FROM ghcr.io/astral-sh/uv:python3.12-trixie-slim AS runtime` as the base directly [CITED: docs.astral.sh/uv/guides/integration/docker/]. Either satisfies D-11's `python:3.12-slim`-family requirement; the planner should pick one explicitly rather than leaving it ambiguous, since the two approaches produce a different `FROM` line.

### Pattern 2: Static file mount ordering in FastAPI
**What:** Register all API routers before mounting `StaticFiles` at `/`, so unmatched paths (i.e. everything not `/api/*`) fall through to the static handler.
**When to use:** Single-container deployments serving both an API and a static SPA from one process (PLAN.md §3's exact architecture).
**Example:**
```python
# Source: fastapi.tiangolo.com/tutorial/static-files/ (official docs) + D-04 (locked)
from fastapi.staticfiles import StaticFiles

def create_app() -> FastAPI:
    app = FastAPI(title="FinAlly", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, ...)  # unchanged, D-03
    app.include_router(health.router)
    app.include_router(stream.router)
    app.include_router(portfolio.router)
    app.include_router(watchlist_routes.router)
    app.include_router(chat.router)
    # Mounted LAST — D-04. Path only exists inside the built Docker image
    # (Dockerfile copies frontend/out/ to ./static); local `uv run` without
    # a built frontend has no ./static dir, so this should not error when
    # the directory is absent in dev (see Common Pitfalls).
    app.mount("/", StaticFiles(directory="static", html=True), name="static")
    return app
```

### Pattern 3: Idempotent container lifecycle check (bash)
**What:** Query actual Docker state before acting, rather than assuming a prior run's outcome.
**When to use:** Any start/stop script that must be safe to re-run (DEPLOY-03).
**Example:**
```bash
# Source: general docker CLI idempotency pattern (websearch, common practice)
CONTAINER_NAME="finally"
if [ -n "$(docker ps --filter "name=^${CONTAINER_NAME}$" --filter "status=running" -q)" ]; then
  echo "FinAlly is already running at http://localhost:8000"
  exit 0
fi
```
The `^...$` anchoring on `--filter name=` avoids a substring false-positive match against an unrelated container whose name merely contains "finally".

### Anti-Patterns to Avoid
- **Copying `node_modules/` or `.venv/` into any image layer:** Bloats the image and defeats reproducibility (the `.venv` is platform-dependent per the official uv Docker guide [CITED: docs.astral.sh/uv/guides/integration/docker/]). Use a `.dockerignore` excluding both, plus `frontend/out/` from the *backend*'s own build context if using separate `docker build` contexts.
- **Using `docker ps` (no `--filter`) and grepping the name column:** Fragile against partial name matches and column-width truncation; use `--filter name=^<name>$` or `docker inspect <name>` and check the exit code instead.
- **Assuming `MASSIVE_API_KEY`/`OPENROUTER_API_KEY` absence is caught at container-run time:** `.env` presence is checked by the *scripts* (D-09), not the Dockerfile — the container itself will start fine with no `.env` (backend's `load_dotenv` silently no-ops if the file is absent) but chat will fail opaquely later. D-09 exists specifically to catch this earlier, at the script layer.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|--------------|-----|
| SPA fallback routing to `index.html` | A custom Starlette middleware or catch-all route that reads `index.html` on 404 | Starlette's `StaticFiles(html=True)` | Already does exactly this — serves `index.html` for any directory-like request; no custom logic needed given the app has only one route (`frontend/app/page.tsx`, confirmed the only route [VERIFIED: `frontend/app/` listing implied by CONTEXT.md's canonical_refs, treat as CITED via CONTEXT.md]) |
| Reproducible Python dependency install | A custom `pip freeze > requirements.txt` step, or unpinned `pip install -e .` | `uv sync --frozen` against the committed `uv.lock` | The project has already standardized on `uv` end-to-end; `--frozen` guarantees byte-for-byte the same resolution used in development, matching `npm ci`'s guarantee for the frontend |
| Docker container "is it running" detection | Custom PID-file or lockfile tracking on the host | `docker ps --filter`/`docker inspect` against the Docker daemon's own state | Docker already tracks this authoritatively; a host-side lockfile can drift out of sync with actual container state (e.g. if the container crashes or is removed externally) |

**Key insight:** Every mechanism this phase needs (reproducible installs, SPA static serving, container state queries) already has a first-party, well-documented tool-native answer. The temptation in a "just package it" phase is to write custom glue scripts where a documented flag or built-in already exists — resist that, per the project's established "no new config surface unless PLAN.md already implies one" pattern (see STATE.md's Phase 2 precedent).

## Runtime State Inventory

> Not applicable — this phase is not a rename/refactor/migration phase. It is new deployment infrastructure (Dockerfile, scripts, `.env.example`) layered on top of already-complete, unchanged application code. Skipped per the trigger condition in the researcher's instructions.

## Common Pitfalls

### Pitfall 1: Trusting a plausible-sounding but nonexistent framework API from web search
**What goes wrong:** A web search for "FastAPI StaticFiles SPA serving" returned multiple blog posts (dev.to, a personal blog) confidently describing a new `app.frontend()` helper method allegedly "shipped in FastAPI 0.138.0–0.141.0" — exactly matching this project's pinned `fastapi==0.141.1`. Taken at face value, this would have led the planner to recommend replacing D-04's manual `StaticFiles(html=True)` mount with a simpler, nonexistent API.
**Why it happens:** LLM-generated or speculative blog content about "upcoming" or "just-shipped" framework features is a known hallucination vector, especially for version numbers that sound current relative to the session's date.
**How to avoid:** Before accepting any claim about a specific pinned dependency's API surface, read the actual installed source. Done here: `Grep` for `frontend` across `backend/.venv/Lib/site-packages/fastapi/` returned **zero matches**; `backend/.venv/Lib/site-packages/fastapi/staticfiles.py` is a one-line re-export of `starlette.staticfiles.StaticFiles` with nothing else added. This is a positive falsification — the claim is refuted, not merely unverified.
**Warning signs:** Confident claims about brand-new API additions in blog posts rather than the project's own official docs changelog or release notes; version numbers matching the exact pinned dependency (a hallucination often "helpfully" targets what it infers you're using).

### Pitfall 2: Relative bind-mount paths on Docker Desktop for Windows
**What goes wrong:** `docker run -v ./db:/app/db` (a bare relative path) can silently mount an empty or unexpected directory, or fail outright, depending on the shell's working directory at invocation time and Docker Desktop's WSL2 backend path translation. Documented in multiple `docker/for-win` GitHub issues (#7431, #7905) [CITED: github.com/docker/for-win/issues/7431, #7905 — found via websearch, not independently fetched this session, so tagged CITED not VERIFIED].
**Why it happens:** Docker Desktop's WSL2 integration translates Windows paths through `/mnt/c/...` or `/run/desktop/mnt/host/wsl/...` internally; a relative path resolved against the wrong working directory produces a path that "looks" valid but points nowhere useful.
**How to avoid:** D-02 (already locked) mandates resolving `db/` to an absolute path before mounting, in both the bash and PowerShell scripts. This directly addresses the documented failure mode — implement exactly as specified, do not simplify to a relative path "for readability."
**Warning signs:** SQLite database appears empty/reset after every container restart; `docker inspect finally --format '{{json .Mounts}}'` shows a `Source` path that doesn't match the expected absolute repo path.

### Pitfall 3: `StaticFiles(directory="static", ...)` raising at import time if the directory is absent
**What goes wrong:** Starlette's `StaticFiles` constructor validates the directory exists at construction time (not lazily) by default; if `backend/app/main.py` is imported without a `static/` directory present (e.g. running `uv run pytest` or `uvicorn app.main:app` locally without ever running the frontend Docker build stage), `create_app()` can raise `RuntimeError` before any tests or the dev server even start.
**Why it happens:** `static/` only exists inside the built Docker image (populated by the `COPY --from=frontend-build` step); it has no equivalent in the bare backend checkout.
**How to avoid:** The planner should decide explicitly whether to (a) always ensure a `static/` directory exists in the backend tree (e.g. an empty placeholder with `.gitkeep`, git-ignored actual contents) so local `uv run`/pytest never breaks, or (b) guard the mount with an existence check. Given `backend/tests/test_main.py` already exercises `create_app()` directly (`test_cors_allows_local_dev_frontend_origin`, confirmed present [VERIFIED: `uv run pytest --collect-only` output this session, listed `tests/test_main.py::test_cors_allows_local_dev_frontend_origin`]), this is not hypothetical — it will break the existing test suite unless handled. This is flagged as an Open Question below since CONTEXT.md's D-04 doesn't address it.
**Warning signs:** `uv run pytest` fails with a `RuntimeError`/`StaticFiles directory does not exist` error immediately after the `StaticFiles` mount line is added, even though the Dockerfile itself builds fine.

### Pitfall 4: `.dockerignore` omission bloating build context and image size
**What goes wrong:** Without a `.dockerignore`, `docker build` sends the entire repo (including `frontend/node_modules/`, `backend/.venv/`, `.git/`, `db/finally.db`, `frontend/out/` from a stale local build) as build context, slowing builds and risking a stale `frontend/out/` accidentally leaking into a build step that doesn't expect it.
**Why it happens:** No `.dockerignore` currently exists anywhere in the repo [VERIFIED: `ls .dockerignore frontend/.dockerignore backend/.dockerignore` all returned "No such file or directory" this session].
**How to avoid:** Add a root `.dockerignore` excluding at minimum: `**/node_modules`, `**/.venv`, `**/__pycache__`, `.git`, `db/*.db`, `frontend/out` (rebuilt fresh inside the image), `test/node_modules`, `.pytest_cache`.
**Warning signs:** `docker build` takes noticeably longer than expected; `docker images` shows a surprisingly large image.

## Code Examples

### `.env.example`
```bash
# Source: PLAN.md §5 (verbatim variable names and behavior description)
# Required: OpenRouter API key for LLM chat functionality
OPENROUTER_API_KEY=your-openrouter-api-key-here

# Optional: Massive (Polygon.io) API key for real market data
# If not set, the built-in market simulator is used (recommended for most users)
MASSIVE_API_KEY=

# Optional: Set to "true" for deterministic mock LLM responses (testing)
LLM_MOCK=false
```
Confirmed this file does not yet exist in the repo [VERIFIED: `ls .env.example` returned "No such file or directory" this session] — DEPLOY-04 is fully unmet as of research time.

### Idempotent PowerShell start check
```powershell
# Source: general PowerShell + docker CLI pattern (websearch), adapted to match the bash pattern above
$ContainerName = "finally"
$running = docker ps --filter "name=^$ContainerName$" --filter "status=running" -q
if ($running) {
    Write-Host "FinAlly is already running at http://localhost:8000"
    exit 0
}
```

### Absolute path resolution (already specified in D-02, restated for completeness)
```bash
# bash — Source: D-02 (locked, quoted verbatim from CONTEXT.md)
DB_DIR="$(cd "$(dirname "$0")/.." && pwd)/db"
mkdir -p "$DB_DIR"
```
```powershell
# PowerShell — Source: D-02 (locked, quoted verbatim from CONTEXT.md)
$DbDir = (Resolve-Path (Join-Path $PSScriptRoot "..\db")).Path
New-Item -ItemType Directory -Force -Path $DbDir | Out-Null
```
Note: `Resolve-Path` fails if the target doesn't exist yet — the `New-Item -Force` should run *before* `Resolve-Path` is called on the final mount-ready value, or `Resolve-Path` should target the parent and the `db` leaf be appended after. The planner/executor should verify this ordering when implementing, since `Resolve-Path` erroring on a not-yet-created path is a common PowerShell gotcha not fully spelled out in D-02's shorthand.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| `pip install -r requirements.txt` in Docker | `uv sync --frozen` against `uv.lock`, with `--no-install-project` as a separate cache-friendly layer | Project has used `uv` since Phase 1 (already established, not new to this phase) | Faster, reproducible builds; matches the project's existing convention |
| `next export` CLI command | `output: 'export'` in `next.config.ts` | Next.js 13.3+ (well before this project's Next.js 16.3.5) [CITED: nextjs.org/docs/app/guides/static-exports version history table] | Already correctly implemented in `frontend/next.config.ts` — no action needed, confirmed current |

**Deprecated/outdated:** None directly relevant — the project's existing stack choices (uv, `output: 'export'`, FastAPI `StaticFiles`) are all current, non-deprecated approaches as of this research.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|----------------|
| A1 | `node:20-slim` and `python:3.12-slim` Docker Hub tags are currently available and track recent patch releases satisfying Next.js's `>=20.9.0` engines requirement | Standard Stack | Low — these are extremely widely used, actively maintained official tags; if somehow unavailable, any `node:20-*`/`python:3.12-*` variant is a trivial substitution |
| A2 | The `docker/for-win` WSL2 bind-mount issues cited in Pitfall 2 are current as of this project's Docker Desktop version (29.7.2) | Common Pitfalls | Low-medium — these are long-standing, recurring issue patterns across many Docker Desktop versions; D-02's absolute-path mitigation is a superset fix regardless of the exact current bug status |
| A3 | Reading `.venv/Lib/site-packages/fastapi/` source (Windows path casing, this being a Windows dev machine) accurately reflects what a Linux container's `uv sync` would install for the same `fastapi==0.141.1` pin | Common Pitfalls (Pitfall 1) | Low — `uv.lock` pins the exact same version cross-platform; package *source* (Python, not compiled) does not differ by OS for this dependency |
| A4 | `StaticFiles`'s directory-existence check happens at construction/import time (not lazily on first request) in the installed Starlette 1.6.0 | Common Pitfalls (Pitfall 3) | Medium — this claim is based on general Starlette behavior knowledge, not a source read this session; if wrong, Pitfall 3 is a non-issue, but the planner should still decide explicitly rather than assume either way — flagged in Open Questions |

**If this table is empty:** N/A — see rows above.

## Open Questions

1. **Does `backend/app/main.py`'s planned `StaticFiles` mount break `uv run pytest` locally (no `static/` dir present outside Docker)?**
   - What we know: `frontend/out/` already exists in the current checkout from a prior manual build [VERIFIED: `ls frontend` output this session listed `out`], so it happens to work *today* — but that's incidental, not guaranteed for a fresh clone or CI environment without a frontend build step.
   - What's unclear: Whether Starlette 1.6.0's `StaticFiles` validates directory existence eagerly (would break `create_app()`/tests on a fresh checkout with no `static/` present) or lazily (would only 404 on request, leaving tests unaffected).
   - Recommendation: The planner should add a task to either (a) ensure the Docker build always produces `backend/static/` before the app is imported for tests inside CI, or (b) verify Starlette's actual behavior and, if eager, guard the mount so a missing `static/` directory doesn't break `uv run pytest` for contributors who haven't built the frontend. This directly affects whether the existing 224-test suite (and any Phase 5 tests) stays green.

2. **Exact Dockerfile `uv` base-image strategy: `ghcr.io/astral-sh/uv:python3.12-trixie-slim` as the runtime `FROM`, vs. plain `python:3.12-slim` + a `--mount=from=ghcr.io/astral-sh/uv` binary copy?**
   - What we know: Both are documented, valid approaches per the official uv Docker guide [CITED: docs.astral.sh/uv/guides/integration/docker/].
   - What's unclear: D-11 specifically names `python:3.12-slim` as the base (for the "no curl" HEALTHCHECK rationale) — it's unclear whether `ghcr.io/astral-sh/uv:python3.12-trixie-slim` (a Debian Trixie-based image, still without `curl` by default) is drop-in compatible with that rationale or whether it changes the base OS in a way that matters.
   - Recommendation: Use the `--mount=from=ghcr.io/astral-sh/uv,...` binary-copy approach on top of literal `python:3.12-slim`, since that most precisely matches D-11's exact base image naming and avoids introducing an unreviewed third-party base image tag as the `FROM` line.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Docker Engine | Building/running the image (DEPLOY-01, DEPLOY-02, DEPLOY-03) | ✓ [VERIFIED: `docker --version` this session] | 29.7.2 | — |
| Docker Desktop (Windows, WSL2 backend) | Bind mount correctness (D-01/D-02) | ✓ (implied by `docker info` succeeding this session) | — | — |
| Node.js | Local frontend build/dev (not container runtime) | ✓ [VERIFIED: `node --version` this session] | v22.13.0 (exceeds `next`'s `>=20.9.0` requirement; container uses `node:20-slim` per PLAN.md §11, independent of host version) | — |
| npm | `npm ci` locally and in Docker build stage | ✓ [VERIFIED: `npm --version` this session] | 11.0.0 | — |
| uv | Local backend dev + Docker build stage | ✓ [VERIFIED: `uv --version` this session] | 0.10.9 | — |
| Python | Backend dev/test locally (container uses `python:3.12-slim` independent of host) | ✓ [VERIFIED: `python --version` this session] | 3.13.1 (host; container pins 3.12 per `requires-python` and D-11) | — |

**Missing dependencies with no fallback:** None — all required tooling is present on the development machine.
**Missing dependencies with fallback:** None applicable.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ (backend, existing) [VERIFIED: `backend/pyproject.toml:17`, quoted: `"pytest>=8.0"`] — no dedicated Docker/infra test framework exists or is in scope this phase (that's Phase 6's `test/docker-compose.test.yml` + Playwright) |
| Config file | `backend/pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `cd backend && uv run pytest -x -q` |
| Full suite command | `cd backend && uv run pytest` (224 tests collected, confirmed this session) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|--------------------|-------------|
| DEPLOY-01 | Docker image builds successfully, serves frontend + API on port 8000 | manual/smoke (`docker build` + `docker run` + `curl`/browser check) | `docker build -t finally:latest . && docker run -p 8000:8000 --env-file .env finally:latest` then manual browser check | ❌ Wave 0 — no existing automation for Docker build verification; genuinely manual-only for this phase (Phase 6 owns the automated E2E/compose layer) |
| DEPLOY-02 | SQLite persists across container restart via bind mount | manual (`docker run` → trade → `docker stop` → `docker run` again → verify trade still present) | No automated command exists yet; manual verification recommended | ❌ Wave 0 |
| DEPLOY-03 | Start/stop scripts are idempotent | manual (run each script twice in a row, verify no error / correct no-op message both times) | No automated command; manual verification recommended | ❌ Wave 0 |
| DEPLOY-04 | `.env.example` documents all three variables | trivial/static (`grep` for each variable name in the committed file) | `grep -E "OPENROUTER_API_KEY|MASSIVE_API_KEY|LLM_MOCK" .env.example` | ❌ Wave 0 (file doesn't exist yet) |
| (regression) | `StaticFiles` mount doesn't break existing test suite | unit (existing) | `cd backend && uv run pytest -x -q` | ✓ (existing 224 tests; re-run after the one `main.py` code change) |

### Sampling Rate
- **Per task commit:** `cd backend && uv run pytest -x -q` (fast regression check after the `StaticFiles` mount change)
- **Per wave merge:** `cd backend && uv run pytest` (full suite) + manual `docker build`/`docker run` smoke test
- **Phase gate:** Full backend suite green, plus a successful manual end-to-end `docker run` → browser loads → trade persists across restart, before `/gsd-verify-work`

### Wave 0 Gaps
- No automated Docker build/run verification exists — this phase is inherently manual-verification-heavy for DEPLOY-01/02/03 since Phase 6 owns the E2E/compose automation layer (explicitly out of scope here per CONTEXT.md's `<domain>`). This is expected, not a gap to close within Phase 5 itself.
- If the planner resolves Open Question 1 by adding a guard/placeholder for the `static/` directory, a small unit test asserting `create_app()` doesn't raise when `static/` is absent would close that specific regression risk cheaply.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|----------------|---------|--------------------|
| V2 Authentication | No | Project has no auth by design (single-user, PLAN.md/REQUIREMENTS.md explicit out-of-scope item) |
| V3 Session Management | No | No sessions — stateless single-user model |
| V4 Access Control | No | Same as above |
| V5 Input Validation | No (not touched this phase) | Already handled by existing Pydantic models in routes; this phase makes no route changes |
| V6 Cryptography | No | No secrets are generated/stored by this phase; `.env` handling is existing `python-dotenv` behavior |
| V14 Configuration | Yes | `.env.example` must document required vars without ever containing real secret values (a placeholder string only, per PLAN.md §5's own example); `.dockerignore` must exclude `.env`/`db/*.db` from the build context to avoid accidentally baking secrets or user data into an image layer |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|------------------------|
| Secrets baked into a Docker image layer (e.g. a stray `COPY . .` before `.dockerignore` excludes `.env`) | Information Disclosure | `.dockerignore` explicitly excluding `.env`, `db/*.db`, `.git` (Pitfall 4); never `COPY .env` in the Dockerfile — the running container receives it only via `--env-file .env` at `docker run` time, never baked into the image |
| Bind-mounting the wrong host path (e.g. an unresolved relative path landing on an unintended directory) exposing unrelated host files into the container | Tampering / Information Disclosure | D-02's absolute-path resolution before mount (already locked, Pitfall 2) |
| A stale/incorrect `HEALTHCHECK` reporting the container healthy when the app has actually crashed | (Availability, not classic STRIDE) | D-11's `HEALTHCHECK` hitting the real `GET /api/health` endpoint (already implemented, returns `{"status": "ok"}`) rather than a trivial `CMD true`-style no-op check |

## Sources

### Primary (HIGH confidence)
- None fetched with HIGH-confidence provenance this session — no `context7`/`ref`/dedicated docs MCP tools were available in this session's toolset (all config flags for exa/brave/firecrawl/tavily/ref/jina/perplexity are `false` in `.planning/config.json`, and no MCP docs tools were present in the invoked toolset), so all docs research fell back to `WebSearch`/`WebFetch` (see `classify-confidence` seam output: `websearch` base=LOW, `webfetch` base=LOW, `websearch --verified`=MEDIUM).

### Secondary (MEDIUM confidence)
- [Next.js official docs — Static Exports guide](https://nextjs.org/docs/app/guides/static-exports) — fetched directly via WebFetch, official first-party source, cross-checked against the project's own `next.config.ts` comment
- [FastAPI official docs — Static Files](https://fastapi.tiangolo.com/tutorial/static-files/) — fetched directly via WebFetch, official first-party source (also the source that surfaced the refuted `app.frontend()` claim — the mount-ordering guidance itself was independently confirmed against Starlette's actual mount-priority behavior, which is standard/well-established)
- [uv official Docker integration guide](https://docs.astral.sh/uv/guides/integration/docker/) — fetched directly via WebFetch, official first-party source

### Tertiary (LOW confidence — WebSearch summaries, not independently fetched)
- Docker multi-stage build general pattern (various blog posts, cross-checked against well-established Docker documentation concepts)
- Dockerfile `HEALTHCHECK` option defaults (`--interval=30s`, `--timeout=30s`, `--start-period=0s`, `--retries=3`) — WebSearch summary only; attempted direct `WebFetch` of `docs.docker.com/reference/dockerfile/` and `docs.docker.com/engine/reference/builder/` both returned truncated content that didn't include the HEALTHCHECK section verbatim. These default values match well-established, widely-corroborated Docker knowledge but were not independently re-verified against the primary source this session — flag for the planner as a value to sanity-check against `docker --help` or the live Docker docs if precision matters (the planner's own Dockerfile syntax choices don't strictly require the *defaults*, since D-11 doesn't specify custom interval/timeout/retries values, only that a HEALTHCHECK exist calling `/api/health` via Python stdlib)
- `docker/for-win` WSL2 bind-mount GitHub issues (#7431, #7905) — found via WebSearch snippet, not independently fetched
- Bash/PowerShell idempotent Docker lifecycle scripting patterns — general, well-established CLI patterns, WebSearch-sourced
- The refuted `app.frontend()` claim itself — WebSearch surfaced it from dev.to/personal blogs; explicitly investigated and disproven via direct source reading (see Common Pitfalls, Pitfall 1) rather than relied upon

## Metadata

**Confidence breakdown:**
- Standard Stack: HIGH for version numbers and locked-file contents (directly read from `uv.lock`, `package.json`, `pyproject.toml`, and live tool version checks this session); MEDIUM for the general Docker/uv build pattern (official docs fetched, but `classify-confidence` seam scores raw `webfetch` LOW even when cross-checked — treated as MEDIUM per the CITED definition since sources are genuinely official documentation pages)
- Architecture: HIGH — directly derived from CONTEXT.md's locked decisions (D-01 through D-11) plus direct reads of `backend/app/main.py`, `backend/app/db/watchlist.py`, `frontend/next.config.ts`
- Pitfalls: MEDIUM-HIGH — Pitfall 1 (refuted `app.frontend()` claim) is independently verified via source-code reading, the strongest-confidence finding in this document; Pitfalls 2-4 are standard, well-corroborated but not independently re-verified this session

**Research date:** 2026-09-22
**Valid until:** 30 days (Docker/uv/Next.js tooling patterns here are stable; re-verify if `fastapi` or `next` are bumped to a materially newer minor version before this phase executes, given the `app.frontend()` hallucination risk specifically)
