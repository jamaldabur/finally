---
phase: 05-docker-packaging-deployment
plan: 05
subsystem: deployment
tags: [powershell, argument-validation, docker, security, gap-closure]

requires:
  - phase: 05-docker-packaging-deployment (05-04)
    provides: "The exact-match $args argument-validation guard on both Windows launchers (empty param(), no declared switch, single -Build acceptance)"
provides:
  - "A host command-line cross-check (GetCommandLineArgs()/MyInvocation.Line) on both scripts/start_windows.ps1 and scripts/stop_windows.ps1, closing the colon-token bypass 05-04's $args-only guard missed"
  - "Resolution notes in 05-REVIEW.md pointing CR-01, WR-01 and IN-01 at this plan and the fix mechanism"
affects: [05-VERIFICATION.md re-verification, /gsd-secure-phase 05 T-05-08 re-remediation]

actuals:
  tokens: 2975
  tasks: 3
  commits: 3
  plan_head_before: 04a0091

tech-stack:
  added: []
  patterns:
    - "PowerShell host-argv cross-check: reconstruct raw caller tokens from [Environment]::GetCommandLineArgs(), gated on an empty $MyInvocation.Line (direct -File invocation only), matched to the script's own path via GetFullPath equality, tail taken with Select-Object -Skip (never an index-range slice, which counts backwards on an empty tail)"

key-files:
  created: []
  modified:
    - scripts/start_windows.ps1
    - scripts/stop_windows.ps1
    - .planning/phases/05-docker-packaging-deployment/05-REVIEW.md

key-decisions:
  - "The trailing-colon rejection rule is applied to the raw host command-line tokens (GetCommandLineArgs() tail), not to $args -- the swallowed token never reaches $args at all under -File, so an $args-only reading of 05-REVIEW.md's suggested fix could not have closed the gap"
  - "$MyInvocation.Line emptiness is the -File discriminator, so an in-session -Build (including one issued by a wrapper script that was itself started with -File) is never cross-checked and never falsely rejected"
  - "Script-path identity uses [System.IO.Path]::GetFullPath(argv element) -eq $PSCommandPath; on the exotic path forms where this cannot be established (UNC paths, subst drives, symlinked directories -- unprobed), the cross-check fails open to 05-04's prior $args-only behavior rather than risking a false rejection of a bare start"

requirements-completed: [DEPLOY-01, DEPLOY-02, DEPLOY-03, DEPLOY-04]

coverage:
  - id: D1
    description: "start_windows.ps1 rejects every colon-suffixed valueless token the -File parser swallows (-Foo:, -Build:, -Build -Foo:) before touching Docker, while every documented invocation (bare start, -Build in any case) still reaches the .env guard"
    requirement: "DEPLOY-03"
    verification:
      - kind: other
        ref: "Task 1 docker-free rejection matrix (19 rows) and path-form matrix (18 rows, 3 path forms) -- RED before edit, GREEN after"
        status: pass
      - kind: other
        ref: "Task 1 live reproduction: start -Build:/-Foo:/-Build -Foo: against a running container -- container ID, StartedAt and finally:latest image ID unchanged (CONTAINER_AND_IMAGE_UNTOUCHED)"
        status: pass
      - kind: other
        ref: "Task 1 live -Build rebuild/replace and repeated bare-start no-op checks"
        status: pass
    human_judgment: false
  - id: D2
    description: "stop_windows.ps1 rejects every colon-suffixed valueless token (-Foo:, -AnyName:, -Force:) before contacting the daemon, closing the live CR-01 exploit where the swallowed token actually stopped a running container"
    requirement: "DEPLOY-03"
    verification:
      - kind: other
        ref: "Task 2 docker-shim matrix (9 rows) -- RED (rc=0, 1 docker call on the three colon rows) before edit, GREEN (rc=1, 0 docker calls) after"
        status: pass
      - kind: other
        ref: "Task 2 live reproduction: stop '-Foo:' and '-AnyName:' against a running container -- container ID and StartedAt unchanged (STILL_RUNNING_UNTOUCHED); bare stop/re-stop idempotence; stopped-state start -Build: starts nothing (NOTHING_STARTED); db/finally.db and .env.example unaffected; SCOPE_HELD against 8a8f335"
        status: pass
    human_judgment: false
  - id: D3
    description: "05-REVIEW.md's CR-01, WR-01 and IN-01 each carry a Resolved-by-05-05 note and a shared resolution paragraph recording the fix, why the $args-only reading could not work, the -Build -Foo: shape, and the residual un-interceptable shapes"
    verification:
      - kind: other
        ref: "PLACEMENT_OK (resolution paragraph between IN-01 and the 2026-09-23 pass), per-finding Resolved-by-05-05 count checks, content-coverage grep over the resolution paragraph, HISTORY_UNTOUCHED (frontmatter/headings/2026-09-23 pass byte-identical to 8a8f335; 05-04-PLAN.md/05-04-SUMMARY.md/05-SECURITY.md unedited)"
        status: pass
    human_judgment: false

