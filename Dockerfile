# Multi-stage build (PLAN.md §11): Stage 1 builds the Next.js static export,
# Stage 2 is the Python runtime that serves both that export and every
# /api/* route on a single port (DEPLOY-01). Build context is the repo root.

FROM node:20-slim AS frontend-build
WORKDIR /app/frontend
# Dependency layer first so it's cached independently of source changes.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build
# next.config.ts's `output: "export"` produces /app/frontend/out.

FROM python:3.12-slim AS runtime
WORKDIR /app

# P-01: get the pinned `uv` binary into a plain python:3.12-slim base via
# the canonical COPY --from= form (docs.astral.sh/uv/guides/integration/docker),
# rather than FROM ghcr.io/astral-sh/uv:... directly — keeps D-11's literal
# python:3.12-slim base (its "no curl" HEALTHCHECK rationale) intact and
# needs no BuildKit mount syntax. Pinned to the locally installed uv version.
COPY --from=ghcr.io/astral-sh/uv:0.10.9 /uv /bin/uv

ENV UV_LINK_MODE=copy

# Dependency layer cached independently of application source.
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# Install the project itself once application source is present.
COPY backend/app ./app
RUN uv sync --frozen --no-dev

# Frontend build output lands at /app/static — exactly where
# backend/app/main.py's STATIC_DIR (parents[1] from /app/app/main.py)
# resolves to (D-04).
COPY --from=frontend-build /app/frontend/out ./static

ENV PATH="/app/.venv/bin:$PATH"

# Mandatory, not a nicety: app/db/watchlist.py's default DB path is
# Path(__file__).resolve().parents[3] / "db" / "finally.db", which from
# this image's /app/app/db/watchlist.py walks to /db/finally.db — outside
# the bind mount at /app/db. Without this explicit override the app
# silently writes a database that disappears on `docker rm` (DEPLOY-02).
ENV FINALLY_DB_PATH=/app/db/finally.db

EXPOSE 8000

# D-11: python:3.12-slim ships no curl, so the probe uses Python's stdlib
# against the real health endpoint (not a bare TCP check or CMD true) so a
# crashed application can never report healthy. --start-period covers the
# lifespan's six init_db() calls and the market source start.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"

# Exec form, binding 0.0.0.0 so the published port reaches the process.
# Runs as the image's default root user: the D-01 bind mount must stay
# writable by the host user across macOS/Linux/Windows, and a non-root
# container UID that doesn't match the host owner of db/ would break
# DEPLOY-02 on Linux hosts — accepted deliberately (T-05-04), not an
# oversight, given the single-user local-demo scope (PLAN.md §3).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
