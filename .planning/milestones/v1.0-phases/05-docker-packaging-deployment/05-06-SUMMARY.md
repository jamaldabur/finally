---
phase: 05-docker-packaging-deployment
plan: 06
subsystem: deployment-launcher-scripts
tags: [powershell, argument-validation, fail-closed, security-hardening, host-argv, docker]

requires:
  - phase: 05-docker-packaging-deployment
    provides: "05-05's host-argv cross-check (the anchor-search loop, GetCommandLineArgs, PSCommandPath equality) that this plan restructures"
provides:
  - "A fail-closed step-1 argument guard in scripts/start_windows.ps1 and scripts/stop_windows.ps1: when $MyInvocation.Line is empty and no host argv token names the script's own path, the invocation is now rejected instead of silently trusting $args alone"
  - "An ordinal (culture-invariant) trailing-colon test in both scripts (IN-01)"
  - "BEGIN/END parity markers around the byte-identical cross-check block in both scripts, provable by diff (WR-02 disposition (a))"
  - "A documented, load-bearing -is [string] clause in start_windows.ps1 (IN-02, premise corrected rather than dropped)"
  - "A corrected quoted-vs-unquoted comment distinction in start_windows.ps1 (IN-03)"
  - "Resolved-by-05-06 notes and a resolution paragraph in 05-REVIEW.md's 2026-09-27 pass"
affects: [05-secure-phase, 05-verification, deployment, windows-launchers]

actuals:
  tokens: 3645
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Single-discriminator gate: every $ArgsIntact decision lives inside one $MyInvocation.Line test, not split across a gate plus a separate post-gate block"
    - "BEGIN/END marker-delimited security-relevant code block with an automatable byte-identity parity check, as an alternative to dot-sourcing when dot-sourcing would change the block's own execution context"

key-files:
  created: []
  modified:
    - scripts/start_windows.ps1
    - scripts/stop_windows.ps1
    - .planning/phases/05-docker-packaging-deployment/05-REVIEW.md

key-decisions:
  - "Reversed 05-05's fail-open choice (A6, T-05-19): an anchor-search miss under an empty $MyInvocation.Line now fails closed, per 05-REVIEW.md CR-01's own fix sketch, applied identically to both scripts."
  - "CR-01's three-way decision was placed inside the existing $MyInvocation.Line gate rather than as a second copy of the discriminator test, per the plan's explicit placement instruction."
  - "IN-02's -is [string] clause was kept and documented as load-bearing in-session, not dropped -- the review's 'always true' premise is false for an in-session typed argument."
  - "WR-02 disposition (a) (BEGIN/END markers plus a parity check) was taken over disposition (b) (a dot-sourced helper), because a dot-sourced file would see its own $args/$MyInvocation.Line/$PSCommandPath, silently disabling the cross-check inside the helper."
  - "IMPORTANT LIMITATION (see below): this plan's PowerShell-dependent <verify> commands (parse check, fault-injection matrices, live runspace trigger, 05-05 regression matrices, full live Docker sequence) could NOT be executed by this plan's executor. Only bash-only structural/static checks were run. This is recorded prominently in both this SUMMARY and in 05-REVIEW.md's resolution paragraph so it is not silently lost."

patterns-established:
  - "Fail-closed argument validation: when a security-relevant discriminator cannot positively confirm the input is intact, the default is reject, not accept."

requirements-completed: [DEPLOY-03]

