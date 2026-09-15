<!-- GSD:project-start source:PROJECT.md -->

## Project

**FinAlly — AI Trading Workstation**

FinAlly is a visually stunning, AI-powered trading workstation — a browser-based capstone project for an agentic AI coding course. It streams live (simulated or real) market data, lets a single user trade a simulated $10,000 portfolio with instant market-order fills, and integrates an LLM chat assistant that can analyze the user's portfolio and execute trades and watchlist changes on their behalf. It looks and feels like a modern Bloomberg terminal with an AI copilot, ships as a single Docker container on one port, and is itself built entirely by orchestrated coding agents.

**Core Value:** A user can watch live prices, trade a simulated portfolio, and have an AI copilot execute trades on their behalf — the full agentic trading loop (watch → decide → chat → execute → see it reflected in the portfolio) must work end-to-end.

### Constraints

- **Tech stack**: FastAPI (Python, uv) backend, Next.js (TypeScript, static export) frontend, SQLite, SSE, LiteLLM → OpenRouter — all fixed by PLAN.md, not open decisions for this milestone
- **Deployment**: Single Docker container, single port (8000), no docker-compose required for production — per PLAN.md §3/§11
- **LLM model**: Must use `openrouter/openai/gpt-oss-120b` via the `litellm-stream` skill with structured outputs, per PLAN.md §9 and root CLAUDE.md
- **Scope simplification**: Market orders only, no auth, no confirmation dialogs — deliberate choices in PLAN.md to keep portfolio math and demo flow simple
- **Course/demo context**: This is a capstone project meant to demonstrate agentic AI coding; polish and "impressive fluid demo experience" (PLAN.md §9) matter alongside correctness

<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->

## Technology Stack

## Languages

- Python 3.12 — Backend API, market data simulation, database operations
- TypeScript (planned) — Frontend UI (Next.js) — not yet implemented

## Runtime

- Python 3.12.12 (async-first)
- Node.js 20 (planned for frontend — not yet implemented)
- `uv` 0.x — Python dependency manager, produces lockfile (`uv.lock`)
- `npm` (planned) — Frontend dependency manager for Next.js
- `backend/uv.lock` — Production and development Python dependencies locked
- `package.json` (planned) — Frontend dependencies

## Frameworks

- FastAPI 0.141.1 — REST API, SSE streaming, application lifecycle management
- Next.js (planned) — Static export build for deployment with FastAPI
- pytest 8.0+ — Python unit test runner
- pytest-asyncio 0.24+ — Async test support for FastAPI
- respx 0.21+ — Mock HTTP client for market data API testing
- Playwright (planned) — E2E browser testing in `test/docker-compose.test.yml`
- rich 13.0+ — Terminal UI library (used in `scripts/demo_simulator.py`)
- uvicorn 0.30+ (with standard extras) — ASGI server for FastAPI

## Key Dependencies

- `fastapi >= 0.115` — Web framework, handles HTTP routing, SSE, app lifespan
- `httpx >= 0.27` — Async HTTP client for Massive API polling
- `uvicorn[standard] >= 0.30` — ASGI server with uvloop and watchfiles
- `pydantic` — Data validation via FastAPI, used for structured outputs (planned for LLM integration)
- `starlette` — ASGI toolkit underlying FastAPI
- `typing-extensions` — Type hints backports
- `annotated-doc` — Annotations support for FastAPI
- `typing-inspection` — Runtime type introspection
- `anyio` — Async abstraction layer
- `certifi` — SSL/TLS certificates
- `uvloop` — High-performance event loop (via uvicorn[standard])
- `httpcore` — Low-level HTTP transport
- `pydantic-core` — Pydantic's C extension
- `pytest` — Test framework
- `pytest-asyncio` — Pytest plugin for async tests
- `respx` — HTTP mock client for testing
- `rich` — Terminal formatting and tables
- `python-dotenv` — Load environment variables from `.env` file

## Configuration

