# Walking Skeleton — FinAlly

**Phase:** 1
**Generated:** 2026-09-16

## Deliberate adaptation of the template

FinAlly is **brownfield**. A FastAPI app with a working market-data layer (simulator + Massive REST
client behind one interface, `PriceCache`, SSE streaming at `/api/stream/prices`, a seeded read-only
`watchlist` table, 73 passing tests) already runs pre-GSD. The project scaffold, routing, build, test
runner and real data flow that a greenfield walking skeleton establishes from scratch therefore
already exist and are already proven.

ROADMAP.md also deliberately sequences the UI into Phase 2, so the template's "UI — at least one
interactive element wired to the API" checkbox cannot be honoured literally in Phase 1 without
contradicting the roadmap. This document applies the template's **spirit** — the thinnest real slice,
proven early, production-quality, kept for good — with "end-to-end" meaning
**API-caller-to-database**: one real HTTP request, through validation and business logic, to SQLite,
and back as a real response, verifiable with `curl` or a route-level pytest test.

That slice is `01-01-PLAN.md` Task 2, the first task executed in this phase.

## Capability Proven End-to-End

A caller can POST one real market buy order to `/api/portfolio/trade` and have it fill at the live
cached price — debiting persisted cash, creating a position with a correct average cost, and
appending a row to the trade log — in a single HTTP round trip.

## Architectural Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Web framework | FastAPI, routes as `APIRouter` modules under `app/routes/`, app built by the `create_app()` factory | Already the project's only web framework; `health.py` and `stream.py` set the precedent, and the factory lets tests construct isolated instances with their own lifespan run |
| Data layer | stdlib `sqlite3`, one module per table under `app/db/`, each owning its own `CREATE TABLE IF NOT EXISTS` schema and an idempotent `init_db()` | Matches `app/db/watchlist.py` exactly. `.planning/codebase/CONCERNS.md` scopes moving off sync sqlite3 as accepted debt, not this milestone's work |
| DB connection ownership | `DB_PATH` and `_connect()` stay defined in `app/db/watchlist.py`; every other db module does `from .watchlist import _connect` | Python late-binds the module global at call time, so the one `monkeypatch.setattr(watchlist_module, "DB_PATH", …)` in `backend/tests/conftest.py` isolates all six tables with zero changes to the four pre-existing patch call sites (01-RESEARCH.md Pitfall 1) |
| Async/DB boundary | Every db function is a private `_xxx_sync()` wrapped by a public `async def xxx()` via `await asyncio.to_thread(...)` | The existing convention; keeps blocking sqlite off the event loop without introducing a second DB access style mid-project |
| Concurrency control | One `asyncio.Lock` on `app.state.portfolio_lock`, held across the entire validate-and-apply critical section of `execute_trade()` | Mirrors `PriceCache`'s own `asyncio.Lock`, the codebase's single precedent for guarding shared mutable state. Prevents two concurrent trades double-spending the same cash — a real risk once Phase 3's LLM can invoke the same path |
| Service/HTTP layering | `app/portfolio/service.py` returns a structured `TradeResult` (`status`, `reason`) and never raises `HTTPException`; `app/routes/portfolio.py` is the only layer that translates to HTTP | Phase 3 must annotate each LLM-requested action `executed` or `error` *alongside* a chat message, not abort the response with an exception. Deciding this now avoids a Phase 3 refactor (01-RESEARCH.md Pattern 3) |
| Fill-price source | `await app.state.price_cache.get(ticker)`, never `market_source.get_prices()` | The cache is the single-writer source of truth the SSE stream also reads, so the fill price is the price the user's screen is showing. `PriceCache.get()` was built for exactly this |
| Input validation | Pydantic models at the route boundary (`quantity: float = Field(gt=0)`, `side: Literal["buy","sell"]`), ticker normalized with `.strip().upper()` then gated on `is_valid_ticker()` | ASVS V5 is the only applicable category this milestone (no auth, no sessions, no crypto). Validation at the boundary keeps the service free of defensive input checks, matching the codebase's "contract violations documented, not defended" convention |
| Background tasks | `asyncio.create_task()` inside `lifespan`, reference stored in a local, `.cancel()` after `yield` | The existing `update_task` pattern. Pitfall 5: an untracked task leaks across `TestClient` teardown and can write into the next test's throwaway database |
| Directory layout | `app/db/` per-table modules, `app/portfolio/` for shared business logic, `app/routes/` thin HTTP adapters, `app/market/` untouched | Follows `.planning/codebase/STRUCTURE.md`'s own "Where to Add New Code" guidance. Watchlist mutation is thin enough to live in `app/db/` + `app/routes/` with no service module; `app/llm/` stays empty for Phase 3 |
| Dependencies | None added. `backend/pyproject.toml` and `backend/uv.lock` are untouched this phase | `pydantic` is already locked transitively via `fastapi` and importable at 2.13.5 (verified in 01-RESEARCH.md). Nothing else is needed |

