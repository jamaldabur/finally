---
phase: 05-docker-packaging-deployment
plan: 02
subsystem: infra
tags: [bash, powershell, docker, cli-scripting, idempotency, deployment]

requires:
  - phase: 05-docker-packaging-deployment
    provides: "finally:latest image, .env.example, bind-mount host path pattern (05-01)"
provides:
  - "scripts/start_mac.sh and scripts/stop_mac.sh: idempotent bash launcher/stopper for macOS/Linux"
  - "scripts/start_windows.ps1 and scripts/stop_windows.ps1: idempotent PowerShell launcher/stopper for Windows, live-round-trip proven"
affects: [phase-06-testing]

actuals:
  tokens: 3734
  tasks: 2
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Invoke-Docker PowerShell helper: scopes $ErrorActionPreference to \"Continue\" for a single native docker call, then checks $LASTEXITCODE explicitly — avoids Docker Desktop's benign WSL2 stderr warnings being treated as terminating errors under a script-wide $ErrorActionPreference = \"Stop\""
    - "All docker CLI args passed to Invoke-Docker via an explicit -DockerArgs array bound to a named parameter, never as loose positional tokens — a bare \"-p\" token partial-matches the advanced function's implicit -PipelineVariable common parameter and collides with docker's own -p (publish port) flag"
    - "Bounded poll-until-gone after docker rm -f (both bash and PowerShell) before any run/build step proceeds — docker rm -f can return before the daemon fully releases a container name/port, especially for a container with an in-flight HEALTHCHECK exec"
    - "PowerShell scripts kept to plain ASCII only — Windows PowerShell 5.1's -File invocation reads a BOM-less script using the system codepage, not UTF-8, and non-ASCII characters corrupt execution without a parse-time error"

key-files:
  created:
    - scripts/start_mac.sh
    - scripts/stop_mac.sh
    - scripts/start_windows.ps1
    - scripts/stop_windows.ps1

key-decisions:
  - "Bind-mount argument on PowerShell built by concatenation ($DbDir + \":/app/db\") rather than inline string interpolation, so a colon immediately after the variable can't be misread as part of the variable name — the exact form: $mountArg = $DbDir + \":/app/db\"; then -v $mountArg"
  - "Measured readiness-poll duration on this machine: the full first start (image already built, `docker run` to healthy) completed in 19s, well inside the ~40s bound (40 attempts x 1s); no evidence yet that the 40-attempt bound needs tightening or loosening"
  - "The bash pair (start_mac.sh/stop_mac.sh) was verified on Git Bash on Windows only — syntax (bash -n), structural greps against every locked decision, a live unknown-flag rejection, a live .env-guard run, and a live double-stop. It was NOT launch-tested end-to-end (no live `docker run` via start_mac.sh) on this machine: Git Bash's path translation would mangle the bind-mount source before Docker Desktop's Linux daemon sees it, a stated limitation carried in the plan's own Edge Coverage, not a silent gap. No real macOS or Linux host was available this session either."
  - "Root-caused and fixed a live-only PowerShell parsing corruption: Windows PowerShell 5.1's -File invocation reads a script with no BOM using the system codepage rather than UTF-8. The original scripts used an em-dash (U+2014) and section-sign (U+00A7) in comments and one user-facing Write-Host message; under the system codepage those multi-byte UTF-8 sequences corrupted parsing partway through execution (later statements were skipped/echoed as source text) even though the file parsed cleanly under the AST-based structural verify gate (which parses via .NET's own encoding-aware Parser API, not powershell.exe -File). Fixed by stripping all non-ASCII characters rather than relying on forcing a BOM, which is more portable across how the file might be re-saved later."
  - "docker rm -f can return before the daemon has fully released a container name, observed live and reproduced 3 times in a row on this exact machine when start_windows.ps1 -Build ran against an actively running (HEALTHCHECK-probed) container: the immediately following docker run hit \"Conflict: container name ... already in use\". Fixed by polling docker ps -a for the name's actual absence (up to 20 x 250ms) after every docker rm -f, in both start_mac.sh and start_windows.ps1, before any build/run step proceeds."

