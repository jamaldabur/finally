---
phase: 06-test-coverage
plan: 05
subsystem: e2e-testing
tags: [playwright, docker-compose, e2e, sse, chromium]
requires:
  - phase: 05-docker-packaging-deployment
    provides: "Multi-stage Dockerfile with GET /api/health HEALTHCHECK, single-port single-container image"
provides:
  - "Committed test/ E2E project: docker-compose.test.yml (finally-e2e project, throwaway e2e-db volume), Dockerfile.playwright pinned to @playwright/test's exact version, playwright.config.ts (serial, no retries)"
  - "test/run-e2e.mjs: one portable command (npm --prefix test run e2e) that pre-cleans, builds+runs, and always tears down, proven idempotent across two consecutive runs"
  - "test/specs/01-fresh-start.spec.ts: proves a fresh app opens seeded ($10,000 cash/total value, ten default tickers), Connected, and streaming"
  - "test/specs/06-sse-reconnect.spec.ts: proves the browser's own EventSource retry loop reconnects after being unreachable at load; documents (does not paper over) a Chromium/CDP limitation for the live-drop scenario"
  - "test/specs/helpers.ts: shared locators/readers for specs after this plan (Plan 06-06)"
affects: [06-06-trading-loop-e2e-specs]
actuals:
  tokens: 5232
  tasks: 3
  commits: 2
tech-stack:
  added: ["@playwright/test@1.63.0 (test/, devDependency, exact pin)"]
  patterns:
    - "Dedicated runner image (test/Dockerfile.playwright) built from mcr.microsoft.com/playwright:v1.63.0-noble rather than a bind-mounted host install, matching @playwright/test's version exactly"
    - "docker-compose.test.yml project name (finally-e2e) namespaces every container/network/image/volume away from the user's own running app"
    - "Node script (spawnSync-based) for pre-clean/run/always-teardown, avoiding a shell-specific one-liner that doesn't port across cmd.exe and POSIX shells"
key-files:
  created:
    - test/package.json
    - test/package-lock.json
    - test/.gitignore
    - test/.dockerignore
    - test/Dockerfile.playwright
    - test/docker-compose.test.yml
    - test/playwright.config.ts
    - test/run-e2e.mjs
    - test/specs/helpers.ts
    - test/specs/01-fresh-start.spec.ts
    - test/specs/06-sse-reconnect.spec.ts
  modified: []
key-decisions:
  - "Task 1's blocking-human package-legitimacy checkpoint was answered 'approved' by the human in a prior dispatch before this continuation began; Task 2's @playwright/test@1.63.0 install proceeded exactly as evaluated, no substitution"
  - "Gave the app service a dotted network alias (app.e2e) and pointed BASE_URL at it instead of the bare Compose service name (app) — both Chromium and Firefox automatically upgrade http-to-https navigations for dot-less, non-IP-literal hostnames, which broke every navigation with ERR_SSL_PROTOCOL_ERROR/SSL_ERROR_UNKNOWN until fixed (Rule 3, verified live: raw container IP navigates fine, dotted alias navigates fine, bare 'app' fails in both browser engines)"
  - "Left the live-drop SSE reconnect assertion unweakened per the plan's own explicit contingency text, and documented the observed Chromium/CDP limitation as a blocker in .planning/WINDOWS.md rather than forcing a pass — see Deviations below"
