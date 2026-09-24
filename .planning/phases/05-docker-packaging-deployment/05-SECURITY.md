---
phase: "5"
slug: "docker-packaging-deployment"
status: draft
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 1
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
| T-05-08 (amended by 05-04, reopened 2026-09-24) | Tampering | `start_windows.ps1` / `stop_windows.ps1` argument handling | medium | mitigate | 05-02's original claim (declared switch parameter rejects unknown args) was false — 05-VERIFICATION.md reproduced silent acceptance 3x. 05-04 replaced it with an exact-match guard over raw `$args`, closing that specific gap (live-verified against a running container, ID/`StartedAt` unchanged across every tested rejected invocation). **However, the 2026-09-24 code review (05-REVIEW.md CR-01/WR-01) found and the orchestrator independently reproduced a NEW bypass in the same guard**: a dash-prefixed, colon-suffixed, valueless token (e.g. `-Foo:`) is silently dropped by PowerShell's `-File` tokenizer *before* `$args` is populated, so `$args.Count` reads `0` — indistinguishable from true no-argument invocation. `stop_windows.ps1 '-Foo:'` reaches the daemon query and (independently confirmed) `docker stop` a running container, with no error message. `start_windows.ps1 '-Build:'` is swallowed to a normal (non-rebuild) start. The `$args`-only validation strategy 05-04 chose is provably incomplete against PowerShell's own `-File` command-line parser. | **open** |
| T-05-09 | Information Disclosure | `.env` handling in launcher scripts | medium | mitigate | Scripts test only file existence and pass the path to `--env-file`; negative grep confirms no instruction reads file contents. | closed |
| T-05-10 (re-asserted by 05-04) | Tampering / data destruction | Stop scripts | high | mitigate | Neither stop script contains a removal/prune/move/truncate instruction (enforced by negative grep over comment-filtered source); `db/finally.db` confirmed present after every stop sequence, including 05-04's re-run of this gate over the modified `stop_windows.ps1`. Confirmed in codebase: `scripts/stop_windows.ps1` line 3 comment + no destructive verbs found. **Narrow claim still true** (no destructive instruction exists), but see T-05-08 (reopened): CR-01's bypass reaches the script's own legitimate, non-destructive `docker stop` call unintentionally — this row's own guarantee (nothing destructive was added) holds; T-05-08's guarantee (only intended invocations reach that call) does not, currently. | closed (see T-05-08) |
| T-05-11 | Tampering | Bind-mount source resolution | medium | mitigate | Built from `dirname "$0"` / `$PSScriptRoot`, created before use, quoted; verified by invoking from an unrelated working directory. | closed |
| T-05-12 | Spoofing | Container identity detection | low | mitigate | Detection uses `docker ps --filter "name=^finally$" --filter "status=running" -q` — anchored regex prevents a similarly-named container from being mistaken for FinAlly. | closed |
| T-05-13 | Elevation of Privilege | Script execution policy on Windows | low | accept | Verification runs PowerShell with `-ExecutionPolicy Bypass` for unsigned local scripts — see Accepted Risks Log. | closed (accepted) |
| T-05-14 | Information Disclosure | 05-03 Task 1's probe and inventory commands | medium | mitigate | Probes run only post-fix; sentinel files created empty, never written; probes list names only (`find -name`), never contents; project secret-read guard hook refuses any content-reading command against a dotenv filename. | closed |
| T-05-15 | Denial of Service (availability) | `lifespan` shutdown with the Massive source | low | mitigate | `asyncio.gather(update_task, snapshot_task, return_exceptions=True)` before `source.stop()` — no client closed underneath an in-flight request. Locked by `backend/tests/test_main.py::test_lifespan_awaits_background_tasks_before_stopping_source` (currently passing, confirmed in this audit's full-suite run: 228 passed). | closed |
| T-05-16 | Denial of Service (availability) | `start_mac.sh` readiness poll | low | mitigate | Every `curl` call bounded with `--max-time 2`, matching `start_windows.ps1`'s `-TimeoutSec 2`; structural gate asserts every non-comment curl call is bounded. | closed |
| T-05-17 | Denial of Service (availability) | `stop_windows.ps1` | low | mitigate | New (05-04) zero-argument guard exits before any *tested* argument reaches `docker stop`; live gate confirms a rejected stop leaves the running container untouched for every shape 05-04's own matrices covered. **Bypass found 2026-09-24 (see T-05-08):** a colon-suffixed valueless token is not one of those shapes and reaches `docker stop` — this raises T-05-17's own severity in practice (an unintended stop IS a DoS against availability) even though the row's original claim was true for what it tested. | closed (see T-05-08) |
| T-05-18 | Information Disclosure | Launcher usage-message path | low | mitigate | Usage line is a fixed literal that never echoes the rejected token or any environment value; validation runs before the `.env` path is computed; negative grep re-confirms neither script reads `.env` contents. | closed |
| T-05-SC | Tampering | Supply chain — npm / pip / cargo installs | high | mitigate | Zero new packages introduced across all four plans in this phase (05-01 through 05-04). `npm ci` against committed `frontend/package-lock.json` and `uv sync --frozen` against `backend/uv.lock` install only already-audited versions from Phases 1-4 (RESEARCH.md Package Legitimacy Audit: empty table, no `[ASSUMED]`/`[SUS]`/`[SLOP]` verdicts). No legitimacy checkpoint required — nothing new to audit. | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
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

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-09-24 (initial pass) | 19 | 19 | 0 | Claude (gsd-secure-phase, State B — register reconstructed from `<threat_model>` blocks across all four PLAN.md files; short-circuit path per ASVS L1 with `register_authored_at_plan_time: true` — deep auditor spawn not required; register cross-checked against SUMMARY.md coverage evidence and spot-verified directly against `Dockerfile`, `.dockerignore`, `.env.example`, and `scripts/stop_windows.ps1`) |
| 2026-09-24 (reopened, same day) | 19 | 18 | 1 | Claude (orchestrator) — the execute:post code-review gate (`05-REVIEW.md` CR-01/WR-01) found a real, independently-reproduced bypass of the argument-validation guard T-05-08 covers: a colon-suffixed valueless token (`-Foo:`) is dropped by PowerShell's `-File` tokenizer before `$args` sees it, letting `stop_windows.ps1` reach a live `docker stop` with no error, and `start_windows.ps1` silently swallow `-Build:`. Independently confirmed live against the committed scripts (not taken on the reviewer subagent's word alone) before reopening this row. |

