---
phase: 05-docker-packaging-deployment
plan: 04
subsystem: deployment/scripts
tags: [powershell, launcher, gap-closure, argument-validation, deploy-03]
requires:
  - 05-02 (established the -Build spelling and the declared-switch parameter this plan removes)
  - 05-03 (WR-03's [Console]::Error.WriteLine stderr pattern this plan's new guard reuses)
provides:
  - "start_windows.ps1 step-1 exact-match $args guard: accepts only no argument or -Build (any case), rejects everything else with Usage: start_windows.ps1 [-Build] on stderr and exit 1, before any docker call"
  - "stop_windows.ps1 step-1 zero-argument guard: rejects any argument with Usage: stop_windows.ps1 on stderr and exit 1, before the daemon is queried"
  - "05-REVIEW.md WR-04 corrected: original prediction (ParameterBindingException dump) preserved verbatim, appended correction records the real failure mode (silent acceptance), root cause, why the suggested fixes would not have worked, and the fix of record"
affects:
  - scripts/start_windows.ps1
  - scripts/stop_windows.ps1
  - .planning/phases/05-docker-packaging-deployment/05-REVIEW.md
actuals:
  tokens: 1831
  tasks: 3
  commits: 3
tech-stack:
  added: []
  patterns:
    - "PowerShell argument validation via raw $args inspection under an empty param(), not a declared switch/advanced-script attribute -- see start_windows.ps1's step-1 comment for the full rationale"
key-files:
  created: []
  modified:
    - scripts/start_windows.ps1
    - scripts/stop_windows.ps1
    - .planning/phases/05-docker-packaging-deployment/05-REVIEW.md
key-decisions:
  - "P-03 (plan-time): the Windows launcher's rebuild flag is -Build only, in any letter case; both double-dash spellings (--build, --Build) are rejected, resolving a conflict between VERIFICATION.md's concrete re-test list (--build must reject) and its looser allowed-set phrase (which listed --Build as accepted)"
  - "A2 (plan-time): forms PowerShell's old binder used to tolerate (-B, -Bu prefixes, -Build:$true, an empty-string argument) are now rejected, deliberately matching start_mac.sh's exact-match case arm"
requirements-completed: [DEPLOY-03]
coverage:
  - deliverable: "start_windows.ps1 rejects an unrecognised argument with usage + exit 1 before any docker command"
    verification:
      kind: integration
      ref: "docker-free temp-copy matrix + live repro against the running container (Task 1 <verify>)"
      status: pass
    human_judgment: false
  - deliverable: "The three VERIFICATION.md reproductions (--build, --totally-bogus-flag, --i-am-not-a-real-flag) are rejected and the running container's ID/StartedAt are unchanged"
    verification:
      kind: manual_procedural
      ref: "live command sequence run against Docker Desktop during this dispatch, recorded below"
      status: pass
    human_judgment: false
  - deliverable: "Bare start and -Build (any case) behave exactly as before"
    verification:
      kind: manual_procedural
      ref: "live bare-start, -Build rebuild-and-replace, and repeated bare-start (D-07) sequence, recorded below"
      status: pass
    human_judgment: false
  - deliverable: "-File and in-session invocation agree on accept/reject for the same tokens"
    verification:
      kind: integration
      ref: "Task 1 in-session matrix (call-operator invocation) vs -File matrix"
      status: pass
    human_judgment: false
  - deliverable: "Validation is step 1 (runs before the .env guard)"
    verification:
      kind: integration
      ref: "awk GUARD_FIRST/GUARD_MISPLACED structural gate, both scripts"
      status: pass
    human_judgment: false
  - deliverable: "stop_windows.ps1 rejects any argument before contacting Docker; bare stop stays idempotent and non-destructive"
    verification:
      kind: manual_procedural
      ref: "Task 2 live sequence: rejected stop while running, bare stop x2, rejected stop while stopped, db/finally.db intact"
      status: pass
    human_judgment: false
  - deliverable: "No error-record block, no CmdletBinding, pure ASCII, unchanged step order elsewhere"
    verification:
      kind: automated
      ref: "structural grep/awk gates in Tasks 1-2 <verify>"
      status: pass
    human_judgment: false
  - deliverable: "05-REVIEW.md's WR-04 corrected without deleting original text; frontmatter, IN-03, 05-02/05-03-PLAN.md untouched"
    verification:
      kind: automated
      ref: "Task 3 <verify>: PLACEMENT_OK, content-term grep, HISTORY_UNTOUCHED"
      status: pass
    human_judgment: false