requirements-completed: []
coverage:
  - id: D1
    description: "test/docker-compose.test.yml: two-service harness (app + playwright), throwaway e2e-db volume, LLM_MOCK=true, no published port/fixed name/production volume, gated on service_healthy"
    requirement: TEST-05
    verification:
      - kind: integration
        ref: "docker compose -f test/docker-compose.test.yml config -q"
        status: pass
      - kind: integration
        ref: "positive/negative content grep gates (project name, e2e-db, LLM_MOCK, service_healthy, context: .., no env_file/OPENROUTER/ports/container_name/ipc/finally-data/../db/network_mode/image: finally)"
        status: pass
      - kind: e2e
        ref: "npm --prefix test run e2e (full compose up/down cycle, x2 consecutive runs)"
        status: pass
    human_judgment: false
  - id: D2
    description: "test/Dockerfile.playwright pinned to mcr.microsoft.com/playwright:v1.63.0-noble, matching @playwright/test@1.63.0 exactly"
    requirement: TEST-05
    verification:
      - kind: unit
        ref: "grep FROM mcr.microsoft.com/playwright:v1.63.0-noble test/Dockerfile.playwright; grep \"@playwright/test\": \"1.63.0\" test/package.json"
        status: pass
    human_judgment: false
  - id: D3
    description: "test/playwright.config.ts: workers 1, fullyParallel false, retries 0, BASE_URL-driven baseURL"
    requirement: TEST-05
    verification:
      - kind: unit
        ref: "grep workers: 1|fullyParallel: false|retries: 0|process.env.BASE_URL test/playwright.config.ts"
        status: pass
      - kind: e2e
        ref: "npm --prefix test run list (Total: 3 tests in 2 files)"
        status: pass
    human_judgment: false
  - id: D4
    description: "test/run-e2e.mjs: one portable command, pre-clean, --exit-code-from playwright, always-teardown, exits with the suite's status"
    requirement: TEST-05
    verification:
      - kind: e2e
        ref: "npm --prefix test run e2e executed twice consecutively; both runs pre-cleaned, ran, tore down; docker volume ls --filter name=finally-e2e empty after each"
        status: pass
    human_judgment: false
  - id: D5
    description: "test/specs/01-fresh-start.spec.ts: seeded $10,000 cash/total value, ten default tickers, Connected status, fresh-state copy, and streaming prices within 15s"
    requirement: TEST-05
    verification:
      - kind: e2e
        ref: "test/specs/01-fresh-start.spec.ts — 'fresh start shows seeded cash, default watchlist, and streaming prices' (passed both full runs)"
        status: pass
    human_judgment: false
  - id: D6
    description: "test/specs/06-sse-reconnect.spec.ts: unreachable-at-load stream retries at least twice and connects once reachable"
    requirement: TEST-05
    verification:
      - kind: e2e
        ref: "test/specs/06-sse-reconnect.spec.ts — 'an unreachable stream keeps retrying and connects once reachable' (passed both full runs, 7.3s/7.7s)"
        status: pass
    human_judgment: false
  - id: D7
    description: "test/specs/06-sse-reconnect.spec.ts: a live stream that drops (context.setOffline) reconnects without a reload"
    requirement: TEST-05
    verification:
      - kind: e2e
        ref: "test/specs/06-sse-reconnect.spec.ts — 'a live stream that drops reconnects without a reload'"
        status: fail
    human_judgment: true
    rationale: "Deterministically fails in this Chromium (153.0.8010.12): context.setOffline(true) never moves the connection status off 'Connected' within 15s (confirmed non-racy in an isolated 30s diagnostic and across both full pipeline runs). Root cause: CDP's offline emulation blocks new connections but does not interrupt an already-open, continuously-streaming SSE connection — the app's simulator ticks every 500ms, so the stream is never idle enough for the emulation to intercept anything. This is the exact scenario 06-05-PLAN.md's own action text anticipated and pre-authorized documenting rather than weakening; a human should decide whether to accept this as a permanent environment limitation, retarget the technique (e.g. app-container stop/restart instead of context-level emulation), or accept D6 as sufficient proof of the underlying reconnect capability for TEST-05's SSE resilience scenario."
