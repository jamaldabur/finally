---
phase: 05-docker-packaging-deployment
reviewed: 2026-09-27T00:00:00Z
depth: standard
files_reviewed: 2
files_reviewed_list:
  - scripts/start_windows.ps1
  - scripts/stop_windows.ps1
findings:
  critical: 1
  warning: 2
  info: 3
  total: 6
status: issues_found
---

# Phase 5: Code Review Report

**Reviewed:** 2026-09-27T00:00:00Z (2026-09-24 and 2026-09-23 passes below unchanged; 2026-09-27
pass prepended, scoped to the two files gap-closure plan 05-05 modified)
**Depth:** standard
**Files Reviewed:** 2 this pass (`scripts/start_windows.ps1`, `scripts/stop_windows.ps1`); 6 across
all passes to date
**Status:** issues_found

## 2026-09-27 pass — 05-05's host-command-line cross-check (new bugs found)

Scoped re-review of the two files gap-closure plan 05-05 modified to close the colon-token bypass
this same review recorded as CR-01/WR-01 in the 2026-09-24 pass below (now marked resolved there)
and that 05-VERIFICATION.md independently reproduced live as its failed truth 14. `diff_base` for
this pass was `7b5f2e69`, the commit that closed those prior findings, so everything below concerns
only the new cross-check logic 05-05 introduced.

The mechanism itself is sound for every invocation shape 05-05-PLAN.md's own grounding table
enumerates, and that table's probe record is unusually thorough (three path forms, in-session,
wrapper-hosted, pre-script `-:` rows, a docker shim, and live container/image identity checks). I
traced the new logic in both files line by line against that matrix and did not find a case in the
tested set where it misbehaves.