duration: 25min
completed: 2026-09-24
status: complete
---

# Phase 05 Plan 04: PowerShell launchers reject unrecognised arguments (WR-04 gap closure) Summary

Replaced `start_windows.ps1`'s inert `[switch]$Build` parameter and `stop_windows.ps1`'s inert empty
`param()` with an explicit step-1 guard over the raw `$args` list in each script, so a mistyped or
bash-style flag (`--build`, `--Build`, `-Buld`, `-B`, `--totally-bogus-flag`, any stray token) is
refused with a fixed usage line on stderr and `exit 1` before any Docker command runs, in both
`powershell -File` and in-session invocation. Corrected 05-REVIEW.md's WR-04 finding, which had
predicted the wrong failure mode.

## Performance

- **Duration:** ~25 min
- **Started:** 2026-09-24 (session start)
- **Completed:** 2026-09-24T13:14Z
- **Tasks:** 3/3 completed
- **Files changed:** 3 (`scripts/start_windows.ps1`, `scripts/stop_windows.ps1`,
  `.planning/phases/05-docker-packaging-deployment/05-REVIEW.md`)

## Accomplishments

- Closed the only failed Phase 5 must-have (05-VERIFICATION.md gap, truth 14): `start_windows.ps1`
  now rejects an unrecognised argument before touching Docker, proven against the verifier's own
  three-item repro set on the live, committed script.
- Extended the identical fix to `stop_windows.ps1`, which plan-time probing showed had the same
  defect (any argument silently reached `docker stop`).
- Corrected 05-REVIEW.md's WR-04 finding in place, preserving the original text and appending the
  real observed behaviour, root cause, and why WR-04's suggested fixes would not have worked.
- Re-verified the two accepted invocations (bare start, `-Build` in any case) and both idempotent
  no-ops (repeated start, repeated stop) are byte-for-byte unchanged.

## Task Commits

| Task | Commit | Message |
|------|--------|---------|
| 1 | `ff3254e` | fix(05-04): reject unrecognised start_windows.ps1 arguments |
| 2 | `d79ce46` | fix(05-04): reject unrecognised stop_windows.ps1 arguments |
| 3 | `0a704d1` | docs(05-04): correct WR-04's predicted failure mode in the review record |

## Files Created/Modified

- `scripts/start_windows.ps1` (modified) — script-level `[switch]$Build` replaced with empty
  `param()`; new `# 1. Argument validation, before anything else.` block at script scope, placed
  directly after the WR-03 rationale comment and before `# 2. .env guard`.
- `scripts/stop_windows.ps1` (modified) — new `# 1. Accept zero arguments only.` block, placed
  directly after `Invoke-Docker`'s definition and before `# 2.` (daemon reachability).
- `.planning/phases/05-docker-packaging-deployment/05-REVIEW.md` (modified) — a
  `> **Corrected by 05-04:**` note under the WR-04 heading, and an appended
  `**Correction (05-04-PLAN.md):**` paragraph before `## Info`. Original WR-04 text, frontmatter, and
  IN-03 are byte-identical to `e1024f9`.

## Decisions Made

- **P-03** (plan-time, re-confirmed during execution): the Windows launcher's only rebuild spelling
  is `-Build` (any letter case); `--build` and `--Build` are both rejected. Resolves a conflict
  between VERIFICATION.md's concrete re-test list and its looser allowed-set phrasing in favor of the
  concrete list.
- Forms PowerShell's old binder used to tolerate (`-B`, `-Bu` prefixes, `-Build:$true`, an
  empty-string argument) are now rejected, deliberately matching `start_mac.sh`'s exact-match `case`
  arm (flagged assumption A2, not independently re-tested live beyond the docker-free matrix since
  the plan's must-haves don't require a live repro of every one of them).

## Deviations from Plan

None — plan executed exactly as written. The comment block text, guard placement, and correction
wording follow the plan's `<action>` sections verbatim (paraphrased where the plan gave prose
guidance rather than literal text).