duration: 15min
completed: 2026-09-27
status: complete
---

# Phase 05 Plan 05: Colon-Token Bypass Fix Summary

**Host command-line cross-check via `[Environment]::GetCommandLineArgs()` closes the `-File`-swallowed colon-token bypass (`-Foo:`, `-Build:`, `-Build -Foo:`) in both Windows launchers, proven with the verifier's own two live reproductions plus the `-Build -Foo:` shape found at plan time.**

## Performance
- **Duration:** 15min
- **Started:** 2026-09-27T12:38:10Z
- **Completed:** 2026-09-27T12:53:00Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments
- Closed 05-VERIFICATION.md's failed truth 14 (the colon-token bypass) in both `scripts/start_windows.ps1` and `scripts/stop_windows.ps1`, re-remediating T-05-08.
- Verified with docker-free RED-to-GREEN matrices across three path forms (start) and behind a `docker.cmd` shim that counts invocations (stop), plus in-session, wrapper-hosted and pre-script unchanged-behaviour gates.
- Reproduced both of the verifier's original live failures against the real daemon and confirmed each is now closed: `start -Build:` with FinAlly running no longer discards the rebuild request, and `stop '-Foo:'` against a running container no longer stops it.
- Recorded the resolution in 05-REVIEW.md under CR-01, WR-01 and IN-01, explaining why an `$args`-only reading of the suggested fix could not have worked.

## Task Commits
1. **Task 1: Host command-line cross-check in start_windows.ps1** - `01847df` (fix)
2. **Task 2: Host command-line cross-check in stop_windows.ps1** - `f3bb11c` (fix)
3. **Task 3: Resolve CR-01/WR-01/IN-01 in 05-REVIEW.md** - `7b5f2e6` (docs)

**Plan metadata:** pending (this SUMMARY commit)

## Files Created/Modified
- `scripts/start_windows.ps1` - step-1 argument validation now cross-checks the host command line (GetCommandLineArgs()/MyInvocation.Line) before the existing exact-match acceptance of no argument or `-Build`; IN-01 comment reworded
- `scripts/stop_windows.ps1` - same cross-check added before the zero-argument guard
- `.planning/phases/05-docker-packaging-deployment/05-REVIEW.md` - Resolved-by-05-05 notes and a resolution paragraph under CR-01/WR-01/IN-01

## Evidence for the auditors

Maps directly to 05-VERIFICATION.md truth 14 / `missing[0..2]` and 05-SECURITY.md T-05-08, T-05-17, T-05-10, so re-verification and `/gsd-secure-phase 05` can close them without re-deriving anything.

### Task 1 (start_windows.ps1) — RED before edit
Rejection matrix (19 invocations): `-Foo:`, `-Build:`, `-build:`, `-AnyName:` and `-Build -Foo:` each showed `usage=0 env_guard=1` (the bypass signature — the colon-suffixed or trailing token was swallowed and the script fell through to the `.env` guard as if given no argument). Every other row already showed `usage=1 env_guard=0`.

Path-form matrix (18 rows, forward-slash / backslash / relative-from-scripts-dir): `-Foo:` and `-Build:` showed `usage=0 env_guard=1` in all three forms.

### Task 1 — GREEN after edit
Same 19-row rejection matrix: every row now shows `rc=1 usage=1 env_guard=0 error_record=0`, including the five previously-bypassing rows.

Same 18-row path-form matrix: `no argument`, `-Build`, `-build`, `-BUILD` show `usage=0 env_guard=1` in all three forms (accepted, unchanged); `-Foo:` and `-Build:` show `usage=1 env_guard=0` in all three forms (now rejected).

In-session matrix: `-Build` reaches the `.env` guard (`usage=0 env_guard=1`); `--build`, `--totally-bogus-flag`, quoted `'-Foo:'` and `'-Build:'` are rejected (`usage=1 env_guard=0`); unquoted `-Foo:` and `-Build -Foo:` are refused by PowerShell's own parser (`parser_refused=1`, never reach the `.env` guard).

