# FinAlly — AI Trading Workstation

## What This Is

FinAlly is a visually stunning, AI-powered trading workstation — a browser-based capstone project for an agentic AI coding course. It streams live (simulated or real) market data, lets a single user trade a simulated $10,000 portfolio with instant market-order fills, and integrates an LLM chat assistant that can analyze the user's portfolio and execute trades and watchlist changes on their behalf. It looks and feels like a modern Bloomberg terminal with an AI copilot, ships as a single Docker container on one port, and is itself built entirely by orchestrated coding agents.

## Core Value

A user can watch live prices, trade a simulated portfolio, and have an AI copilot execute trades on their behalf — the full agentic trading loop (watch → decide → chat → execute → see it reflected in the portfolio) must work end-to-end.

## Requirements

### Validated

- ✓ Market data abstraction (simulator + optional Massive/Polygon REST client behind one interface) — existing (pre-GSD)
- ✓ GBM price simulator with correlated sector moves and seeded starting prices — existing (pre-GSD)
- ✓ In-memory thread-safe price cache updated by a background task — existing (pre-GSD)
- ✓ SSE endpoint (`GET /api/stream/prices`) streaming price ticks to clients — existing (pre-GSD)
- ✓ SQLite `watchlist` table, lazily initialized and seeded with 10 default tickers (read-only) — existing (pre-GSD)
- ✓ `GET /api/health` liveness endpoint — existing (pre-GSD)
- ✓ Complete SQLite schema: `users_profile`, `positions`, `trades`, `portfolio_snapshots`, `chat_messages` tables (plus watchlist mutation support) — Phase 1
- ✓ Portfolio state: cash balance, positions with avg cost, unrealized P&L (computed live on read, never persisted) — Phase 1
- ✓ Market order trade execution (buy/sell, instant fill, no fees, no confirmation), validated for sufficient cash/shares — Phase 1
- ✓ Portfolio snapshot recording (every 30s + after each trade) for P&L history — Phase 1
- ✓ Watchlist mutation: add ticker (reject unrecognized symbols) and remove ticker — Phase 1
- ✓ REST API: `/api/portfolio`, `/api/portfolio/trade`, `/api/portfolio/history`, `/api/watchlist` (GET/POST/DELETE) — Phase 1
- ✓ Next.js (TypeScript, static export) frontend: dark terminal-themed single-page app, dark theme tokens locked to PLAN.md §2 exactly — Phase 2
- ✓ Watchlist panel: live-updating grid with flash-on-real-change animations for every tracked ticker (per-ticker sparklines deferred — see Active) — Phase 2
- ✓ Positions table (ticker, qty, avg cost, current price, P&L, % change), server-authoritative, live current price — Phase 2
- ✓ Trade bar (ticker, quantity, buy/sell, instant fill, no confirmation dialog), inline backend rejection wording — Phase 2
- ✓ Header: live portfolio value (client-recomputed, sanctioned exception), connection status dot (real onopen/onerror/readyState state machine), cash balance, "Simulated" account marker — Phase 2
- ✓ LLM chat integration via LiteLLM → OpenRouter, structured JSON output (message + trades + watchlist_changes) — Phase 3 (model deviation: `openrouter/openrouter/free`, not the originally-specified `openrouter/openai/gpt-oss-120b` — see Key Decisions)
- ✓ Chat auto-executes trades/watchlist changes through the same validation path as manual actions, annotates each with executed/error outcome — Phase 3
- ✓ `execute_trade()` gains its own input validation (quantity > 0, side is exactly "buy"/"sell") instead of relying solely on the HTTP route's Pydantic layer — Phase 3 (fixed in 03-01 Task 3; originally flagged by Phase 1 code review WR-01/WR-02)
- ✓ `GET /api/chat` (history) and `POST /api/chat` (send message, get full response) endpoints — Phase 3
- ✓ `LLM_MOCK=true` deterministic mock mode for testing — Phase 3
- ✓ AI chat panel (collapsible, hydrates from `GET /api/chat`, inline trade/watchlist confirmation badges) — Phase 3, closed after 3 UAT gap-closure rounds (collapse-control accessibility/motion, LLM fence-recovery/failover, action-outcome normalization, collapsed-rail full-height rendering)
- ✓ Per-ticker sparklines accumulated from the SSE stream, in the watchlist panel — Phase 4
- ✓ Main chart area for the selected ticker, keyboard- and click-selectable from the watchlist — Phase 4, closed after 1 UAT gap-closure round (Recharts default `accessibilityLayer` made the sparkline a second tab stop per row and grew a broken-looking default focus ring; opted sparklines out and gave MainChart/PnlHistoryChart a deliberate themed focus ring instead)
- ✓ Portfolio heatmap (treemap, sized by weight, colored/saturated by P&L%, capped ±10%) — Phase 4, closed after 1 UAT gap-closure round (label visibility was gated on a fixed rectangle threshold instead of the actual text extent; replaced with a measured-glyph-width fit test)
- ✓ P&L line chart from `portfolio_snapshots` — Phase 4, closed after 1 UAT gap-closure round (unbounded snapshot history + a categorical axis made the line read as a bold/busy ink band at real data volume; bounded the backend read, capped the frontend request, and switched to a time-scaled numeric axis)
- [ ] Multi-stage Dockerfile (Node build → Python runtime), single container, port 8000, volume-mounted SQLite
- [ ] Start/stop scripts for macOS/Linux (bash) and Windows (PowerShell), idempotent
- [ ] `.env.example` committed
- [ ] Backend unit tests (pytest): portfolio math, trade edge cases, LLM structured-output parsing, API route contracts
- [ ] Frontend unit tests (React Testing Library or similar): price flash, watchlist CRUD, portfolio calculations, chat rendering
- [ ] Playwright E2E suite in `test/` (own `docker-compose.test.yml`), run with `LLM_MOCK=true`, covering fresh start, watchlist CRUD, buy/sell, visualizations, mocked chat trade execution, SSE reconnection