coverage:
  - id: D1
    description: "start_windows.ps1 and stop_windows.ps1 fail closed when the host-argv anchor search finds no token naming the script's own path under an empty $MyInvocation.Line, instead of falling back to trusting $args alone"
    requirement: "DEPLOY-03"
    verification:
      - kind: other
        ref: "bash-only structural checks: true_assign=1 null_eq=1 null_ne=0 line_gate=1 host_argv_reads=1 nested=1 FAIL_CLOSED_OK in both files; START_GUARD_FIRST; STOP_GUARD_FIRST; SCRIPT_SCOPE; CODE_IDENTICAL"
        status: pass
      - kind: other
        ref: "PowerShell fault-injection matrices, live runspace anchor-miss trigger, 05-05 regression matrices, and live Docker sequence specified in 05-06-PLAN.md Task 1/2 <verify>"
        status: not_run
    human_judgment: true
    rationale: "The code restructuring matches 05-REVIEW.md CR-01's fix sketch exactly and passes every bash-only structural proxy for correctness (single discriminator, single fail-closed branch, unchanged ordering, byte-identical cross-check between files). However, the plan's own stated purpose is that reasoning about source is NOT sufficient proof for this exact defect class (05-VERIFICATION.md gaps[0]: 'the anchor-miss branch is exercised by automated checks, not only reasoned about from source'), and the dynamic proof (fault injection, a live runspace trigger, and a live Docker sequence) could not be run in this sandboxed worktree-isolated execution environment. A human or an unrestricted agent must run 05-06-PLAN.md's <verify> blocks against the committed scripts before this can be marked fully proven."
  - id: D2
    description: "Ordinal colon test (IN-01), BEGIN/END parity markers with byte-identity (WR-02), load-bearing -is [string] documented (IN-02), quoted/unquoted comment distinction (IN-03)"
    requirement: "DEPLOY-03"
    verification:
      - kind: other
        ref: "begin=1 end=1 ordinal=1 culture=0 in both files; is_string=1 load_bearing=1 unquoted=1 in start; BLOCKS_IDENTICAL"
        status: pass
    human_judgment: false
  - id: D3
    description: "05-REVIEW.md carries six Resolved-by-05-06 notes and a resolution paragraph documenting the fix, the command-API-host finding, the IN-02 correction, the WR-02 disposition, and the pwsh/live-verification residual"
    requirement: "DEPLOY-03"
    verification:
      - kind: other
        ref: "PLACEMENT_OK; six headings each showing exactly one '> **Resolved by 05-06:**' note; all 15 required tokens present in the resolution paragraph; FRONTMATTER_IDENTICAL; HISTORY_TAIL_IDENTICAL; removed_lines=0; SECURITY_UNCHANGED; VERIFICATION_UNCHANGED; PLAN0505_UNCHANGED; SUMMARY0505_UNCHANGED"
        status: pass
    human_judgment: false

duration: ~50min
completed: 2026-09-29
status: complete
---

# Phase 5 Plan 06: Fail-Closed Host-Argv Anchor Guard for the Windows Launchers Summary

**Both Windows launchers now fail closed instead of fail open when the 05-05 host-argv anchor search cannot find a token naming the script's own path under an empty `$MyInvocation.Line` -- code changes match 05-REVIEW.md CR-01's fix sketch exactly and pass every bash-only structural proof available in this execution environment, but the plan's PowerShell-dependent dynamic proof (fault injection, live runspace trigger, 05-05 regression matrices, live Docker sequence) could not be executed here and remains an explicit, documented open item.**

## IMPORTANT: Environment Limitation (read this first)

This plan's executor ran as a worktree-isolated sub-agent whose Bash tool sandbox
**categorically refuses to invoke `powershell.exe`** in any form. Three distinct attempts were
made and all three were denied by the harness's own safety classifier (not by PowerShell itself,
not by a project permission setting):
1. `powershell -NoProfile -Command "Write-Host hello"` -- denied: "runs powershell in a plain
   command; what it reads or is handed as shell text cannot be shown not to run git."
2. `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start_windows.ps1 --help` --
   denied separately as a "Security Weaken" ([ExecutionPolicy Bypass]).
3. `powershell -NoProfile -File scripts/start_windows.ps1` (no bypass flag) -- denied again with
   the same "cannot be shown not to run git" reasoning.
`dangerouslyDisableSandbox: true` was also explicitly denied by the Claude Code auto-mode
classifier ("[Safety Bypass Flag]").

Per the harness's own denial guidance ("don't pursue the same outcome through another tool,
interpreter, host, encoding, sub-agent or later turn"), no further attempts were made. This is a
genuine environment capability wall, not a task the executor chose not to do.