requirements-completed: [DEPLOY-03]

coverage:
  - id: D1
    description: "A user on Windows runs start_windows.ps1 and the app is reachable at http://localhost:8000 afterwards, with no Docker knowledge required"
    requirement: DEPLOY-03
    verification:
      - kind: integration
        ref: "docker rm -f finally; powershell -File scripts/start_windows.ps1 -> 'FinAlly is running at http://localhost:8000' (19s); curl http://localhost:8000/api/health -> {\"status\":\"ok\"}"
        status: pass
    human_judgment: false
  - id: D2
    description: "Running start twice while already up is a visible no-op: existing URL printed, exit 0, exactly one container, never a second container or silent restart"
    requirement: DEPLOY-03
    verification:
      - kind: integration
        ref: "powershell -File scripts/start_windows.ps1 (second run) -> 'FinAlly is already running...', rc=0; docker ps -q --filter name=^finally$ --filter status=running | wc -l -> 1"
        status: pass
    human_judgment: false
  - id: D3
    description: "Running start -Build while up replaces the container (proves it is a real rebuild, not a no-op and not a duplicate) and the app answers afterwards"
    requirement: DEPLOY-03
    verification:
      - kind: integration
        ref: "powershell -File scripts/start_windows.ps1 -Build -> rebuild message, docker build (cached, ~5s), 'FinAlly is running...', rc=0; docker ps -q ... | wc -l -> 1; docker inspect finally --format StartedAt shows a new timestamp; curl /api/health -> {\"status\":\"ok\"}"
        status: pass
    human_judgment: false
  - id: D4
    description: "stop and a repeated stop both exit 0, and db/finally.db survives the entire start/start/start-Build/stop/stop sequence untouched"
    requirement: DEPLOY-03
    verification:
      - kind: integration
        ref: "powershell -File scripts/stop_windows.ps1 -> zero running containers, rc=0; run again -> 'FinAlly is not running.', rc=0; invoked from $env:TEMP -> same result (cwd-independent); test -f db/finally.db -> DATA_INTACT throughout"
        status: pass
    human_judgment: false
  - id: D5
    description: "The bash pair (start_mac.sh/stop_mac.sh) is idempotent, argument-validated, non-destructive, and .env-guarded, verified structurally and via live non-launch checks on Git Bash on Windows"
    requirement: DEPLOY-03
    verification:
      - kind: unit
        ref: "bash -n on both scripts; structural greps for set -euo pipefail, anchored name=^ filters, status=running, .env.example, :/app/db, --env-file, --build, /api/health, dirname \"$0\"; negative greps proving no destructive instruction in stop_mac.sh and no .env content read in either script"
        status: pass
      - kind: integration
        ref: "start_mac.sh --bogus-flag rejected pre-daemon (rc!=0); .env temporarily removed -> start_mac.sh fails naming .env.example, restored immediately after; stop_mac.sh exits 0 twice in a row and from an unrelated cwd (/tmp); git ls-files -s shows both scripts at mode 100755"
        status: pass
    human_judgment: true
    rationale: "No live `docker run` via start_mac.sh itself was exercised on this machine (Git Bash path translation would mangle the bind-mount source before Docker Desktop's Linux daemon sees it, per RESEARCH Pitfall 2 and the plan's own Edge Coverage). A human on a real macOS/Linux host, or Phase 6's E2E infrastructure, should confirm the actual container launch path once available."

duration: ~35min
completed: 2026-09-22
status: complete
---

# Phase 5 Plan 2: Start/Stop Scripts Summary

**Idempotent start/stop scripts for macOS/Linux and Windows, with the Windows pair proven end-to-end by a real four-invocation round trip against the Docker daemon that also caught and fixed two live-only bugs invisible to static/structural checks.**

