# Phase 5: Docker Packaging & Deployment - Pattern Map

**Mapped:** 2026-09-22
**Files analyzed:** 8 (Dockerfile, .dockerignore, .env.example, 4 scripts, main.py edit)
**Analogs found:** 2 / 8 (in-repo code analogs); 6 files are genuinely net-new infra with no in-repo precedent — this is expected for a "first packaging phase"

## Context

This phase is almost entirely **new infrastructure** (Dockerfile, `.dockerignore`, `.env.example`, 4 shell/PowerShell scripts) rather than application code. A repo-wide check confirmed **zero existing Dockerfile, docker-compose, `.sh`, or `.ps1` script anywhere in tracked source** (only vendored `node_modules`/`.venv` scripts exist, which are not analogs — they're third-party). RESEARCH.md's own Code Examples section (already vetted against CONTEXT.md's locked decisions D-01 through D-11) is therefore the primary pattern source for the net-new files, not an in-repo analog. The one genuine in-repo analog is for the single required code change to `backend/app/main.py`.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|-----------------|---------------|
| `backend/app/main.py` (edit: add `StaticFiles` mount) | config/route-wiring | request-response | `backend/app/main.py` itself (existing `create_app()`) | exact — editing in place, not a new file |
| `Dockerfile` | config (build) | batch (build-time transform) | none in-repo — RESEARCH.md Pattern 1 | no analog |
| `.dockerignore` | config | N/A | none in-repo — RESEARCH.md Pitfall 4 | no analog |
| `.env.example` | config | N/A | `planning/PLAN.md` §5 (env var doc, not code) | no code analog — doc-derived |
| `scripts/start_mac.sh` | utility (lifecycle script) | event-driven (CLI invocation) | none in-repo — RESEARCH.md Pattern 3 | no analog |
| `scripts/stop_mac.sh` | utility (lifecycle script) | event-driven (CLI invocation) | none in-repo — RESEARCH.md Pattern 3 | no analog |
| `scripts/start_windows.ps1` | utility (lifecycle script) | event-driven (CLI invocation) | none in-repo — RESEARCH.md "Idempotent PowerShell start check" | no analog |
| `scripts/stop_windows.ps1` | utility (lifecycle script) | event-driven (CLI invocation) | none in-repo | no analog |

## Pattern Assignments

### `backend/app/main.py` (config/route-wiring edit)

**Analog:** itself — `backend/app/main.py` lines 84-106 (`create_app()`), read in full this session.

**Imports pattern** (lines 10-26) — add one import alongside the existing route imports:
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# ADD:
from fastapi.staticfiles import StaticFiles

from .routes import chat, health, portfolio, stream
from .routes import watchlist as watchlist_routes
```

**Core wiring pattern — router registration order** (lines 84-106, exact text this session):
```python
def create_app() -> FastAPI:
    app = FastAPI(title="FinAlly", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(stream.router)
    app.include_router(portfolio.router)
    app.include_router(watchlist_routes.router)
    app.include_router(chat.router)
    return app
```

**Required change (D-04, RESEARCH.md Pattern 2):** append the `StaticFiles` mount as the *last* statement before `return app`, so it never shadows an `/api/*` route:
```python
    app.mount("/", StaticFiles(directory="static", html=True), name="static")
    return app
```

**Regression risk to carry into planning (RESEARCH.md Pitfall 3 / Open Question 1):** `backend/tests/test_main.py` already calls `create_app()` directly (confirmed tracked: `git ls-files -- backend/tests/test_main.py`). Starlette's `StaticFiles` constructor may validate `directory` exists at construction time, not lazily — if so, this mount will raise on every `uv run pytest` invocation where `backend/static/` doesn't exist (it only exists inside the built Docker image via `COPY --from=frontend-build`). The planner must decide explicitly: either commit an empty `backend/static/.gitkeep` placeholder so local/test runs never break, or guard the mount with an existence check. Do not silently skip this — it will break the existing 224-test suite otherwise.

**Env var pattern to reuse (no code change needed, cited for the Dockerfile author):** `backend/app/db/watchlist.py` lines 28-33 — the exact `FINALLY_DB_PATH` contract the Dockerfile/bind-mount must satisfy:
```python
# backend/app/db/watchlist.py:28-33
_DEFAULT_DB_PATH = Path(__file__).resolve().parents[3] / "db" / "finally.db"
DB_PATH = Path(os.environ.get("FINALLY_DB_PATH", str(_DEFAULT_DB_PATH)))
```
Either rely on this default (matching `WORKDIR`/copy layout so `parents[3]` still resolves to `/app`) or set `ENV FINALLY_DB_PATH=/app/db/finally.db` explicitly in the Dockerfile — RESEARCH.md recommends the explicit env var for clarity.

**Health check target (D-11), already implemented, zero changes needed:**
```python
# backend/app/routes/health.py — full file, 11 lines
@router.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
```

---

### `Dockerfile` (config, batch/build-time transform)

**No in-repo analog — use RESEARCH.md's vetted skeleton verbatim as the pattern source** (already cross-checked against PLAN.md §11 and D-01 through D-11):

```dockerfile
# Source: RESEARCH.md Pattern 1, PLAN.md §11 (Stage 1: Node 20 slim, Stage 2: Python 3.12 slim)
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

RESEARCH.md's Open Question 2 recommends the `--mount=from=ghcr.io/astral-sh/uv,...` binary-copy approach (not `FROM ghcr.io/astral-sh/uv:...` as the base) specifically because D-11 names `python:3.12-slim` literally for its "no curl" HEALTHCHECK rationale — keep the `FROM python:3.12-slim` line unchanged.

---

### `.dockerignore` (config)

**No in-repo analog — use RESEARCH.md Pitfall 4's list verbatim:**
```
**/node_modules
**/.venv
**/__pycache__
.git
db/*.db
frontend/out
test/node_modules
.pytest_cache
.env
```
Note: `.env` added per Security Domain guidance (V14) — never let real secrets enter the build context even though the Dockerfile doesn't `COPY .env`.

---

### `.env.example` (config)

**Source of truth:** `planning/PLAN.md` §5, quoted verbatim by RESEARCH.md's Code Examples section — copy exactly:
```bash
# Required: OpenRouter API key for LLM chat functionality
OPENROUTER_API_KEY=your-openrouter-api-key-here

# Optional: Massive (Polygon.io) API key for real market data
# If not set, the built-in market simulator is used (recommended for most users)
MASSIVE_API_KEY=

# Optional: Set to "true" for deterministic mock LLM responses (testing)
LLM_MOCK=false
```

---

### `scripts/start_mac.sh` / `scripts/stop_mac.sh` (utility, event-driven CLI)

**No in-repo analog — pattern source is RESEARCH.md Pattern 3 + Code Examples, per locked decisions D-02, D-06, D-07, D-08, D-09.**

Idempotent running-state check (RESEARCH.md Pattern 3):
```bash
CONTAINER_NAME="finally"
if [ -n "$(docker ps --filter "name=^${CONTAINER_NAME}$" --filter "status=running" -q)" ]; then
  echo "FinAlly is already running at http://localhost:8000"
  exit 0
fi
```

Absolute path resolution for the bind mount (D-02, quoted verbatim from CONTEXT.md):
```bash
DB_DIR="$(cd "$(dirname "$0")/.." && pwd)/db"
mkdir -p "$DB_DIR"
```

`.env` existence check (D-09) — no in-repo precedent; write as a simple guard before any `docker` invocation:
```bash
if [ ! -f ".env" ]; then
  echo "Error: .env not found. Copy .env.example to .env and fill in OPENROUTER_API_KEY." >&2
  exit 1
fi
```

Full `docker run` invocation shape (D-01, D-02, D-06):
```bash
docker run -d --name finally \
  -v "$DB_DIR:/app/db" \
  -p 8000:8000 \
  --env-file .env \
  finally:latest
```

`stop_mac.sh` mirrors the same running-state check inverted (D-07): no-op with a friendly message if not running, otherwise `docker stop finally` — never touches the bind-mounted `db/` (D-08).

---

### `scripts/start_windows.ps1` / `scripts/stop_windows.ps1` (utility, event-driven CLI)

**No in-repo analog — PowerShell equivalents of the bash scripts above, per RESEARCH.md's "Idempotent PowerShell start check" and D-02's PowerShell snippet.**

```powershell
$ContainerName = "finally"
$running = docker ps --filter "name=^$ContainerName$" --filter "status=running" -q
if ($running) {
    Write-Host "FinAlly is already running at http://localhost:8000"
    exit 0
}
```

Absolute path resolution (D-02) — note RESEARCH.md flags a real gotcha here: `Resolve-Path` throws if the target doesn't exist yet, so `New-Item -Force` must run before the final `Resolve-Path` call, or resolve the parent and append the `db` leaf afterward:
```powershell
$DbDir = Join-Path $PSScriptRoot "..\db"
New-Item -ItemType Directory -Force -Path $DbDir | Out-Null
$DbDir = (Resolve-Path $DbDir).Path
```

---

## Shared Patterns

### Env var loading (already implemented, zero changes)
**Source:** `backend/app/main.py` line 32 — `load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)`
**Apply to:** No file in this phase needs to duplicate this; it's already wired. Scripts only need to ensure `--env-file .env` reaches `docker run` (D-09 handles the pre-flight check; the Dockerfile does nothing extra).

### FINALLY_DB_PATH contract
**Source:** `backend/app/db/watchlist.py` lines 28-33 (quoted above)
**Apply to:** `Dockerfile` (optionally set `ENV FINALLY_DB_PATH=/app/db/finally.db`) and both start scripts (bind-mount target must be `/app/db`, matching D-01).

### Idempotent Docker CLI state detection
**Source:** RESEARCH.md Pattern 3 / "Idempotent PowerShell start check" (no in-repo precedent — first infra scripts in this repo)
**Apply to:** All four scripts — bash and PowerShell versions both filter on `--filter "name=^finally$" --filter "status=running" -q"` rather than parsing unfiltered `docker ps` output (RESEARCH.md Anti-Patterns explicitly warns against grep-based name matching).

### Health check target
**Source:** `backend/app/routes/health.py` (full file, unchanged) — `GET /api/health` returns `{"status": "ok"}`
**Apply to:** `Dockerfile`'s `HEALTHCHECK` instruction only; no code change.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `Dockerfile` | config | batch | Repo has zero prior Dockerfiles/compose files (verified via `git ls-files` — none found outside vendored `node_modules`/`.venv`). Use RESEARCH.md Pattern 1 as the vetted source instead. |
| `.dockerignore` | config | N/A | Same — none exists anywhere in the repo (RESEARCH.md Pitfall 4 confirms via `ls` this session). |
| `.env.example` | config | N/A | File confirmed not to exist yet (RESEARCH.md Code Examples section, verified via `ls .env.example` this session). Derive from PLAN.md §5 text, not code. |
| `scripts/start_mac.sh`, `stop_mac.sh` | utility | event-driven | No `.sh` scripts exist in tracked source at all. |
| `scripts/start_windows.ps1`, `stop_windows.ps1` | utility | event-driven | No `.ps1` scripts exist in tracked source at all. |

## Metadata

**Analog search scope:** Repo-wide `Glob` for `**/*.sh` and `**/*.ps1` (only vendored third-party scripts matched); `git ls-files` checks confirming tracked status of `backend/app/main.py`, `backend/app/db/watchlist.py`, `backend/app/routes/health.py`, `backend/tests/test_main.py`, `db/.gitkeep`, `.gitignore`, and confirming absence of any `Dockerfile`/`.dockerignore`/`.env.example` in tracked source.
**Files scanned:** `backend/app/main.py` (full, 109 lines), `backend/app/db/watchlist.py` (lines 1-45), `backend/app/routes/health.py` (full, 11 lines), plus RESEARCH.md's already-vetted Code Examples (which cross-reference `frontend/next.config.ts`, `backend/pyproject.toml`, `backend/uv.lock` — not re-read here since RESEARCH.md already quotes them verbatim with line numbers).
**Pattern extraction date:** 2026-09-22