duration: ~50min (continuation dispatch only — Task 1's blocking-human checkpoint was answered in a separate, earlier dispatch not measured here)
completed: 2026-09-28
status: complete
---

# Phase 6 Plan 5: E2E Test Harness — Fresh Start & SSE Reconnection Summary

**Docker Compose two-service Playwright E2E harness (finally-e2e project) against the real production image, proving fresh-start seeding and one of two SSE-reconnection scenarios; the second (browser-offline-emulation) scenario deterministically cannot be observed in this Chromium and is documented as an open blocker rather than papered over.**

## Performance
- **Duration:** ~50min (this continuation dispatch — Tasks 2 and 3 only)
- **Completed:** 2026-09-28
- **Tasks:** 3 (Task 1's blocking-human checkpoint was satisfied by human approval in a prior dispatch; Tasks 2 and 3 executed here)
- **Files modified:** 12 (11 under `test/`, plus `.planning/WINDOWS.md`)

## Accomplishments
- Built `test/docker-compose.test.yml`: a two-service harness (`app` built from the real repo-root `Dockerfile` with `LLM_MOCK=true` on a throwaway `e2e-db` volume; `playwright` built from a pinned runner image) gated on the app's own `HEALTHCHECK` via `condition: service_healthy` — no sleep, no polling script, no published port, no fixed container name.
- Pinned `test/Dockerfile.playwright` to `mcr.microsoft.com/playwright:v1.63.0-noble`, matching the `@playwright/test@1.63.0` devDependency installed in Task 2 after the human's "approved" response to the Task 1 legitimacy checkpoint.
- Proved the full harness end-to-end: `test/specs/01-fresh-start.spec.ts` passed against the real Docker-built image (seeded $10,000 cash/total value, ten default tickers, Connected status, streaming prices) — both as a standalone `docker compose up` run and via the final `npm --prefix test run e2e` command.
- Built `test/run-e2e.mjs` (P-16): a portable Node script (`spawnSync`-based, no shell-specific syntax) that pre-cleans, runs with `--exit-code-from playwright`, always tears down, and exits with the suite's own status. Proved idempotent by running it twice consecutively — both runs reset the database from scratch (fresh-start passed both times) and left no `finally-e2e` Docker volume behind.
- Built `test/specs/06-sse-reconnect.spec.ts` and `test/specs/helpers.ts`. The unreachable-at-load scenario (`page.route` abort with `internetdisconnected`) passed reliably in both full runs, proving the browser's own `EventSource` retry loop fires at least twice and reconnects once the stream becomes reachable — with no app code reopening it.

## Task Commits
1. **Task 2: End-to-end "a fresh app opens seeded and streaming"** - `0b0c1d0` (feat)
2. **Task 3: Portable runner, shared helpers, SSE reconnect proof** - `99f000d` (test)

(Task 1's blocking-human checkpoint made no commits — evidence-gathering only, per its own acceptance criteria.)

## Files Created/Modified
- `test/package.json` - `finally-e2e` project; scripts `test`, `list`, `e2e`; `@playwright/test` pinned exact at `1.63.0`
- `test/package-lock.json` - committed lockfile for `npm ci` in the runner image
- `test/.gitignore` / `test/.dockerignore` - keep `node_modules`/run artifacts out of git and the runner image's build context
- `test/Dockerfile.playwright` - runner image on the pinned Playwright base, `npm ci` against the committed lockfile
- `test/docker-compose.test.yml` - `finally-e2e` project; `app` + `playwright` services; `e2e-db` throwaway volume; `app.e2e` network alias (see Deviations)
- `test/playwright.config.ts` - serial (`workers: 1`, `fullyParallel: false`, `retries: 0`), `BASE_URL`-driven `baseURL`, chromium project at 1600×1000
- `test/run-e2e.mjs` - the one portable `npm run e2e` entry point
- `test/specs/helpers.ts` - `DEFAULT_TICKERS`, `watchlistSection`, `watchlistRow`, `connectionStatus`, `readCash`, `readTotalValue`, `waitForPricesToMove`
- `test/specs/01-fresh-start.spec.ts` - the harness's own smoke test (self-contained, no shared helpers)
- `test/specs/06-sse-reconnect.spec.ts` - live-drop (documented blocker) and unreachable-at-load (passing) reconnection scenarios
- `.planning/WINDOWS.md` - new cross-phase defect ledger; entry 1 records the live-drop test's open blocker

## Decisions Made
- **Network alias fix (Rule 3, blocking config issue):** Both Chromium and Firefox automatically upgrade `http://` navigations to `https://` for dot-less, non-IP-literal hostnames — verified live by testing a raw container IP (works), the bare Compose service name `app` (fails `ERR_SSL_PROTOCOL_ERROR` in Chromium and `SSL_ERROR_UNKNOWN` in Firefox in both cases), and a dotted alias `app.e2e` (works). Tried several `--disable-features=HttpsUpgrades`-family Chromium launch flags first; none suppressed the behavior in this Chromium version (153.0.8010.12). Fixed by giving the `app` service a `networks.default.aliases: [app.e2e]` entry and pointing `BASE_URL` at `http://app.e2e:8000` — no other config changed, none of the plan's positive/negative compose-file verify gates were affected.
- **Live-drop assertion left unweakened (per plan's own explicit contingency):** 06-05-PLAN.md's Task 3 action text explicitly anticipated the possibility that `context.setOffline(true)` might never move the connection status off "Connected" in some Chromium builds, and instructed: do not weaken or remove the assertion, record the observation as a blocker, and rely on the second (unreachable-at-load) test to independently prove the underlying retry/reconnect capability. That is exactly what happened here (confirmed deterministic via an isolated 30-second diagnostic, not a timing race), so the spec was left exactly as originally written and the finding was recorded in `.planning/WINDOWS.md` rather than forced to pass.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking config issue] Browser-side HTTP→HTTPS auto-upgrade for the bare Compose hostname**
- **Found during:** Task 2, first `npm --prefix test run e2e` / `docker compose up` attempt
- **Issue:** `page.goto("/")` against `http://app:8000` (the plan's and RESEARCH.md's originally suggested `BASE_URL`) failed with `net::ERR_SSL_PROTOCOL_ERROR`; `uvicorn` simultaneously logged "Invalid HTTP request received" for the same connection, indicating the browser attempted a TLS handshake against a plain-HTTP port.
- **Fix:** Added a dotted network alias (`app.e2e`) to the `app` service via `networks.default.aliases`, and changed `BASE_URL` to `http://app.e2e:8000`. Verified via direct Playwright scripts inside the built runner image: raw IP works, dotted alias works, bare `app` fails in both Chromium and Firefox.
- **Files modified:** `test/docker-compose.test.yml`
- **Verification:** `docker compose -f test/docker-compose.test.yml config -q`; full positive/negative grep gate re-run (all pass); `npm --prefix test run e2e` passing twice consecutively.
- **Commit:** `0b0c1d0`

### Documented (not auto-fixed) blocker

**2. [Plan-anticipated, documented per explicit contingency text] Live-drop SSE reconnect test cannot observe a status transition in this Chromium**
- **Found during:** Task 3, first `npm --prefix test run e2e` run
- **Issue:** `context.setOffline(true)` never moves the header's connection-status text off "Connected" within the test's 15s window — confirmed deterministic (not a timing race) via an isolated 30-second diagnostic script and reproduced identically across both full `npm --prefix test run e2e` runs.
- **Root cause:** Chromium's CDP-based offline emulation blocks new network connections but does not interrupt an already-open, continuously-streaming SSE connection. The app's simulator pushes a new tick every 500ms (root PLAN.md §6), so the connection is never idle — there is no gap in delivery for the emulation layer to intercept.
- **Action taken:** Per 06-05-PLAN.md's own explicit instruction ("do not weaken or remove the assertion — record the observation in the SUMMARY as a blocker; the second test still proves the retry path independently"), the assertion was left exactly as written. The finding is recorded in `.planning/WINDOWS.md` (entry 1, `kind: deviation`).
- **Files:** `test/specs/06-sse-reconnect.spec.ts` (unchanged from its originally written form)
- **Independent proof retained:** `06-sse-reconnect.spec.ts`'s second test (`page.route` abort with `internetdisconnected`) passed reliably in both full runs (7.3s, 7.7s), independently proving the browser's own `EventSource` retry loop — the same underlying capability the live-drop test targets.
- **Commit:** `99f000d`

**Total deviations:** 1 auto-fixed (Rule 3, network hostname/HTTPS-upgrade), 1 documented-not-fixed (plan-anticipated environment limitation, recorded in `.planning/WINDOWS.md`).
**Impact:** The E2E harness itself (compose lifecycle, health-gating, throwaway database, idempotency) is fully proven — both `npm --prefix test run e2e` runs exited non-zero solely because of the one documented, plan-anticipated test, not because of any harness or app defect. `TEST-05`'s SSE-resilience scenario is proven via the unreachable-at-load path; the live-drop path via browser-offline-emulation is an open, tracked gap for a human to resolve (accept as environment limitation, or retarget the technique — see D7's rationale).

## Issues Encountered
See Deviations above — both issues are fully documented there. No other issues encountered.

## User Setup Required
None beyond what 06-05-PLAN.md's frontmatter already declared (`docker-desktop` running; confirmed reachable throughout this dispatch, `docker info` exits 0).

## Next Phase Readiness
- `test/specs/helpers.ts` is ready for Plan 06-06 to extend with trading-loop specs (watchlist add/remove, buy/sell, visualization, mocked chat trade execution) per its own docblock's guidance to keep each helper independent.
- **Open item for a human/future plan:** `.planning/WINDOWS.md` entry 1 — decide whether the live-drop SSE reconnect scenario is an acceptable permanent gap (given D6's independent proof of the same underlying capability) or whether a different technique (e.g., stopping/restarting the `app` container mid-test, which RESEARCH.md's Open Question 2 considered and deliberately deprioritized in favor of `setOffline`) should replace it.
- `TEST-05` is NOT marked complete in REQUIREMENTS.md by this plan — it is declared by both 06-05 and 06-06 (shared ID), and 06-06 has not yet executed.

---
*Phase: 06-test-coverage*
*Completed: 2026-09-28*

## Self-Check: PASSED

All 13 created files confirmed present on disk (`test/package.json`, `test/package-lock.json`, `test/.gitignore`, `test/.dockerignore`, `test/Dockerfile.playwright`, `test/docker-compose.test.yml`, `test/playwright.config.ts`, `test/run-e2e.mjs`, `test/specs/helpers.ts`, `test/specs/01-fresh-start.spec.ts`, `test/specs/06-sse-reconnect.spec.ts`, `.planning/WINDOWS.md`, this SUMMARY). All 3 commit hashes confirmed present in git history (`0b0c1d0`, `99f000d`, `44bf057`).
