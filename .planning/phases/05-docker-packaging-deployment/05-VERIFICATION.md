---
phase: 05-docker-packaging-deployment
verified: 2026-09-27T14:00:00Z
status: gaps_found
score: 13/14 must-haves verified
covered_files:
  - ".dockerignore"
  - ".env.example"
  - ".planning/REQUIREMENTS.md"
  - ".planning/phases/05-docker-packaging-deployment/05-01-PLAN.md"
  - ".planning/phases/05-docker-packaging-deployment/05-01-SUMMARY.md"
  - ".planning/phases/05-docker-packaging-deployment/05-02-PLAN.md"
  - ".planning/phases/05-docker-packaging-deployment/05-02-SUMMARY.md"
  - ".planning/phases/05-docker-packaging-deployment/05-03-PLAN.md"
  - ".planning/phases/05-docker-packaging-deployment/05-03-SUMMARY.md"
  - ".planning/phases/05-docker-packaging-deployment/05-04-PLAN.md"
  - ".planning/phases/05-docker-packaging-deployment/05-04-SUMMARY.md"
  - ".planning/phases/05-docker-packaging-deployment/05-05-PLAN.md"
  - ".planning/phases/05-docker-packaging-deployment/05-05-SUMMARY.md"
  - ".planning/phases/05-docker-packaging-deployment/05-REVIEW.md"
  - ".planning/phases/05-docker-packaging-deployment/05-SECURITY.md"
  - "Dockerfile"
  - "backend/app/main.py"
  - "backend/tests/test_main.py"
  - "scripts/start_mac.sh"
  - "scripts/start_windows.ps1"
  - "scripts/stop_mac.sh"
  - "scripts/stop_windows.ps1"
covered_digest: "v1:sha256:83ad3561d6cabd0e13d7bea03c04019030c0c42aeeb9b87f68de5ead7d15572b"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 13/14
  gaps_closed:
    - "05-05's host-command-line cross-check genuinely closes both of the previous verification pass's live reproductions for the documented, real-world invocation path: `stop_windows.ps1 '-Foo:'` against a genuinely running container now exits 1 with `Usage: stop_windows.ps1` and the container's ID/StartedAt are unchanged; `start_windows.ps1 '-Build:'` against the existing image now exits 1 with `Usage: start_windows.ps1 [-Build]` and the image ID/running container are unchanged. Both independently re-run live this pass (Windows PowerShell 5.1, relative-path invocation from the repo root, real Docker daemon, real `finally:latest` image) -- not taken on 05-05-SUMMARY.md's word."
  gaps_remaining:
    - "A new, distinct fail-open defect in the exact same fix (05-REVIEW.md CR-01/WR-01, 2026-09-27 pass), independently confirmed this pass by direct line-by-line reading of the current committed scripts, not merely accepted on the review's word. See gaps below."
  regressions: []
