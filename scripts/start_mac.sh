#!/usr/bin/env bash
# Idempotent launcher for FinAlly (PLAN.md §11, DEPLOY-03).
#
# Order of operations is part of the contract: each step exists to fail
# before the next one can fail confusingly. See
# .planning/phases/05-docker-packaging-deployment/05-02-PLAN.md Task 1.
set -euo pipefail

IMAGE_TAG="finally:latest"
CONTAINER_NAME="finally"
HOST_PORT=8000
APP_URL="http://localhost:8000"

# Resolve the repository root from this script's own location, never the
# caller's working directory (D-02).
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# 1. Argument validation, before anything else. Exact-equality match only —
# no prefix/glob test — so an unrecognised argument can never reach a
# docker invocation.
BUILD_FLAG=false
case "${1-}" in
  "")
    ;;
  --build)
    BUILD_FLAG=true
    ;;
  *)
    echo "Usage: $0 [--build]" >&2
    exit 1
    ;;
esac
if [ "$#" -gt 1 ]; then
  echo "Usage: $0 [--build]" >&2
  exit 1
fi

# 2. .env guard (D-09). Existence only — never read, print, or source it.
if [ ! -f "$REPO_ROOT/.env" ]; then
  echo "Error: .env not found at $REPO_ROOT/.env" >&2
  echo "Copy .env.example to .env and fill in OPENROUTER_API_KEY before starting FinAlly." >&2
  exit 1
fi

# 3. Daemon reachability. Only the exit status matters.
if ! docker info >/dev/null 2>&1; then
  echo "Error: Docker does not appear to be running. Start Docker Desktop (or the Docker daemon) and try again." >&2
  exit 1
fi

# 4. Already-running check (D-07), anchored name + status filter so an
# unrelated container whose name merely contains the word is never matched.
RUNNING_ID="$(docker ps --filter "name=^${CONTAINER_NAME}$" --filter "status=running" -q)"
if [ -n "$RUNNING_ID" ]; then
  if [ "$BUILD_FLAG" = false ]; then
    echo "FinAlly is already running at ${APP_URL}"
    exit 0
  fi
  # P-02: an explicit rebuild wins over "already running".
  echo "Explicit rebuild requested — stopping the running container before rebuilding."
  docker rm -f "$CONTAINER_NAME" >/dev/null
fi

# 5. Clear any stopped container of the same name so `docker run --name`
# doesn't fail with a name collision. The container holds no state.
STOPPED_ID="$(docker ps -a --filter "name=^${CONTAINER_NAME}$" -q)"
if [ -n "$STOPPED_ID" ]; then
  docker rm -f "$CONTAINER_NAME" >/dev/null
fi

# 6. Build if needed (D-06).
if [ "$BUILD_FLAG" = true ] || ! docker image inspect "$IMAGE_TAG" >/dev/null 2>&1; then
  echo "Building ${IMAGE_TAG} — this may take several minutes on a first run."
  docker build -t "$IMAGE_TAG" "$REPO_ROOT"
fi

# 7. Resolve and create the mount source (D-02). Created before mounting so
# Docker doesn't create it itself with daemon-owned permissions.
DB_DIR="$REPO_ROOT/db"
mkdir -p "$DB_DIR"

# 8. Run.
docker run -d --name "$CONTAINER_NAME" \
  -p "${HOST_PORT}:8000" \
  --env-file "$REPO_ROOT/.env" \
  -v "$DB_DIR:/app/db" \
  "$IMAGE_TAG" >/dev/null

# 9. Wait for readiness — roughly forty attempts, one second apart.
READY=false
for _ in $(seq 1 40); do
  if curl -fsS "${APP_URL}/api/health" >/dev/null 2>&1; then
    READY=true
    break
  fi
  sleep 1
done
if [ "$READY" = false ]; then
  echo "FinAlly's container started but never became healthy." >&2
  echo "Check the logs with: docker logs ${CONTAINER_NAME}" >&2
  exit 1
fi

# 10. Print the URL, then best-effort browser open (D-08). Must never fail
# the script — a headless machine, CI runner, or missing opener still
# leaves a successful start successful.
echo "FinAlly is running at ${APP_URL}"
if command -v open >/dev/null 2>&1; then
  open "$APP_URL" >/dev/null 2>&1 || true
elif command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$APP_URL" >/dev/null 2>&1 || true
fi

exit 0
