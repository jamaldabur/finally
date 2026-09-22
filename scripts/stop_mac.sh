#!/usr/bin/env bash
# Idempotent stopper for FinAlly (PLAN.md §11, DEPLOY-03).
#
# Never removes, prunes, moves, or truncates anything — stopping FinAlly
# must never be destructive to the user's portfolio (D-08).
set -euo pipefail

CONTAINER_NAME="finally"

# Resolve the repository root from this script's own location, not the
# caller's working directory — matches start_mac.sh's constants exactly.
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# 1. Accept zero arguments only.
if [ "$#" -gt 0 ]; then
  echo "Usage: $0" >&2
  exit 1
fi

# 2. If the daemon isn't reachable, FinAlly definitionally is not running.
if ! docker info >/dev/null 2>&1; then
  echo "FinAlly is not running (Docker does not appear to be running)."
  exit 0
fi

# 3. Query the same anchored running filter used by start_mac.sh (D-07).
RUNNING_ID="$(docker ps --filter "name=^${CONTAINER_NAME}$" --filter "status=running" -q)"
if [ -z "$RUNNING_ID" ]; then
  echo "FinAlly is not running."
  exit 0
fi

# 4. Stop it. The data in db/ is left untouched.
docker stop "$CONTAINER_NAME" >/dev/null
echo "FinAlly is stopped. The data in ${REPO_ROOT}/db has been left untouched."
exit 0
