---
phase: 05-docker-packaging-deployment
verified: 2026-09-22T20:15:00Z
status: gaps_found
score: 9/10 must-haves verified
covered_files:
  - ".dockerignore"
  - ".env.example"
  - ".planning/REQUIREMENTS.md"
  - ".planning/phases/05-docker-packaging-deployment/05-01-PLAN.md"
  - ".planning/phases/05-docker-packaging-deployment/05-01-SUMMARY.md"
  - ".planning/phases/05-docker-packaging-deployment/05-02-PLAN.md"
  - ".planning/phases/05-docker-packaging-deployment/05-02-SUMMARY.md"
  - ".planning/phases/05-docker-packaging-deployment/05-REVIEW.md"
  - "Dockerfile"
  - "backend/app/main.py"
  - "backend/tests/test_main.py"
  - "scripts/start_mac.sh"
  - "scripts/start_windows.ps1"
  - "scripts/stop_mac.sh"
  - "scripts/stop_windows.ps1"
covered_digest: "v1:sha256:84611ecc754c4a7b4a8c2df8b8721de8e35b5425f47132689529360971fa4c55"
behavior_unverified: 0
overrides_applied: 0
gaps:
  - truth: "No secret ever enters a Docker image layer via the build context (T-05-01 threat, disposition 'mitigate', Plan 05-01 must_haves.truths and must_haves.prohibitions)"
    status: failed
    reason: >
      `.dockerignore` excludes only the literal basename `.env` (line 15: a bare `.env`
      line, no wildcard), not `.env.*` variants. `frontend/.env.development.local`
      currently exists in this checkout — confirmed via `git status --porcelain
      --ignored=matching -- frontend/` which lists it as `!! frontend/.env.development.local`
      (present on disk, git-ignored by `frontend/.gitignore`'s broader `.env*` pattern,
      but NOT excluded by the root `.dockerignore`). `Dockerfile:10` (`COPY frontend/ ./`
      in the `frontend-build` stage) recursively copies the entire frontend source tree,
      including this unexcluded file, into that stage's image layer. This is the exact
      gap identified and empirically verified in the phase's own code review (CR-01,
      05-REVIEW.md), and it remains unresolved as of this verification pass — re-read
      both files directly and re-confirmed the file's presence independently. The plan's
      own claimed verification for this threat (a negative grep for `COPY .env`, Task 1)
      does not and cannot catch this path, because the leak comes from the frontend
      stage's blanket `COPY frontend/ ./`, not from an explicit `.env` copy instruction.
    artifacts:
      - path: ".dockerignore"
        issue: "Line 15 `.env` is an exact-basename match only (Docker's ignore-pattern semantics mirror .gitignore); does not match `.env.local`, `.env.development.local`, `.env.production`, etc."
      - path: "Dockerfile"
        issue: "Line 10 `COPY frontend/ ./` copies the full frontend/ tree into the frontend-build stage's layer with no per-file exclusion beyond .dockerignore"
    missing:
      - "Broaden `.dockerignore` to cover all dotenv variants while keeping the committed template, e.g.: `**/.env`, `**/.env.*`, `!**/.env.example` (CR-01's suggested fix), or equivalently `.env*` plus `!.env.example` at every depth, mirroring frontend/.gitignore's own pattern."
      - "Re-verify with `git status --porcelain --ignored=matching` that no `.env.*` variant remains uncovered, and confirm via `docker build --target frontend-build` + `docker history`/layer inspection that no dotenv file lands in that stage's layer."
---

# Phase 5: Docker Packaging & Deployment Verification Report

