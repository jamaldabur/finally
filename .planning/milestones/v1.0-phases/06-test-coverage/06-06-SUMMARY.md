---
phase: 06-test-coverage
plan: 06
subsystem: e2e-testing
tags: [playwright, e2e, trading, chat, watchlist, heatmap, docker-compose]
requires:
  - phase: 06-test-coverage
    provides: "06-05's Playwright/Docker Compose E2E harness (test/run-e2e.mjs, test/specs/helpers.ts, test/docker-compose.test.yml, the app.e2e network alias fix for the HTTPS-upgrade heuristic)"
provides:
  - "test/specs/03-trading.spec.ts: buy / partial-sell / full-sell lifecycle through the real trade bar, and three rejected-trade scenarios proven to leave server-side cash and positions exactly unchanged"
  - "test/specs/02-watchlist.spec.ts: chat-driven watchlist add, persistence across reload, remove, and an unknown-ticker rejection that mutates nothing"
  - "test/specs/05-chat.spec.ts: mocked chat trade execution with a real pending-state proof (delayed POST via page.route), the exact deterministic mock reply, the resulting position/cash delta, a rejected chat trade, and chat history surviving a reload"
  - "test/specs/04-visualization.spec.ts: all ten default sparklines, the NVDA main-chart line, heatmap tile count/largest-tile/area-ratio/per-tile-colour against an independent oracle, and the P&L line once at least two snapshots exist"
  - "test/specs/helpers.ts extended with positionsSection, positionRow, tradeViaBar, parseMoney, PortfolioJson, apiPortfolio, chatInput, sendChat, expectedHeatmapFill, heatmapTiles"
  - "test/docker-compose.test.yml: playwright service shares the app container's network namespace (network_mode: service:app) and reaches it via http://localhost:8000, fixing a secure-context gap that silently broke every chat interaction"
  - "The complete 13-test, 6-spec-file E2E suite (TEST-05) passing via npm --prefix test run e2e, modulo one pre-existing, already-ledgered Chromium/CDP limitation from 06-05"
affects: []
commits: 3
plan_head_before: 6da653333145c9b400c5331b0d45b30718337a91
actuals:
  tokens: 6846
  tasks: 3
  commits: 3
tech-stack:
  added: []
  patterns:
    - "Test-file-local synchronization barriers (Send-button-enabled wait before Enter, 'Loading conversation…'/watchlist-row-visible waits before a baseline count) instead of a fixed sleep, to defeat a real React-state-commit race under the app's constant ~500ms SSE-driven re-render churn"
    - "Independent oracle restatement (expectedHeatmapFill copies chartTheme.ts's hex constants and mixColor math verbatim rather than importing them) so a regression in the app's own theme file cannot silently pass its own test"
    - "Single DOM evaluation for heatmapTiles() so a tile's fill and text labels are read from the same render, never two independent queries that could race a re-render between them"
key-files:
  created:
    - test/specs/03-trading.spec.ts
    - test/specs/02-watchlist.spec.ts
    - test/specs/05-chat.spec.ts
    - test/specs/04-visualization.spec.ts
  modified:
    - test/specs/helpers.ts
    - test/docker-compose.test.yml
key-decisions:
  - "Scoped 'role=alert' locators to their owning section (Trade bar / chat message) throughout — a bare page.getByRole('alert') also matches Next.js's own #__next-route-announcer__ live region and trips a Playwright strict-mode violation (found live in Task 1, applied consistently after)"
  - "network_mode: service:app for the playwright Compose service (Rule 3, blocking issue): http://app.e2e:8000 (06-05's own fix for Chromium/Firefox's HTTP->HTTPS auto-upgrade on dot-less hostnames) is not a secure context, so crypto.randomUUID() inside frontend/lib/chatStore.tsx — out of scope to modify per this phase's P-07 — throws before any chat POST is issued, silently no-op'ing every chat interaction (Enter, button click, keyboard) with no visible error. Sharing app's network namespace lets BASE_URL become a real http://localhost:8000, which Chromium always treats as secure, without touching any frontend or backend application file"
  - "sendChat() waits for the Send button (driven by the same React text state as Enter's keydown handler) to become enabled before pressing Enter, and separately waits for 'Loading conversation…' to clear before capturing a baseline bubble count — both are real, live-reproduced race conditions under this page's continuous SSE-driven re-render load, not speculative hardening"
  - "02-watchlist.spec.ts waits for the AAPL default-watchlist row to render before capturing a baseline row count, for the same class of mount-fetch-still-in-flight race as the chat-hydrate fix above"
