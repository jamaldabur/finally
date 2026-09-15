# syntax=docker/dockerfile:1

# ---- Stage 1: build the Next.js static export -----------------------------
FROM node:20-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build
# Next.js `output: 'export'` writes the static site to frontend/out

# ---- Stage 2: FastAPI backend + bundled static frontend --------------------
FROM python:3.12-slim AS backend
WORKDIR /app

RUN pip install --no-cache-dir uv

COPY backend/pyproject.toml backend/uv.lock ./backend/
WORKDIR /app/backend
RUN uv sync --frozen --no-dev

COPY backend/ ./

COPY --from=frontend-build /app/frontend/out /app/static

ENV FINALLY_DB_PATH=/app/db/finally.db
ENV PATH="/app/backend/.venv/bin:${PATH}"

EXPOSE 8000

# Invoke uvicorn directly (venv already on PATH) rather than via `uv run` —
# `uv run` re-syncs the environment on every container start (pulling in the
# dev dependency group and hitting the network), which is both slow and
# wrong for a frozen production image.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