**Phase Goal:** A user can start the entire application with a single command and have their data persist across restarts
**Verified:** 2026-09-22T20:15:00Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A single multi-stage Docker build produces one image serving the frontend and every `/api/*` route on port 8000 (DEPLOY-01) | ✓ VERIFIED | Live: restarted the existing `finally:latest` container; `GET /api/health` → `{"status":"ok"}`, `GET /` → `<!DOCTYPE html>...` (Next.js export), `GET /api/portfolio` → 200, all on port 8000 from one container |
| 2 | The SQLite database persists across container restarts/replacement via a `db/` bind mount (DEPLOY-02) | ✓ VERIFIED | `docker inspect finally --format '{{json .Mounts}}'` shows `{"Type":"bind","Source":"...\\db","Destination":"/app/db",...}`; removed the container entirely and started a brand-new one against the same host `db/` — `GET /api/watchlist` still returned the previously-added `CSCO` ticker |
| 3 | Idempotent start/stop scripts exist for macOS/Linux (bash) and Windows (PowerShell) (DEPLOY-03) | ✓ VERIFIED | All 4 scripts present under `scripts/`, bash pair at git mode 100755. Live-tested bash non-launch behavior here (unknown-flag rejection rc=1, `stop_mac.sh` idempotent twice rc=0/0, cwd-independent from `/tmp`, `db/finally.db` intact throughout). PowerShell pair's full live round trip (start/re-start/rebuild/stop/re-stop) is documented and evidenced in 05-02-SUMMARY.md's `coverage` block (D1-D4, all `status: pass`) |
| 4 | `.env.example` is committed and documents `OPENROUTER_API_KEY`, `MASSIVE_API_KEY`, `LLM_MOCK` (DEPLOY-04) | ✓ VERIFIED | `git ls-files .env.example` lists it; `git check-ignore -v .env.example` exits 1 (not ignored); file contains all three variables as assignments with placeholder-only values |
| 5 | The static mount never breaks a frontend-less checkout and never shadows an API route (D-04) | ✓ VERIFIED | `uv run pytest tests/test_main.py` → 6 passed (3 pre-existing + 3 new); full suite `uv run pytest` → 227 passed |
| 6 | `FINALLY_DB_PATH` is explicitly set so the container's DB writes land inside the bind mount, not the container-default path | ✓ VERIFIED | `docker inspect finally --format Config.Env` shows `FINALLY_DB_PATH=/app/db/finally.db`; `db/finally.db` exists on host after every container lifecycle tested |
| 7 | Stop scripts are non-destructive — `db/finally.db` is byte-for-byte present after repeated stops (D-08) | ✓ VERIFIED | Ran `stop_mac.sh` twice in a row and from an unrelated cwd; `db/finally.db` present throughout; both scripts' source contains no removal/prune/move/truncate instruction (grep-confirmed) |
| 8 | No secret ever enters a Docker image layer via the build context (T-05-01, threat disposition "mitigate") | ✗ FAILED | `.dockerignore`'s `.env` pattern is a literal-basename match only; `frontend/.env.development.local` exists on disk, is git-ignored but NOT dockerignored, and `Dockerfile:10`'s `COPY frontend/ ./` copies it into the `frontend-build` layer. Independently re-confirmed CR-01 (05-REVIEW.md) is unresolved — see Gaps below |
| 9 | No top-level `docker-compose.yml` exists (D-10) | ✓ VERIFIED | `test ! -f docker-compose.yml` → true |
| 10 | Base and tool images are tag-pinned, no floating `latest` (T-05-03) | ✓ VERIFIED | Dockerfile has exactly 2 pinned `FROM` stages (`node:20-slim`, `python:3.12-slim`) plus `ghcr.io/astral-sh/uv:0.10.9`; negative grep for `:latest`/unpinned `FROM` found none |