## Verification Evidence

### Task 1 — `start_windows.ps1`

**Step 0 RED (before the fix, docker-free, temp copy with no `.env`):**
```
rejection matrix:  --build, --totally-bogus-flag, --i-am-not-a-real-flag, --Build,
                    -Buld, -B, foo  ->  all: rc=1 usage=0 env_guard=1 (fell through
                    to the .env guard unrecognised; -Build extra likewise)
accepted-forms:     NONE, -Build, -build, -BUILD -> all: rc=1 usage=0 env_guard=1
in-session:         --build, --totally-bogus-flag, -Build -> all: rc=1 usage=0 env_guard=1
```
This matches the plan's grounding baseline exactly (usage=0/env_guard=1 across the board — the
temp copy's missing `.env` makes rc=1 for every case, which is why usage/env_guard, not rc, are the
real RED signal).

**Step 2 GREEN (after the fix):**
```
rejection matrix:  --build, --totally-bogus-flag, --i-am-not-a-real-flag, --Build,
                    -Buld, -B, foo, "-Build extra"  ->  all: rc=1 usage=1 env_guard=0
accepted-forms:     NONE, -Build, -build, -BUILD -> all: rc=1 usage=0 env_guard=1 (reached .env guard)
in-session:         --build, --totally-bogus-flag -> rc=1 usage=1 env_guard=0
                    -Build -> rc=1 usage=0 env_guard=1
```

**Structural gates:** PARSE_OK; 0 non-ASCII bytes; exactly 1 `^param()$` line; 0 `[switch]`/
`CmdletBinding` on code lines; `usage_lines=1 stderr_writes=6 exit1=6 write_error=0`; GUARD_FIRST.

**Live, against the committed script:**
- Bare start: `rc=0`, `/api/health` → `{"status":"ok"}`.
- Container before the three VERIFICATION.md repros: ID `94cec0d5a037...` StartedAt
  `2026-09-24T10:09:59.103896257Z`. After `--build`, `--totally-bogus-flag`,
  `--i-am-not-a-real-flag` (each `rc=1`, usage printed, `reported_running=0`): same ID, same
  StartedAt — `CONTAINER_UNTOUCHED`.
- `-Build`: rebuilt the image (cache-hit layers), replaced the container (`replaced=yes`,
  `running=1`), `rc=0`, `/api/health` → `{"status":"ok"}`.
- Repeated bare start: `rc=0`, printed "already running", `same_container=yes` (D-07 no-op).

### Task 2 — `stop_windows.ps1`

**RED (docker-free, unmodified script):** `--totally-bogus-flag`, `--i-am-not-a-real-flag`,
`-Force`, `extra` → all `rc=0 usage=0 reached_docker=1` (matches the grounding baseline).

**GREEN (after the fix):** same four args → all `rc=1 usage=1 reached_docker=0`.