The problem is what happens outside that tested set. The cross-check's ability to reject a
swallowed colon-token depends entirely on finding, inside `[Environment]::GetCommandLineArgs()`, a
token whose `[System.IO.Path]::GetFullPath(...)` result is lexically `-eq` to `$PSCommandPath`. If
that anchor search ever fails to find a match, the code does not fail closed — it silently falls
back to trusting `$args` alone, which is exactly the pre-05-05 vulnerable behavior this plan exists
to close, with zero diagnostic output. The plan's own grounding record states its live probes ran on
"Windows PowerShell 5.1, the only PowerShell on this machine; pwsh 7 is still not installed" — so
this exact fallback path has never been exercised against PowerShell 7 (pwsh), a
Microsoft-recommended, commonly-installed runtime, nor against symlinked/junctioned checkouts,
`subst`'d drives, or UNC-vs-mapped-drive path mismatches, all of which are plausible ways for the
anchor match to silently miss on a real developer or CI machine. This is the central finding below
(CR-01/WR-01 of this pass), split by severity to match this project's own prior finding that the
stop-side defect is more severe than the start-side one (05-VERIFICATION.md: "the more severe of the
two, since it is an unintended destructive-to-availability action").

Beyond that, the two ~28-line cross-check blocks are verbatim duplicates across the two files
(introducing a future-drift risk if one is hand-edited without the other) and there are a couple of
minor style nits. No hardcoded secrets, no dangerous functions, no non-ASCII bytes, and no violation
of the project's "exactly one usage write, no `-like`/`-match`/prefix matching" contract were found
in either file.

### CR-01 (2026-09-27): Host-argv anchor match fails open in `stop_windows.ps1`, silently reproducing the exact colon-bypass this plan closes

**File:** `scripts/stop_windows.ps1:39-70`
**Issue:**
The cross-check (lines 39-66) only ever *sets* `$RawArgs` when it finds a token in
`[Environment]::GetCommandLineArgs()` whose `[System.IO.Path]::GetFullPath(...)` is lexically equal
to `$PSCommandPath` (lines 43-54). If no such token is found — the loop simply falls through without
matching — `$RawArgs` stays `$null`, and the very next block (lines 56-66) leaves
`$ArgsIntact = $true` unconditionally, because that block's body only runs
`if ($null -ne $RawArgs)`. The final guard at line 67
(`if (-not $ArgsIntact -or $ScriptArgs.Count -gt 0)`) then evaluates using `$args` alone — the exact
mechanism CR-01/WR-01 (2026-09-24 pass, below) and 05-VERIFICATION.md truth 14 proved is not a
complete record of what the caller typed under `-File`.

This means: whenever `$MyInvocation.Line` is empty (a `-File`-style invocation, by this code's own
discriminator) *and* the anchor search fails to find a matching token, a colon-suffixed token such
as `-Foo:` is silently swallowed by PowerShell's own `-File` tokenizer *and* undetected by this
cross-check — falling straight through to `docker info` (line 73) and then `docker stop` (line 87)
against a genuinely running container, with exit 0 and no usage message. That is the identical live
failure mode 05-VERIFICATION.md reproduced against the pre-05-05 code (an unintended `docker stop`
against a running `finally` container, described there as "the more severe of the two" defects
because it is destructive to availability, not merely a silently-discarded rebuild request).

The anchor search can plausibly fail to match in situations never exercised by 05-05-PLAN.md's own
grounding probes, which were run only on "Windows PowerShell 5.1, the only PowerShell on this
machine; pwsh 7 is still not installed" (05-05-PLAN.md `<grounding>`):
- PowerShell 7 (`pwsh.exe`), a distinct, Microsoft-recommended, commonly co-installed runtime whose
  `Path.GetFullPath` normalization is implemented on .NET (not .NET Framework) and was never probed.
- A repository checked out through a symlink or NTFS junction (common with synced-folder or
  worktree setups), where the `-File` argument and `$PSCommandPath` can resolve through different
  real/lexical path forms even though both point at the same file.
- A `subst`'d drive letter, or a UNC path passed where `$PSCommandPath` reports a mapped-drive form
  (or vice versa) — neither is a lexical rewrite that `GetFullPath` performs.

None of this is documented as an accepted residual risk in `05-SECURITY.md`'s Accepted Risks Log
(that log lists only AR-05-02 through AR-05-04, none of which cover this cross-check), so this is
not a signed-off tradeoff — it is an untested fail-open path in the very control T-05-08 exists to
close.

**Fix:** Make the discriminator fail closed instead of fail open. When `$MyInvocation.Line` is
empty (so this is definitely a `-File`-style invocation) but the anchor search never finds a
matching token, treat that as "cannot verify" rather than "nothing to verify":

```powershell
$ArgsIntact = $true
if ([string]::IsNullOrEmpty($MyInvocation.Line)) {
    if ($null -eq $RawArgs) {
        # The host argv never contained a token matching this script's own
        # resolved path. Fail closed rather than silently trusting $args --
        # see 05-REVIEW.md CR-01 (2026-09-27 pass).
        $ArgsIntact = $false
    } elseif ($RawArgs.Count -ne $ScriptArgs.Count) {
        $ArgsIntact = $false
    } else {
        foreach ($token in $RawArgs) {
            if ($token.EndsWith(":")) {
                $ArgsIntact = $false
            }
        }
    }
}
```
This preserves every currently-passing case in 05-05-PLAN.md's matrix (the anchor is found in all
of them) while turning the untested "anchor not found" case into the same safe rejection the rest of
the guard already produces for a detected mismatch, instead of a silent, undiagnosed reversion to
the pre-fix behavior. Apply the identical restructuring to `start_windows.ps1` (see WR-01 below).

### WR-01 (2026-09-27): Same fail-open anchor-match gap in `start_windows.ps1` (lower severity: silently discards `-Build`, does not touch a running container)