**Score:** 9/10 truths verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `Dockerfile` | Two-stage build, node:20-slim → python:3.12-slim, FINALLY_DB_PATH set, real HEALTHCHECK | ✓ VERIFIED | Read in full; confirmed 2 FROM stages, `ENV FINALLY_DB_PATH=/app/db/finally.db`, `HEALTHCHECK` probing `/api/health` via stdlib Python |
| `.dockerignore` | Excludes secrets, user DB, deps from build context | ⚠️ PARTIAL | Excludes `db/*.db`, `db/*.db-journal`, `.env` (literal) — but NOT `.env.*` variants; see CR-01 gap |
| `.env.example` | Committed, documents 3 vars, placeholder-only | ✓ VERIFIED | All 3 vars present as assignments, no high-entropy tokens, not gitignored |
| `backend/app/main.py` | Guarded StaticFiles mount, module-scope STATIC_DIR | ✓ VERIFIED | `STATIC_DIR = Path(__file__).resolve().parents[1] / "static"`; guarded `if STATIC_DIR.is_dir(): app.mount(...)` as last statement of `create_app()`, after all 5 routers |
| `backend/tests/test_main.py` | 3 new regression tests for the static mount | ✓ VERIFIED | 6 tests pass (3 pre-existing + 3 new); full 227-test suite green |
| `scripts/start_mac.sh` | Idempotent bash launcher | ✓ VERIFIED | Present, executable (mode 100755), passes all structural + live non-launch checks |
| `scripts/stop_mac.sh` | Idempotent bash stopper, non-destructive | ✓ VERIFIED | Present, executable (mode 100755), live-tested idempotent + non-destructive |
| `scripts/start_windows.ps1` | Idempotent PowerShell launcher | ✓ VERIFIED | Present; matches bash contract; live round trip evidenced in 05-02-SUMMARY.md |
| `scripts/stop_windows.ps1` | Idempotent PowerShell stopper | ✓ VERIFIED | Present; matches bash contract; no destructive instruction found on read |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `Dockerfile` | `backend/app/main.py` | frontend build output copied to `/app/static`, matching `STATIC_DIR` | ✓ WIRED | Live `GET /` returned the built Next.js HTML |
| `Dockerfile` | `backend/app/db/watchlist.py` | `ENV FINALLY_DB_PATH=/app/db/finally.db` overrides the module default | ✓ WIRED | `docker inspect` confirms env var set; DB persisted at the bind-mounted path |
| host `db/` | container `/app/db` | bind mount | ✓ WIRED | `docker inspect --format Mounts` confirms bind type, correct source/destination |
| `Dockerfile HEALTHCHECK` | `backend/app/routes/health.py` | stdlib `urllib.request` against `/api/health` | ✓ WIRED | Live curl of the same endpoint returns the expected body |
| `scripts/start_mac.sh` | `Dockerfile` | `docker build -t "$IMAGE_TAG" "$REPO_ROOT"` | ✓ WIRED | Read in full; matches |
| `scripts/start_mac.sh` | host `db/` | `DB_DIR="$REPO_ROOT/db"; mkdir -p; -v "$DB_DIR:/app/db"` | ✓ WIRED | Read in full; matches |
| `scripts/start_mac.sh` | `.env.example` | missing-`.env` error names the template | ✓ WIRED | Line 61: `"Copy .env.example to .env and fill in OPENROUTER_API_KEY..."` |
| `scripts/start_mac.sh` | `backend/app/routes/health.py` | readiness poll against `/api/health` | ✓ WIRED | Line 112 |
| `scripts/start_windows.ps1` | `scripts/start_mac.sh` | same contract, two languages | ✓ WIRED | Identical constants, step order, exit codes confirmed by side-by-side read |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Container answers `/api/health` | `docker start finally` + `curl /api/health` | `{"status":"ok"}` | ✓ PASS |
| Container serves frontend at `/` | `curl /` | `<!DOCTYPE html>...` | ✓ PASS |
| Container answers `/api/portfolio` | `curl -o /dev/null -w '%{http_code}'` | `200` | ✓ PASS |
| Bind mount is real (not a named volume/copy) | `docker inspect --format Mounts` | `Type: bind`, host `db/` → `/app/db` | ✓ PASS |
| Data survives container replacement | add ticker → `docker rm -f` → fresh `docker run` → `GET /api/watchlist` | `CSCO` still present | ✓ PASS |
| Static-mount regression tests | `uv run pytest tests/test_main.py` | 6 passed | ✓ PASS |
| Full backend suite | `uv run pytest` (run once) | 227 passed | ✓ PASS |
| Bash scripts parse | `bash -n scripts/start_mac.sh scripts/stop_mac.sh` | SYNTAX_OK | ✓ PASS |
| Unknown flag rejected pre-daemon | `bash scripts/start_mac.sh --bogus-flag` | rc=1 | ✓ PASS |
| Stop idempotent twice | `bash scripts/stop_mac.sh` x2 | rc=0, rc=0 | ✓ PASS |
| Stop is cwd-independent | invoked from `/tmp` | `CWD_INDEPENDENT` | ✓ PASS |
| `db/finally.db` intact after all runs | `test -f db/finally.db` | `DATA_INTACT` | ✓ PASS |
| Scripts executable in git index | `git ls-files -s scripts/start_mac.sh scripts/stop_mac.sh` | both `100755` | ✓ PASS |
| No `docker-compose.yml` | `test ! -f docker-compose.yml` | `NO_COMPOSE` | ✓ PASS |
| All claimed commit hashes exist | `git cat-file -e <hash>` x6 | all OK | ✓ PASS |
| **CR-01 secrets-leak re-check** | `git status --porcelain --ignored=matching -- frontend/` + read `.dockerignore` | `frontend/.env.development.local` present, ignored, NOT dockerignored | ✗ FAIL (confirms CR-01 unresolved) |

### Probe Execution

SKIPPED (no `scripts/*/tests/probe-*.sh` files exist, and neither plan declares any probe path).

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|--------------|--------|----------|
| DEPLOY-01 | 05-01 | Multi-stage image serves frontend + API on port 8000 | ✓ SATISFIED | Live container round-trip (see Behavioral Spot-Checks) |
| DEPLOY-02 | 05-01 | SQLite persists via `db/` bind mount | ✓ SATISFIED | Live round-trip across container destruction/replacement |
| DEPLOY-03 | 05-02 | Idempotent start/stop scripts, macOS/Linux + Windows | ✓ SATISFIED | Structural + live non-launch checks here; PowerShell live round trip in 05-02-SUMMARY.md coverage block |
| DEPLOY-04 | 05-01 | `.env.example` committed, documents 3 vars | ✓ SATISFIED | grep assertions + `git check-ignore` |