**Structural gates:** PARSE_OK (both scripts); 0 non-ASCII bytes; `empty_param=1 usage_lines=1
exit1=1 forbidden=0`; GUARD_FIRST; no destructive instruction (`Remove-Item`, `docker rm`, `docker
volume`, `docker system`, `Move-Item`, `Clear-Content` all absent); no `Get-Content` call anywhere in
either script (stronger than the plan's literal negative-grep, verified directly).

**Live sequence:**
- Made sure FinAlly was running via a bare `start_windows.ps1` (it had briefly exited between
  Task 1 and Task 2 for reasons unrelated to this plan — Docker Desktop / grace-period behavior, not
  a launcher defect; re-started cleanly).
- Rejected stop (`--totally-bogus-flag`, `-Force`): both `rc=1`, usage printed; container ID
  unchanged before/after → `STILL_RUNNING_UNTOUCHED`.
- Bare stop: `rc=0`, `running=0`. Repeated bare stop: `rc=0`, printed "FinAlly is not running."
  (D-07 no-op).
- Rejected stop while stopped (`extra`): `rc=1`, usage printed — rejection does not depend on
  whether FinAlly happens to be running.
- `db/finally.db` present after the whole sequence → `DATA_INTACT`.
- Bash parity regression: `bash scripts/start_mac.sh --bogus-flag` and
  `bash scripts/stop_mac.sh --bogus-flag` both still exit non-zero.
- Scope check: `scripts/start_mac.sh`, `scripts/stop_mac.sh`, `Dockerfile`, `.dockerignore`,
  `backend/` have no diff against `e1024f9`; no top-level `docker-compose.yml` → `SCOPE_HELD`.

### Task 3 — `05-REVIEW.md`

- `PLACEMENT_OK` (correction sits inside WR-04, before `## Info`).
- `> **Corrected by 05-04:**` note present exactly once, between the heading and `**File:**`.
- All ten required terms present in the correction region (`silently`, `$args`, `--build`,
  `-File`, `ParameterBindingException`, `CmdletBinding`, `-Verbose`, `stop_windows.ps1`, `T-05-08`,
  `05-04-PLAN.md`).
- Original WR-04 heading, the Fix paragraph's "at minimum wrap the script body" sentence, and
  IN-03's heading all still present verbatim.
- `HISTORY_UNTOUCHED`: frontmatter (lines 1-18) byte-identical to `e1024f9`; 05-02-PLAN.md and
  05-03-PLAN.md have no diff against `e1024f9`.

## Flagged Assumptions (carried from plan-time, re-affirmed at execution)

- **A1/P-03:** `--build`/`--Build` are rejected on Windows; only `-Build` (any case) is accepted.
- **A2:** `-B`, `-Bu`, `-Build:$true`, and an empty-string argument are rejected, stricter than the
  bash launcher's `case`, which happens to accept an empty-string argument — a harmless divergence,
  not independently live-tested beyond the docker-free matrix.
- **A3:** Verified on Windows PowerShell 5.1 only; `pwsh` (PowerShell 7) is not installed on this
  machine, so behaviour under `pwsh -File` is unverified. The design relies only on raw tokens
  reaching `$args` when no parameters are declared, which is expected to hold under `pwsh` too, but
  this was not re-tested.
- **A4:** The bash launch path (`start_mac.sh`/`stop_mac.sh` actually starting/stopping a container)
  remains unexercised live on this Windows machine; only their argument-rejection exit codes were
  re-run as a regression (both still exit non-zero on a bogus flag).

## IN-03 Status

Observed, not acted on (info-level, not a gap). Task 1 places the new step-1 guard directly under
the WR-03 rationale comment block, so that comment still sits above the file's first stderr write.
No back-reference comments were added at the other four `[Console]::Error.WriteLine` sites — this
matches the plan's disposition of IN-03 as out of scope for this gap-closure plan.

## Issues Encountered

None. The container's brief unexplained exit (137) between Task 1 and Task 2 (visible in `docker
logs finally`, timestamped mid-way through the session) was Docker/host behavior unrelated to either
script's logic — no argument was passed to either launcher at that point, and the container was
cleanly re-started with a bare `start_windows.ps1` before Task 2's live checks, which all then
passed cleanly.

## User Setup Required

None. Docker Desktop was already running, `finally:latest` was already present, and no `finally`
container existed at dispatch start — the plan's `user_setup` precondition was satisfied throughout
and never blocked execution.

## Next Phase Readiness

The 05-VERIFICATION.md gap (truth 14, the only failed Phase 5 must-have) is closed with live
evidence against the committed script. Phase 5 should now re-verify at 14/14. `DEPLOY-03` is the
sole requirement this plan carries; no sibling plan in this phase shares it, so it is ready to be
marked complete once this plan's commits land.

## Self-Check: PASSED

- `scripts/start_windows.ps1` — FOUND, contains the step-1 guard and `Usage: start_windows.ps1
  [-Build]`.
- `scripts/stop_windows.ps1` — FOUND, contains the step-1 guard and `Usage: stop_windows.ps1`.
- `.planning/phases/05-docker-packaging-deployment/05-REVIEW.md` — FOUND, contains
  `**Correction (05-04-PLAN.md):**`.
- `git log --oneline --all --grep="05-04"` returns the three task commits (`ff3254e`, `d79ce46`,
  `0a704d1`) plus this plan's own creation commit (`c502ade`).
- Acceptance criteria for all three tasks re-verified as PASS in this document's Verification
  Evidence section above.
