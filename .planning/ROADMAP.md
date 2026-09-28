# Roadmap: FinAlly

## Overview

FinAlly already has a working market data layer (simulator + Massive REST client behind one interface, SSE price streaming, read-only seeded watchlist). This milestone builds everything else PLAN.md specifies on top of it, as a vertical MVP: first a complete backend trading engine (schema, portfolio math, trade execution, watchlist mutation), then the minimal frontend needed to actually drive that engine end-to-end (watchlist, trade bar, positions, header), then the AI chat copilot that trades on the user's behalf through that same validated path, then the richer visualizations (sparklines, main chart, heatmap, P&L chart) that make the terminal feel alive, then Docker packaging so the whole thing runs as a single container, and finally the test suites (backend, frontend, E2E) that verify all of it. Each phase produces something a user (or, for Phase 1, a caller of the API) can directly observe working.

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Backend Trading Engine** - Complete DB schema, portfolio state, trade execution, and watchlist mutation behind REST endpoints (completed 2026-09-16)
- [x] **Phase 2: Core Trading UI** - Minimal Next.js frontend wiring watchlist, trade bar, positions, and header to the live backend (completed 2026-09-17)
- [x] **Phase 3: AI Chat Copilot** - LLM chat assistant that analyzes the portfolio and auto-executes trades/watchlist changes (completed 2026-09-21)
- [x] **Phase 4: Portfolio Visualization** - Sparklines, main chart, portfolio heatmap, and P&L history chart (completed 2026-09-22)
- [ ] **Phase 5: Docker Packaging & Deployment** - Single-container multi-stage build with volume-mounted SQLite and start/stop scripts
- [ ] **Phase 6: Test Coverage** - Backend unit, frontend unit, and Playwright E2E suites covering the full trading loop

## Phase Details

### Phase 1: Backend Trading Engine

**Goal**: A caller of the API can execute market trades against a persistent, validated portfolio and mutate the watchlist — the full trading engine works end-to-end, ready for a frontend to consume
**Mode:** mvp
**Depends on**: Nothing (builds on the existing market data layer)
**Requirements**: DATA-01, DATA-02, DATA-03, DATA-04, DATA-05, DATA-06, PORT-01, PORT-02, PORT-03, PORT-04, PORT-05, PORT-06, WLST-01, WLST-02, WLST-03
**Success Criteria** (what must be TRUE):

  1. `POST /api/portfolio/trade` executes a buy order — cash decreases, a position appears/grows with correct avg_cost, and the trade is recorded in `trades`
  2. `POST /api/portfolio/trade` executes a sell order — cash increases, the position updates or clears, and the trade is recorded
  3. A buy with insufficient cash or a sell exceeding owned shares is rejected with a clear error and no state change
  4. `GET /api/portfolio` returns current cash, positions with unrealized P&L, and total value; `GET /api/portfolio/history` returns value snapshots recorded every 30s and immediately after each trade
  5. `POST /api/watchlist` adds a recognized ticker (400 on unrecognized) and `DELETE /api/watchlist/{ticker}` removes it, with both persisted in SQLite across restarts

**Plans:** 4/4 plans complete

Plans:
**Wave 1**

- [x] 01-01-PLAN.md — Walking skeleton: one real market BUY end-to-end, HTTP → lock-guarded service → SQLite → response (wave 1)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 01-02-PLAN.md — Market SELL path and state-preserving rejections for insufficient cash/shares (wave 2)
- [x] 01-03-PLAN.md — Watchlist add/remove/list endpoints plus the chat_messages schema (wave 2)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 01-04-PLAN.md — Portfolio valuation endpoints and the snapshot history recorder (wave 3)

### Phase 2: Core Trading UI

**Goal**: A user can watch live prices, place trades, and see their portfolio update in the browser — the core agentic trading loop (watch → trade → see it reflected) is usable end-to-end
**Mode:** mvp
**Depends on**: Phase 1
**Requirements**: UI-01, UI-06, UI-07, UI-09, UI-10
**Success Criteria** (what must be TRUE):

  1. The watchlist panel displays live-updating prices from the SSE stream, flashing green/red on price change and fading out
  2. The user can submit a buy or sell market order via the trade bar and immediately see cash and positions update, with no confirmation dialog
  3. The positions table shows ticker, quantity, avg cost, current price, unrealized P&L, and % change, staying live as prices tick
  4. The header shows live total portfolio value, cash balance, and a connection status dot reflecting SSE connection state
  5. The UI renders in the dark trading-terminal theme (colors, density) specified in PLAN.md §2