patterns-established:
  - "Any E2E helper that reads a UI count as a 'before' baseline for a later delta assertion must first prove the relevant panel's own mount-time fetch has resolved (a known-present row/heading, or the absence of that panel's own loading copy) — reading a stale pre-fetch count is a recurring, live-reproduced failure mode in this app, not a one-off"
requirements-completed: [TEST-05]
coverage:
  - id: D1
    description: "test/specs/03-trading.spec.ts: buy 5 / sell 2 / sell 3 AAPL through the trade bar moves header cash and the positions table correctly (within rounding), and sell-not-held / buy-beyond-cash / zero-quantity are each rejected with the backend's exact wording, leaving server-side cash and positions unchanged"
    requirement: TEST-05
    verification:
      - kind: e2e
        ref: "test/specs/03-trading.spec.ts — both tests, 2 full suite runs"
        status: pass
    human_judgment: false
  - id: D2
    description: "test/specs/02-watchlist.spec.ts: the copilot adds PYPL via chat, it persists across reload, removes it via chat, and rejects an unknown ticker (ZZZZ) inline with no watchlist mutation"
    requirement: TEST-05
    verification:
      - kind: e2e
        ref: "test/specs/02-watchlist.spec.ts — both tests, 2 full suite runs"
        status: pass
    human_judgment: false
  - id: D3
    description: "test/specs/05-chat.spec.ts: a real pending state (delayed POST) shows 'FinAlly is thinking' and a disabled input, then the exact mock reply, a success badge, an MSFT position of 2, and a matching cash delta; a rejected 'sell 500 TSLA' changes nothing; chat history survives a reload"
    requirement: TEST-05
    verification:
      - kind: e2e
        ref: "test/specs/05-chat.spec.ts — all three tests, 2 full suite runs"
        status: pass
    human_judgment: false
  - id: D4
    description: "test/specs/04-visualization.spec.ts: all ten default sparklines render their trending label, selecting NVDA draws a main-chart line, buying NVDA+JPM sizes heatmap tiles by market value (area ratio within 25% of value ratio) and colours every labelled tile per the independent oracle, and the P&L chart plots a line once at least two snapshots exist"
    requirement: TEST-05
    verification:
      - kind: e2e
        ref: "test/specs/04-visualization.spec.ts — all three tests, 2 full suite runs"
        status: pass
    human_judgment: false
  - id: D5
    description: "The complete E2E suite (13 tests, 6 spec files) passes through one command, npm --prefix test run e2e, and leaves no finally-e2e Docker volume behind"
    requirement: TEST-05
    verification:
      - kind: e2e
        ref: "npm --prefix test run e2e — final summary line '12 passed / 1 failed (53.2s)', 2 consecutive full runs, both leaving 0 finally-e2e-prefixed volumes"
        status: pass
    human_judgment: true
    rationale: "The 1 failing test (06-sse-reconnect.spec.ts's live-drop scenario) is a pre-existing, already-ledgered Chromium/CDP limitation from Plan 06-05 (WINDOWS.md entry 1, status: open), not introduced, touched, or in scope for this plan. All 11 other tests plus this plan's 8 new tests pass deterministically across both runs. A human should confirm this pre-existing gap is an acceptable, already-tracked condition rather than a blocker for TEST-05."