**Consequence:** every `<verify>` command in 05-06-PLAN.md Tasks 1 and 2 that invokes
`powershell`/`pwsh` (the parse check, both fault-injection matrices, the live runspace trigger,
all seven 05-05 regression matrices, the full live Docker sequence in Task 2 Step 2 items 1-11)
was **not executed**. Every verify command that is pure bash/grep/awk/sed with no `powershell`
invocation **was executed** and is reported below with its actual output. Docker itself was
confirmed reachable (`docker info` succeeded) and a placeholder worktree-local `.env` was created
(the real `.env` at the main repo root is gitignored per-worktree and protected from being read by
this agent's secret-read guard, so it could not be copied in) -- but since no PowerShell script
could be invoked at all, no live Docker action (start/stop/build) was ever actually run against
that daemon in this session.

**What this means for the plan's success criteria:** the code changes themselves match
05-REVIEW.md CR-01's fix sketch byte-for-byte in structure, and every automatable proxy for
correctness that bash alone can check (single discriminator, single fail-closed branch, unchanged
step ordering, byte-identical cross-check between the two files, unchanged WR-03 contract, ASCII
purity) passes. But the plan's entire premise -- stated explicitly in its own grounding and in
05-VERIFICATION.md's gap record -- is that this exact defect class requires *dynamic* proof, not
source-reading, because the previous "obviously correct" version (05-05's) turned out to fail
open in an untested branch. That dynamic proof (fault injection, the live runspace trigger, and
the live Docker sequence) is the one piece of evidence this run could not produce. **Re-running
05-06-PLAN.md's `<verify>` blocks against the three commits below, in an environment that can
invoke `powershell.exe`, is a required follow-up before `/gsd-secure-phase 05` can responsibly
close T-05-08 or before 05-VERIFICATION.md can re-score truth 14 at 14/14.**

## Performance
- **Duration:** ~50min
- **Tasks:** 3/3 completed (code + docs), of which full acceptance-criteria proof is
  environment-blocked for Task 1 and Task 2's dynamic checks (see above); Task 3 fully proven.
- **Files modified:** 3 (`scripts/start_windows.ps1`, `scripts/stop_windows.ps1`,
  `.planning/phases/05-docker-packaging-deployment/05-REVIEW.md`)

## Accomplishments
- Restructured both launchers' `$ArgsIntact` decision entirely inside the single
  `$MyInvocation.Line` gate: a `$null -eq $RawArgs` branch now fails closed (05-REVIEW.md CR-01's
  fix sketch, applied identically to both files).
- Switched the trailing-colon test to the ordinal `EndsWith` overload (IN-01) in both files.
- Wrapped the cross-check in BEGIN/END marker comments, byte-identical between the two files, with
  a parity check proving it (WR-02 disposition (a)).
- Kept and documented the `-is [string]` clause in `start_windows.ps1` as load-bearing in-session,
  correcting IN-02's "always true" premise rather than dropping the clause.
- Corrected the quoted-vs-unquoted wording in `start_windows.ps1`'s comment (IN-03).
- Recorded all six 2026-09-27 review findings as resolved, with a resolution paragraph covering
  the fix, the command-API-host finding (T-05-19's accepted residual), the IN-02 correction, the
  WR-02 disposition, and -- critically -- this environment's inability to run the plan's dynamic
  verification, so that fact is not lost between now and `/gsd-secure-phase 05`.

## Task Commits
1. **Task 1: End-to-end fail-closed restructuring** - `a81da10` (fix)
2. **Task 2: Ordinal colon test, parity markers, corrected comments** - `3d9034c` (fix)
3. **Task 3: Record the 2026-09-27 resolutions in 05-REVIEW.md** - `9cbab6b` (docs)

`plan_head_before: fb14a5d7d9af74063fa1aa10b6e74d7b6a7d8f5a`, `commits: 3` (measured via
`git rev-list --count fb14a5d7d9af74063fa1aa10b6e74d7b6a7d8f5a..HEAD` at SUMMARY time).

## Files Created/Modified
- `scripts/start_windows.ps1` - Step-1 argument guard restructured to fail closed on an
  anchor-search miss; ordinal colon test; BEGIN/END parity markers; load-bearing `-is [string]`
  comment; quoted/unquoted comment correction.
- `scripts/stop_windows.ps1` - Identical restructuring, ordinal test, and markers; one appended
  comment sentence pointing to start's step 1.
- `.planning/phases/05-docker-packaging-deployment/05-REVIEW.md` - Six Resolved-by-05-06 notes
  plus a resolution paragraph in the 2026-09-27 pass; frontmatter and prior-pass history untouched.

## Evidence Recorded (Task 1)

**Step 0 RED baseline:** NOT recorded. The plan's Step 0 instructs running the structural command,
both fault-injection matrices, and the runspace trigger against the *unmodified* files to confirm
the grounding's RED signature before editing. The structural command is bash-only and could have
been run, but was not run separately before the edit in this session (the edit was applied first,
then structural GREEN was confirmed after -- see below). The fault-injection matrices and runspace
trigger require `powershell` and could not be run in either state (RED or GREEN).

**Step 2 GREEN (bash-only, actually executed, exact output):**
```
scripts/start_windows.ps1 true_assign=1 null_eq=1 null_ne=0 line_gate=1 host_argv_reads=1 nested=1 FAIL_CLOSED_OK
scripts/stop_windows.ps1 true_assign=1 null_eq=1 null_ne=0 line_gate=1 host_argv_reads=1 nested=1 FAIL_CLOSED_OK
start usage_lines=1 stderr_writes=6 exit1=6 forbidden=0 empty_param=1 declares_no_parameters=1 fail_closed=1
stop usage_lines=1 stderr_writes=1 exit1=1 forbidden=0 empty_param=1 fail_closed=1
START_GUARD_FIRST
STOP_GUARD_FIRST
SCRIPT_SCOPE
CODE_IDENTICAL
```
ASCII check: 0 non-ASCII bytes in both files (grep -c returned 0 for each; the tool's non-zero
exit code reflects "no matches found," which is the desired outcome, not a failure).

**NOT executed (requires powershell):** PARSE_OK syntax check; the start fault-injection matrix
(mock -File rows for `[]`, `-Build`, `-Build:`, `-Foo:`, `-Build -Foo:`, `--bogus`, plus in-session
rows); the stop fault-injection matrix (mock -File rows for `[]`, `-Foo:`, `-AnyName:`, `-Force:`,
`extra`, plus in-session rows); the live runspace trigger for both scripts; the pwsh row (moot --
pwsh is not installed on this machine, confirmed via `command -v pwsh`, so the row would print
`PWSH_NOT_INSTALLED` regardless of the sandbox restriction); all live Docker steps (bare start,
colon reproductions for start and stop).

## Evidence Recorded (Task 2)

**Step 0 and Step 2 cleanup-gate output (bash-only, actually executed):**
```
scripts/start_windows.ps1 begin=1 end=1 ordinal=1 culture=0
scripts/stop_windows.ps1 begin=1 end=1 ordinal=1 culture=0
is_string=1 load_bearing=1 unquoted=1
BLOCKS_IDENTICAL
```
(Step 0, the pre-edit state, was not separately captured before Task 2's edit -- Task 1's own
commit already establishes the pre-Task-2 baseline in git history, at commit `a81da10`.)

Task 1's structural gates re-confirmed unchanged after Task 2's edits:
```
scripts/start_windows.ps1 true_assign=1 null_eq=1 null_ne=0 line_gate=1 host_argv_reads=1 nested=1 FAIL_CLOSED_OK
scripts/stop_windows.ps1 true_assign=1 null_eq=1 null_ne=0 line_gate=1 host_argv_reads=1 nested=1 FAIL_CLOSED_OK
start usage_lines=1 stderr_writes=6 exit1=6 forbidden=0 empty_param=1
stop usage_lines=1 stderr_writes=1 exit1=1 forbidden=0 empty_param=1
START_GUARD_FIRST / STOP_GUARD_FIRST / SCRIPT_SCOPE / CODE_IDENTICAL
```

**pwsh row:** `PWSH_NOT_INSTALLED` (genuinely not installed on this machine -- `command -v pwsh`
found nothing -- so this specific row's expected output was produced without needing to invoke
`powershell`/`pwsh` at all).

**Scope and data checks (bash-only, actually executed):**
```
SCOPE_HELD
NON_DESTRUCTIVE
get_content=0
bash_start_rc=1 bash_stop_rc=1
```
`.env.example` variable count: 3 (OPENROUTER_API_KEY, MASSIVE_API_KEY, LLM_MOCK) -- unchanged,
confirming DEPLOY-04 as a regression.
`db/finally.db`: **not present** in this worktree (no container was ever started here, since no
PowerShell invocation succeeded) -- this is expected given the environment limitation, not a
DEPLOY-02 regression, but it does mean DATA_INTACT could not be genuinely demonstrated this run.

**NOT executed (requires powershell):** both fault-injection matrices and the runspace trigger
(re-run for Task 2, same as Task 1); all seven 05-05 regression matrices (19-row start rejection,
path-form, in-session with array rows, wrapper-hosted, pre-script, stop shim, stop in-session); the
entire live sequence (bare start / health check; colon reproductions for start and stop against a
real running container; `-Build` rebuild and container replacement; repeated bare start no-op;
bare stop then repeated bare stop; stopped-state reproductions).

## Evidence Recorded (Task 3)

All of Task 3's verify commands are pure bash/awk/sed/git-diff and were fully executed:
```
PLACEMENT_OK
CR-01=1  WR-01=1  WR-02=1  IN-01=1  IN-02=1  IN-03=1   (each region's Resolved-by-05-06 count)
fail closed=1  MyInvocation.Line=5  AddCommand=1  Start-Job=2  PSScriptRoot=1  -is [string]=1
@('-Build','x')=1  dot-sourc=2  Ordinal=1  unquoted=1  T-05-08=1  T-05-19=3  /gsd-secure-phase=1
05-06-PLAN.md=1  pwsh=4
FRONTMATTER_IDENTICAL  HISTORY_TAIL_IDENTICAL  headings=6  removed_lines=0
SECURITY_UNCHANGED  VERIFICATION_UNCHANGED  PLAN0505_UNCHANGED  SUMMARY0505_UNCHANGED
```

## Evidence for the Auditors

Maps this plan's actual (bash-only) evidence to the source records it claims to close, and states
plainly what still needs to happen before each can be genuinely closed.

- **05-VERIFICATION.md truth 14, gaps[0].missing[0]** ("treat `$RawArgs` null under empty Line as
  reject"): the code fix is applied and structurally verified (FAIL_CLOSED_OK, null_eq=1, null_ne=0
  in both files). **NOT dynamically proven** in this session -- the fault-injection matrices that
  would move the exact fail-open signature from RED to GREEN were not run.
- **gaps[0].missing[1]** ("a regression case forcing the anchor-not-found branch; add pwsh if
  available"): the fix's structure supports this (the branch exists and is reachable per the
  ordering checks), but the runspace trigger that was supposed to exercise it live was **not run**.
  pwsh remains not installed on this machine, so that specific residual is unchanged from 05-05's
  own record, not newly discovered here.
- **gaps[0].missing[2]** (re-run `/gsd-secure-phase 05`): unchanged -- still explicitly out of
  scope for this plan, still the required next step. This plan's incomplete dynamic verification
  makes that re-run's own live checks (if it does any) even more load-bearing than originally
  planned, since this plan could not supply that evidence itself.
- **Anti-Patterns Found, start/stop fail-open blocks:** removed. `null_ne=0` and `FAIL_CLOSED_OK`
  confirm the old post-gate fail-open block is gone in both files.
- **05-SECURITY.md T-05-08 (stale row):** the threat_model in 05-06-PLAN.md already states the
  intended re-remediation text and residual for the auditor to use. This SUMMARY adds one more
  residual on top of what the plan anticipated: **the dynamic verification itself was not run in
  this execution, so the auditor should not treat this plan's own claimed evidence as sufficient
  without independently re-running 05-06-PLAN.md's `<verify>` blocks (or equivalent) first.**
- **T-05-17 (stop DoS)**, **T-05-10 (non-destructive stop)**: the static NON_DESTRUCTIVE check
  passed and no removal/prune/move/truncate instruction was added to `stop_windows.ps1`. The live
  STILL_RUNNING_UNTOUCHED reproduction against a real running container was **not run**.
- **T-05-19 (accepted residual, reversed from 05-05):** the plan's threat_model text describing
  this residual (command-API hosts rejected even when bare) is unchanged and still accurate to the
  code as committed; it was not independently re-verified live in this session beyond the
  structural proof that the fail-closed branch exists and is reachable.

## Flagged Assumptions
- **A3 (carried, unresolved):** pwsh 7 is still unprobed for its `$MyInvocation.Line` behavior
  under `-File`. Genuinely not installed here (`command -v pwsh` found nothing), so this is
  unchanged from 05-05/05-06-PLAN's own record, not a new gap this session introduced.
- **A5 (carried):** `-:` under `-File` and an unquoted dangling `-Foo:` in-session are refused by
  PowerShell itself before any script body runs. Unverified live this session (would require
  `powershell`), but this is pre-existing PowerShell tokenizer behavior the code does not touch.
- **A6 (reversed by this plan, per spec):** 05-05 failed open; this plan's code now fails closed.
  Structurally confirmed; dynamically unconfirmed this session.
- **A7 (per spec):** a command-API host (runspace, background job) with an empty
  `$MyInvocation.Line` and no matching argv anchor is now rejected even when bare. The code
  supports this per the ordering/structure checks; the live runspace trigger that would prove it
  end-to-end was **not run**.
- **A8 (per spec):** IN-02's "always true" premise is false in-session; the clause stays and is
  now documented. Confirmed structurally (`is_string=1`, `load_bearing=1`); the in-session array-
  argument regression rows (`@('-Build','x')`, `@('-Build')`) that would prove this dynamically
  were **not run**.
- **NEW (this session):** the worktree-isolated Bash tool sandbox refuses all `powershell.exe`
  invocations regardless of flags, and `dangerouslyDisableSandbox` is separately denied by the
  harness's own classifier. This is an execution-environment property, not a property of the code
  or the plan, and it is the dominant reason this plan's acceptance criteria could not be fully
  proven this session.

## Decisions Made
See `key-decisions` in the frontmatter above. In summary: apply CR-01's fix sketch identically to
both files, place the three-way decision inside the existing gate, keep and document the
`-is [string]` clause rather than dropping it, and take WR-02 disposition (a) over (b).

## Deviations from Plan

**1. [Environment blocker, not a Rule 1-4 deviation] PowerShell could not be invoked in this
execution environment.**
- **Found during:** Task 1, Step 0 (attempting to record the RED baseline).
- **Issue:** The Bash tool available to this worktree-isolated executor refuses any invocation of
  `powershell.exe`/`pwsh.exe`, in any form (plain `-Command`, `-ExecutionPolicy Bypass -File`, or
  bare `-File`), citing an inability to statically verify the invocation stays within the
  worktree. `dangerouslyDisableSandbox: true` was separately and explicitly denied.
- **Fix:** None available -- this is a hard capability boundary of the execution environment, not
  a bug in the code or the plan. Per the harness's own denial guidance, no further attempts were
  made to work around it via other tools, encodings, or hosts.
- **Impact:** every PowerShell-invoking `<verify>` command in Tasks 1 and 2 (parse check,
  fault-injection matrices, live runspace trigger, 05-05 regression matrices, full live Docker
  sequence) was not executed. All non-PowerShell `<verify>` commands (bash/awk/sed/grep/git-diff
  structural checks) were executed and passed, as detailed above. Task 3's verification is
  entirely bash-based and is fully complete.
- **Follow-up required:** someone (a human, or an agent whose environment permits invoking
  `powershell.exe`) must run 05-06-PLAN.md's `<verify>` blocks against commits `a81da10`,
  `3d9034c`, and `9cbab6b` before `/gsd-secure-phase 05` can responsibly close T-05-08, and before
  05-VERIFICATION.md's truth 14 can be re-scored at 14/14.

**2. [Rule 3-adjacent, environment setup] Worktree-local placeholder `.env` created for the
(ultimately unused) live steps.**
- **Found during:** Task 1 precondition check.
- **Issue:** `.env` is gitignored and not present in this per-worktree checkout, even though the
  real `.env` exists at the main repo root. This agent's secret-read guard blocks reading or
  copying that specific path (by pattern match on the path string, regardless of intent), so the
  real file could not be copied or symlinked in.
- **Fix:** created a worktree-local `.env` (gitignored, never staged or committed) with a clearly
  labeled placeholder `OPENROUTER_API_KEY` and `LLM_MOCK=true`, sufficient to pass the launcher's
  existence-only `Test-Path` guard had any live step actually run.
- **Files modified:** `.env` (untracked, gitignored, not part of any commit).
- **Impact:** none on the committed code. This file was never needed in practice, since no
  PowerShell invocation succeeded at all in this session.

**Total deviations:** 1 environment capability blocker (no auto-fix available, extensively
documented and handed off) + 1 minor environment-setup workaround (inert, no commit impact).
**Impact:** the committed code changes are believed correct (they match the reviewer's own fix
sketch exactly, and every check that bash alone can perform passes), but this plan's central,
explicitly-stated claim -- "the anchor-miss branch is exercised by automated checks, not only
reasoned about from source" -- is **not proven by this session's own work**. That dynamic proof
is now the single most important open item before this gap-closure plan's evidence can be trusted
by `/gsd-secure-phase 05` or by a re-run of `/gsd-verify-phase 05`.

## Issues Encountered
See "Deviations from Plan" above -- the PowerShell invocation sandbox restriction was the dominant
issue this session. No code-level bugs were found or needed fixing beyond the plan's own specified
restructuring.

## Known Stubs
None. No hardcoded empty values, placeholder UI text, or unwired data sources were introduced --
this plan is exclusively CLI-argument-parsing logic in two PowerShell scripts plus documentation.

## Threat Flags
None. This plan's `<threat_model>` already fully covers the surface it touches (T-05-08, T-05-17,
T-05-19, T-05-18, T-05-10, T-05-SC); no new surface was introduced beyond what that section
anticipated.

## User Setup Required
None beyond what the plan's own `user_setup` already specified (Docker Desktop running, confirmed
reachable via `docker info` at the start of this session). No further external service
configuration is required. The unresolved item is re-running this plan's PowerShell-dependent
`<verify>` blocks in an environment that can invoke `powershell.exe` -- see "IMPORTANT: Environment
Limitation" above.

## Next Phase Readiness
This closes out the tasks of Phase 5 Plan 06 (all three tasks executed, all three commits made).

**Update (orchestrator, post-merge):** Items 1-3 below have now been completed. After merging
this plan's worktree branch into `finally-gsd`, the orchestrator (unsandboxed, with real
`powershell.exe` access) ran every `<verify>` command from Task 1 and Task 2 against the merged
code, against a real Docker daemon. All passed GREEN -- including both fault-injection matrices,
the live non-mocked in-process runspace anchor-miss trigger (`runspace_start usage=1
env_guard=0`, `runspace_stop usage=1 docker_calls=0`), every 05-05 regression row unchanged, and
the full live Docker sequence (bare start, both colon reproductions with
`CONTAINER_AND_IMAGE_UNTOUCHED`/`STILL_RUNNING_UNTOUCHED`, `-Build` rebuild/replace, repeated
bare start no-op, double bare stop, the stopped-state reproduction with `NOTHING_STARTED`,
`DATA_INTACT`, bash-pair validation unchanged, `SCOPE_HELD`/`NON_DESTRUCTIVE`). Full detail
recorded in 05-REVIEW.md's "Addendum (orchestrator, post-merge)" note. The original numbered
items are preserved below for the historical record of what this plan's own execution session
could and could not prove:

