#!/usr/bin/env bash
# Build (if needed) and run the FinAlly Docker container.
# Safe to run multiple times: reuses an existing image unless --build is
# passed, and replaces any existing container of the same name.
set -euo pipefail

cd "$(dirname "$0")/.."

IMAGE_NAME="finally"
CONTAINER_NAME="finally"
PORT="8000"
FORCE_BUILD=0

for arg in "$@"; do
  case "$arg" in
    --build) FORCE_BUILD=1 ;;
  esac
done

if [ ! -f .env ]; then
  echo "No .env file found — copying .env.example to .env."
  echo "Edit .env and add your OPENROUTER_API_KEY before using AI chat."
  cp .env.example .env
fi

if [ "$FORCE_BUILD" -eq 1 ] || ! docker image inspect "$IMAGE_NAME" >/dev/null 2>&1; then
  echo "Building $IMAGE_NAME image..."
  docker build -t "$IMAGE_NAME" .
fi

if docker ps -a --format '{{.Names}}' | grep -qx "$CONTAINER_NAME"; then
  echo "Removing existing $CONTAINER_NAME container..."
  docker rm -f "$CONTAINER_NAME" >/dev/null
fi

echo "Starting $CONTAINER_NAME..."
docker run -d \
  --name "$CONTAINER_NAME" \
  -p "$PORT:8000" \
  -v finally-data:/app/db \
  --env-file .env \
  "$IMAGE_NAME"

URL="http://localhost:$PORT"
echo "FinAlly is running at $URL"

if command -v open >/dev/null 2>&1; then
  open "$URL" || true
fi
