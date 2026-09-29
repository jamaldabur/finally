---
phase: "5"
slug: "docker-packaging-deployment"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-09-24"
---

# Phase 5 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Host filesystem → Docker build context | `docker build` reads the repo tree via `COPY` instructions in `Dockerfile` | Source code, lockfiles, and (if not excluded) any local dotenv/secret files on the host |
| Host filesystem ↔ container, `db/` bind mount | `docker run -v .../db:/app/db` | SQLite database file (`finally.db`) — user's simulated portfolio/watchlist/chat data, no real financial or credential data |
| Browser ↔ container | HTTP on port 8000 (`/api/*` routes + static frontend export) | Application requests/responses; no auth, single local user, no multi-tenant boundary |
| Host shell (launcher scripts) ↔ Docker daemon | `scripts/start_mac.sh` / `stop_mac.sh` / `start_windows.ps1` / `stop_windows.ps1` invoke `docker build`/`run`/`stop`/`rm` | Command-line arguments only; no data payload |
| Container ↔ external registries | Base image pulls (`node:20-slim`, `python:3.12-slim`, `ghcr.io/astral-sh/uv:0.10.9`) and dependency installs (`npm ci`, `uv sync --frozen`) at build time | Pinned image digests/tags and lockfile-pinned package versions only |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-05-01 (amended by 05-03) | Information Disclosure | Docker build context / image layers | high | mitigate | `.dockerignore` excludes `**/.env` and `**/.env.*` at every depth, re-includes `!**/.env.example`; verified against what Docker actually received (whole-context, `--target frontend-build`, and runtime-image sentinel probes, all three showing only `.env.example` names present). Confirmed in codebase: `.dockerignore` lines 28-30. Residual (accepted, low): pre-fix local build-cache layers on this dev machine may still hold the old leak; local-only, no registry push exists, user can `docker builder prune` at their discretion. | closed |
| T-05-02 | Information Disclosure | `.env.example` | high | mitigate | Placeholder-only values (no high-entropy token), `git check-ignore` confirms it is committable. Confirmed: `.env.example` has zero high-entropy assignment lines. | closed |
| T-05-03 | Tampering / Spoofing | Base and tool images | medium | mitigate | `node:20-slim`, `python:3.12-slim`, `ghcr.io/astral-sh/uv:0.10.9` all tag/digest-pinned, no floating tags. Confirmed in `Dockerfile`. | closed |
| T-05-04 | Elevation of Privilege | Container process identity | medium | accept | Container runs as the image's default root user (no `USER` instruction) — see Accepted Risks Log. | closed (accepted) |
| T-05-05 | Tampering | `db/` bind mount source path | medium | mitigate | Mount source resolved to an absolute host path before use (`dirname "$0"` / `$PSScriptRoot`), created before use, quoted on expansion. | closed |
| T-05-06 | Denial of Service (availability) | `HEALTHCHECK` | low | mitigate | Real HTTP GET against `/api/health` via Python stdlib — a crashed app cannot report healthy. Confirmed: `Dockerfile` line 54-55. | closed |
| T-05-07 | Information Disclosure | Static file mount at `/` | low | accept | Path-traversal protection is Starlette `StaticFiles`' own responsibility; mounted directory contains only the public frontend export — see Accepted Risks Log. | closed (accepted) |
| T-05-08 (re-remediated by 05-06; reopened 2026-09-24; residual reopened and closed 2026-09-27/29) | Tampering | `start_windows.ps1` / `stop_windows.ps1` argument handling | medium | mitigate | 05-04's exact-match guard over raw `$args` closed the original colon-bypass; 05-05 added a host-argv cross-check (`[Environment]::GetCommandLineArgs()` vs `$args`) but that cross-check itself failed open when the anchor search found no token matching the script's own path (05-REVIEW.md 2026-09-27 CR-01/WR-01; 05-VERIFICATION.md truth 14). **05-06's fix:** `$ArgsIntact` is now decided entirely inside the single `$MyInvocation.Line` gate — a missing anchor (`$null -eq $RawArgs`) sets `$ArgsIntact = $false` (fail closed) instead of leaving it at its `$true` default; a count mismatch or a trailing-colon token (ordinal comparison) also reject. Code: `scripts/start_windows.ps1:113-146`, `scripts/stop_windows.ps1:41-74`. **Verified twice, independently:** the orchestrator ran every `<verify>` command from 05-06-PLAN.md live against a real Docker daemon (both fault-injection matrices GREEN, the live non-mocked in-process runspace anchor-miss trigger GREEN, every 05-05 regression row unchanged, and the full live Docker sequence — bare start, both colon reproductions with `CONTAINER_AND_IMAGE_UNTOUCHED`/`STILL_RUNNING_UNTOUCHED`, `-Build` rebuild, repeated start/stop, the stopped-state reproduction with `NOTHING_STARTED`, `DATA_INTACT`, `SCOPE_HELD` — see 05-REVIEW.md's "Addendum (orchestrator, post-merge)"). A separate `gsd-security-auditor` pass then independently re-derived the static structural gates and re-ran the fault-injection/runspace/regression checks itself on temp copies (declining only to re-run the live Docker sequence against the real container, relying on the orchestrator's addendum for those rows instead) and confirmed the fix. **Residual, both accepted:** pwsh 7 remains unprobed on this machine (`PWSH_NOT_INSTALLED` confirmed; if pwsh left `$MyInvocation.Line` non-empty under `-File` the cross-check would be skipped, a fail-open — the plan's conditional pwsh verify row catches this wherever pwsh becomes available); and see T-05-19 for the new self-inflicted-rejection tradeoff this fix accepts. | closed |
| T-05-09 | Information Disclosure | `.env` handling in launcher scripts | medium | mitigate | Scripts test only file existence and pass the path to `--env-file`; negative grep confirms no instruction reads file contents. | closed |
| T-05-10 (re-asserted by 05-04, 05-06) | Tampering / data destruction | Stop scripts | high | mitigate | Neither stop script contains a removal/prune/move/truncate instruction (enforced by negative grep over comment-filtered source: `NON_DESTRUCTIVE`, re-confirmed after 05-06's edit — the only docker verbs in `stop_windows.ps1` are `info`, `ps` and `stop`); `db/finally.db` confirmed present (`DATA_INTACT`) after 05-06's full live start/stop sequence. T-05-08's residual bypass (which reached this script's own legitimate `docker stop` call unintentionally) is now closed, so this row's guarantee (only intended invocations reach that call) holds without qualification. | closed |
| T-05-11 | Tampering | Bind-mount source resolution | medium | mitigate | Built from `dirname "$0"` / `$PSScriptRoot`, created before use, quoted; verified by invoking from an unrelated working directory. | closed |
| T-05-12 | Spoofing | Container identity detection | low | mitigate | Detection uses `docker ps --filter "name=^finally$" --filter "status=running" -q` — anchored regex prevents a similarly-named container from being mistaken for FinAlly. | closed |
| T-05-13 | Elevation of Privilege | Script execution policy on Windows | low | accept | Verification runs PowerShell with `-ExecutionPolicy Bypass` for unsigned local scripts — see Accepted Risks Log. | closed (accepted) |
| T-05-14 | Information Disclosure | 05-03 Task 1's probe and inventory commands | medium | mitigate | Probes run only post-fix; sentinel files created empty, never written; probes list names only (`find -name`), never contents; project secret-read guard hook refuses any content-reading command against a dotenv filename. | closed |
| T-05-15 | Denial of Service (availability) | `lifespan` shutdown with the Massive source | low | mitigate | `asyncio.gather(update_task, snapshot_task, return_exceptions=True)` before `source.stop()` — no client closed underneath an in-flight request. Locked by `backend/tests/test_main.py::test_lifespan_awaits_background_tasks_before_stopping_source` (currently passing, confirmed in this audit's full-suite run: 228 passed). | closed |
| T-05-16 | Denial of Service (availability) | `start_mac.sh` readiness poll | low | mitigate | Every `curl` call bounded with `--max-time 2`, matching `start_windows.ps1`'s `-TimeoutSec 2`; structural gate asserts every non-comment curl call is bounded. | closed |
| T-05-17 | Denial of Service (availability) | `stop_windows.ps1` | low | mitigate | 05-04's zero-argument guard plus 05-06's fail-closed anchor-miss fix together exit before any tested or previously-bypassing argument shape reaches `docker stop`. Re-confirmed live: fault-injected stop rows (`[]`, `-Foo:`, `-AnyName:`, `-Force:`, `extra`) and the live runspace trigger all show `docker_calls=0`; the real container's `STILL_RUNNING_UNTOUCHED` after the `-Foo:`/`-AnyName:` colon reproductions. | closed |
| T-05-18 | Information Disclosure | Launcher usage-message path | low | mitigate | Usage line is a fixed literal that never echoes the rejected token, a host-argv element, or any environment value (`$RawArgs`/`$HostArgs`/`$ScriptArgs`/`$token`/`$args` never appear on an output line); validation runs before the `.env` path is computed; negative grep re-confirms neither script reads `.env` contents (`get_content=0`). | closed |
| T-05-19 (introduced by 05-05; amended and accepted by 05-06) | Denial of Service (availability, self-inflicted) | host-argv cross-check | low | accept | 05-05's cross-check failed open on an anchor miss to avoid falsely rejecting a bare invocation; 05-06 reverses that choice and fails closed instead (see T-05-08). New cost: an invocation from a host that leaves `$MyInvocation.Line` empty with no host-argv token naming the script — an in-process PowerShell runspace (live-reproduced), or any unprobed path form/runtime whose `GetFullPath` differs from `$PSCommandPath` — is now rejected even when it passes no arguments. `Start-Job -FilePath` is unaffected: `$RepoRoot` resolution throws before step 1 runs in that host regardless. See Accepted Risks Log AR-05-05. | closed (accepted) |
| T-05-SC | Tampering | Supply chain — npm / pip / cargo installs | high | mitigate | Zero new packages introduced across all six plans in this phase (05-01 through 05-06 — `git diff` since `fb14a5d` touches no manifest or lockfile, `NO_PACKAGE_CHANGES`). `npm ci` against committed `frontend/package-lock.json` and `uv sync --frozen` against `backend/uv.lock` install only already-audited versions from Phases 1-4 (RESEARCH.md Package Legitimacy Audit: empty table, no `[ASSUMED]`/`[SUS]`/`[SLOP]` verdicts). No legitimacy checkpoint required — nothing new to audit. | closed |

*Status: all closed — threats_open: 0*
*Severity: critical > high > medium > low — only open threats at or above `workflow.security_block_on` (high) count toward `threats_open`*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-05-01 | T-05-04 | Container runs as the image's default root user. A non-root UID would have to match the host owner of the bind-mounted `db/` on Linux, or DEPLOY-02 (data persistence) breaks. The container exposes only port 8000, handles no multi-tenant input, and is a single-user local demo per PLAN.md §3. | 05-01-PLAN.md threat model (plan-time) | 2026-09-22 |
| AR-05-02 | T-05-07 | Path traversal below the static-mount directory is Starlette `StaticFiles`' own responsibility and the canonical answer for this class; the mounted directory contains only the public frontend export, so a traversal would disclose nothing the browser is not already served. | 05-01-PLAN.md threat model (plan-time) | 2026-09-22 |
| AR-05-03 | T-05-13 | Verification runs PowerShell with `-ExecutionPolicy Bypass` because the launcher scripts are unsigned local files. Signing a capstone project's helper scripts is disproportionate; scripts are read from the repository the user already trusts enough to build and run. | 05-02-PLAN.md threat model (plan-time) | 2026-09-22 |
| AR-05-04 | T-05-01 residual | Pre-fix local Docker build-cache layers on this development machine may still hold `frontend/.env.development.local` from before the CR-01 fix. Local-only, owned by the same user who owns the source file; no registry push or cache export exists in this project. `docker builder prune` left as an optional, user-discretion cleanup rather than an automated step. | 05-03-PLAN.md threat model (plan-time) | 2026-09-23 |
| AR-05-05 | T-05-19 | Both Windows launchers fail closed when `$MyInvocation.Line` is empty and no host argv token resolves to the script's own path. A command-API host is therefore rejected even for a bare invocation, with the fixed usage line, exit 1 and zero Docker actions. This covers an in-process runspace (reproduced live) and any unprobed path form or runtime whose `GetFullPath` differs from `$PSCommandPath`. The risk is accepted for five reasons: none of these is a documented invocation (README.md, PLAN.md §11); the failure direction is safe (usage line, exit 1, zero Docker actions); a workaround is documented in the step-1 comment (a PowerShell prompt, or the call operator); every tested `-File` path form is still accepted; and failing open was the exact blocker this fix closes. | 05-06-PLAN.md threat model (plan-time); confirmed by gsd-security-auditor | 2026-09-29 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-09-24 (initial pass) | 19 | 19 | 0 | Claude (gsd-secure-phase, State B — register reconstructed from `<threat_model>` blocks across all four PLAN.md files; short-circuit path per ASVS L1 with `register_authored_at_plan_time: true` — deep auditor spawn not required; register cross-checked against SUMMARY.md coverage evidence and spot-verified directly against `Dockerfile`, `.dockerignore`, `.env.example`, and `scripts/stop_windows.ps1`) |
| 2026-09-24 (reopened, same day) | 19 | 18 | 1 | Claude (orchestrator) — the execute:post code-review gate (`05-REVIEW.md` CR-01/WR-01) found a real, independently-reproduced bypass of the argument-validation guard T-05-08 covers: a colon-suffixed valueless token (`-Foo:`) is dropped by PowerShell's `-File` tokenizer before `$args` sees it, letting `stop_windows.ps1` reach a live `docker stop` with no error, and `start_windows.ps1` silently swallow `-Build:`. Independently confirmed live against the committed scripts (not taken on the reviewer subagent's word alone) before reopening this row. |
| 2026-09-29 | 20 | 20 | 0 | Claude (gsd-secure-phase, State A — register updated from 05-06-PLAN.md's `<threat_model>`, `register_authored_at_plan_time: true`). 05-05's genuine partial fix (closed the original colon-bypass) had its own fail-open residual in the same host-argv cross-check (05-REVIEW.md 2026-09-27 CR-01/WR-01; 05-VERIFICATION.md truth 14) — the anchor-miss branch silently fell back to trusting `$args` alone. 05-06 restructured both launchers to fail closed instead. Verified twice: the orchestrator (unsandboxed, after merging 05-06's worktree branch) ran every `<verify>` command from 05-06-PLAN.md live against a real Docker daemon — both fault-injection matrices, the live non-mocked in-process runspace anchor-miss trigger, every 05-05 regression row, and the full live Docker sequence (colon reproductions, `-Build` rebuild, repeated start/stop, the stopped-state reproduction) all GREEN. A `gsd-security-auditor` pass then independently re-derived the static structural gates and re-ran the fault-injection/runspace/regression checks itself, declining only to repeat the live sequence against the real running container (relied on the orchestrator's addendum in 05-REVIEW.md for those specific rows). T-05-19 (05-05's fail-open choice, now reversed) added to the register as an `accept` disposition with Accepted Risks Log entry AR-05-05. `threats_open: 0`, `status: verified`. |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer) — 15 mitigate, 5 accept (T-05-04, T-05-07, T-05-13, T-05-19, plus the T-05-01 residual), 0 transfer.
- [x] Accepted risks documented in Accepted Risks Log.
- [x] `threats_open: 0` confirmed.
- [x] `status: verified` set in frontmatter.

**Approval:** verified — see GSD ► PHASE 5 THREAT-SECURE below.

## GSD ► PHASE 5 THREAT-SECURE

threats_open: 0 — no blocking threats remain. All 20 threats in the register are closed (15 mitigated, 5 accepted with documented rationale in the Accepted Risks Log).

▶ /gsd-validate-phase 5    validate test coverage
▶ /gsd-verify-work 5       run UAT