**File:** `scripts/start_windows.ps1:102-138`
**Issue:** Identical structure and identical root cause to CR-01 above, in the sibling script: if
`$MyInvocation.Line` is empty but the loop at lines 106-117 never finds a host-argv token whose
`GetFullPath` equals `$PSCommandPath`, `$RawArgs` stays `$null`, `$ArgsIntact` stays `$true`
unconditionally (lines 119-129 only act `if ($null -ne $RawArgs)`), and the accept/reject decision
at lines 130-138 falls back to trusting `$ScriptArgs` (i.e. `$args`) alone. A swallowed `-Build:`
token would then silently fall through to the bare-start path — the caller's explicit rebuild
request is discarded with exit 0 and no diagnostic, exactly the failure 05-VERIFICATION.md's live
`-Build:` reproduction described (image ID confirmed unchanged, "the caller's explicit rebuild
intent was silently discarded"). This is scored as a Warning rather than Critical here only because
its worst observed outcome is a stale, non-rebuilt container rather than an unintended stop of a
running one — matching this project's own precedent for rating the two scripts' identical defect at
different severities.
**Fix:** Same restructuring as CR-01's fix block, applied to `start_windows.ps1`'s copy of the
cross-check (before the existing `$Build = $false` line).

### WR-02 (2026-09-27): The two ~28-line cross-check blocks are verbatim duplicates with no shared source

**File:** `scripts/start_windows.ps1:102-129`, `scripts/stop_windows.ps1:39-66`
**Issue:** The host-argv cross-check — the anchor-search loop, the try/catch around `GetFullPath`,
and the `$ArgsIntact` computation — is copy-pasted identically between the two scripts (the
comments in `stop_windows.ps1` even say so explicitly: "matches start_windows.ps1 exactly"). This is
intricate, security-relevant logic (this very review found a bug in it). Any future hand-edit to one
copy — a bug fix, a hardening pass, a new colon-adjacent tokenizer case discovered later — has no
structural enforcement that it also lands in the other file. The project's own conventions favor
self-contained, dependency-free launcher scripts (no `.` dot-sourcing of a shared helper is
currently used anywhere in `scripts/`), so a shared module file may be a deliberate tradeoff rather
than an oversight; flagging it here so that tradeoff is made explicitly rather than by omission.
**Fix:** Either (a) accept the duplication as an intentional tradeoff for script portability and add
a one-line comment cross-reference in each copy noting "if you change this block, change the
matching block in the other script" (stronger than the current one-directional comment), or (b)
factor the block into a small dot-sourced `scripts/_arg-check.ps1` that both scripts source via
`. (Join-Path $PSScriptRoot "_arg-check.ps1")`, accepting the minor increase in moving parts in
exchange for a single source of truth.

### IN-01 (2026-09-27): Culture-sensitive `EndsWith` used for a security-relevant literal-colon check

**File:** `scripts/start_windows.ps1:125`, `scripts/stop_windows.ps1:62`
**Issue:** `$token.EndsWith(":")` uses the default (current-culture) overload of `String.EndsWith`,
rather than an ordinal comparison. For a single ASCII `:` this is very unlikely to misbehave under
any realistic locale, but this is exactly the kind of string comparison PowerShell/.NET style guides
flag for ordinal comparison specifically because it is a security-relevant equality check, not a
display-formatting one — the failure mode of a culture-aware comparison unexpectedly matching or
missing is silent and locale-dependent, which is hard to catch in testing done on a single
US-locale machine (as this plan's grounding record documents).
**Fix:** `$token.EndsWith(":", [System.StringComparison]::Ordinal)` in both files.

### IN-02 (2026-09-27): Redundant runtime type-check on `$ScriptArgs[0]`

**File:** `scripts/start_windows.ps1:133`
**Issue:** `$ScriptArgs[0] -is [string]` is always true — `$args` elements from a real command-line
invocation are always `[string]`; this cannot be a non-string here. It is harmless dead-weight in
the condition but adds a clause a future reader has to reason about for no behavioral payoff.
**Fix:** Drop the `-is [string]` clause, or if it is meant as defense against some future refactor
that could put non-string elements into `$ScriptArgs`, add a one-line comment saying so.

### IN-03 (2026-09-27): Comment doesn't distinguish the quoted vs. unquoted in-session `-Foo:` cases it describes

**File:** `scripts/start_windows.ps1:100-101`, `scripts/stop_windows.ps1:37-38`
**Issue:** The comment states "In-session, PowerShell's own parser refuses a dangling -Foo: before
this script runs," which is true only for an *unquoted* dangling token at the call site (per this
plan's own grounding table: unquoted `-Foo:` is refused by the parser with a `ParserError`, while a
*quoted* `'-Foo:'` is accepted by the parser, lands in `$args`, and is rejected by this script's own
code, not the parser). A future maintainer skimming only the comment (not the full 05-05-PLAN.md
grounding record) could reasonably conclude the code's colon check is redundant for all in-session
cases, when it is actually load-bearing for the quoted case.
**Fix:** Add "(unquoted)" after "a dangling -Foo:" in both comments to make the distinction explicit
in-line, without needing to cross-reference the plan document.

---

## 2026-09-24 pass — 05-04's argument-validation guard (scripts/start_windows.ps1, scripts/stop_windows.ps1)

Scoped re-review of the two files gap-closure plan 05-04 modified to close the WR-04 gap below
(silent acceptance of unrecognised arguments). I independently reproduced every finding live
against the committed scripts and real `docker.exe` on this machine before recording it — see
CR-01 and WR-01 immediately below. This section is prepended to preserve the 2026-09-23 pass
(WR-04 + its 05-04 correction, IN-03) unedited beneath it.

### CR-01 (2026-09-24): A single dash-prefixed, colon-suffixed, valueless token silently bypasses `stop_windows.ps1`'s zero-argument guard, reaching the daemon and (if a container is running) actually stopping it

> **Resolved by 05-05:** `stop_windows.ps1` now cross-checks the host
> command line before its zero-argument guard, so a swallowed colon token
> is rejected instead of reaching the daemon. See the resolution
> paragraph at the end of this pass. **Note (2026-09-27 pass):** that fix
> itself has a residual fail-open gap in the same anchor-matching logic --
> see CR-01/WR-01 in the 2026-09-27 pass above.

**File:** `scripts/stop_windows.ps1:36-39`
**Issue:** The guard is `if ($args.Count -gt 0) { ... exit 1 }`. Under `powershell -File stop_windows.ps1 <token>` invocation, PowerShell's own command-line parser treats any token of the shape `-Name:` (a dash, an identifier, a trailing colon, nothing after it — whether or not `-Name` is a real declared parameter of the script) as colon-syntax parameter binding, and when nothing follows the colon it silently drops the token instead of raising an error or leaving it in `$args`. The result: `$args.Count` is `0`, indistinguishable from true no-argument invocation, and 05-04's guard lets the script fall straight through to the docker daemon query and (if a container named `finally` is running) the actual `docker stop` call — with no error message at all.

Live, reproduced directly against the committed file (independently re-confirmed by the orchestrator, not just the reviewing agent):
```
$ powershell -NoProfile -File scripts/stop_windows.ps1 '-Foo:'
FinAlly is not running.
exit=0
```
Control (no colon) still correctly rejected:
```
$ powershell -NoProfile -File scripts/stop_windows.ps1 '-Foo'
Usage: stop_windows.ps1
exit=1
```
With a container actually running, `-Foo:` was independently confirmed to reach and execute the real `docker stop $ContainerName` call — i.e. this silently and unexpectedly stops the user's running container, worse than a raw error dump because there is no signal anything went wrong. This is exactly the failure class the whole 05-04 initiative exists to close (per its own commit message: "stop_windows.ps1's empty param() accepted any argument the same way it accepted none... so any invocation like `stop_windows.ps1 --help` would have stopped the running app") — just not the shape that was tested; this one narrow shape (a stray or templated/CI-constructed flag resolving to an empty value after a colon, e.g. `-Reason:%REASON%` with `%REASON%` expanding empty) still gets through.

**Fix:** Do not rely on `$args` alone as "the whole of what the caller typed" under `-File`; it demonstrably is not. Reject any `$args` element whose string form ends in `:` immediately (an unbound colon-suffixed token is never a valid empty-argument invocation for either launcher), and/or inspect `[Environment]::GetCommandLineArgs()` / `$MyInvocation.Line` to detect that the caller passed something even when PowerShell's tokenizer swallowed it out of `$args`. Add a regression matrix entry for `-File stop_windows.ps1 '-AnyName:'` (and the `start_windows.ps1` equivalent, WR-01 below) alongside the existing RED/GREEN matrices 05-04 already built — none of them covered a colon-suffixed token.

### WR-01 (2026-09-24): The same colon-suffixed-token gap lets `start_windows.ps1` silently swallow `-Build:` and proceed as a normal (non-rebuild) start instead of rejecting it

> **Resolved by 05-05:** same fix as CR-01, in `start_windows.ps1`. **Note
> (2026-09-27 pass):** same residual fail-open gap noted there applies
> here too.

**File:** `scripts/start_windows.ps1:87-95`
**Issue:** Identical root cause to CR-01. Live, independently reconfirmed:
```
$ powershell -NoProfile -File scripts/start_windows.ps1 '-Build:'
FinAlly is running at http://localhost:8000
exit=0
```
`$args.Count` is `0` (the `-Build:` token is dropped by PowerShell's `-File` parser before the script sees it), so the guard's zero-argument branch takes over and the script proceeds as if no argument had been given. Lower severity than CR-01 — it falls back to the already-safe default (no rebuild) rather than triggering an unwanted action — but it breaks the same exact-match contract for a concretely reproducible input.
**Fix:** Same as CR-01.

### IN-01 (2026-09-24): The step-1 rationale comment describes the old (fixed) `--build` rewrite bug as if it were still true of the current script's behavior under `-File`

> **Resolved by 05-05:** the step-1 comment now says the rewrite happened
> only while a matching switch parameter was declared, which is why the
> script declares no parameters.

**File:** `scripts/start_windows.ps1:76-86`
**Issue:** The comment reads as an ongoing fact about `-File` parsing in general ("the parser rewrites `--build` into the `-Build` switch"), but that rewrite only ever happened because the *old* code declared `param([switch]$Build)` — a matching declared switch parameter is what `-File` rewrites `--name` into. The current script's `param()` is empty, so `--build` now correctly lands as a literal, rejected token. The comment is accurate as historical justification but could mislead a future maintainer who re-adds a declared parameter into thinking that rewrite risk is categorically retired.
**Fix:** Reword to make the causality explicit — the rewrite happens for any declared switch parameter whose name collides with a `--`-prefixed input, which is exactly why this script now declares none.

**Threat register note:** T-05-08's "mitigate" disposition in the phase threat model (05-02-PLAN.md, amended by 05-04-PLAN.md) covers argument-handling tampering; CR-01/WR-01 are a mitigation gap in that same control, not a new trust boundary. T-05-10 (stop-script non-destructiveness) and T-05-17 (`stop_windows.ps1` DoS) are also implicated — CR-01's exploit path is precisely an unintended `docker stop` reaching a running container. See `05-SECURITY.md` for the reopened disposition.

**Resolution (05-05-PLAN.md):** CR-01, WR-01 and IN-01 are closed as follows, citing the
RED/GREEN matrices and live evidence recorded in 05-05-SUMMARY.md's Tasks 1 and 2.

(a) The fix of record. Both launchers now reconstruct the caller's raw tokens from
`[Environment]::GetCommandLineArgs()`: the tail after the argv element whose full path equals
the script's own path (`$PSCommandPath`). They do this only when `$MyInvocation.Line` is empty,
which means the host started the script from its own command line. They reject the invocation
when any raw token ends in a colon or when the raw count differs from `$args`. 05-04's exact-match
acceptance (no argument, or a single `-Build` in any letter case, for `start_windows.ps1`; no
argument for `stop_windows.ps1`) is otherwise unchanged.

(b) Why the `$args`-only variant of the suggested fix could not close this. The swallowed token
never reaches `$args` at all under `-File` — that is the entire mechanism of the bypass — and any
`$args` element that does end in a colon was already rejected by 05-04's exact match. The
trailing-colon rule therefore had to be applied to the raw host command-line tokens, not to
`$args`. `$MyInvocation.UnboundArguments` and `$PSBoundParameters` were also probed at plan time
and are equally blind to the swallowed token.

(c) A further shape found at plan time. `-Build -Foo:` reached 05-04's guard as a lone `-Build`
and was accepted as a rebuild, with the stray `-Foo:` token silently dropped. It is now rejected,
because the raw host token count (2) no longer matches the count 05-04's guard saw in `$args` (1).

(d) Residual shapes no in-script guard can intercept. Under `-File`, a bare `-:` token makes
PowerShell print its own argument error ("requires an argument") before the script body runs.
In-session, an unquoted dangling `-Foo:` is refused by PowerShell's own parser with the same
message. Both exit non-zero and never reach Docker, but they print PowerShell's own error text and
not the fixed usage line, because no script code ever executes on those two shapes.

(e) The threat record. T-05-08's re-remediation is recorded in 05-05-PLAN.md's threat model.
Closing the row in `05-SECURITY.md` is left to re-running `/gsd-secure-phase 05`, and re-scoring
05-VERIFICATION.md truth 14 is left to re-verification, in the same division 05-04 followed.

---

## 2026-09-23 pass (original, unedited below)

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

> **Corrected by 05-04:** the failure mode described below (a raw PowerShell
> `ParameterBindingException` dump) is not what happens. The actual behaviour
> is silent acceptance with exit 0 -- see the correction appended at the end
> of this finding.

**File:** `scripts/start_windows.ps1:7` (whole-file gap, no corresponding step)
**Issue:** `start_mac.sh` has an explicit, commented "1. Argument validation" step (`start_mac.sh:38-56`) that exact-matches `""` or `--build` and otherwise prints `Usage: $0 [--build]` to stderr and exits 1 — this is exactly the same category of fix WR-03 just addressed (a clean, predictable stderr message on bad input). `start_windows.ps1` has no equivalent step; it relies solely on `param([switch]$Build)` for argument handling. If a caller passes anything PowerShell's binder can't resolve against that single switch parameter (e.g. `.\start_windows.ps1 --build` — the bash-style long flag, an easy mistake given the two scripts are documented as having "identical step order" — or any stray positional token), PowerShell raises a `ParameterBindingException` *before* the script body (and its `$ErrorActionPreference = "Stop"`) ever executes, printing the same kind of raw error-record block (message, `At <file>:<line>`, `CategoryInfo`, `FullyQualifiedErrorId`) that WR-03 just eliminated from the script's own explicit error paths — just from a code path this diff didn't touch. This directly undercuts the file's header claim of parity ("identical step order... in PowerShell") and the very rationale WR-03 was fixed for.
**Fix:** Add an explicit switch-parse guard mirroring the bash script's step 1, e.g. validate `$args`/extra positional tokens before relying on PowerShell's implicit binding, or at minimum wrap the script body's entry in a `try/catch` that catches `System.Management.Automation.ParameterBindingException` and writes a clean `Usage: start_windows.ps1 [-Build]` message via `[Console]::Error.WriteLine` before `exit 1`.

**Correction (05-04-PLAN.md):** Plan-time probing and 05-VERIFICATION.md's own
live reproduction (`--build`, `--totally-bogus-flag`, `--i-am-not-a-real-flag`,
each run three times against the committed script) both falsify the failure
mode this finding predicted. No `ParameterBindingException` was ever raised.

(a) Observed behaviour. Nothing was raised and the exit code was 0:
- Under `powershell -File`, powershell.exe's own command-line parser rewrote
  `--build` and `--Build` into the `-Build` switch, which caused a real
  rebuild and container replacement the caller never asked for.
- Unrecognised tokens such as `--totally-bogus-flag`, `-Buld` or `foo` were
  silently collected into the automatic `$args` variable and ignored.
- Under in-session invocation, the same `--build` landed in `$args` and was
  ignored.
- `stop_windows.ps1`'s empty `param()` accepted any argument the same way,
  so an invocation like `stop_windows.ps1 --help` would have stopped the app.

(b) Root cause. Neither script is an advanced script. Without a
`[CmdletBinding()]` attribute or a parameter attribute on the script-level
block, PowerShell never raises `ParameterBindingException` for an unbound
argument.

(c) Why WR-04's suggested fixes would not have closed it.
- A `try/catch` on `ParameterBindingException` never fires, because nothing
  is thrown.
- Adding `[CmdletBinding()]` would make unknown tokens print the raw
  error-record block (the WR-03 failure mode), would still accept `--build`
  under `-File`, and would silently accept common parameters such as
  `-Verbose`.

(d) The fix of record.
- 05-04-PLAN.md replaced the declared switch with an empty `param()` plus an
  exact-match check of `$args` as step 1, accepting only no argument or a
  single `-Build` in any letter case.
- It added the zero-argument check to `stop_windows.ps1`.
- It made the double-dash spelling a rejected token on Windows (P-03).

(e) The threat claim. T-05-08's mitigation claim in 05-02-PLAN.md was false
and is amended by 05-04-PLAN.md's threat model.

## Info

### IN-03: WR-03's rationale comment is anchored to only the first of five replaced call sites

**File:** `scripts/start_windows.ps1:63-72`
**Issue:** The comment block explaining why `Write-Error` was replaced with `[Console]::Error.WriteLine` (and why `Write-Host`/scoped `$ErrorActionPreference` were rejected) sits once, immediately before the `.env` guard's error path (the first of five sites this pattern now appears at: `.env` guard, Docker-not-running, build failure, run failure, readiness failure). A future contributor reading only one of the later four sites in isolation (e.g. while debugging the readiness-failure path at the bottom of the file) won't see this rationale and could "simplify" one of them back to `Write-Error` without realizing why it regresses.
**Fix:** Either move the comment to sit directly above `Invoke-Docker`/near the top of the script as a file-level convention note, or add a one-line back-reference (`# See rationale near the .env guard above`) at each of the other four sites.

---

_Reviewed: 2026-09-23T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
