#!/usr/bin/env bash
# Stop and remove the FinAlly container. Does NOT remove the data volume —
# your portfolio/watchlist persist across restarts. Safe to run repeatedly.
set -euo pipefail

CONTAINER_NAME="finally"

if docker ps -a --format '{{.Names}}' | grep -qx "$CONTAINER_NAME"; then
  echo "Stopping and removing $CONTAINER_NAME..."
  docker rm -f "$CONTAINER_NAME" >/dev/null
  echo "Stopped."
else
  echo "$CONTAINER_NAME is not running."
fi