### Out of Scope

- Multi-user support / authentication — single hardcoded `user_id="default"`, explicitly deferred per PLAN.md
- Limit orders, partial fills, order book — market orders only, to keep portfolio math simple
- Trade confirmation dialogs — deliberate zero-friction design for the agentic demo
- Postgres or any external DB server — SQLite is sufficient for single-user, self-contained deployment
- WebSockets — SSE covers the one-way price-push need with less complexity
- Cloud deployment (Terraform/App Runner) — stretch goal per PLAN.md §11, not core v1

## Context

- This is a brownfield GSD bootstrap: the codebase already contains a working market data layer (~40-50% of PLAN.md complete per `.planning/codebase/CONCERNS.md`), built pre-GSD across commits up through `12782cf`/`8375047`.
- `planning/PLAN.md` (repo-checked-in, referenced by root `CLAUDE.md`) is the authoritative, exhaustive spec for this project — architecture, schema, API surface, LLM integration contract, frontend layout, Docker/deployment, and testing strategy are all already fully decided there. This PROJECT.md defers to PLAN.md for implementation detail and exists to drive GSD's requirements/roadmap/execution machinery on top of it.
- `.planning/codebase/` (ARCHITECTURE.md, STACK.md, CONCERNS.md, CONVENTIONS.md, INTEGRATIONS.md, STRUCTURE.md, TESTING.md) documents the current as-built state and known gaps/tech debt; `CONCERNS.md` in particular enumerates every missing piece (full DB schema, all non-health/stream routes, LLM integration, entire frontend, Docker/deployment, E2E tests) — that list is effectively the seed for this milestone's Active requirements.
- Known minor tech debt to be aware of but not required to fix in this milestone: synchronous SQLite calls wrapped in `asyncio.to_thread`, no connection pooling, inline (non-file) schema definitions, broad exception handling in the market update loop. Acceptable at current single-user demo scale per the codebase audit.
- Backend is a `uv`-managed Python 3.12 / FastAPI project; frontend does not exist yet and will be a fresh Next.js TypeScript project using static export.

## Constraints