No orphaned requirements — REQUIREMENTS.md maps exactly DEPLOY-01..04 to Phase 5, and both plans together claim all four.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `.dockerignore` / `Dockerfile` | `.dockerignore:15`, `Dockerfile:10` | Secrets-capable file (`frontend/.env.development.local`) not excluded from build context, copied into `frontend-build` image layer | 🛑 Blocker | CR-01 (unresolved, code review already verified this empirically); contradicts the plan's own T-05-01 threat-model mitigation and ASVS V14 intent; re-confirmed present in this verification pass |
| `backend/app/main.py` | 90-92 | `update_task.cancel(); snapshot_task.cancel(); await source.stop()` — tasks cancelled but not awaited before releasing the shared `httpx.AsyncClient` | ⚠️ Warning | WR-01: can log a spurious shutdown error against `MassiveMarketDataSource`; not exercised by the simulator-default test suite |
| `scripts/start_mac.sh` | 112 | `curl -fsS "${APP_URL}/api/health"` has no `--max-time`/`--connect-timeout` | ⚠️ Warning | WR-02: a single hung attempt can blow through the documented ~40s readiness bound; the Windows script correctly bounds each attempt |
| `scripts/start_windows.ps1` | 66, 74, 105, 129, 148 | `Write-Error` under `$ErrorActionPreference = "Stop"` terminates before the following `exit 1`, printing a raw exception block instead of a clean message | ⚠️ Warning | WR-03: exit code contract still holds (non-zero), but user-facing error text is a stack-trace-shaped dump, not the intended one-liner |
| `Dockerfile` | 1-63 | No `ENV PYTHONUNBUFFERED=1` | ℹ️ Info | IN-01: minor `docker logs` ordering/delay confusion during debugging |
| `Dockerfile` | 57-62 | Container runs as root, no `USER` directive | ℹ️ Info | IN-02: documented, accepted tradeoff (T-05-04) given cross-platform bind-mount ownership constraints; not flagged as an oversight |

## Gaps Summary

One Blocker remains unresolved: **CR-01**, already identified by this phase's own code review and independently re-verified here by direct inspection of `.dockerignore`, `Dockerfile`, and the live filesystem state (`git status --porcelain --ignored=matching`). `frontend/.env.development.local` exists in this checkout right now, is excluded from git by `frontend/.gitignore`'s broad `.env*` pattern, but is **not** excluded from the Docker build context by the root `.dockerignore` (which only matches the literal basename `.env`). Because `Dockerfile:10` does an unqualified `COPY frontend/ ./` in the `frontend-build` stage, any secret dropped into a `.env.local`/`.env.development.local`-style file during local frontend development would be copied into that stage's image layer — persisting in the local build cache and in any exported/pushed build cache, inspectable via `docker build --target frontend-build` + `docker history`/layer export, even though the final runtime stage doesn't ship it directly.

This directly implicates the plan's own must-have: "No secret and no user database ever enters an image layer" (Plan 05-01 must_haves.truths) and its paired prohibition "MUST NOT bake ... the project `.env` file into any image layer ... by omitting them from `.dockerignore`." The plan's own verification mechanism for this threat (T-05-01, a negative grep for a `COPY .env` instruction) is structurally blind to this leak path, since the leak comes from a blanket directory copy, not an explicit `.env` copy instruction.

**This looks fixable in one line, not architectural.** The suggested fix from CR-01 is a `.dockerignore` broadening (`**/.env`, `**/.env.*`, `!**/.env.example`), with no Dockerfile or application-code change required. No override is being applied — the underlying security gap is real and demonstrated, not merely theoretical, so it is reported as a gap for either a fix or an explicit accepted-risk override, rather than silently passed.

**Secondary, non-blocking note (residual, already self-disclosed by the phase):** the bash pair's actual `docker run` launch path (as opposed to `.env`-guard/idempotency/cwd-independence, all of which were live-tested here) has still not been exercised end-to-end on a real macOS/Linux host — this verifier's environment is Windows, the same constraint the plan's own Edge Coverage section names. This does not block DEPLOY-03 (idempotency, argument validation, and non-destructiveness were all live-proven for the bash pair, and the equivalent Windows script — proven to share an identical contract — was fully round-tripped), but it remains an open item for a future real-host check or Phase 6's E2E infrastructure.

---

_Verified: 2026-09-22T20:15:00Z_
_Verifier: Claude (gsd-verifier)_