- `OPENROUTER_API_KEY` — LiteLLM authentication key for LLM integration (required for chat, not yet used)
- `MASSIVE_API_KEY` — Polygon.io/Massive API key for real market data (optional; simulator used if absent)
- `LLM_MOCK` — Set to `"true"` for deterministic mock LLM responses in testing
- `FINALLY_DB_PATH` — SQLite database file path (default: `<repo-root>/db/finally.db`)
- `pyproject.toml` — Project metadata, dependencies, build system, pytest configuration
- `pytest.ini_options` — asyncio_mode: auto, testpaths: tests, pythonpath: ["."]
- Hatchling — Python build backend

## Platform Requirements

- Python 3.12+
- `uv` package manager
- Git
- Bash (for `scripts/start_mac.sh`, `scripts/stop_mac.sh`) or PowerShell (for Windows scripts)
- Docker (recommended for production)
- Docker volume for SQLite persistence (`db/` mount point)
- Port 8000 (single container, single port per PLAN.md §3)
- Docker container with:
- SQLite database (zero external DB dependencies)
- Environment variables passed via `--env-file .env`

## Architecture Overview

## Database

- File: `db/finally.db` (volume-mounted in Docker)
- Lazy initialization on first request — schema created automatically
- Single user model (no authentication)
- `user_id` column reserved for future multi-user support
- `watchlist` — Tickers user is watching (implemented)
- (Planned) `users_profile`, `positions`, `trades`, `portfolio_snapshots`, `chat_messages`

## External SDK/Services (Planned/Used)

- Massive REST API (`api.massive.com/v2/snapshot/...`) — Optional, polled via `httpx`
- No WebSocket or dedicated SDK — plain HTTP REST
- LiteLLM (planned dependency) — Abstraction layer over LLM providers
- OpenRouter API — LLM provider (model: `openrouter/openai/gpt-oss-120b`)
- No real code yet; infrastructure scaffolded only
- Authentication (single-user hardcoded)
- Caching (in-memory only)
- Monitoring/logging (print/logging module only)
- File storage (none needed; all data in SQLite)

## Summary Table

| Component | Technology | Version | Status |
|-----------|-----------|---------|--------|
| Backend Runtime | Python | 3.12 | Complete |
| Backend Framework | FastAPI | 0.141.1 | Complete (market data only) |
| Backend Server | Uvicorn | 0.30+ | Complete |
| HTTP Client | httpx | 0.27+ | Complete |
| Database | SQLite | Built-in | Complete (watchlist schema) |
| Market Data | Built-in + Massive | — | Complete (market layer) |
| Package Manager | uv | — | Complete |
| Testing | pytest | 8.0+ | Complete |
| Frontend | Next.js | — | Not started |
| LLM Integration | LiteLLM → OpenRouter | — | Not started |
| Deployment | Docker | — | Not started |
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->

## Conventions

## Naming Patterns

- Modules use `snake_case`: `watchlist.py`, `simulator.py`, `stream.py`
- Test files match implementation with `test_` prefix: `test_simulator.py`, `test_watchlist.py`
- Private/internal module marker: Leading underscore for utility functions (e.g., `_gbm_step()`, `_maybe_apply_event()`)
- All functions use `snake_case`
- Async functions have no special prefix — async keyword is explicit
- Private functions (module-level helpers) prefixed with single underscore
- Factory functions named `build_*` or `create_*` (e.g., `build_market_data_source()`, `create_app()`)
- Local variables and parameters: `snake_case`
- Instance variables prefixed with underscore: `self._prices`, `self._client`, `self._latest`
- Constants: `UPPERCASE_WITH_UNDERSCORES` (e.g., `DEFAULT_WATCHLIST`, `TICKER_UNIVERSE`, `SSE_BROADCAST_SECONDS`)
- Classes use `PascalCase`: `SimulatorMarketDataSource`, `MassiveMarketDataSource`, `PriceCache`, `PriceTick`
- Enums use `PascalCase`: `ChangeDirection`
- Dataclasses use `PascalCase` and are frozen (`@dataclass(frozen=True)`) when representing immutable values

## Code Style