## Stack Touched in Phase 1

- [x] Project scaffold (framework, build, lint, test runner) — **pre-existing**, unchanged; `uv` + FastAPI + pytest/pytest-asyncio already in place
- [x] Routing — three new real routes in the tracer plan's slice and six across the phase, registered through `create_app()`
- [x] Database — real reads AND real writes across five new tables plus write paths on the existing `watchlist` table
- [ ] UI — **deliberately out of scope**; ROADMAP.md sequences the frontend into Phase 2. The skeleton's far end is the HTTP boundary, exercised by `curl` and FastAPI `TestClient`
- [x] Deployment — documented local full-stack run: `cd backend && uv run uvicorn app.main:app` (Docker packaging is Phase 5)

## Out of Scope (Deferred to Later Slices)

Explicitly not in the skeleton. This list exists so later phases do not re-litigate Phase 1's minimalism.

- Any frontend — no Next.js work at all this phase (Phase 2)
- Chat / LLM logic — the `chat_messages` table is created for schema completeness only; `app/llm/` stays empty and no LiteLLM call is written (Phase 3)
- Charts, sparklines, heatmap, P&L visualization — Phase 1 only produces the `portfolio_snapshots` series they will read (Phase 4)
- Docker, start/stop scripts, `.env.example` (Phase 5)
- Playwright E2E and frontend unit tests (Phase 6)
- Limit orders, partial fills, order book, fees, trade confirmation dialogs — permanently out of scope per REQUIREMENTS.md
- Multi-user auth — every table carries `user_id` defaulting to `"default"`, reserving the shape without building the feature (v2: PLAT2-01)
- Migrating off sync `sqlite3`, adding connection pooling, extracting schema SQL to `backend/schema/` — accepted debt per `.planning/codebase/CONCERNS.md`, not this milestone
- Pruning `portfolio_snapshots` — `planning/PLAN.md` §7 explicitly accepts unbounded growth
- Logging rejected trade attempts — `trades` is a log of fills; no schema column exists for attempt outcomes (01-RESEARCH.md Assumption A2)

## Subsequent Slice Plan

Each later phase adds one vertical slice on top of this skeleton without altering its architectural decisions:

- **Phase 2 — Core Trading UI:** a user can watch live prices, place a trade, and see their portfolio update in the browser. Consumes the JSON contracts locked in `01-01-PLAN.md` and `01-04-PLAN.md`.
- **Phase 3 — AI Chat Copilot:** a user can have the LLM execute trades, calling the *same* `execute_trade()` returning the *same* `TradeResult` — the layering decision above is what makes this a pure addition.
- **Phase 4 — Portfolio Visualization:** sparklines, main chart, heatmap, and a P&L chart reading the `portfolio_snapshots` series this phase begins recording.
- **Phase 5 — Docker Packaging:** one container, one port, SQLite on a volume at `db/` — the path `app/db/watchlist.py::DB_PATH` already resolves to, overridable via the existing `FINALLY_DB_PATH`.
- **Phase 6 — Test Coverage:** backend, frontend, and Playwright E2E suites over the full loop.