## Performance
- **Duration:** ~35min
- **Started:** 2026-09-22T15:56:57Z (STATE.md session marker after Plan 05-01)
- **Completed:** 2026-09-22T16:22:05Z
- **Tasks:** 2 completed
- **Files modified:** 4 created (scripts/start_mac.sh, scripts/stop_mac.sh, scripts/start_windows.ps1, scripts/stop_windows.ps1)

## Accomplishments
- `scripts/start_mac.sh` / `scripts/stop_mac.sh`: full D-02/D-06/D-07/D-08/D-09 contract — argument validation before any daemon call, `.env` existence guard, anchored daemon-state detection, P-02 rebuild-wins-over-running, absolute-path bind mount, readiness poll, best-effort browser open, non-destructive idempotent stop
- `scripts/start_windows.ps1` / `scripts/stop_windows.ps1`: the same contract in PowerShell, proven by an actual live round trip on this machine (start, start again, start `-Build` while running, stop, stop again), not just structural inspection
- Root-caused and fixed a live-only PowerShell parsing corruption from non-ASCII characters under Windows PowerShell 5.1's `-File` codepage handling — invisible to the AST-based structural verify gate, only reproducible in a real invocation
- Root-caused and fixed a real `docker rm -f` / `docker run` name-collision race for a container with an active `HEALTHCHECK`, reproduced 3 times live before the fix, in both PowerShell and (ported for parity) bash

## Task Commits
1. **Task 1: The macOS/Linux pair** - `ccd929f` (feat)
2. **[Deviation] REPO_ROOT parity fix in stop_mac.sh** - `7c739e2` (fix)
3. **Task 2: The Windows pair + live round trip, plus the bash rm-race port** - `2932d1e` (feat)

## Files Created/Modified
- `scripts/start_mac.sh` - Idempotent launcher: args -> `.env` guard -> daemon check -> already-running check (P-02 rebuild override) -> stopped-container cleanup (now via a poll-until-gone `remove_finally_container` helper) -> build if needed -> absolute mount resolution -> run -> readiness poll -> best-effort browser open
- `scripts/stop_mac.sh` - Idempotent stopper: args -> daemon-down-means-not-running -> anchored running check -> `docker stop`, never touching `db/`
- `scripts/start_windows.ps1` - PowerShell equivalent of `start_mac.sh`, using `param([switch]$Build)`, an `Invoke-Docker` stderr-safe native-call wrapper, and a `Remove-FinallyContainer` poll-until-gone helper
- `scripts/stop_windows.ps1` - PowerShell equivalent of `stop_mac.sh`, sharing the same `Invoke-Docker` helper

## Decisions Made
See `key-decisions` in frontmatter for the full detail on: the `$mountArg` concatenation fix for the PowerShell bind-mount colon ambiguity, the measured 19s first-start readiness duration, the bash pair's verification scope (structural + live non-launch checks, no live `docker run` launch on this machine), the non-ASCII-character root cause and fix, and the `docker rm -f` race fix.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `stop_mac.sh` was missing the `REPO_ROOT` constant the plan's own action text requires ("shared constants at the top of each file, identical in both")**
- **Found during:** Task 2, while implementing the Windows pair — its own verify gate requires `$PSScriptRoot` in *both* `start_windows.ps1` and `stop_windows.ps1`, which surfaced that Task 1's `stop_mac.sh` had skipped the equivalent bash constant.
- **Issue:** `stop_mac.sh` had no `REPO_ROOT`, breaking constant parity with `start_mac.sh` and with what `stop_windows.ps1` would need to match.
- **Fix:** Added `REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"` to `stop_mac.sh`, and used it to name the exact `db/` path in the stop confirmation message.
- **Files modified:** `scripts/stop_mac.sh`
- **Verification:** Re-ran `bash -n`, the anchored-filter grep, the non-destructive grep, stop-idempotent, and cwd-independent checks — all still passed.
- **Commit:** `7c739e2`