- Line length: Observed 88-100 character soft limit (no explicit formatter configured, but consistent formatting throughout)
- Indentation: 4 spaces
- String quotes: Double quotes preferred for docstrings and regular strings
- Imports: Grouped in standard order (stdlib, third-party, local), separated by blank lines
- Full type annotations on function signatures are mandatory
- Return types explicitly annotated (e.g., `-> dict[str, float]`, `-> PriceTick | None`)
- Parameter types always specified (e.g., `tickers: list[str]`)
- Union types use pipe syntax: `int | None`, `dict[str, float] | None`
- No `type: ignore` comments observed — full type compliance expected
- Module-level docstrings required for all files (triple-quoted)
- Describe purpose, design rationale, and references to planning docs
- Class docstrings explain responsibilities and invariants
- Function docstrings document contract: parameters, return value, and any side effects
- Example: `"""Return the latest known price for each requested ticker. Tickers this source has no data for are simply omitted from the result dict — callers must not treat a missing key as an error."""`

## Import Organization

- No path aliases (no `@` prefixes like `@app/`) in backend — all imports relative within package hierarchy

## Error Handling

## Logging

- Module-level logger: `logger = logging.getLogger(__name__)`
- Used in `massive.py` and `loop.py` for error reporting and debugging
- Log levels:

## Comments

- Complex mathematical logic: GBM step calculation, sector correlation factors — explain the "why"
- Non-obvious design decisions: Why `previous_price` carries forward on heartbeat (preventing false flash animations)
- References to external docs: PLAN.md §6, planning/MARKET_DATA_DESIGN.md
- Edge cases and workarounds: Why events are disabled in certain tests, retry backoff logic
- Code that reads clearly (good naming) needs no comment
- Avoid restating the code: Don't comment `x = y  # assign y to x`

## Function Design

- Explicit return types on all functions
- `None` return implies side effect only (e.g., `async def start(self) -> None`)
- Dictionary returns document what keys are present and which may be missing (e.g., "unknown tickers omitted from result dict")
- All I/O operations are async (no blocking calls)
- Synchronous utility functions (GBM math, random events) remain sync — no unnecessary async wrappers
- Database access wrapped via `asyncio.to_thread()` to keep it off the event loop

## Module Design

- Each module exports its public interface clearly in imports (`from app.market.base import MarketDataSource`)
- Private functions/classes (leading `_`) are not for external import
- Concrete implementations (`SimulatorMarketDataSource`, `MassiveMarketDataSource`) exported for testing; consumers use via abstract `MarketDataSource`
- `app/market/base.py`: Abstract interface (`MarketDataSource`, `PriceTick`, `ChangeDirection`)
- `app/market/simulator.py`: Concrete implementation with all GBM math and constants
- `app/market/massive.py`: Concrete implementation with HTTP client and error handling
- `app/market/cache.py`: Shared in-memory store (not a data source)
- `app/market/loop.py`: Orchestration (drives either data source into cache)
- `app/market/factory.py`: Dependency selection based on environment
- `app/db/watchlist.py`: Persistence layer for watchlist tickers
- `app/routes/health.py`, `app/routes/stream.py`: FastAPI endpoints
- `app/main.py`: FastAPI app factory and lifespan management

## Async Patterns

- Created via `asyncio.create_task()` in lifespan
- Stored on `app.state` for access by routes
- Cancelled on shutdown via `task.cancel()`
- Blocking sync operations (DB, math) use `asyncio.to_thread()` to prevent blocking the event loop
- Example: `await asyncio.to_thread(_init_db_sync)`

## Testing Conventions (See TESTING.md)

- Use `pytest.mark.asyncio` for async test functions
- `monkeypatch` fixture for environment variables and module constants
- `tmp_path` fixture for isolated database files
- Type hints in test code as well
- Clear, descriptive test names

<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->

## Architecture

## System Overview