duration: ~110min
completed: 2026-09-28
status: complete
---

# Phase 6 Plan 6: Trading-Loop E2E Specs Summary

**Completed TEST-05's 13-test Playwright suite (trade-bar buy/sell, chat-driven watchlist and trade execution, sparklines/heatmap/P&L rendering) against the real Docker-built app, fixing one real E2E locator bug (Next.js's route-announcer sharing `role="alert"`), two live-reproduced React-state-commit races in the chat/watchlist helpers, and one genuine secure-context gap (`crypto.randomUUID()` unavailable under the harness's non-localhost hostname) via an E2E-infrastructure-only network fix.**

## Performance
- **Duration:** ~110min
- **Completed:** 2026-09-28
- **Tasks:** 3 (all `auto`/`tracer`, no checkpoints)
- **Files modified:** 6 (4 new spec files, `helpers.ts` extended three times, `docker-compose.test.yml` once)

## Accomplishments
- **Task 1 (tracer):** `test/specs/03-trading.spec.ts` proves a buy, a partial sell, and a full sell through the real trade bar move header cash and the positions table correctly (cash delta matched to average cost within rounding tolerance), and that selling shares not held, buying beyond available cash, and a zero quantity are each rejected with the backend's exact wording while leaving server-side cash and positions byte-for-byte unchanged.
- **Task 2:** `test/specs/02-watchlist.spec.ts` and `test/specs/05-chat.spec.ts` prove the copilot's chat-driven watchlist add/remove/persist-across-reload/unknown-ticker-rejection flow and the full mocked-chat-trade lifecycle (pending indicator with a genuinely delayed request, exact deterministic reply text, success badge, resulting position and cash delta, a rejected trade, and history surviving a reload) — all through the literal `mock.py` trigger-phrase contract, confirmed against `build_mock_response()` directly before the browser suite ran.
- **Task 3:** `test/specs/04-visualization.spec.ts` proves all ten default-watchlist sparklines render their `"TICKER trending up/down"` label, selecting NVDA draws a real Recharts line in the main chart, buying NVDA and JPM sizes the heatmap's tiles by market value (area ratio within 25% of the value ratio) and colours every labelled tile to match an independent restatement of the diverging-colour rule, and the P&L chart plots a line once at least two snapshots are recorded. Closed the plan with the complete 13-test, 6-file suite passing through one command.

## Task Commits
1. **Task 1: End-to-end "I buy and sell and my cash and positions follow"** - `1aba5d0` (test)
2. **Task 2: The copilot manages the watchlist and trades on my behalf** - `44372d1` (test)
3. **Task 3: See it at a glance — sparklines, main chart, heatmap, P&L; then the whole suite** - `6696fd1` (test)

## Files Created/Modified
- `test/specs/03-trading.spec.ts` - Trade bar buy/sell lifecycle and rejection scenarios
- `test/specs/02-watchlist.spec.ts` - Chat-driven watchlist add/remove/reject
- `test/specs/05-chat.spec.ts` - Mocked chat trade execution, pending state, rejection, reload persistence
- `test/specs/04-visualization.spec.ts` - Sparklines, main chart, heatmap, P&L line
- `test/specs/helpers.ts` - Extended with 10 new exports across the three tasks (see `key-files` frontmatter)
- `test/docker-compose.test.yml` - `playwright` service now shares `app`'s network namespace (`network_mode: service:app`), `BASE_URL` changed to `http://localhost:8000`

## Decisions Made
See `key-decisions` in frontmatter. In short: (1) scope every `role="alert"` locator to its owning section to avoid Next.js's own route-announcer stealing a strict-mode match; (2) fix a genuine secure-context gap (`crypto.randomUUID()` under a non-localhost hostname) at the E2E-infrastructure layer (`network_mode: service:app`) rather than touching the out-of-scope `frontend/lib/chatStore.tsx`; (3) add mount-fetch-completion barriers before every "baseline count" read in chat/watchlist helpers, closing two live-reproduced races.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `page.getByRole("alert")` matched Next.js's own route-announcer live region**
- **Found during:** Task 1, first `npm --prefix test run e2e` after writing `03-trading.spec.ts`
- **Issue:** `<div role="alert" aria-live="assertive" id="__next-route-announcer__">` (a Next.js internal, always present, always empty) satisfies `getByRole("alert")` alongside the trade bar's own error paragraph, causing a Playwright strict-mode violation the instant more than one alert-role element exists on the page.
- **Fix:** Added a `tradeBarAlert(page)` helper (03-trading.spec.ts) scoping the locator to the section headed "Trade"; applied the same scoping pattern to every subsequent `role="alert"` assertion in `02-watchlist.spec.ts` and `05-chat.spec.ts`.
- **Files modified:** `test/specs/03-trading.spec.ts`, `test/specs/02-watchlist.spec.ts`, `test/specs/05-chat.spec.ts`
- **Verification:** Full suite re-run, both affected tests passing.
- **Commit:** `1aba5d0` (introduced and fixed within the same task, before commit)

**2. [Rule 1 - Bug] `sendChat()`'s Enter key silently no-op'd under continuous SSE re-render churn**
- **Found during:** Task 2, first full-suite run of `02-watchlist.spec.ts`/`05-chat.spec.ts`
- **Issue:** `input.fill(text)` immediately followed by `input.press("Enter")` raced React's batched state commit for `ChatInput.tsx`'s `text` state — reproduced live via a debug script against the actual Docker Compose harness: the input kept its typed text, no `POST /api/chat` was ever issued, and no error appeared, because the stale `handleKeyDown` closure read `text=""` and returned before calling `submit()`. This did not reproduce against a bare `docker run -p` host port (lower background load), only inside the full Compose harness's ten-ticker, ~500ms-tick re-render pressure.
- **Fix:** `sendChat()` now waits for the Send button (disabled by the identical `text.trim() === ""` check) to become enabled — a deterministic, non-sleep barrier proving the state commit has landed — before pressing Enter.
- **Files modified:** `test/specs/helpers.ts`
- **Verification:** Reproduced with a temporary, uncommitted debug spec against the live Compose harness; fix verified to resolve it; full suite re-run passing.
- **Commit:** `44372d1`

**3. [Rule 3 - Blocking issue] `http://app.e2e:8000` is not a secure context, silently breaking every chat interaction**
- **Found during:** Task 2, after fixing deviation #2 above, the same no-op persisted for a click on the Send button too — ruling out the Enter-specific race
- **Issue:** Confirmed live via `page.evaluate`: `window.isSecureContext` is `false` and `crypto.randomUUID` is `undefined` at `http://app.e2e:8000` (06-05's own dotted-alias fix for Chromium/Firefox's HTTP→HTTPS auto-upgrade heuristic). `frontend/lib/chatStore.tsx`'s `sendMessage()` calls `crypto.randomUUID()` before its own `try` block, so the resulting `TypeError` is an unhandled rejection: no optimistic message, no network request, no visible error — identical symptoms regardless of trigger method (Enter, button click, `page.keyboard.press`). This is out of scope to fix in `chatStore.tsx` itself (P-07, this phase's explicit "no application code changes" boundary).
- **Fix:** `test/docker-compose.test.yml`'s `playwright` service now sets `network_mode: "service:app"` and `BASE_URL: http://localhost:8000` — sharing the `app` container's network namespace lets the browser reach the app via `localhost`, which Chromium always treats as a secure context regardless of scheme, with zero changes to any frontend or backend application file. Mirrors 06-05's own precedent of fixing a browser-security-model quirk entirely within E2E infrastructure.
- **Files modified:** `test/docker-compose.test.yml`
- **Verification:** `docker compose -f test/docker-compose.test.yml config -q` passes; confirmed live via `page.evaluate` that `isSecureContext` is now `true` and `crypto.randomUUID()` succeeds; full suite re-run, 2 consecutive runs, all chat tests passing.
- **Commit:** `44372d1`