**Plans:** 3/3 plans complete
**UI hint**: yes

Plans:
**Wave 1**

- [x] 02-01-PLAN.md — Tracer: scaffold `frontend/`, stream one live price end-to-end, and place real buy/sell market orders from the trade bar (wave 1)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 02-02-PLAN.md — Watchlist panel with live prices and flash-on-real-change, on the one shared SSE connection (wave 2)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 02-03-PLAN.md — Positions table, header with live total value and connection dot, and the dark terminal theme finish (wave 3)

### Phase 3: AI Chat Copilot

**Goal**: A user can converse with an AI assistant that analyzes their portfolio and executes trades or watchlist changes on their behalf, with each action's outcome visible inline
**Mode:** mvp
**Depends on**: Phase 2
**Requirements**: CHAT-01, CHAT-02, CHAT-03, CHAT-04, CHAT-05, CHAT-06, UI-08
**Success Criteria** (what must be TRUE):

  1. Sending a chat message returns a structured response (`message` + `trades[]` + `watchlist_changes[]`) via `POST /api/chat`, requested and parsed as structured output through LiteLLM → OpenRouter (`openrouter/openai/gpt-oss-120b`)
  2. Trades/watchlist changes the LLM requests auto-execute through the same validation path as manual trade-bar/watchlist actions, with no confirmation dialog
  3. Each LLM-requested action is annotated `executed` or `error` and rendered as an inline success/error badge in the chat panel, separate from the chat bubble text
  4. The chat panel hydrates prior conversation history from `GET /api/chat` on mount, surviving a page refresh
  5. With `LLM_MOCK=true`, chat returns deterministic mock responses without calling OpenRouter

**Plans:** 8/8 plans complete
**UI hint**: yes

Plans:
**Wave 1**

- [x] 03-01-PLAN.md — Tracer: a chat message becomes a real executed trade — LLM structured output, shared validation path, annotated outcomes (wave 1)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 03-02-PLAN.md — Chat history persistence, `GET /api/chat` hydration, and a bounded prompt context (wave 2)
- [x] 03-03-PLAN.md — Chat panel in the browser: wire contract, store, third column, input and message list (wave 2)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 03-04-PLAN.md — Inline action badges, collapse rail, scroll-to-latest pill, and live watchlist/portfolio refresh (wave 3)

**Wave 4** *(gap closure — UAT gaps G-03-1/G-03-2/G-03-3; the two plans share no files and run in parallel)*

- [x] 03-05-PLAN.md — Gap closure G-03-1/G-03-2: amend the UI-SPEC collapse contract, then rebuild ChatPanel's collapse control as one persistent, animating, perceivable element (wave 4)
- [x] 03-06-PLAN.md — Gap closure G-03-3: recover code-fenced LLM JSON so trades stop silently dropping, never show raw model text, stop streaming, and fail over once (wave 4)

**Wave 5** *(gap closure — round-2 UAT gaps G-03-4/G-03-5/G-03-6; the two plans share no files and run in parallel)*

- [x] 03-07-PLAN.md — Gap closure G-03-4: let the chat column stretch to full height instead of collapsing to a corner chip, stand the collapsed rail's label upright, and amend the UI-SPEC to state the rail's height (wave 5)
- [x] 03-08-PLAN.md — Gap closure G-03-5/G-03-6: normalize each LLM action once and reuse it for validation and execution, recover a sell's redundant negative sign, and tell the model the sign convention (wave 5)

### Phase 4: Portfolio Visualization

**Goal**: A user can visually understand portfolio composition, risk concentration, and performance at a glance
**Mode:** mvp
**Depends on**: Phase 2
**Requirements**: UI-02, UI-03, UI-04, UI-05
**Success Criteria** (what must be TRUE):

  1. Each watchlist ticker shows a sparkline mini-chart accumulated from the SSE stream since page load, filling in progressively
  2. Clicking a ticker in the watchlist shows a larger detailed chart for it in the main chart area
  3. The portfolio heatmap sizes rectangles by position weight and colors/saturates them by unrealized P&L%, capped at ±10%
  4. A P&L line chart shows total portfolio value over time, sourced from `portfolio_snapshots`

