---
phase: 05-docker-packaging-deployment
reviewed: 2026-09-22T00:00:00Z
depth: standard
files_reviewed: 9
files_reviewed_list:
  - .dockerignore
  - .env.example
  - Dockerfile
  - backend/app/main.py
  - backend/tests/test_main.py
  - scripts/start_mac.sh
  - scripts/start_windows.ps1
  - scripts/stop_mac.sh
  - scripts/stop_windows.ps1
findings:
  critical: 1
  warning: 3
  info: 2
  total: 6
status: issues_found
---

# Phase 5: Code Review Report

**Reviewed:** 2026-09-22T00:00:00Z
**Depth:** standard
**Files Reviewed:** 9
**Status:** issues_found

## Summary

Reviewed the Docker packaging/deployment surface: `.dockerignore`, `.env.example`, `Dockerfile`, `backend/app/main.py`, `backend/tests/test_main.py`, and the four start/stop scripts. Most of this code is careful and well-commented — the idempotency logic in the start/stop scripts, the static-mount ordering guard in `main.py`, and the multi-stage Dockerfile layering are all sound. However, I found one concrete, verified secrets-exposure gap in `.dockerignore` that directly contradicts its own stated security rationale, plus real async-shutdown and cross-platform-script robustness issues.

Verification performed beyond static reading: confirmed via `git status --porcelain --ignored=matching` that `frontend/.env.development.local` currently exists on disk and is git-ignored (correctly, by `frontend/.gitignore`'s broad `.env*` pattern) but is **not** excluded by the root `.dockerignore`, whose pattern is the narrower literal `.env`. Also empirically reproduced the `Write-Error` + `$ErrorActionPreference = "Stop"` termination behavior in `start_windows.ps1` with a standalone PowerShell script to confirm it aborts before reaching the following `exit 1` and prints a full exception/stack trace rather than a clean message.

## Critical Issues

### CR-01: `.dockerignore`'s `.env` pattern does not cover `.env.*` variants, leaking secrets into a Docker image layer

**File:** `.dockerignore:15` (combined with `Dockerfile:10`)
**Issue:** The `.dockerignore` header explicitly states its purpose: "Keeps ... secrets ... out of the build context and every image layer (ASVS V14)." Its env-file exclusion is a single literal line:

```
.env
```

Docker's ignore-pattern matching (like `.gitignore`) treats an unslashed pattern with no wildcard as an exact basename match at any depth — it does **not** match `.env.local`, `.env.development.local`, `.env.production`, etc. `frontend/.gitignore` itself acknowledges this class of file exists locally, via its own broad `.env*` (with a `!.env.example` carve-out) pattern — and indeed, `frontend/.env.development.local` exists on disk in this checkout right now (confirmed via `git status --porcelain --ignored=matching`, which lists it as `!!  frontend/.env.development.local`, i.e. present and gitignored but not dockerignored).

`Dockerfile:10` does `COPY frontend/ ./` in the `frontend-build` stage — a full recursive copy of the frontend source tree into the Docker build context and then into that stage's image layer. Because `.dockerignore` fails to exclude `.env.development.local`-style files, any secret placed in such a file (e.g. a locally-configured `NEXT_PUBLIC_*` key, a dev API token, anything a contributor drops into a Next.js `.env.local`/`.env.development.local` for local iteration) is copied into the `frontend-build` stage's filesystem layer. Even though the final runtime stage only copies `/app/frontend/out` out of that stage (so the file itself isn't in the shipped image), the `frontend-build` stage's layers persist in the local build cache and in any exported/pushed build cache, and are directly inspectable by anyone who can run `docker build --target frontend-build` + `docker run/exec`, or `docker history`/layer export against a cached build. This is a real, demonstrated gap between the file's own stated intent and its actual behavior, not a hypothetical.

**Fix:**
```
# .dockerignore
# Broaden from a literal ".env" to every dotenv variant, still keeping the
# committed template.
**/.env
**/.env.*
!**/.env.example
```
(Equivalently: `.env*` plus `!.env.example` at every depth, mirroring `frontend/.gitignore`'s own pattern.)

## Warnings

### WR-01: Background tasks are cancelled but never awaited before tearing down shared resources on shutdown

**File:** `backend/app/main.py:90-92`
**Issue:**
```python
update_task.cancel()
snapshot_task.cancel()
await source.stop()
```
`Task.cancel()` only *schedules* delivery of `CancelledError` at the task's next suspension point — it does not block until the task has actually unwound. Immediately calling `await source.stop()` afterward can run concurrently with `update_task` still mid-flight inside `source.get_prices()`. For `MassiveMarketDataSource` (`backend/app/market/massive.py`), `stop()` calls `await self._client.aclose()` on the same `httpx.AsyncClient` that `update_task` may still be awaiting a response from inside `get_prices()` — a live race between "close the client" and "still using the client." The resulting exception is an `Exception` subclass (not `CancelledError`), so `run_update_loop`'s `except Exception: logger.exception(...)` in `backend/app/market/loop.py` will catch and log it as a spurious "market data update loop iteration failed" on every shutdown when running against Massive, and in the worst case an unawaited, still-pending task can trigger asyncio's "Task was destroyed but it is pending!" warning.

**Fix:** Await the cancelled tasks (swallowing `CancelledError`) before releasing resources they depend on:
```python
update_task.cancel()
snapshot_task.cancel()
await asyncio.gather(update_task, snapshot_task, return_exceptions=True)
await source.stop()
```

### WR-02: `start_mac.sh`'s readiness poll can hang indefinitely on a single attempt, unlike its Windows counterpart

**File:** `scripts/start_mac.sh:112`
**Issue:** The readiness loop is documented as "roughly forty attempts, one second apart" (line 109), implying a bounded ~40-second wait. But:
```bash
if curl -fsS "${APP_URL}/api/health" >/dev/null 2>&1; then
```
has no `--max-time` or `--connect-timeout`. If the container accepts the TCP connection but the FastAPI process hangs mid-response (e.g. stuck in `init_db()` deadlock, not crashed, not refusing connections), a single `curl` invocation can block far longer than the intended 1-attempt-per-second cadence, silently blowing through the documented timeout budget. `scripts/start_windows.ps1:137` correctly bounds each attempt with `-TimeoutSec 2` — the two platform scripts are meant to have "identical step order" (per both files' header comments) but diverge here in a way that changes actual behavior, not just phrasing.

**Fix:**
```bash
if curl -fsS --max-time 2 "${APP_URL}/api/health" >/dev/null 2>&1; then
```

### WR-03: `Write-Error` under `$ErrorActionPreference = "Stop"` aborts `start_windows.ps1` with a raw exception dump, and makes the following `exit 1` unreachable

**File:** `scripts/start_windows.ps1:66, 74, 105, 148`
**Issue:** `$ErrorActionPreference = "Stop"` (line 9) promotes `Write-Error` from a non-terminating to a terminating error. Every one of the four error paths in this script follows the pattern:
```powershell
Write-Error "Error: .env not found at $EnvFile`n..."
exit 1
```
I verified this empirically: a minimal repro script (`$ErrorActionPreference = "Stop"; Write-Error "msg"; Write-Host "unreachable"; exit 1`) terminates at the `Write-Error` call — the `Write-Host` line never executes — and PowerShell prints a full `WriteErrorException` block (message, `At <file>:<line>`, `CategoryInfo`, `FullyQualifiedErrorId`) rather than the clean single-line stderr message the bash counterpart (`echo "Error: ..." >&2; exit 1`) produces. The exit code does still end up `1` in this case, so the *contract* (nonzero exit) holds, but (a) the four `exit 1` statements are dead code, and (b) the actual console output is a stack-trace-shaped error block instead of the intended user-facing one-liner — a real UX regression relative to the bash script's deliberately plain messaging, and easy to miss because the exit code still "looks right" in casual testing.

**Fix:** Either scope `$ErrorActionPreference` around the message, or switch to a non-terminating output call for these user-facing messages:
```powershell
$prevEap = $ErrorActionPreference
$ErrorActionPreference = "Continue"
Write-Error "Error: .env not found at $EnvFile`n..."
$ErrorActionPreference = $prevEap
exit 1
```
or simply use `[Console]::Error.WriteLine(...)` / `Write-Host ... -ForegroundColor Red` (to stderr) instead of `Write-Error`, matching the plain-text style already used for the success-path `Write-Host` calls.

## Info

### IN-01: Dockerfile does not set `PYTHONUNBUFFERED=1`

**File:** `Dockerfile:1-63`
**Issue:** Python's stdout is block-buffered when not attached to a TTY (as is the case under `docker run -d`/`docker logs`), which can delay or reorder log output from the uvicorn process relative to when it was actually emitted — a minor but common source of confusion when debugging a running container (e.g. via `docker logs -f` while reproducing an issue live).
**Fix:**
```dockerfile
ENV PYTHONUNBUFFERED=1
```

### IN-02: Container runs as root (documented tradeoff, noted for completeness)

**File:** `Dockerfile:57-62`
**Issue:** The image has no `USER` directive, so the process runs as root inside the container. The comment at lines 58-62 explicitly documents this as an accepted tradeoff (T-05-04) given the bind-mount ownership constraints across macOS/Linux/Windows hosts and the single-user local-demo scope — this is not flagged as an oversight, just recorded for defense-in-depth awareness since it is a standard hardening checklist item reviewers are expected to consider.
**Fix:** No action required given the documented rationale; if this project is ever adapted for multi-user or externally-reachable deployment, revisit with a non-root `USER` plus a documented ownership/UID-mapping story for the `db/` bind mount.

---

_Reviewed: 2026-09-22T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
