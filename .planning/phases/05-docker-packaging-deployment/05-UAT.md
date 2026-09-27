---
status: complete
phase: 05-docker-packaging-deployment
source: [05-01-SUMMARY.md, 05-02-SUMMARY.md, 05-03-SUMMARY.md, 05-04-SUMMARY.md, 05-05-SUMMARY.md]
started: 2026-09-27T13:28:34Z
updated: 2026-09-27T15:45:03Z
---

## Current Test

[testing complete]

## Tests

### 1. Cold Start Smoke Test
expected: Kill any running FinAlly container, start fresh via `scripts/start_windows.ps1`, and confirm `http://localhost:8000/api/health` returns `{"status":"ok"}` and the app is reachable with no manual Docker steps.
result: pass

### 2. macOS/Linux launcher pair (start_mac.sh / stop_mac.sh)
expected: On a real macOS or Linux host, `start_mac.sh` builds/starts the container and the app answers at http://localhost:8000; `stop_mac.sh` stops it cleanly; both reject unrecognised arguments and never touch `.env` contents or `db/`. (Structural checks and non-launch live checks already passed on this Windows dev machine per 05-02-SUMMARY.md D5 — the actual `docker run` launch path via the bash script has not been exercised on a real macOS/Linux host.)
result: pass

### 3. start_windows.ps1 rejects unrecognised arguments before touching Docker
expected: An unrecognised argument (e.g. `--build`, `--totally-bogus-flag`) to `start_windows.ps1` prints a usage message and exits 1 before any Docker command runs.
result: pass

### 4. VERIFICATION.md's three reproduction cases stay rejected
expected: `--build`, `--totally-bogus-flag`, and `--i-am-not-a-real-flag` are each rejected, and the running container's ID/StartedAt are unchanged afterward.
result: pass

### 5. Bare start and -Build (any case) behave exactly as documented
expected: A bare `start_windows.ps1` invocation starts (or reports already running); `-Build`/`-build`/`-BUILD` all trigger a rebuild-and-replace of the container.
result: pass

### 6. -File and in-session invocation agree on accept/reject
expected: The same token is accepted or rejected identically whether the script is run via `-File` or invoked in-session with the call operator.
result: pass

### 7. Argument validation runs before the .env guard
expected: In both `start_windows.ps1` and `stop_windows.ps1`, an invalid-argument rejection happens before the script ever checks for `.env`.
result: pass

### 8. stop_windows.ps1 rejects arguments before contacting Docker; stays idempotent
expected: `stop_windows.ps1` with any argument is rejected before the Docker daemon is contacted; a bare stop is idempotent (safe to run twice) and never touches `db/`.
result: pass

### 9. No error-record dumps, pure ASCII, stable step order
expected: Rejections print a plain usage line (no PowerShell error-record block), both scripts contain only ASCII bytes, and no unrelated step was reordered.
result: pass

### 10. 05-REVIEW.md's WR-04 correction is recorded without deleting history
expected: `05-REVIEW.md`'s WR-04 entry has an appended correction (original prediction preserved verbatim) describing the real failure mode, root cause, and the fix of record; frontmatter and other entries are untouched.
result: pass

### 11. One Docker image serves frontend + all API routes on port 8000
expected: One `docker build` produces a single image; the running container serves the Next.js frontend and every `/api/*` route on port 8000.
result: pass
source: automated
coverage_id: D1

### 12. SQLite persists across container replacement
expected: Data written via the API survives `docker rm -f` + a fresh `docker run` against the same `db/` bind mount.
result: pass
source: automated
coverage_id: D2

### 13. .env.example is committed and placeholder-only
expected: `.env.example` documents `OPENROUTER_API_KEY`, `MASSIVE_API_KEY`, `LLM_MOCK` with placeholder values only, is not gitignored.
result: pass
source: automated
coverage_id: D3

### 14. Static mount never breaks a frontend-less checkout or shadows /api/*
expected: The app starts fine with no frontend build present, serves the index when present, and `/api/*` always wins over the static mount.
result: pass
source: automated
coverage_id: D4

### 15. Windows: single command reaches a running app
expected: Running `start_windows.ps1` with no Docker knowledge required results in the app reachable at http://localhost:8000.
result: pass
source: automated
coverage_id: D1

### 16. Windows: repeated start is a visible no-op
expected: Running `start_windows.ps1` again while already up prints "already running", exits 0, and never creates a second container.
result: pass
source: automated
coverage_id: D2

### 17. Windows: -Build replaces the running container
expected: `start_windows.ps1 -Build` while up performs a real rebuild-and-replace (new container ID/StartedAt), and the app answers afterward.
result: pass
source: automated
coverage_id: D3

### 18. Windows: stop is idempotent and db/ survives
expected: `stop_windows.ps1` and a repeated stop both exit 0; `db/finally.db` survives the full start/start/-Build/stop/stop sequence untouched.
result: pass
source: automated
coverage_id: D4

### 19. CR-01 closed: secrets never enter the Docker build context
expected: No `.env*` file (other than `.env.example`) is present anywhere in the build context, any build stage, or the final runtime image.
result: pass
source: automated
coverage_id: D1

### 20. WR-01 closed: clean shutdown waits for in-flight background tasks
expected: Lifespan shutdown awaits the update/snapshot background tasks before stopping the market data source — no in-flight work is abandoned.
result: pass
source: automated
coverage_id: D2

### 21. WR-02 closed: consistent readiness-check timeout across launchers
expected: Every readiness curl in `start_mac.sh` uses the same 2-second timeout as `start_windows.ps1`.
result: pass
source: automated
coverage_id: D3

### 22. WR-03 closed: usage errors print correctly instead of raw error records
expected: All `start_windows.ps1` failure paths print a clean message via `[Console]::Error.WriteLine` (not a raw PowerShell error dump) and exit 1.
result: pass
source: automated
coverage_id: D4

### 23. Colon-token bypass closed in start_windows.ps1
expected: `-Foo:`, `-Build:`, and `-Build -Foo:` are all rejected before Docker is touched; documented invocations (bare start, `-Build` any case) still work.
result: pass
source: automated
coverage_id: D1

### 24. Colon-token bypass closed in stop_windows.ps1 (the live exploit)
expected: `-Foo:`, `-AnyName:`, `-Force:` are rejected before the daemon is contacted — the previously-live exploit (an unintended `docker stop` against a running container) no longer occurs.
result: pass
source: automated
coverage_id: D2

### 25. 05-REVIEW.md records CR-01/WR-01/IN-01 resolution
expected: Each of CR-01, WR-01, IN-01 carries a "Resolved by 05-05" note and a shared resolution paragraph; prior review history is untouched.
result: pass
source: automated
coverage_id: D3

## Summary

total: 25
passed: 25
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none yet]