gaps:
  - truth: "An unrecognised command-line argument to scripts/start_windows.ps1 or scripts/stop_windows.ps1 is rejected with a usage message and a non-zero exit before any docker command runs, for every token shape a caller might pass -- including when the host-argv anchor search this pass's own fix relies on fails to find a match (05-05-PLAN.md must-have; 05-REVIEW.md CR-01/WR-01, 2026-09-27 pass; T-05-08; DEPLOY-03)"
    status: failed
    reason: >
      05-05's fix (`$ScriptArgs`/`$RawArgs`/`$ArgsIntact` cross-check) correctly closes the two specific
      reproductions the prior verification pass used, confirmed by live re-run this pass. But the fix's
      own control flow has a fail-open branch that reintroduces the identical vulnerability class it was
      built to close, confirmed by direct reading of the current committed files (not taken on
      05-REVIEW.md's word alone):

      In both `scripts/start_windows.ps1:119-129` and `scripts/stop_windows.ps1:56-66`, `$ArgsIntact` is
      initialised to `$true` and is only ever set to `$false` inside a block gated on
      `if ($null -ne $RawArgs)`. `$RawArgs` is populated only when the anchor-search loop
      (`start_windows.ps1:104-118`, `stop_windows.ps1:41-55`) finds a token in
      `[Environment]::GetCommandLineArgs()` whose `[System.IO.Path]::GetFullPath(...)` is lexically `-eq`
      to `$PSCommandPath`. If that search never finds a match while `$MyInvocation.Line` is empty (i.e.
      the host definitely started the script via `-File`), `$RawArgs` stays `$null`, the `$ArgsIntact`
      block never executes, and `$ArgsIntact` stays `$true` unconditionally -- so the final accept/reject
      decision falls back to trusting `$ScriptArgs` (`$args`) alone. That is exactly the pre-05-05
      vulnerable behaviour: a colon-suffixed, valueless token swallowed by PowerShell's own `-File`
      tokenizer would once again read as zero arguments, silently bypassing the guard.

      This is not a theoretical worry raised only by the review -- I read the current file's control flow
      directly and confirmed the logic independently. What is not established this pass is how easily the
      anchor search can actually fail to match in practice. 05-05-PLAN.md's own grounding record states
      probing was done only on "Windows PowerShell 5.1, the only PowerShell on this machine; pwsh 7 is
      still not installed" -- and this verification pass independently confirmed only PowerShell 5.1 is
      installed here too (`$PSVersionTable.PSVersion` -> 5.1.26100.9444; `where pwsh` -> not found), so
      the review's named highest-likelihood trigger (PowerShell 7 / `pwsh.exe`, a distinct, commonly
      co-installed, Microsoft-recommended runtime) could not be live-exercised on this machine either. I
      attempted one plausible trigger available on this machine -- mapping the `scripts/` directory to a
      `subst`-created drive letter (`Z:`) and invoking `Z:\start_windows.ps1 '-Build:'` -- and the
      anchor search still matched correctly (rc=1, usage line printed, image/container untouched), so
      `subst` alone does not reproduce the fail-open path on this machine's .NET Framework
      `Path.GetFullPath` implementation. Symlinked/junctioned checkouts and UNC-vs-mapped-drive mismatches
      (the review's other two named triggers) were not attempted. So the defect is confirmed to exist by
      direct code inspection, but its live trigger condition remains unreproduced on this machine's
      available toolchain -- consistent with 05-REVIEW.md's own framing that this is an *untested* path,
      not a *never-reachable* one.

      Both flagged files (`scripts/start_windows.ps1`, `scripts/stop_windows.ps1`) were git-modified by
      05-05 (commits `01847df`, `f3bb11c`) after the prior verification pass's `verified:` timestamp
      (2026-09-24T15:00:00Z), so per the re-verification evidence gate this finding blocks unconditionally
      rather than requiring separate deterministic reproduction evidence to stay blocking.

      05-SECURITY.md has not been updated since the 2026-09-24 reopening: it still shows `status: draft`,
      `threats_open: 1`, and the "PHASE 5 SECURITY BLOCKED" gate describing only the pre-05-05 finding.
      `/gsd-secure-phase 05` has not been re-run to record either 05-05's genuine fix of the original
      colon-bypass or this pass's newly-confirmed fail-open defect, so that file's own blocking gate is
      currently stale in both directions and cannot be read as either closed or accurately describing the
      current risk.
    artifacts:
      - path: "scripts/start_windows.ps1"
        issue: "Lines 119-129: $ArgsIntact defaults to $true and is only ever downgraded to $false inside `if ($null -ne $RawArgs)`. When the host-argv anchor search (lines 104-118) never finds a token matching $PSCommandPath, $RawArgs stays $null and $ArgsIntact silently stays $true, so the accept/reject decision at lines 130-138 falls back to trusting $ScriptArgs ($args) alone -- the exact pre-05-05 vulnerable behaviour"
      - path: "scripts/stop_windows.ps1"
        issue: "Lines 56-66: identical structure and identical root cause. If the anchor search (lines 41-55) never matches, $ArgsIntact stays $true and the guard at line 67 falls back to $ScriptArgs.Count alone, which can again read 0 for a swallowed colon-suffixed token, letting the script reach docker info and, on a running container, the real docker stop call"
    missing:
      - "Restructure $ArgsIntact so that '$RawArgs is $null while $MyInvocation.Line is empty' (anchor never found under a definite -File invocation) is treated as 'cannot verify, reject' rather than 'nothing to check, accept' -- 05-REVIEW.md CR-01 (2026-09-27 pass) includes a concrete fail-closed restructuring for both files."
      - "Add a regression case that forces the anchor-not-found branch (e.g. a wrapper/mock that empties $MyInvocation.Line while presenting a GetCommandLineArgs() array containing no token matching $PSCommandPath) so this path is exercised by an automated check rather than only reasoned about from source. If PowerShell 7 (pwsh) becomes available, add it to the plan's probe matrix explicitly, since it is the review's named highest-likelihood trigger and remains completely unprobed on this project's own development machine."
      - "Re-run /gsd-secure-phase 05 once the fail-closed restructuring lands, so 05-SECURITY.md's T-05-08 row and its ENFORCING GATE reflect the actual current state (05-05's genuine fix of the original bypass, and this pass's newly-confirmed residual) instead of the stale 2026-09-24 snapshot it currently shows."
---

# Phase 5: Docker Packaging & Deployment Verification Report

**Phase Goal:** A user can start the entire application with a single command and have their data persist across restarts
**Verified:** 2026-09-27T14:00:00Z
**Status:** gaps_found
**Re-verification:** Yes -- after gap-closure plan 05-05, which fixed the prior pass's truth-14 finding (the colon-token bypass). A same-day code review (05-REVIEW.md, 2026-09-27 pass) then found a new, distinct Critical defect in that same fix (CR-01/WR-01). This report independently reproduces the fix's success on the original two failure modes and independently confirms the new defect by direct code reading, rather than deferring to either document's word.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A single multi-stage Docker build produces one image serving the frontend and every `/api/*` route on port 8000 (DEPLOY-01) | ✓ VERIFIED | Live `start_windows.ps1` bare invocation this pass reached readiness and `curl http://localhost:8000/api/health` was implicitly confirmed by the script's own readiness poll succeeding (rc=0, "FinAlly is running..."). `Dockerfile` not touched by 05-05 (git log confirms only the two PowerShell scripts changed since the prior pass). |
| 2 | The SQLite database persists across container restarts/replacement via a `db/` bind mount (DEPLOY-02) | ✓ VERIFIED | `db/finally.db` confirmed present (`DATA_INTACT`) after this pass's full live sequence (start, rejected stop via `-Foo:`, rejected start via `-Build:`, clean stop), which touched the running container multiple times. `ENV FINALLY_DB_PATH` unchanged in `Dockerfile`. |
| 3 | Start/stop scripts are idempotent for the documented, correctly-formed invocations (DEPLOY-03, core idempotency) | ✓ VERIFIED | This pass: bare start reached readiness (rc=0); bare stop after the container was running printed "FinAlly is stopped..." (rc=0). Unaffected by this pass's CR-01 finding, which concerns a *different* input shape (a malformed flag reaching a fail-open branch), not the zero-argument path. |
| 4 | `.env.example` is committed and documents `OPENROUTER_API_KEY`, `MASSIVE_API_KEY`, `LLM_MOCK` (DEPLOY-04) | ✓ VERIFIED | `grep -E "^(OPENROUTER_API_KEY|MASSIVE_API_KEY|LLM_MOCK)" .env.example` this pass shows all three, placeholder-only. Unaffected by 05-05 (git history shows no commits touching this file since 05-01). |
| 5 | The static mount never breaks a frontend-less checkout and never shadows an API route (D-04) | ✓ VERIFIED (quick regression) | `uv run --directory backend pytest -q tests/test_main.py` re-run this pass -> 7 passed, unchanged. `backend/app/main.py` not touched by 05-05. |
| 6 | `FINALLY_DB_PATH` is explicitly set so the container's DB writes land inside the bind mount | ✓ VERIFIED (quick regression) | `Dockerfile` unchanged; not in 05-05's `files_modified` list. |
| 7 | Stop scripts are non-destructive under a correctly-formed invocation -- `db/finally.db` is byte-for-byte present after repeated stops (D-08) | ✓ VERIFIED | `db/finally.db` present throughout this pass's live sequence. |
| 8 | No secret ever enters a Docker image layer via the build context, at any depth (CR-01, T-05-01 amended) | ✓ VERIFIED (quick regression) | `.dockerignore` and `Dockerfile` unchanged since the prior pass; not re-probed live since nothing in the covered set changed. |
| 9 | No top-level `docker-compose.yml` exists (D-10) | ✓ VERIFIED | `test ! -f docker-compose.yml` -> `NO_COMPOSE`, re-run this pass. |
| 10 | Base and tool images are tag-pinned, no floating `latest` (T-05-03) | ✓ VERIFIED (quick regression) | `grep -nE "^FROM" Dockerfile` this pass -> `node:20-slim`, `python:3.12-slim`, both pinned, unchanged. |
| 11 | On shutdown, the lifespan awaits both cancelled background tasks before `source.stop()` releases the market source's client (WR-01) | ✓ VERIFIED (quick regression) | `backend/app/main.py` untouched by 05-05; `pytest tests/test_main.py` re-run this pass, 7/7 passed including the WR-01 regression test. |
| 12 | `scripts/start_mac.sh`'s readiness poll bounds every `curl` attempt (WR-02) | ✓ VERIFIED (quick regression) | `scripts/start_mac.sh` not in 05-05's `files_modified`; `git log` confirms no commits touching it since 05-03. |
| 13 | `scripts/start_windows.ps1`'s failure paths write a plain stderr line and reach `exit 1`, with no PowerShell error-record dump (WR-03) | ✓ VERIFIED | Read the current file: the new cross-check falls through to the same single `[Console]::Error.WriteLine(...)` + `exit 1` else branch as before; no new stderr write or exit path was added (confirmed by direct reading, matching 05-05-SUMMARY.md's own structural gate `stderr_writes=6 exit1=6 write_error=0`). |
| 14 | An unrecognised command-line argument to `start_windows.ps1`/`stop_windows.ps1` is rejected with a usage message and a non-zero exit before any docker command runs, for **every** token shape a caller might pass (05-02/05-04/05-05-PLAN.md must-have; T-05-08) | ✗ FAILED | **Independently confirmed this pass by live re-reproduction of the two closed shapes plus direct reading of the current code for the newly-reported shape -- not taken on 05-05-SUMMARY.md's or 05-REVIEW.md's word.** The prior pass's two specific reproductions (`stop '-Foo:'` against a running container, `start '-Build:'` against the existing image) are now genuinely closed for the documented invocation path -- both re-run live this pass with the usage message and unchanged container/image identity. But 05-REVIEW.md's 2026-09-27 pass found, and this verification independently confirmed by direct code reading, a fail-open branch in the same cross-check: when the host-argv anchor search fails to find the script's own path, `$ArgsIntact` silently defaults to `$true` and the guard reverts to trusting `$args` alone -- the identical vulnerability class this whole gap-closure lineage exists to close. A `subst`-drive live attempt to trigger this branch on this machine did not succeed (the anchor still matched); PowerShell 7, the review's named highest-likelihood trigger, is not installed on this machine and so could not be tested either way. See Gaps below. |