**2. [Rule 1 - Bug] PowerShell scripts corrupted mid-execution under Windows PowerShell 5.1's `-File` invocation, due to non-ASCII characters (em-dash, section sign) with no BOM present**
- **Found during:** Task 2's live round trip — `start_windows.ps1 -Build` while a container was running consistently failed with "docker run failed" (a genuine name conflict), while every structural/parse check kept passing.
- **Issue:** Windows PowerShell 5.1 reads a BOM-less script file using the system codepage, not UTF-8. The scripts' comments and one `Write-Host` message used `—` (U+2014) and `§` (U+00A7); under the codepage mismatch, later statements were effectively skipped or echoed as literal source text rather than executed — invisible to `[System.Management.Automation.Language.Parser]::ParseFile`, which is encoding-aware independent of `powershell.exe -File`'s own codepage handling.
- **Fix:** Removed all non-ASCII characters from both `.ps1` files (em-dash to `-`, section sign to `section `), rather than relying on forcing a UTF-8 BOM onto the files.
- **Files modified:** `scripts/start_windows.ps1`, `scripts/stop_windows.ps1`
- **Verification:** Re-ran the full live round trip after the fix; `start -Build` while running succeeded cleanly on the very next attempt and twice more.
- **Commit:** `2932d1e`

**3. [Rule 1 - Bug] `docker rm -f` can return before the daemon fully releases a container name, causing the immediately-following `docker run --name finally` to fail with a name conflict**
- **Found during:** Task 2's live round trip, reproduced 3 times in a row against a container with an active `HEALTHCHECK` (D-11) before being fixed.
- **Issue:** The original `start_windows.ps1`/`start_mac.sh` called `docker rm -f` and immediately proceeded to build/run, trusting the CLI's exit code as proof of completion. On this machine, that assumption didn't hold for a container with an in-flight `HEALTHCHECK` exec.
- **Fix:** Added `Remove-FinallyContainer` (PowerShell) / `remove_finally_container` (bash) — both call `docker rm -f` and then poll `docker ps -a --filter name=^finally$ -q` (up to 20 x 250ms) until the name is actually gone, before any build/run step proceeds. Ported to the bash pair for contract parity even though the bash launch path isn't live-testable on this machine (see Edge Coverage below).
- **Files modified:** `scripts/start_windows.ps1`, `scripts/start_mac.sh`
- **Verification:** Re-ran the full live round trip 3 additional times after the fix; the rebuild-while-running step passed cleanly every time, confirmed by a new `docker inspect --format StartedAt` timestamp each time.
- **Commit:** `2932d1e`

**Total deviations:** 3 auto-fixed (all Rule 1 — bugs found live, none architectural). **Impact:** All three were invisible to static/structural verification and would have shipped broken without the plan's own mandate to actually run the live round trip on this machine — the round trip did exactly the job it was scoped for.

## Issues Encountered
None beyond the three deviations above, all resolved within this plan's own scope.

## User Setup Required
None - Docker Desktop was already confirmed running before dispatch, and the daemon/image preconditions for both tasks were re-verified at the start of execution.

## Next Phase Readiness
DEPLOY-03 is satisfied: a user on Windows has a start/stop pair proven by a real round trip; a user on macOS/Linux has a start/stop pair proven structurally and by every live check short of an actual container launch (the one gap explicitly carried forward, see Edge Coverage in `05-02-PLAN.md`, closable on a real macOS/Linux host or by Phase 6's E2E infrastructure). No blockers for Phase 6.

---
*Phase: 05-docker-packaging-deployment*
*Completed: 2026-09-22*

## Self-Check: PASSED

All four created files confirmed present on disk (scripts/start_mac.sh,
scripts/stop_mac.sh, scripts/start_windows.ps1, scripts/stop_windows.ps1).
All three commit hashes (ccd929f, 7c739e2, 2932d1e) confirmed present in
`git log --oneline --all`.