```text

```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| FastAPI App Factory | Wires all components together; manages startup/shutdown lifecycle | `app/main.py` |
| Market Data Source (Abstract) | Unified interface for price data retrieval | `app/market/base.py` |
| Simulator | Generates synthetic prices via GBM with correlated sector moves | `app/market/simulator.py` |
| Massive API Client | Fetches real prices via Polygon.io REST API | `app/market/massive.py` |
| Factory | Selects implementation based on `MASSIVE_API_KEY` env var | `app/market/factory.py` |
| Price Cache | Thread-safe, in-memory store of latest prices and direction | `app/market/cache.py` |
| Update Loop | Background task; polls source and updates cache on interval | `app/market/loop.py` |
| SSE Route | HTTP endpoint streaming cache snapshots to connected clients | `app/routes/stream.py` |
| Watchlist DB | Lazy-initialized SQLite table; seeds 10 default tickers | `app/db/watchlist.py` |
| Health Route | Trivial liveness check | `app/routes/health.py` |

## Pattern Overview

- **Abstraction-first**: `MarketDataSource` ABC ensures swappable implementations (simulator ↔ Massive) with zero coupling in downstream code
- **Single writer, multiple readers**: Only `run_update_loop` writes to `PriceCache`; all readers (SSE clients, future trade execution) read immutably from app.state
- **Lazy initialization**: SQLite schema and seed data created on first app startup, idempotent, no migrations
- **No global state**: All long-lived state stored on `app.state` (FastAPI's lifespan pattern), not module-level singletons

## Layers

- Purpose: FastAPI application listening on port 8000, serves static files (frontend, once built) and API routes
- Location: `app/main.py`
- Contains: FastAPI app factory, lifespan context manager
- Depends on: All layers below
- Used by: Uvicorn server process
- Purpose: Abstracts where prices come from (simulator or real API)
- Location: `app/market/base.py` (abstract), `app/market/simulator.py` and `app/market/massive.py` (implementations), `app/market/factory.py` (selection logic)
- Contains: `MarketDataSource` ABC, `SimulatorMarketDataSource`, `MassiveMarketDataSource`
- Depends on: None (simulator is stateless; Massive uses only stdlib and httpx)
- Used by: Update loop, factory during startup
- Purpose: Single source of truth for current prices; computes previous price and price direction for frontend flash animations
- Location: `app/market/cache.py`
- Contains: `PriceCache` class with async lock-protected read/write
- Depends on: `MarketDataSource` (only via type annotations, not at runtime)
- Used by: Update loop (writer), SSE route (reader), future trade execution (reader)
- Purpose: Background task that fetches prices from the active source and feeds them into the cache at fixed intervals
- Location: `app/market/loop.py`
- Contains: `run_update_loop()` coroutine, configurable intervals per source type
- Depends on: `MarketDataSource`, `PriceCache`, `get_watchlist_tickers()`
- Used by: App lifespan (started at startup, cancelled at shutdown)
- Purpose: Persistent storage of watchlist (currently); scaffolding for future portfolio/trades/snapshots tables
- Location: `app/db/watchlist.py`
- Contains: Schema definition, seed data, read path (`get_watchlist_tickers`)
- Depends on: None (uses only stdlib sqlite3)
- Used by: Update loop (reads watchlist on each cycle)
- Purpose: REST and SSE endpoints exposing market data and system health
- Location: `app/routes/`
- Contains: `stream.py` (SSE `/api/stream/prices`), `health.py` (GET `/api/health`)
- Depends on: `PriceCache` (via app.state)
- Used by: FastAPI router, clients (browser, curl, etc.)

## Data Flow

### Primary Request Path (SSE Price Stream)

### Background Update Cycle

### Startup Initialization

### Shutdown Teardown

- **Simulator**: State lives entirely in `SimulatorMarketDataSource._prices` dict and RNG; no persistent storage
- **Massive**: State is just the `httpx.AsyncClient`; prices not stored (fetched fresh each poll)
- **Cache**: In-memory dict, not persisted; rebuilds on each startup (frontend accumulates its own sparkline data)
- **Database**: SQLite file (`db/finally.db` volume mount); watchlist and future portfolio data persists across restarts

## Key Abstractions

- Purpose: Defines contract for any source that can provide prices and validate tickers
- Examples: `SimulatorMarketDataSource`, `MassiveMarketDataSource`
- Pattern: Abstract base class with four async methods (`start`, `stop`, `get_prices`, `is_valid_ticker`)
- Rationale: Allows swapping implementations at startup with zero downstream coupling; every route, the cache, and the loop code only reference the abstract type
- Purpose: Bundles price, previous price, timestamp, and direction for one ticker
- Examples: Emitted by `cache.update()`, returned by `cache.snapshot()`, serialized in SSE events
- Pattern: Frozen dataclass ensures immutability
- Rationale: Prevents accidental mutation of price history; safe to share across async tasks
- Purpose: Single source of truth for "what's the current price, and did it go up or down?"
- Examples: Snapshot read in SSE route, single-ticker lookup for future trade execution
- Pattern: Async lock guards the internal dict; all mutations are atomic
- Rationale: Multiple concurrent readers (SSE clients) and one writer (update loop) need serialization; atomicity ensures `previous_price` never falls behind actual history

## Entry Points

- Location: `app/main.py:create_app()` → `app = create_app()` module-level instantiation
- Triggers: `uvicorn app.main:app` command starts the server
- Responsibilities: Orchestrates startup (source, cache, loop), serves routes, orchestrates shutdown
- Used by: Uvicorn ASGI server
- Location: `app/routes/stream.py:stream_prices()`
- Triggers: Browser's `new EventSource('/api/stream/prices')`
- Responsibilities: Retrieves cache from app.state, yields price snapshots every 500ms
- Used by: Frontend, test clients (curl -N)
- Location: `app/routes/health.py:health_check()`
- Triggers: `GET /api/health`
- Responsibilities: Returns `{"status": "ok"}` — used by Docker/orchestrators to probe liveness
- Used by: Load balancers, Docker health checks

## Architectural Constraints

- **Threading:** Single-threaded event loop (FastAPI/asyncio model). No threads spawned except via `asyncio.to_thread()` for sync SQLite calls. Simulator's internal tick loop runs as an asyncio task, not a thread. Massive's HTTP client (httpx) is async-only.
- **Global state:** None. All long-lived state stored on `app.state` (market_source, price_cache) within the lifespan context. `run_update_loop` is a background task, not a global. Database connections are created on-demand via `_connect()`, not pooled.
- **Circular imports:** None detected. `app/market/` modules have no imports from `app/routes/` or `app/db/`; routes import from market only for type annotations. Clean dependency graph: market → no one else; cache ↑ source; loop ↑ cache + source + db; routes ↑ cache; main ↑ everything.
- **Concurrency model:** Update loop is the sole writer to PriceCache; all SSE clients are readers. Lock in PriceCache ensures atomicity. No TOCTOU issues: each update and snapshot read is atomic.

## Anti-Patterns

### Avoided: Source-specific branching in downstream code

### Avoided: Global module-level source or cache

### Avoided: Caching prices in the update loop

## Error Handling

- **Update loop errors**: Wrapped in try/except that logs but does not re-raise. If `source.get_prices()` raises (violates contract), the loop logs and sleeps; prices go stale but the app stays up. Tests ensure this doesn't happen in practice.
- **Source errors**: Both `SimulatorMarketDataSource` and `MassiveMarketDataSource` never raise; rate limits, network errors, malformed JSON are caught and returned as `{}` (no update this cycle).
- **SSE client disconnect**: Checked on each yield via `if await request.is_disconnected()`. Client closes stream cleanly; server stops sending.
- **Database errors**: `_connect()` creates DB file and parent dirs on demand; `init_db()` idempotently creates schema. Sync calls run on `asyncio.to_thread()` so don't block the event loop.

## Cross-Cutting Concerns

<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->

## Project Skills

| Skill | Description | Path |
|-------|-------------|------|
| litellm-stream | Use this to write code to call an LLM using LiteLLM and OpenRouter | `.claude/skills/litellm-stream/SKILL.md` |
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->

## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:

- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->

## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