**Plans:** 7/7 plans complete
**UI hint**: yes

Plans:
**Wave 1**

- [x] 04-01-PLAN.md — Tracer: a live sparkline in every watchlist row, from one shared price-history buffer (wave 1)

**Wave 2** *(blocked on Wave 1 — extends WatchlistRow and consumes the buffer)*

- [x] 04-02-PLAN.md — Click a ticker to drill in: selection context, the main chart, and the stacked-panel centre column (wave 2)

**Wave 3** *(blocked on Wave 2 — shares `frontend/app/page.tsx`)*

- [x] 04-03-PLAN.md — Portfolio heatmap: treemap tiles sized by weight, filled by ±10%-capped diverging P&L colour, with its legend (wave 3)

**Wave 4** *(blocked on Wave 3 — shares `frontend/app/page.tsx`)*

- [x] 04-04-PLAN.md — Portfolio value over time: history types, fetch, 30s polling store, and the P&L line chart (wave 4)

**Wave 5** *(gap closure — UAT gaps G-04-2a/G-04-2b, G-04-3 and G-04-4; the three plans share no files and run in parallel)*

- [x] 04-05-PLAN.md — Gap closure G-04-2a/G-04-2b: stop the sparkline stealing the watchlist's tab stop, and give the charts that stay focusable an on-theme focus ring (wave 5)
- [x] 04-06-PLAN.md — Gap closure G-04-3: gate heatmap tile labels on the width of the text being drawn instead of fixed rectangle thresholds (wave 5)
- [x] 04-07-PLAN.md — Gap closure G-04-4: bound the portfolio history read to a most-recent window and put the P&L line on a real time axis (wave 5)

### Phase 5: Docker Packaging & Deployment

**Goal**: A user can start the entire application with a single command and have their data persist across restarts
**Mode:** mvp
**Depends on**: Phase 3, Phase 4
**Requirements**: DEPLOY-01, DEPLOY-02, DEPLOY-03, DEPLOY-04
**Success Criteria** (what must be TRUE):

  1. A multi-stage Docker build (Node build stage → Python runtime stage) produces one image that serves the frontend and all API routes on port 8000
  2. The SQLite database persists across container restarts via a volume mount at `db/`
  3. Start/stop scripts exist for macOS/Linux (bash) and Windows (PowerShell), and running either repeatedly is safe (idempotent)
  4. `.env.example` is committed and documents `OPENROUTER_API_KEY`, `MASSIVE_API_KEY`, and `LLM_MOCK`

**Plans**: 5/5 plans executed

Plans:
**Wave 1**

- [x] 05-01-PLAN.md — Tracer: one multi-stage image serves frontend + API on port 8000 with a bind-mounted SQLite that survives container replacement, plus the guarded static mount, its regression tests, and `.env.example` (wave 1)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 05-02-PLAN.md — Idempotent start/stop scripts for macOS/Linux (bash) and Windows (PowerShell), proven by a live start/re-start/stop/re-stop round trip (wave 2)

**Wave 3** *(gap closure — verification blocker CR-01 plus review warnings WR-01/WR-02/WR-03; blocked on Waves 1-2)*

- [x] 05-03-PLAN.md — Gap closure CR-01/WR-01/WR-02/WR-03: keep every dotenv variant out of the Docker build context (proven by sentinel-seeded probes of the context, the frontend-build layer and the runtime image), await background tasks before stopping the market source on shutdown, bound start_mac.sh's per-attempt readiness probe, and give start_windows.ps1 plain one-line failure messages (wave 3)

**Wave 4** *(gap closure — verification gap: start_windows.ps1 silently accepts unrecognised arguments; review correction WR-04; blocked on Waves 1-3)*