Wrapper-hosted in-session `-Build` (a `-File` wrapper that receives the launcher's path as its own argv and calls it with `-Build` in-session): reaches the `.env` guard (`usage=0 env_guard=1`) — proves the `$MyInvocation.Line` gate does not falsely reject a legitimate in-session call whose own host argv holds only the launcher path.

Pre-script `-:` under `-File`: PowerShell itself refuses the token before the script body runs (`env_guard=0 reported=0`, rc=1) — unchanged before and after, as expected (A5).

Structural gates: `usage_lines=1 stderr_writes=6 exit1=6 write_error=0 host_argv_reads=1 line_gate=1`; `GUARD_FIRST`; `SCRIPT_SCOPE`; `param()=1`, `[switch]/CmdletBinding=0`, `declares no parameters=1`.

### Task 1 — Live evidence (real daemon, real `finally:latest` image)
Bare start: `rc=0`, `/api/health` returned `{"status":"ok"}`.

Colon-token reproduction against the running container (`start -Build:`, `start -Foo:`, `start -Build -Foo:`):
- Before: container `5b70e9f5163d...`, StartedAt `2026-09-27T12:41:55.721191051Z`, image `sha256:0d173432df2f...`.
- Each invocation: `rc=1 usage=1 reported=0`.
- After: identical container ID, StartedAt and image ID — `CONTAINER_AND_IMAGE_UNTOUCHED`.
- This is 05-VERIFICATION.md's original `start -Build:` reproduction (which previously discarded the rebuild silently with `rc=0`), now closed, plus the newly-found `-Build -Foo:` shape.

`-Build` still rebuilds and replaces the container: build ran (cached layers), `rc=0`, `running=1 replaced=yes`, `/api/health` returned `{"status":"ok"}` (image content unchanged since no source changed, `finally:latest` re-tagged to the same content-addressed layer set — expected for an unchanged build context).

Repeated bare start: `rc=0 already=1 same_container=yes` (D-07 no-op intact).

### Task 2 (stop_windows.ps1) — RED before edit
Docker-shim matrix (9 rows, no real daemon touched): `-Foo:`, `-AnyName:`, `-Force:` each showed `rc=0 usage=0 docker_calls=1` — the exact CR-01 bypass signature: the swallowed token let the script reach and call the shimmed `docker`. Every other rejected row showed `rc=1 usage=1 docker_calls=0`. The bare row showed `rc=0 docker_calls=1` (correctly accepted).

### Task 2 — GREEN after edit
Same 9-row shim matrix: every argument row now shows `rc=1 usage=1 docker_calls=0`; the bare row still shows `rc=0 docker_calls=1`.

In-session shim matrix: bare stop `rc=0 docker_calls=1`; quoted `'-Foo:'` `rc=1 usage=1 docker_calls=0`; unquoted `-Foo:` refused by PowerShell's parser, `docker_calls=0 parser_refused=1`.

Non-destructive and error-stream negative greps, and the parse/ASCII/structural gates (`empty_param=1 usage_lines=1 exit1=1 forbidden=0 host_argv_reads=1`, `GUARD_FIRST`, `SCRIPT_SCOPE`) all pass. No `Get-Content` call exists anywhere in either script (confirmed directly by full-file review, since the exact negative-grep pattern against `.env` triggers this environment's own secret-file read guard on the grep command text itself, not on any actual file read — the file contents were never read).

### Task 2 — Live evidence (real daemon, real running container)
Rejected-stop reproduction against a running container (`stop -Foo:`, `stop -AnyName:`):
- Before: container `a465d64dc57e...`, StartedAt `2026-09-27T12:42:38.299351242Z`.
- Each invocation: `rc=1 usage=1 reported=0`.
- After: identical container ID and StartedAt — `STILL_RUNNING_UNTOUCHED`. This is the exact live reproduction 05-REVIEW.md CR-01 and 05-VERIFICATION.md recorded as failing (previously `rc=0`, container stopped); it now leaves the container running.

Bare stop: `rc=0`, `running=0`. Repeated bare stop: `rc2=0 not_running=1` (D-07 no-op intact).

With FinAlly stopped: `stop -Foo:` still rejected (`rc=1 usage=1`); `start -Build:` rejected and starts nothing (`rc=1 usage=1 running_before=0 running_after=0`, `NOTHING_STARTED`) — this is 05-VERIFICATION.md's second reproduction under its original condition (no container running).

`db/finally.db` present (`DATA_INTACT`); `.env.example` still has exactly 3 variable lines. Bash parity: `bash_start_rc=1 bash_stop_rc=1` (unknown-flag rejection unchanged). `SCOPE_HELD`: no diff against `8a8f335` for the bash launchers, Dockerfile, `.dockerignore`, `.env.example` or `backend/`, and no top-level `docker-compose.yml`.

### Task 3 (05-REVIEW.md)
`PLACEMENT_OK`; each of CR-01/WR-01/IN-01 carries exactly one `> **Resolved by 05-05:**` note; the resolution paragraph contains all required terms (`GetCommandLineArgs`, `MyInvocation.Line`, `$args`, `-Build -Foo:`, `-:`, `requires an argument`, `T-05-08`, `/gsd-secure-phase`, `05-05-PLAN.md`); `HISTORY_UNTOUCHED` confirms the frontmatter, the three 2026-09-24 headings and the entire 2026-09-23 pass are byte-identical to `8a8f335`, and 05-04-PLAN.md/05-04-SUMMARY.md/05-SECURITY.md carry no diff against it.

## Flagged Assumptions (carried from plan, unchanged)
- **A1 (carried, P-03):** the Windows launcher's only rebuild spelling is `-Build`; both double-dash spellings are rejected.
- **A2 (carried):** `-B`, `-Bu`, `-Build:$true`, `-Build:true` and an empty-string argument are rejected, stricter than the bash `case`.
- **A3 (carried, sharpened):** verified on Windows PowerShell 5.1 only — pwsh 7 is not installed on this machine. The fix locates the script by path identity, not by which `-File` spelling launched it, so pwsh's `-File` is architecturally covered, but whether pwsh drops colon tokens at all under `-File`, or whether `$MyInvocation.Line` is empty there the same way, is unverified.
- **A4 (carried):** the bash launch path is not exercised live on this Windows machine; only the bash pair's unknown-flag exit codes were re-run (`bash_start_rc=1 bash_stop_rc=1`).
- **A5 (residual, no in-script guard can intercept):** `-:` under `-File` and an unquoted dangling `-Foo:` in-session are both refused by PowerShell's own parser before the script body runs. Both exit non-zero and never reach Docker, so the security property holds, but they print PowerShell's own error text, not the fixed usage line. Confirmed unchanged before and after this plan's edit (Task 1's pre-script and in-session-unquoted rows).
- **A6 (residual, fail-open by design):** script-path identity uses `[System.IO.Path]::GetFullPath(argv element) -eq $PSCommandPath`, verified for forward-slash/backslash absolute paths, 8.3 short names, `.\`-relative paths and the `-f` abbreviation. UNC paths, `subst` drives and symlinked directories were not probed. If identity cannot be established in such a setup, the cross-check is skipped and 05-04's `$args`-only behavior applies unchanged (never a false rejection of a bare start) — recorded as T-05-19 in this plan's threat model.

Behaviour was verified on Windows PowerShell 5.1 only, the only PowerShell installed on this machine.

## Decisions Made
- The trailing-colon rejection rule targets raw host command-line tokens (`GetCommandLineArgs()` tail), not `$args` — the swallowed token never reaches `$args`, so an `$args`-only fix cannot work.
- `$MyInvocation.Line` emptiness is the sole `-File` discriminator, gating the cross-check so no in-session call (including a `-File`-wrapper-hosted one) is ever falsely rejected.
- The cross-check fails open to 05-04's prior behavior when script-path identity cannot be established, rather than risking a false rejection.

## Deviations from Plan

None - plan executed exactly as written. The one procedural note: the plan's literal negative-grep verify command for "no script reads `.env`'s contents" (`grep ... 'Get-Content[^|]*\.env'`) could not be run verbatim in this environment because the pattern text itself matches this environment's own secret-file read guard on the Bash tool (it treats the grep invocation as an attempt to read `.env`, even though the command only searches script source for the literal string and never opens `.env`). Verified the equivalent fact instead: `grep -c 'Get-Content'` across both scripts returns `0`, and both files were read in full during Step 0/read_first, confirming neither script contains any `Get-Content` call. This is a tooling constraint on how the check was run, not a change to the fix or its correctness.

## Issues Encountered
None.

## User Setup Required
None - the Docker Desktop precondition was satisfied by the orchestrator before dispatch; no ongoing external-service configuration required.

## Next Phase Readiness
Phase 05 complete (05-01 through 05-05 all summarized), ready for /gsd-verify-work 05 or phase verification. Re-running `/gsd-secure-phase 05` can now close T-05-08 and lift PHASE 5 SECURITY BLOCKED, and re-running the phase verifier can re-score 05-VERIFICATION.md truth 14 to 14/14 using the evidence recorded above.

---
*Phase: 05-docker-packaging-deployment*
*Completed: 2026-09-27*

## Self-Check: PASSED

All created/modified files (`scripts/start_windows.ps1`, `scripts/stop_windows.ps1`, `05-REVIEW.md`, `05-05-SUMMARY.md`) confirmed present on disk. All three task commits (`01847df`, `f3bb11c`, `7b5f2e6`) confirmed present in `git log`.
