---
gsd_state_version: "1.0"
current_phase: 6
current_phase_name: Test Coverage
status: executing
stopped_at: Phase 6 context gathered
last_updated: "2026-09-27T20:30:23.748Z"
last_activity: 2026-09-27
last_activity_desc: Phase 05 execution started
state_head: 47c357e9417fe9a39a13a34f4fc963b55c6544a2
progress:
  total_phases: 6
  completed_phases: 4
  total_plans: 33
  completed_plans: 27
  percent: 67
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-09-22)

**Core value:** A user can watch live prices, trade a simulated portfolio, and have an AI copilot execute trades on their behalf — the full agentic trading loop (watch → decide → chat → execute → see it reflected in the portfolio) must work end-to-end.
**Current focus:** Phase 05 — Docker Packaging & Deployment

## Current Position

Phase: 6 (Test Coverage) — READY TO EXECUTE
Plan: 2 of 5
Status: Ready to execute
Last activity: 2026-09-27 — Phase 05 execution started

Progress: [███████░░░] 67%

## Performance Metrics

**Velocity:**

- Total plans completed: 22
- Average duration: - min
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 4 | - | - |
| 02 | 3 | - | - |
| 03 | 8 | - | - |
| 04 | 7 | - | - |

**Recent Trend:**

- Last 5 plans: -
- Trend: -