- [x] 05-04-PLAN.md — Gap closure WR-04: make start_windows.ps1 and stop_windows.ps1 reject any argument they do not recognise as an explicit exact-match step 1 before Docker is touched (proven with VERIFICATION.md's own reproductions, a docker-free RED-to-GREEN matrix, in-session invocation, and a live unchanged-container check), keep a bare start and `-Build` behaving exactly as before, and correct WR-04's mischaracterised failure mode in the review record (wave 4)

**Wave 5** *(gap closure — verification truth 14 / review CR-01+WR-01+IN-01 / T-05-08 reopened: a colon-suffixed valueless token such as `-Foo:` or `-Build:` is dropped by PowerShell's `-File` parser before `$args` is populated, bypassing both launchers' guard; blocked on Wave 4)*

- [x] 05-05-PLAN.md — Gap closure CR-01/WR-01/IN-01 (T-05-08): cross-check each PowerShell launcher's `$args` against the host command line (`[Environment]::GetCommandLineArgs()`, gated on an empty `$MyInvocation.Line`), rejecting any raw token ending in `:` or a raw count that differs from `$args` before Docker is touched; prove it with a docker-free RED-to-GREEN matrix over three path forms, a docker-shim stop matrix, in-session and wrapper-hosted no-false-rejection gates, and the verifier's own live `stop '-Foo:'` and `start '-Build:'` reproductions; and record the resolution in the review (wave 5)

### Phase 6: Test Coverage

**Goal**: The full trading loop — backend logic, frontend behavior, and the Docker-deployed app — is verified by automated tests
**Mode:** mvp
**Depends on**: Phase 5
**Requirements**: TEST-01, TEST-02, TEST-03, TEST-04, TEST-05
**Success Criteria** (what must be TRUE):

  1. Backend pytest suite passes covering trade execution logic, P&L calculations, and edge cases (insufficient cash/shares)
  2. Backend pytest suite passes covering LLM structured-output parsing, including malformed responses
  3. Backend pytest suite passes covering API route status codes and response shapes for portfolio/watchlist/chat endpoints
  4. Frontend unit tests pass covering price flash animation triggering, watchlist CRUD, portfolio display calculations, and chat rendering/loading state
  5. The Playwright E2E suite (in `test/`, own `docker-compose.test.yml`, `LLM_MOCK=true`) passes covering fresh start, watchlist add/remove, buy, sell, visualization rendering, mocked chat trade execution, and SSE reconnection

**Plans:** 4/6 plans executed

Plans:
**Wave 1**

- [x] 06-01-PLAN.md — Backend audit and gap closure: empty/blank ticker 422/400 on POST /api/watchlist, selling at a loss, and a TEST-01/02/03 audit matrix (wave 1)
- [x] 06-02-PLAN.md — Tracer: Vitest + RTL harness (legitimacy checkpoint, EventSource and fetch stubs, provider wrapper) proven on price flash, the SSE store and the header's live total; test code kept out of the Docker image (wave 1)

**Wave 2** *(blocked on 06-02)*

- [x] 06-03-PLAN.md — Frontend watchlist CRUD (read states plus chat-driven add/remove) and chat rendering/loading states (wave 2)
- [x] 06-04-PLAN.md — Frontend portfolio display calculations: positions table, formatters, heatmap colour-scale thresholds, watchlist change % (wave 2)
- [ ] 06-05-PLAN.md — Tracer: Playwright E2E harness (legitimacy checkpoint, `test/docker-compose.test.yml` with a throwaway volume and health-gated runner, portable `npm --prefix test run e2e`) proven on fresh start and SSE reconnection (wave 2)

**Wave 3** *(blocked on 06-05)*

- [ ] 06-06-PLAN.md — E2E trading loop: buy/sell, chat-driven watchlist add/remove, mocked chat trades, sparklines, main chart, heatmap sizing and colour, P&L line (wave 3)

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6

| Phase | Plans Complete | Status | Completed |
|-------|-----------------|--------|-----------|
| 1. Backend Trading Engine | 4/4 | Complete    | 2026-09-16 |
| 2. Core Trading UI | 3/3 | Complete    | 2026-09-17 |
| 3. AI Chat Copilot | 8/8 | Complete    | 2026-09-21 |
| 4. Portfolio Visualization | 7/7 | Complete    | 2026-09-22 |
| 5. Docker Packaging & Deployment | 5/5 | In Progress|  |
| 6. Test Coverage | 4/6 | In Progress|  |