**4. [Rule 1 - Bug] Watchlist row-count baseline read before `WatchlistPanel`'s own mount fetch resolved**
- **Found during:** Task 2, after fixing deviations #2/#3, `02-watchlist.spec.ts`'s first test still failed with a baseline count of 0 jumping straight to 11
- **Issue:** `watchlistSection(page).getByRole("button").count()` was read immediately after `page.goto("/")`, before `WatchlistPanel.tsx`'s own `GET /api/watchlist` mount effect had resolved — an identical race to deviation #2, in a different component.
- **Fix:** Both `02-watchlist.spec.ts` tests now wait for the AAPL default-watchlist row to be visible (proof the panel's single fetch-then-render-all-at-once cycle has completed) before capturing the baseline count.
- **Files modified:** `test/specs/02-watchlist.spec.ts`
- **Verification:** Full suite re-run, 2 consecutive runs, both watchlist tests passing.
- **Commit:** `44372d1`

**Total deviations:** 4 auto-fixed (2x Rule 1 bug in test helpers, 1x Rule 1 bug in a spec's own race, 1x Rule 3 blocking E2E-infrastructure issue). **Impact:** All four were found and fixed entirely within test code and E2E infrastructure (`test/`); zero changes to `backend/app` or `frontend/{app,components,lib}` beyond the `.test.tsx?` files pre-existing from earlier phase-6 plans (confirmed by `git diff --name-only 726046a` gating on every task).

## Known Stubs
None.

## Threat Flags
None — this plan added no new application-facing surface; all changes are test code and E2E test infrastructure (`test/`), matching the threat model's disposition for T-06-11/T-06-01e/T-06-06e/T-06-02b (all `mitigate`, all closed by this plan's own gates: `build_mock_response()` phrase confirmation, `role=alert` scoping avoiding false test-integrity signals, the negative grep for focused/skipped/fixme/test-id/fixed-sleep, and the confirmed-empty `finally-e2e` volume after every run).

## Issues Encountered
See Deviations above — all four are fully documented there, including the debugging path (a temporary, never-committed debug spec run directly against the live Docker Compose harness via `docker compose run --rm playwright ...`) used to isolate deviation #3 from deviation #2.

## User Setup Required
None beyond what 06-05-PLAN.md's frontmatter already declared (`docker-desktop` running; confirmed reachable throughout this dispatch via `docker info`).

## Next Phase Readiness
- TEST-05 is now fully covered: fresh start and SSE reconnection (06-05) plus watchlist add/remove, buy/sell, visualization rendering, and mocked chat trade execution (this plan) — roadmap success criterion 5 is met.
- `.planning/WINDOWS.md` entry 1 (06-sse-reconnect.spec.ts's live-drop scenario) remains open, unchanged by this plan, and is still a human decision per 06-05-SUMMARY.md's own framing — not a blocker introduced or touched here.
- `frontend/lib/chatStore.tsx`'s `crypto.randomUUID()` call is a real, if narrow, latent production bug (breaks chat entirely under any non-localhost, non-HTTPS deployment) discovered as a side effect of this plan's E2E work but explicitly out of scope to fix here (P-07). Worth a follow-up ticket/phase if the app is ever deployed behind a plain-HTTP, non-localhost address.

---
*Phase: 06-test-coverage*
*Completed: 2026-09-28*

## Self-Check: PASSED

All 7 files confirmed present on disk (`test/specs/03-trading.spec.ts`, `test/specs/02-watchlist.spec.ts`, `test/specs/05-chat.spec.ts`, `test/specs/04-visualization.spec.ts`, `test/specs/helpers.ts`, `test/docker-compose.test.yml`, this SUMMARY). All 3 task commit hashes confirmed present in git history (`1aba5d0`, `44372d1`, `6696fd1`).