*Updated after each plan completion*
**Per-Plan Metrics:**

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 01 P01-01 | 17min | 3 tasks | 15 files |
| Phase 01 P01-02 | 25min | 3 tasks | 4 files |
| Phase 01 P01-03 | 11min | 3 tasks | 10 files |
| Phase 01 P01-04 | 15min | 3 tasks | 9 files |
| Phase 02 P01 | 19min | 3 tasks | 5 files |
| Phase 02 P02 | 24min | 2 tasks | 5 files |
| Phase 02 P03 | 11min | 3 tasks | 9 files |
| Phase 03 P01 | 24min | 3 tasks | 15 files |
| Phase 03 P02 | 35min | 2 tasks | 7 files |
| Phase 03 P03 | 20min | 2 tasks | 8 files |
| Phase 03 P04 | 30min | 2 tasks | 5 files |
| Phase 03 P06 | 25min | 2 tasks | 2 files |
| Phase 03 P05 | 35min | 2 tasks | 2 files |
| Phase 03 P08 | 45min | 2 tasks | 5 files |
| Phase 03 P07 | 20min | 2 tasks | 2 files |
| Phase 04 P01 | 15min | 2 tasks | 6 files |
| Phase 04 P04 | 15min | 2 tasks | 6 files |
| Phase 04 P05 | 15min | 2 tasks | 3 files |
| Phase 04 P04-06 | 12min | 2 tasks | 1 files |
| Phase 04 P04-07 | 15min | 3 tasks | 7 files |
| Phase 05 P01 | 25min | 3 tasks | 5 files |
| Phase 05 P02 | 35min | 2 tasks | 4 files |
| Phase 05 P03 | 30min | 3 tasks | 5 files |
| Phase 05 P04 | 25min | 3 tasks | 3 files |
| Phase 05 P05 | 15min | 3 tasks | 3 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Milestone-wide: Treat `planning/PLAN.md` as the binding spec; this GSD cycle scopes/sequences work rather than re-deciding architecture
- Milestone-wide: Single v1 milestone covers the full remainder of PLAN.md (portfolio, chat, frontend, Docker, tests)
- Roadmap: Structured as a Vertical MVP — Phase 1 delivers a complete backend trading engine, Phase 2 wires the minimal frontend to it, then chat, then visualization, then packaging, then tests
- [Phase 01]: Route tests use TestClient.portal.call(...) as the sync-safe pattern to drive async price-cache seeding/DB reads on the app's own event loop — Avoids cross-event-loop hazard between a pytest-asyncio test loop and TestClient's dedicated portal thread where the app's lifespan and background tasks actually run
- [Phase 01]: BUY-path route tests seed prices on CSCO (valid but not on DEFAULT_WATCHLIST) instead of AAPL — AAPL is on the default watchlist, so the real background update loop races the test's manually-seeded price under full-suite load; a non-watchlist ticker is never touched by that loop
- [Phase 01]: Task 2/3 tests for Plan 01-02 passed immediately (no paired feat commit) because the sell sufficiency guard was load-bearing for Task 1's own correctness — Documented as a process note in 01-02-SUMMARY.md deviations, not a Rule 1-4 auto-fix
- [Phase 01]: Watchlist join test uses a POST-added, non-DEFAULT_WATCHLIST ticker (ORCL) instead of AAPL to avoid the run_update_loop race documented in Plan 01
- [Phase 01]: Resolved a pytest module-basename collision between tests/db/test_watchlist.py and the plan-locked tests/routes/test_watchlist.py by adding package __init__.py files rather than renaming either file
- [Phase 01]: [Phase 01]: portfolio_snapshots.init_db() wired into app/main.py's lifespan during Task 2 instead of Task 3, since GET /api/portfolio/history (a Task 2 deliverable) needs the table to exist
- [Phase 01]: [Phase 01]: Rounded compute_portfolio_view()'s derived monetary/percentage values to cent precision to match app/market/simulator.py's round-once convention and avoid float-precision leaking into the locked API contract
- [Phase 02]: [Phase 02-01]: typescript pinned to 6.0.3 (not the plan's 7.0.2) because eslint-config-next@16.3.5's bundled typescript-eslint@8.70.0 requires typescript <6.1.0
- [Phase 02]: [Phase 02-01]: portfolioStore.tsx's mount-time fetch is a self-contained async IIFE effect, not a call to the exported refresh() callback, to satisfy eslint-plugin-react-hooks 7.1.1's set-state-in-effect rule
- [Phase 02]: [Phase 02-02]: PriceCell flash trigger compares against a per-cell useRef of its own last rendered price, never the SSE tick's previous_price field — PriceCache.update() keeps the old previous_price on an unchanged heartbeat
- [Phase 02]: [Phase 02-02]: WatchlistRow's change% is session-relative (since page open, from priceStore's firstPrices), labelled "Chg. since open" since the backend contract carries no daily open/previous close
- [Phase 02]: [Phase 02-03]: Numeric-cell monospace font applied via one global .tabular-nums { font-family } CSS rule rather than threading a second utility class into WatchlistRow/PriceCell (outside this plan's file scope) — reaches every existing tabular-nums element site-wide
- [Phase 02]: [Phase 02-03]: portfolioStore's 5s refresh interval and TradeBar's post-trade refresh share one isRefreshingRef guard, so an in-flight fetch from either source blocks a second overlapping fetch
- [Phase 02]: [Phase 02-03]: priceStore's D-06 grace-timer uses a single useRef timer handle, always cleared before being re-armed on onopen/prices/onerror, so interleaved error/recovery events can never leave the connection dot stuck red while the stream is live
- [Phase 03]: [Phase 03-01]: LLM model switched from openrouter/openai/gpt-oss-120b to openrouter/openrouter/free after live verification hit 402 insufficient credits on the original model (user-directed, re-verified end-to-end before continuing)
- [Phase 03]: [Phase 03-01]: execute_trade() gains a leading quantity/side validation guard (before ticker normalization and is_valid_ticker) closing the Phase 1 WR-01/WR-02 blocker, since the chat flow calls it directly bypassing the HTTP route's Pydantic layer
- [Phase 03]: [Phase 03-02]: PROMPT_HISTORY_LIMIT=20 and GET /api/chat limit=50 (03-RESEARCH.md A2) — no pruning policy existed in PLAN.md for chat_messages, decided explicitly here
- [Phase 03]: [Phase 03-02]: chat_messages history ordered by SQLite rowid, not created_at — two rows written inside one request can carry identical ISO timestamps
- [Phase 03]: [Phase 03-03]: messages typed ChatMessage[] | null (never defaulting to []) so hydrating and hydrated-empty stay distinguishable states
- [Phase 03]: [Phase 03-03]: ChatProvider nests inside PortfolioProvider (load-bearing) — chatStore calls usePortfolio().refresh() after an executed chat trade
- [Phase 03]: [Phase 03-04]: ActionBadge reason span uses normal-case despite the UI-SPEC's single Micro/Badge role for the whole pill — uppercasing a full rejection sentence would make the string the user most needs to read the least readable
- [Phase 03]: [Phase 03-04]: ChatPanel's collapsed flag and collapsed-at-count are held in useState (not useRef) since both are read during render to derive hasUnread, per the project's react-hooks rule against reading ref.current at render time
- [Phase 03]: [Phase 03-04]: ChatMessageList's scroll-pin/new-activity flags are derived during render (conditional setState during render) rather than in a useEffect body, avoiding a set-state-in-effect lint violation while the actual DOM scroll mutation stays in a real useEffect
- [Phase 03]: [Phase 03-06]: Deleted litellm.enable_json_schema_validation rather than re-enabling it after dropping stream=True — re-enabling would raise before parse_llm_response()'s fence recovery ever runs, reintroducing the exact silently-dropped-trade failure (G-03-3)
- [Phase 03]: [Phase 03-06]: FALLBACK_MODEL set to openrouter/nvidia/nemotron-3-super-120b-a12b:free, matching this repo's agent-teams branch's independent choice for the same free-router flakiness
- [Phase 03]: [Phase 03]: [Phase 03-05]: Amended 03-UI-SPEC.md before touching ChatPanel.tsx (spec-first) since the debug session traced G-03-1/G-03-2 to the spec itself, not the 03-04 executor's faithful implementation of it
- [Phase 03]: [Phase 03]: [Phase 03-05]: Collapsed rail's WCAG 1.4.11 fix targets the edge token (border-terminal-text-muted, ~6.2:1), not the fill, so the rail doesn't become the brightest surface on screen and compete with the chat content it stands in for
- [Phase 03]: [Phase 03]: [Phase 03-05]: ChatPanel's collapsed/expanded states merged into one persistent width-owning wrapper (transition-[width]) instead of two disjoint conditional returns, since CSS cannot interpolate a width across an unmount/remount
- [Phase 03]: [Phase 03-08]: Annotations now report the normalized ticker/side/quantity/action values, not the raw model item -- the coherent choice once validation and execution both read the single normalized result from _normalize_trade_item()/_normalize_watchlist_item()
- [Phase 03]: [Phase 03-08]: LlmWatchlistChange intentionally received no Field(description=...) this round -- its padded-action failure (G-03-6) is closed structurally by the single-normalization fix in actions.py, so a schema hint there would reduce nothing still reachable
- [Phase 03]: [Phase 03-08]: backend/app/portfolio/service.py and backend/app/llm/mock.py were deliberately left unmodified -- execute_trade()'s own quantity guard is the last line of defense for direct non-chat callers, and mock.py's regex patterns are a determinism contract for Phase 6's E2E suite
- [Phase 03]: [Phase 03][Plan 03-07]: Removed h-full from ChatPanel's wrapper rather than adding a compensating align-self/inline-style override — the debug session proved that combination still disables flex stretch, since a non-auto computed cross size disables it outright rather than merely leaving it unrequested
- [Phase 03]: [Phase 03][Plan 03-07]: Left frontend/app/page.tsx untouched — the rail height fix is fully contained in ChatPanel's own wrapper; the adjacent long-conversation page-scroll defect needs a separate definite-height-chain fix, explicitly out of scope
- [Phase 04]: 04-01: priceHistory lives in PriceStoreProvider; recharts is the chart engine
- [Phase 04]: [Phase 04][04-05]: Sparkline opts out via accessibilityLayer={false} rather than tabIndex={-1} — removes role="application" and Recharts' keydown middleware too, not just the tab stop
- [Phase 04]: [Phase 04][04-05]: MainChart and PnlHistoryChart deliberately keep their focusable chart surface (standalone panels, keyboard tooltip access); PortfolioHeatmap verified structurally focus-less via Treemap's Surface (not RootSurface) rendering
- [Phase 04]: [Phase 04][04-05]: Chart focus ring implemented as one shared .recharts-surface:focus-visible global CSS rule (2px solid var(--color-terminal-text), 2px offset), matching the existing .tabular-nums one-rule-reaches-every-instance pattern
- [Phase 04]: [Phase 04][04-06]: Split the two-task heatmap label-fit fix into two separate commits despite touching the same function, so PCT_MIN_HEIGHT/drop-order structure changes (Task 2) land distinctly from the labelFits() text-fit gate (Task 1)
- [Phase 04]: [Phase 04][04-06]: Per-glyph advance constants (ticker=7, pct=6) pinned to the top of the measured live range rather than the middle, since under-reporting risks label overflow which the UI-SPEC forbids outright
- [Phase 04]: [Phase 04][04-07]: Selected the bounded snapshot window by SQLite rowid rather than recorded_at — the 30s recorder and an on-trade insert can share an identical ISO timestamp, mirroring chat_messages.py's existing fix
- [Phase 04]: [Phase 04][04-07]: HISTORY_POINT_LIMIT=180 derived from measured plot geometry (190-430px) at MainChart's proven ~0.46 points/px density, not picked arbitrarily
- [Phase 04]: [Phase 04][04-07]: Server-side window (SQL LIMIT + validated route param) chosen over client-side trim or downsample — also stops the response body's unbounded growth, converting T-04-12 from accepted to mitigated
- [Phase 05]: [Phase 05][05-01]: P-01 uv-acquisition strategy resolved with no substitution — ghcr.io/astral-sh/uv:0.10.9 (matching the locally installed uv version) pulled and built successfully on the first attempt
- [Phase 05]: [Phase 05][05-01]: Bind-mount host path form proven on this Windows/Git-Bash/Docker-Desktop-WSL2 machine is 'pwd -W' plus MSYS_NO_PATHCONV=1 on docker run, not bare pwd — recorded for Plan 05-02's scripts to reuse
- [Phase 05]: [Phase 05][05-02]: PowerShell scripts kept to plain ASCII only -- Windows PowerShell 5.1's -File invocation reads a BOM-less script via the system codepage, not UTF-8, and an em-dash/section-sign corrupted live execution invisibly to the AST-based structural verify gate
- [Phase 05]: [Phase 05][05-02]: docker rm -f can return before the daemon releases a container name (observed live for a container with an active HEALTHCHECK) -- both start scripts now poll until the name is actually gone before any build/run step proceeds
- [Phase 05]: [Phase 05][05-02]: PowerShell docker calls always pass args via an explicit -DockerArgs array bound to a named parameter -- a bare -p token partial-matches the Invoke-Docker helper's implicit -PipelineVariable common parameter and collides with docker's own -p (publish port) flag
- [Phase 05]: [Phase 05][05-03]: Live round-trip proof required closing the auto-opened FinAlly browser tab (D-08) before stop_windows.ps1 -- its open SSE connection otherwise blocks uvicorn's graceful shutdown past docker stop's 10s grace period (exit 137), a pre-existing SSE characteristic unrelated to the asyncio.gather fix
- [Phase 05]: [Phase 05][05-04]: P-03 -- Windows launcher's only rebuild spelling is -Build (any case); both double-dash spellings (--build, --Build) are rejected, resolving a conflict between VERIFICATION.md's concrete re-test list and its looser allowed-set phrasing
- [Phase 05]: [Phase 05][05-04]: Argument validation on both PowerShell launchers moved from a declared switch/empty param() to an explicit step-1 guard over raw $args -- a non-advanced script never raises ParameterBindingException for an unbound token, and powershell.exe's -File parser silently rewrites --build/--Build into -Build, so a declared parameter validated nothing and behaved differently between -File and in-session invocation
- [Phase 05]: [Phase 05][05-05]: Trailing-colon rejection rule applied to raw host command-line tokens (GetCommandLineArgs() tail), not to $args -- the swallowed token never reaches $args at all under -File
- [Phase 05]: [Phase 05][05-05]: $MyInvocation.Line emptiness used as the -File discriminator for the host command-line cross-check, so no in-session call is ever falsely rejected

### Pending Todos

None yet.

### Blockers/Concerns

- REQUIREMENTS.md's original "34 total" coverage count was a pre-enumeration estimate; the actual enumerated v1 list contains 40 REQ-IDs. Traceability table and coverage count corrected to 40/40 during roadmap creation.
- Known tech debt in the existing market data layer (sync SQLite via `asyncio.to_thread`, no connection pooling, inline schema definitions, broad exception handling in the update loop) is acceptable at current single-user demo scale per `.planning/codebase/CONCERNS.md` — not blocking, not required to fix this milestone.
- [Phase 1] The 30s background snapshot recorder (`run_portfolio_snapshot_loop`) does not hold `portfolio_lock`, unlike the on-trade snapshot insert — a trade racing the recorder's read could record a torn (partially-committed) `total_value` into the never-pruned `portfolio_snapshots` table. Flagged by 01-REVIEW.md (WR-03); narrow window, no test currently covers it.
- [Phase 3] Three non-blocking advisories from 03-REVIEW.md/03-VERIFICATION.md remain unfixed by design (all narrow, non-destructive): `chatStore.tsx`'s send try-block scope could misclassify a successful send as failed if `refreshPortfolio()` ever started rejecting (currently never does); the hasSentRef release-on-failed-send fix only covers one of two hydrate/send orderings, so a fast failing send before hydrate resolves could still discard history for that session; the collapsed-panel unread dot is dead code since `ChatInput` unmounts while collapsed. None contradict a roadmap success criterion.
- [Phase 4] Three non-blocking advisories from 04-REVIEW.md (gap-closure round) remain unfixed by design: `PnlHistoryChart.tsx`'s time-scaled axis has no explicit handling for two same-`recorded_at` points (a documented, tested legitimate occurrence in `portfolio_snapshots.py`) — renders as a vertical spike rather than a data error; the docblock's "a chart that visibly fails is better than one that quietly omits a value" claim doesn't match `formatAxisTime`'s actual silent-blank behavior on non-finite values; `get_snapshots()`/`_get_snapshots_sync` trust the route's `Query(ge=1,le=MAX_SNAPSHOT_LIMIT)` validation rather than bounding `limit` themselves, so a future direct (non-route) caller passing a negative limit would reopen G-04-4 via SQLite's negative-LIMIT-means-unbounded behavior. None contradict a roadmap success criterion.

## Deferred Items

Items acknowledged and deferred at milestone close, most recent first:

| Category | Item | Status | Deferred At | Milestone |
|----------|------|--------|-------------|-----------|
| *(none)* | | | | |

## Session Continuity

Last session: 2026-09-27T16:24:38.046Z
Stopped at: Phase 6 context gathered
Resume file: .planning/phases/06-test-coverage/06-CONTEXT.md