- **Tech stack**: FastAPI (Python, uv) backend, Next.js (TypeScript, static export) frontend, SQLite, SSE, LiteLLM → OpenRouter — all fixed by PLAN.md, not open decisions for this milestone
- **Deployment**: Single Docker container, single port (8000), no docker-compose required for production — per PLAN.md §3/§11
- **LLM model**: Must use `openrouter/openrouter/free` via the `litellm-stream` skill with structured outputs, per PLAN.md §9 and root CLAUDE.md
- **Scope simplification**: Market orders only, no auth, no confirmation dialogs — deliberate choices in PLAN.md to keep portfolio math and demo flow simple
- **Course/demo context**: This is a capstone project meant to demonstrate agentic AI coding; polish and "impressive fluid demo experience" (PLAN.md §9) matter alongside correctness

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Treat `planning/PLAN.md` as the binding spec; this GSD cycle scopes/sequences work rather than re-deciding architecture | PLAN.md is already exhaustive and pre-approved; re-litigating it would waste the detailed prior design work | — Pending |
| Single v1 milestone covering the full remainder of PLAN.md (portfolio, chat, frontend, Docker, tests) | Scope is already tightly bounded by PLAN.md; splitting into multiple milestones would add process overhead without a clear natural cut point | — Pending |
| Structure roadmap as a Vertical MVP (thin end-to-end slice first, then layer in visualization/AI/packaging) rather than Horizontal Layers | Gets a demoable trade-execution loop working early against the already-live market data stream, reducing integration risk versus building all layers in parallel and wiring at the end | ✓ Validated by Phase 1 — walking-skeleton tracer (one BUY order, full stack) landed first and every later plan/task extended it without rework |
| Keep inline `_SCHEMA` constants per `app/db/*.py` module (mirroring the existing `watchlist.py` pattern) rather than extracting to a `backend/schema/` directory as root PLAN.md §4 anticipates | All five new tables needed to ship fast behind a single shared `_connect()`/`DB_PATH`; extracting a schema layer now would be a pure refactor with no behavior change and no phase currently blocked on it | Phase 1 — kept inline; revisit only if a future phase actually needs schema/migration tooling |
| `execute_trade()` trusts its caller for `quantity > 0` and `side ∈ {"buy","sell"}` rather than re-validating internally | Plan 01 scoped it as the trade route's backing function only; Pydantic at the HTTP layer was assumed sufficient | Phase 1 — flagged as a gap by code review (WR-01/WR-02) once Phase 3's direct-call chat flow was considered; added to Active requirements, not yet fixed |
| Defer all frontend automated testing (Vitest/React Testing Library) to Phase 6, verify Phase 2 entirely by manual browser UAT instead | Introducing a test framework mid-phase for a single wave of UI work would add setup cost without a second consumer yet; Phase 6 (`TEST-04`) already owns frontend test infra project-wide | ✓ Validated by Phase 2 — `workflow.human_verify_mode: end-of-phase` deferred every `<human-check>` to one end-of-phase UAT batch (8 items), all passed with 0 issues; Nyquist validation confirmed manual-by-design is not a coverage gap |
| Client-side price-cell flash triggers on the cell's own last-rendered price (a `useRef`), never on the SSE tick's `previous_price` field | `PriceCache.update()` keeps `previous_price` stale-but-different forever after the first real move on an unchanged-price heartbeat, so a `previous_price`-based trigger would flash on every 0.5s heartbeat forever | ✓ Validated by Phase 2 — verified correct by code review, phase verification, and live 20+-second UAT observation (test 5) |
| Use `openrouter/openrouter/free` instead of root PLAN.md §9's specified `openrouter/openai/gpt-oss-120b` | The specified model returned HTTP 402 (insufficient credits) on the very first live call; the free router was the only working path | ✓ Validated by Phase 3 — user-approved Rule 4 deviation (03-01-SUMMARY.md), re-confirmed and hardened around (not reverted) by every later gap-closure plan (03-06 failover, 03-08 sign-convention prompting) |
| Normalize each LLM-proposed trade/watchlist item exactly once per loop iteration and reuse that single result for validation, execution, and outcome annotation, rather than deriving the normalized value separately at each of those three points | A confirmed live data-loss bug (G-03-6): the validator's normalized `" add".strip().lower()` passed, but the executor's separate `.lower()`-only re-derivation didn't match `"add"`, so it silently fell through to `remove_watchlist_ticker()` while reporting `outcome=executed` | ✓ Validated by Phase 3 (03-08) — structurally prevents the whole class of validator/executor divergence, not just the one reported instance |
| Bound `portfolio_snapshots` reads at the query layer (`rowid DESC LIMIT` + reverse, route-validated `limit`) rather than pruning the table | UAT reported the Portfolio Value chart as "busy"; root cause was ~2094 unbounded rows drawn into a ~126px plot, not stroke width. PLAN.md §7 explicitly accepts unbounded row growth as a demo-scale tradeoff — the fix had to leave storage alone and window only the read/render path | ✓ Validated by Phase 4 (04-07) — backend TDD tracer added the first genuinely behavioral (non-structural-grep) test coverage in this phase; re-scopes threat T-04-12 from `accept` to `mitigate` |
| Opt Recharts-based mini-charts (Sparkline) out of the library's default `accessibilityLayer`, but keep it on for standalone panels (MainChart, PnlHistoryChart) with an explicit themed focus ring | Recharts 3.x makes every chart focusable by default; nesting one inside an already-focusable `WatchlistRow` created a duplicate tab stop and a broken-looking default focus ring, but standalone charts still need arrow-key tooltip navigation | ✓ Validated by Phase 4 (04-05) — live keyboard-traversal check approved by user before the ring/heatmap-never-focuses portion was deferred to end-of-phase UAT (also passed) |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-09-22 after Phase 4*
