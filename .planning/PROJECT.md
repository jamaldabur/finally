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

### Active

- [ ] LLM chat integration via LiteLLM → OpenRouter (`openrouter/openai/gpt-oss-120b`), structured JSON output (message + trades + watchlist_changes)
- [ ] Chat auto-executes trades/watchlist changes through the same validation path as manual actions, annotates each with executed/error outcome
- [ ] `execute_trade()` gains its own input validation (quantity > 0, side is exactly "buy"/"sell") instead of relying solely on the HTTP route's Pydantic layer — emerged from Phase 1 code review (01-REVIEW.md WR-01/WR-02): a direct non-HTTP call with a negative/zero quantity can mint free cash or raise an uncaught `ZeroDivisionError` inside the portfolio lock, and Phase 3's chat flow is specified to call `execute_trade()` directly with LLM-sourced args, bypassing that route-level guard
- [ ] `GET /api/chat` (history) and `POST /api/chat` (send message, get full response) endpoints
- [ ] `LLM_MOCK=true` deterministic mock mode for testing
- [ ] Next.js (TypeScript, static export) frontend: dark terminal-themed single-page app
- [ ] Watchlist panel: live-updating grid with flash animations and per-ticker sparklines accumulated from the SSE stream
- [ ] Main chart area for the selected ticker
- [ ] Portfolio heatmap (treemap, sized by weight, colored/saturated by P&L%)
- [ ] P&L line chart from `portfolio_snapshots`
- [ ] Positions table (ticker, qty, avg cost, current price, P&L, % change)
- [ ] Trade bar (ticker, quantity, buy/sell, instant fill)
- [ ] AI chat panel (collapsible, hydrates from `GET /api/chat`, inline trade/watchlist confirmation badges)
- [ ] Header: live portfolio value, connection status dot, cash balance
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
- **LLM model**: Must use `openrouter/openai/gpt-oss-120b` via the `litellm-stream` skill with structured outputs, per PLAN.md §9 and root CLAUDE.md
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
*Last updated: 2026-09-16 after Phase 1*
