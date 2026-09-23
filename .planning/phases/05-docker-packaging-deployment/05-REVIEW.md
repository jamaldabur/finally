---
phase: 05-docker-packaging-deployment
reviewed: 2026-09-23T00:00:00Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - .dockerignore
  - backend/app/main.py
  - backend/tests/test_main.py
  - scripts/start_mac.sh
  - scripts/start_windows.ps1
findings:
  critical: 0
  warning: 1
  info: 1
  total: 2
status: issues_found
---

# Phase 5: Code Review Report

**Reviewed:** 2026-09-23T00:00:00Z
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found

## Summary

Re-reviewed the five files touched by gap-closure plan 05-03, which claimed to fix four findings from the prior 05-REVIEW.md (CR-01 dotenv-variant leakage, WR-01 unawaited shutdown tasks, WR-02 unbounded bash readiness curl, WR-03 `Write-Error` under `$ErrorActionPreference = "Stop"`). I independently verified each fix against the current file contents and, where the fix's correctness depended on behavior of code outside these five files, read that code too (`app/market/loop.py`, `app/portfolio/snapshots.py`, `app/market/massive.py`, `Dockerfile`, `frontend/next.config.ts`, `frontend/lib/api.ts`) rather than trusting the plan's own claims.

**All four prior findings are genuinely and completely fixed:**

- **CR-01 (dotenv leak):** `.dockerignore` now reads `**/.env` / `**/.env.*` / `!**/.env.example`. I confirmed on disk that `frontend/.env.development.local` exists (the exact file the prior review used as its proof-of-concept) and that it is matched by `**/.env.*` at every depth, and that `.env.example` is correctly re-included by the negation ordered after the broad exclusion (Docker's last-match-wins semantics). I also confirmed the frontend build does not require any `.env.production`/`.env.local` file to be present — `NEXT_PUBLIC_API_BASE_URL` defaults to `""` (same-origin) in both `lib/api.ts` and `lib/priceStore.tsx` — so excluding these files from the build context cannot break `npm run build` inside the `frontend-build` stage.
- **WR-01 (unawaited shutdown tasks):** `backend/app/main.py` now does `await asyncio.gather(update_task, snapshot_task, return_exceptions=True)` before `await source.stop()`. I confirmed both `run_update_loop` (`app/market/loop.py:36`) and `run_portfolio_snapshot_loop` (`app/portfolio/snapshots.py:34`) catch only `Exception`, not `BaseException`, so `CancelledError` (a `BaseException` subclass) always propagates out and the `gather(..., return_exceptions=True)` cannot hang. The new regression test (`test_lifespan_awaits_background_tasks_before_stopping_source`) exercises the real race with a source whose `get_prices()` parks in `asyncio.sleep(3600)` and asserts `stop()` observes `in_flight is False` and the snapshot task already `done()` — this is a real, non-tautological test of the fix, not just a mock-call assertion.
- **WR-02 (unbounded bash readiness curl):** `scripts/start_mac.sh` now uses `curl -fsS --max-time 2 ...`, matching `start_windows.ps1`'s pre-existing `-TimeoutSec 2`. The updated comment's worst-case math (40 × (2s + 1s) ≈ 120s) checks out.
- **WR-03 (`Write-Error` under `Stop`):** all four `Write-Error` call sites in `scripts/start_windows.ps1` (`.env` guard, Docker-not-running, build failure, run failure, readiness failure — five sites total, all four originally flagged plus the pre-existing `docker run failed` site) are now `[Console]::Error.WriteLine(...)`, which writes directly to the process's stderr handle without going through PowerShell's error stream, so it cannot become a terminating error under `$ErrorActionPreference = "Stop"`. `exit 1` is reachable again on every path. Verified no `Write-Error` calls remain in the file (the one remaining textual match is inside the explanatory comment, not code).

No new BLOCKER-level issues were introduced by this change set. Two residual/new items below.

## Warnings

### WR-04: `start_windows.ps1` has no argument-validation step, unlike its bash counterpart, so a bad invocation prints a raw PowerShell error instead of a usage message

**File:** `scripts/start_windows.ps1:7` (whole-file gap, no corresponding step)
**Issue:** `start_mac.sh` has an explicit, commented "1. Argument validation" step (`start_mac.sh:38-56`) that exact-matches `""` or `--build` and otherwise prints `Usage: $0 [--build]` to stderr and exits 1 — this is exactly the same category of fix WR-03 just addressed (a clean, predictable stderr message on bad input). `start_windows.ps1` has no equivalent step; it relies solely on `param([switch]$Build)` for argument handling. If a caller passes anything PowerShell's binder can't resolve against that single switch parameter (e.g. `.\start_windows.ps1 --build` — the bash-style long flag, an easy mistake given the two scripts are documented as having "identical step order" — or any stray positional token), PowerShell raises a `ParameterBindingException` *before* the script body (and its `$ErrorActionPreference = "Stop"`) ever executes, printing the same kind of raw error-record block (message, `At <file>:<line>`, `CategoryInfo`, `FullyQualifiedErrorId`) that WR-03 just eliminated from the script's own explicit error paths — just from a code path this diff didn't touch. This directly undercuts the file's header claim of parity ("identical step order... in PowerShell") and the very rationale WR-03 was fixed for.
**Fix:** Add an explicit switch-parse guard mirroring the bash script's step 1, e.g. validate `$args`/extra positional tokens before relying on PowerShell's implicit binding, or at minimum wrap the script body's entry in a `try/catch` that catches `System.Management.Automation.ParameterBindingException` and writes a clean `Usage: start_windows.ps1 [-Build]` message via `[Console]::Error.WriteLine` before `exit 1`.

## Info

### IN-03: WR-03's rationale comment is anchored to only the first of five replaced call sites

**File:** `scripts/start_windows.ps1:63-72`
**Issue:** The comment block explaining why `Write-Error` was replaced with `[Console]::Error.WriteLine` (and why `Write-Host`/scoped `$ErrorActionPreference` were rejected) sits once, immediately before the `.env` guard's error path (the first of five sites this pattern now appears at: `.env` guard, Docker-not-running, build failure, run failure, readiness failure). A future contributor reading only one of the later four sites in isolation (e.g. while debugging the readiness-failure path at the bottom of the file) won't see this rationale and could "simplify" one of them back to `Write-Error` without realizing why it regresses.
**Fix:** Either move the comment to sit directly above `Invoke-Docker`/near the top of the script as a file-level convention note, or add a one-line back-reference (`# See rationale near the .env guard above`) at each of the other four sites.

---

_Reviewed: 2026-09-23T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