**Score:** 13/14 truths verified (0 present, behavior-unverified)

### Deferred Items

None. Phase 6's stated goal (automated test coverage for the trading loop, TEST-01..05) does not cover deployment-script argument parsing, so it does not address this gap.

### Advisory (New Scope, Unevidenced)

None. The CR-01/WR-01 finding is reported as a gap, not an advisory: it concerns files git-modified since the prior verification pass (`scripts/start_windows.ps1`, `scripts/stop_windows.ps1`, both changed by 05-05 after the 2026-09-24 `verified:` timestamp), so per the re-verification evidence gate it blocks unconditionally rather than requiring separate deterministic reproduction to stay blocking. It also carries direct evidence (line-by-line code reading of the current committed files, performed independently in this pass, not merely deferred to 05-REVIEW.md).

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `scripts/start_windows.ps1` | Step-1 guard rejects every unrecognised token, including one the `-File` tokenizer swallows, before any docker call | ⚠️ PARTIAL | Correctly rejects the two shapes the prior verification pass found bypassing 05-04's guard (`-Build:`, `-Foo:`), live-reconfirmed this pass. Has an unresolved fail-open branch (lines 119-129) for the case where the host-argv anchor search cannot locate the script's own path -- confirmed by direct reading, not live-triggered on this machine. |
| `scripts/stop_windows.ps1` | Step-1 guard rejects any argument, including a swallowed colon token, before contacting Docker | ⚠️ PARTIAL | Same partial result -- the live `-Foo:` reproduction against a running container is now closed (STILL_RUNNING_UNTOUCHED, re-confirmed this pass), but the identical fail-open branch exists at lines 56-66. |
| `.planning/phases/05-docker-packaging-deployment/05-REVIEW.md` | 2026-09-27 pass records CR-01/WR-01 against 05-05's fix; 2026-09-24 pass's CR-01/WR-01/IN-01 show Resolved-by-05-05 notes | ✓ VERIFIED | Read in full: both passes present, in order, with the resolution paragraph and the new pass's findings intact. |
| `.planning/phases/05-docker-packaging-deployment/05-SECURITY.md` | T-05-08 disposition reflects current reality | ✗ STALE | Read in full: still shows `status: draft`, `threats_open: 1`, and describes only the pre-05-05 finding (05-04's `$args`-only guard, not 05-05's fail-open cross-check). Neither 05-05's genuine fix nor this pass's CR-01 finding is recorded. `/gsd-secure-phase 05` has not been re-run since 05-05 landed. |
| `Dockerfile` | Unchanged by 05-05 | ✓ VERIFIED | Not in 05-05's `files_modified`; `FROM` lines confirmed pinned this pass. |
| `.dockerignore` | Unchanged by 05-05 | ✓ VERIFIED | Not in 05-05's `files_modified`. |
| `.env.example` | Unchanged, committed, placeholder-only | ✓ VERIFIED | Confirmed this pass. |
| `scripts/start_mac.sh`, `scripts/stop_mac.sh` | Unchanged by 05-05 | ✓ VERIFIED | Not in 05-05's `files_modified`; no diff in `git log` since 05-03. |
| `backend/app/main.py`, `backend/tests/test_main.py` | Unchanged by 05-05 | ✓ VERIFIED | Not in 05-05's `files_modified`; 7/7 tests re-run and passing this pass. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `scripts/start_windows.ps1` host-argv anchor search | `scripts/start_windows.ps1` `$ArgsIntact` computation | A found `$RawArgs` gates the count/colon checks | ⚠️ PARTIAL | Wired correctly when the anchor is found (confirmed live for the documented invocation path). Not wired at all when the anchor is not found: the `$ArgsIntact` block (lines 120-129) is entirely skipped, so `$ArgsIntact` never leaves its `$true` default -- confirmed by direct reading |
| `scripts/stop_windows.ps1` host-argv anchor search | `scripts/stop_windows.ps1` step-2 (`docker info`) | Guard must short-circuit before any Docker call | ⚠️ PARTIAL | Same partial result as start_windows.ps1's link, for the identical reason |
| `.planning/phases/05-docker-packaging-deployment/05-REVIEW.md` (2026-09-27 pass) | `.planning/phases/05-docker-packaging-deployment/05-SECURITY.md` T-05-08 | New finding should reopen/update the same threat row | ✗ NOT WIRED | 05-SECURITY.md has not been updated since 2026-09-24; it does not reference the 2026-09-27 review pass or its CR-01/WR-01 findings at all |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Daemon reachable, image present | `docker info`, `docker images finally:latest` | `DAEMON_UP`; image `0d173432df2f` present | ✓ PASS (baseline) |
| Only PowerShell 5.1 installed (matches 05-05's own grounding claim) | `$PSVersionTable.PSVersion`; `where pwsh` | `5.1.26100.9444`; pwsh not found | ✓ PASS (confirms the review's named untested runtime is genuinely untestable on this machine) |
| `start_windows.ps1` bare invocation | `powershell -File scripts/start_windows.ps1` | `FinAlly is running at http://localhost:8000`, rc=0 | ✓ PASS |
| `stop_windows.ps1 '-Foo:'` LIVE against a running container | bare start, then `stop_windows.ps1 '-Foo:'` | `Usage: stop_windows.ps1`, rc=1; container ID and StartedAt identical before/after -- `STILL_RUNNING_UNTOUCHED` | ✓ PASS (prior pass's gap now closed for this shape) |
| `start_windows.ps1 '-Build:'` LIVE against the real image | `start_windows.ps1 '-Build:'` | `Usage: start_windows.ps1 [-Build]`, rc=1; image ID and running container identical before/after -- `IMAGE_AND_CONTAINER_UNTOUCHED` | ✓ PASS (prior pass's gap now closed for this shape) |
| Attempted live trigger of the CR-01 fail-open branch via a `subst` drive letter mapped to `scripts/` | `subst Z: ...\scripts`; `powershell -File Z:\start_windows.ps1 '-Build:'` | `Usage: start_windows.ps1 [-Build]`, rc=1 -- anchor search still matched | ✗ DID NOT REPRODUCE (on this machine/PS version; does not clear the defect, which was independently confirmed by code reading regardless) |
| Data persistence through the whole live sequence | `test -f db/finally.db` before and after | `DATA_INTACT` throughout | ✓ PASS |
| Backend regression suite for files this plan did not touch | `uv run --directory backend pytest -q tests/test_main.py` | 7 passed | ✓ PASS |
| Cleanup: container returned to a stopped state | `stop_windows.ps1` (bare) | `FinAlly is stopped...`, rc=0; `db/finally.db` present | ✓ PASS |

### Probe Execution

SKIPPED (no `scripts/*/tests/probe-*.sh` files exist, and no plan declares any probe path) -- unchanged from the prior pass.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|--------------|--------|----------|
| DEPLOY-01 | 05-01 | Multi-stage image serves frontend + API on port 8000 | ✓ SATISFIED | Unaffected by 05-05; re-confirmed via live health-poll success this pass |
| DEPLOY-02 | 05-01 | SQLite persists via `db/` bind mount | ✓ SATISFIED | Data confirmed intact through this pass's full live sequence |
| DEPLOY-03 | 05-02 (amended 05-03, 05-04, 05-05) | Idempotent start/stop scripts, macOS/Linux + Windows | ✗ NOT SATISFIED | The prior pass's two specific reproductions are genuinely closed by 05-05. But a newly-found, code-confirmed fail-open branch in the same guard (CR-01/WR-01) means "an unrecognised command-line argument is rejected... for every token shape" is still not established -- on `stop_windows.ps1` this branch, if triggered, reaches a live, unintended `docker stop` against a running container, a direct violation of the safe-launcher contract DEPLOY-03 promises |
| DEPLOY-04 | 05-01 | `.env.example` committed, documents 3 vars | ✓ SATISFIED | Confirmed this pass |

Note: `.planning/REQUIREMENTS.md`'s own tracking table (line 135) and checklist (line 60) both still show `DEPLOY-03` as `Complete`/checked, alongside DEPLOY-01/02/04 (lines 58-59, 61 also checked, unlike the prior pass's report of them being unchecked -- the checklist appears to have been updated since, but the tracking table's DEPLOY-03 row remains stale). This verification's own independent finding overrides that bookkeeping: DEPLOY-03 is NOT satisfied pending the fail-open fix. No orphaned requirements -- REQUIREMENTS.md maps exactly DEPLOY-01..04 to Phase 5, matching this verification's phase requirement IDs exactly.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `scripts/start_windows.ps1` | 119-129 | `$ArgsIntact` defaults to `$true` and is only ever set `$false` inside a block gated on `$RawArgs` being non-null; the anchor-search loop that populates `$RawArgs` can fail to find a match, leaving `$ArgsIntact` at its unconditional default | 🛑 Blocker | Code-confirmed by direct reading this pass: on anchor-search failure under a definite `-File` invocation, the guard silently reverts to trusting `$args` alone -- the exact pre-05-05 vulnerable behavior. Live trigger not reproduced on this machine (PowerShell 5.1 only, `subst` attempt did not trigger it), but the control-flow defect itself does not depend on any live reproduction to be real |
| `scripts/stop_windows.ps1` | 56-66 | Identical defect | 🛑 Blocker | Same as above; more severe in this file because the fallback path reaches a live `docker stop` against a genuinely running container rather than merely skipping a rebuild |
| `.planning/phases/05-docker-packaging-deployment/05-SECURITY.md` | T-05-08 row, ENFORCING GATE | Stale: reflects only the 2026-09-24 finding, not 05-05's fix or this pass's CR-01 | ⚠️ Warning | `threats_open: 1`, `status: draft`, "PHASE 5 SECURITY BLOCKED" gate all currently active but describing an outdated picture; needs a fresh `/gsd-secure-phase 05` run regardless of how the CR-01 fix lands |
| `Dockerfile` | 1-63 | No `ENV PYTHONUNBUFFERED=1` (IN-01, carried, explicitly deferred) | ℹ️ Info | Unchanged deferral, still valid |
| `Dockerfile` | 57-62 | Container runs as root (accepted tradeoff T-05-04) | ℹ️ Info | Documented, accepted, not an oversight |

## Human Verification Required

None. The gap in this report was confirmed by direct, deterministic reading of the current committed scripts' control flow (a null-check gating a state-mutation block, verified line-by-line), not by a judgment call requiring human interpretation. The one item that could not be settled mechanically -- whether the anchor-search failure is easy or hard to trigger on a real user's machine (PowerShell 7 install, symlinked checkout, subst drive, UNC path) -- is recorded as an open question in the gap's `missing` items for the next gap-closure plan to probe further, not as something requiring a human UAT session.

## Gaps Summary

**One Blocker, carried forward in substance but changed in mechanism.** 05-05 genuinely and completely closes the specific colon-token bypass the prior verification pass reproduced live: both of that pass's reproductions (`stop_windows.ps1 '-Foo:'` stopping a running container; `start_windows.ps1 '-Build:'` silently discarding a rebuild) were independently re-run this pass against the real Docker daemon and are now correctly rejected, with container/image identity unchanged in both cases.

But the same-day code review (05-REVIEW.md, 2026-09-27 pass) found a new Critical/Warning pair (CR-01 for `stop_windows.ps1`, WR-01 for `start_windows.ps1`) in the fix itself: the host-argv anchor search that the cross-check depends on can fail to find a match, and when it does, the code does not fail closed -- it silently reverts to 05-04's original `$args`-only behavior, reopening the identical bypass class for whatever invocation shapes can trigger that failure to match. This verification pass did not accept that finding on the review's word: I read both files' current committed control flow directly and confirmed the defect exists exactly as described (`$ArgsIntact` stays at its `$true` default whenever `$RawArgs` stays `$null`).

I also attempted independent live reproduction of the trigger condition itself, since the review named several candidate triggers (PowerShell 7, symlinked/junctioned checkouts, subst drives, UNC-vs-mapped-drive mismatches) that 05-05's own grounding record admits were never probed. This machine has only PowerShell 5.1 installed (confirmed: `pwsh` not found), so the review's highest-likelihood trigger could not be tested. A `subst`-drive attempt (mapping `scripts/` to `Z:` and invoking through it) did not trigger the failure -- the anchor search still matched correctly. This narrows, but does not eliminate, the practical risk: the defect is real by direct code inspection, but this pass could not demonstrate it firing live on the available toolchain.

Both flagged files were git-modified by 05-05 after the prior verification's timestamp, so per the re-verification evidence gate this finding blocks unconditionally.

`05-SECURITY.md` has not been updated since the 2026-09-24 reopening -- it still describes only the pre-05-05 finding, has not recorded 05-05's genuine fix, and has not recorded this pass's new finding. Its own "PHASE 5 SECURITY BLOCKED" gate remains active but is stale in both directions. `/gsd-secure-phase 05` needs to be re-run regardless of how the fail-open fix lands, to bring that file's record back in sync with reality.

**This looks fixable with the same restructuring 05-REVIEW.md's CR-01 already sketches**: treat "anchor not found under a definite `-File` invocation" as a rejection condition rather than a no-op, mirroring how the rest of the guard already treats a detected mismatch. No override is suggested -- this is a genuine, code-confirmed defect with a well-understood fix, not a deliberate deviation to accept. If the project instead judges the residual risk (an untested-but-plausible failure mode on runtimes/setups not available on this development machine) acceptable for a local single-user course demo, that decision belongs in `05-SECURITY.md`'s Accepted Risks Log as an explicit, dated entry -- not in a silent pass here.

**Everything else re-checked this pass is solid.** DEPLOY-01, DEPLOY-02, and DEPLOY-04 are unaffected by 05-05's changes and re-confirmed live or via quick regression. The backend test suite (`tests/test_main.py`) is unaffected and re-run clean (7/7). `db/finally.db` survived this pass's entire live sequence intact.

---

_Verified: 2026-09-27T14:00:00Z_
_Verifier: Claude (gsd-verifier)_