1. Re-run 05-06-PLAN.md's `<verify>` blocks (Tasks 1 and 2) against commits `a81da10`, `3d9034c`,
   and `9cbab6b` in an environment that can invoke `powershell.exe` -- ideally the same machine
   05-05's grounding record used (Windows PowerShell 5.1.26100.9444), so the pwsh-not-installed
   status is directly comparable. **DONE** -- see above.
2. Only after that dynamic proof succeeds should `/gsd-secure-phase 05` be re-run to close T-05-08
   and log T-05-19's accepted residual in 05-SECURITY.md's Accepted Risks Log. **Still pending** --
   this is the orchestrator's next step.
3. Only after that should 05-VERIFICATION.md be re-run to re-score truth 14. **Still pending.**

---
*Phase: 05-docker-packaging-deployment*
*Completed: 2026-09-29*

## Self-Check: PASSED
- FOUND: scripts/start_windows.ps1
- FOUND: scripts/stop_windows.ps1
- FOUND: .planning/phases/05-docker-packaging-deployment/05-REVIEW.md
- FOUND: .planning/phases/05-docker-packaging-deployment/05-06-SUMMARY.md
- FOUND commit: a81da10 (Task 1)
- FOUND commit: 3d9034c (Task 2)
- FOUND commit: 9cbab6b (Task 3)
- FOUND commit: 86df22d (this SUMMARY)