---

## Sign-Off

- [ ] All threats have a disposition (mitigate / accept / transfer) — 15 mitigate (1 currently open: T-05-08), 4 accept (T-05-04, T-05-07, T-05-13, plus the T-05-01 residual), 0 transfer.
- [x] Accepted risks documented in Accepted Risks Log.
- [ ] `threats_open: 0` confirmed. **Currently `threats_open: 1`** (T-05-08).
- [ ] `status: verified` set in frontmatter. **Currently `status: draft`** — phase advancement blocked until resolved.

**Approval:** pending — see ENFORCING GATE below.

## GSD ► PHASE 5 SECURITY BLOCKED

1 blocking threat open (T-05-08, medium severity — argument-validation guard on `start_windows.ps1`/`stop_windows.ps1` has a colon-suffixed-token bypass) — phase advancement blocked until `threats_open: 0`.

▶ Fix the mitigation (reject any `$args` element ending in `:`, and/or cross-check `[Environment]::GetCommandLineArgs()` against `$args` for a stray token count) in a new gap-closure plan, then re-run `/gsd-secure-phase 05`.
▶ Or, if this residual risk is judged acceptable for a local single-user demo, document it explicitly in the Accepted Risks Log above and re-run `/gsd-secure-phase 05`.

Do NOT emit next-phase routing while this stands open.
