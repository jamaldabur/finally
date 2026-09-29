---
last_mapped_commit: 20fd6385728d5909231f6772c7abc2d5c3111cb7
last_mapped_at: 2026-09-15
---
# Codebase Structure

**Analysis Date:** 2026-09-15

## Directory Layout

```
finally/                                # Project root
├── backend/                            # Python/FastAPI backend (uv-managed)
│   ├── app/                            # Application package
│   │   ├── __init__.py
│   │   ├── main.py                     # Entry point; FastAPI app factory
│   │   │
│   │   ├── market/                     # Market data layer (BUILT)
│   │   │   ├── __init__.py
│   │   │   ├── base.py                 # Abstract MarketDataSource interface
│   │   │   ├── simulator.py            # Default: GBM price generator
│   │   │   ├── massive.py              # Optional: Polygon.io REST client
│   │   │   ├── factory.py              # Selects implementation at startup
│   │   │   ├── cache.py                # Thread-safe price cache
│   │   │   └── loop.py                 # Background update task
│   │   │
│   │   ├── db/                         # Database layer (PARTIAL)
│   │   │   ├── __init__.py
│   │   │   └── watchlist.py            # SQLite watchlist table + seed
│   │   │
│   │   ├── routes/                     # HTTP endpoints (PARTIAL)
│   │   │   ├── __init__.py
│   │   │   ├── stream.py               # SSE /api/stream/prices
│   │   │   └── health.py               # GET /api/health
│   │   │
│   │   ├── portfolio/                  # NOT YET BUILT
│   │   ├── watchlist/                  # NOT YET BUILT
│   │   └── llm/                        # NOT YET BUILT
│   │
│   ├── tests/                          # Pytest test suite
│   │   ├── market/                     # Tests for market data layer
│   │   │   ├── test_simulator.py
│   │   │   ├── test_massive.py
│   │   │   ├── test_cache.py
│   │   │   ├── test_factory.py
│   │   │   ├── test_loop.py
│   │   │   ├── test_interface_conformance.py
│   │   ├── db/                         # Tests for DB layer
│   │   │   └── test_watchlist.py
│   │   ├── routes/                     # Tests for HTTP layer
│   │   │   ├── test_stream.py
│   │   │   └── test_health.py
│   │   └── test_main.py                # App startup/shutdown
│   │
│   ├── scripts/                        # Utility scripts
│   │   └── demo_simulator.py           # Terminal UI for market data
│   │
│   ├── pyproject.toml                  # Dependencies, pytest config
│   └── .venv/                          # Virtual environment (git-ignored)
│
├── frontend/                           # NOT YET BUILT
│   │                                   # Will be Next.js TypeScript app
│   │                                   # Static export served by backend
│
├── planning/                           # Project documentation
│   ├── PLAN.md                         # Full system specification
│   ├── MARKET_DATA_SUMMARY.md          # Summary of what's built
│   └── archive/                        # Archived design docs
│       ├── MARKET_DATA_DESIGN.md
│       ├── MARKET_INTERFACE.md
│       ├── MARKET_SIMULATOR.md
│       └── MASSIVE_API.md
│
├── .planning/codebase/                 # Agent-generated analysis docs
│   ├── ARCHITECTURE.md                 # System layers and patterns
│   ├── STRUCTURE.md                    # This file
│   ├── CONVENTIONS.md                  # (Not yet written)
│   ├── TESTING.md                      # (Not yet written)
│   ├── STACK.md                        # (Not yet written)
│   ├── INTEGRATIONS.md                 # (Not yet written)
│   └── CONCERNS.md                     # (Not yet written)
│
├── test/                               # Playwright E2E tests (not yet active)
│   └── node_modules/                   # Playwright dependencies
│
├── db/                                 # SQLite runtime data (git-ignored)
│   └── finally.db                      # Created on first backend run
│
├── scripts/                            # Docker/deployment scripts
│   ├── start_mac.sh                    # Launch container (macOS/Linux)
│   ├── stop_mac.sh                     # Stop container (macOS/Linux)
│   ├── start_windows.ps1               # Launch container (Windows)
│   └── stop_windows.ps1                # Stop container (Windows)
│
├── Dockerfile                          # Multi-stage build (Node → Python)
├── docker-compose.yml                  # Optional development wrapper
├── .env                                # Environment config (git-ignored)
├── .env.example                        # Environment template (committed)
├── .gitignore                          # Git exclusions
├── CLAUDE.md                           # Project instructions
├── README.md                           # Repo overview
└── LICENSE                             # MIT license
```

## Directory Purposes

**backend/:**

- Purpose: Self-contained FastAPI application with its own `pyproject.toml` and dependency isolation
- Contains: Python app code, tests, demo scripts
- Entry: `app/main.py:app` (Uvicorn serves this)
- Database: SQLite at `../../db/finally.db` (path relative to `app/db/watchlist.py`)

**backend/app/:**

- Purpose: Top-level Python package; imported as `from app.market ...` in routes and main
- Contains: All application modules organized by concern (market, db, routes, portfolio stub)

**backend/app/market/:**

- Purpose: Market data layer — completely built, tested, 73 passing tests
- Contains: Abstract interface (base.py), two implementations (simulator/massive), factory, cache, update loop
- Key abstraction: `MarketDataSource` ABC; everything above it is agnostic to which implementation is active

**backend/app/db/:**

- Purpose: Persistence layer; currently only watchlist
- Contains: SQLite schema, seed data, read path
- Roadmap: Will expand to include `users_profile`, `positions`, `trades`, `portfolio_snapshots`, `chat_messages` (see PLAN.md §7)

**backend/app/routes/:**

- Purpose: HTTP endpoints exposed to clients
- Contains: Stream (SSE), health check
- Roadmap: Will add `/api/portfolio`, `/api/watchlist`, `/api/chat` once those services exist

**backend/app/portfolio/**, **backend/app/watchlist/**, **backend/app/llm/:**

- Purpose: Placeholder directories for future modules
- Status: Exist but contain no code
- Design: Will follow same layering pattern: business logic module, then route handlers that call them

**backend/tests/:**

- Purpose: Pytest test suite, organized to mirror app structure
- Contains: 73 passing tests; unit tests for simulator, massive client, cache, loop, factory, DB, routes, app startup
- Run: `uv run pytest` from backend/

**planning/:**

- Purpose: Shared documentation all agents reference
- Key files: `PLAN.md` (full spec), `MARKET_DATA_SUMMARY.md` (current status), `archive/` (design rationale)
- Read-only for agents; not code

**.planning/codebase/:**

- Purpose: Agent-generated codebase analysis documents (you are here)
- Consumed by: `/gsd-plan-phase` and `/gsd-execute-phase` to guide future work
- Files: One per topic (ARCHITECTURE.md, STRUCTURE.md, CONVENTIONS.md, etc.)

**db/:**

- Purpose: Runtime data directory; SQLite file volume-mounted at container `/app/db`
- Git-ignored: `db/finally.db` is created on first run and not committed
- Persists across container restarts via Docker named volume

**scripts/:**

- Purpose: Convenience wrappers for Docker container lifecycle
- Idempotent: Safe to run multiple times; checks for existing containers
- Platforms: Separate shell scripts (Mac/Linux) and PowerShell scripts (Windows)

**frontend/:**

- Purpose: Next.js static export (not yet built)
- Roadmap: Will be built as self-contained Next.js project, output to `out/`, copied into backend's static file serving path
- Communication: HTTP to backend on same origin (`/api/*` and `/api/stream/*`)

## Key File Locations

**Entry Points:**

- `backend/app/main.py` — FastAPI app factory; startup/shutdown orchestration
- `backend/app/market/factory.py` — Selects Simulator or Massive at startup based on `MASSIVE_API_KEY`
- `backend/app/db/watchlist.py` — Lazy DB init on app startup

**Configuration:**

- `backend/pyproject.toml` — Python dependencies, pytest config (asyncio_mode, testpaths)
- `.env` (git-ignored) — Runtime environment (MASSIVE_API_KEY, OPENROUTER_API_KEY)
- `.env.example` — Template for .env setup

**Core Market Data Logic:**

- `backend/app/market/base.py` — `MarketDataSource` abstract interface
- `backend/app/market/simulator.py` — GBM implementation; 30-ticker universe with correlated sector moves
- `backend/app/market/massive.py` — Polygon.io REST client with resilient error handling
- `backend/app/market/cache.py` — `PriceCache`; thread-safe, computes direction for frontend animation
- `backend/app/market/loop.py` — `run_update_loop()`; background task pulling source into cache

**Database & Persistence:**

- `backend/app/db/watchlist.py` — `get_watchlist_tickers()`, schema, seed data
- `db/finally.db` — SQLite file (created on first run, git-ignored, volume-mounted for persistence)

**HTTP Routing:**

- `backend/app/routes/stream.py` — SSE endpoint `/api/stream/prices`
- `backend/app/routes/health.py` — Liveness check `/api/health`

**Testing:**

- `backend/tests/test_main.py` — App lifespan (startup/shutdown)
- `backend/tests/market/test_simulator.py` — GBM math, correlated moves, events
- `backend/tests/market/test_massive.py` — Rate limit resilience, error handling, response parsing
- `backend/tests/market/test_cache.py` — Previous price carry-forward, lock behavior
- `backend/tests/market/test_loop.py` — Update loop resilience, error isolation
- `backend/tests/market/test_interface_conformance.py` — Both sources implement abstract interface correctly

## Naming Conventions

**Files:**

- Snake case: `market_data_source.py`, `test_simulator.py`, `run_update_loop()`
- Private: `_serialize_tick()`, `_gbm_step()`, `_connect()`
- Modules mirror classes: `cache.py` contains `PriceCache`, `base.py` contains `MarketDataSource`

**Directories:**

- Lowercase, plural for packages: `market/`, `routes/`, `tests/`, `db/`
- Singular for concerns: `backend/`, `frontend/`, `planning/`

**Classes:**

- PascalCase: `MarketDataSource`, `PriceCache`, `PriceTick`, `ChangeDirection`, `SimulatorMarketDataSource`, `MassiveMarketDataSource`
- Enums: `ChangeDirection` with members `UP`, `DOWN`, `UNCHANGED`

**Functions & Methods:**

- Snake case: `get_prices()`, `is_valid_ticker()`, `run_update_loop()`, `build_market_data_source()`
- Async coroutines: `async def` convention; no `async_` prefix (asyncio style)
- Private methods: `_tick_forever()`, `_advance_all()`, `_gbm_step()`

**Database:**

- Tables: Singular nouns (not yet all built): `watchlist`, `users_profile`, `positions`, `trades`, `portfolio_snapshots`, `chat_messages`
- Columns: Snake case: `user_id`, `ticker`, `added_at`, `is_valid_ticker`

**Environment Variables:**

- Uppercase with underscores: `MASSIVE_API_KEY`, `OPENROUTER_API_KEY`, `LLM_MOCK`, `FINALLY_DB_PATH`

## Where to Add New Code

**New Market Data Feature (e.g., Alpaca Integration):**

- Create `backend/app/market/alpaca.py` implementing `MarketDataSource`
- Add tests at `backend/tests/market/test_alpaca.py`
- Update `backend/app/market/factory.py` to select Alpaca if env var is set
- No changes to cache, loop, routes, or main — abstraction handles it

**New Portfolio Management Feature:**

- Implement service module at `backend/app/portfolio/service.py` (validate trades, update positions, compute P&L)
- Add database functions to `backend/app/db/` (extend schema, add mutation functions)
- Add route handlers at `backend/app/routes/portfolio.py` (POST trade, GET positions, GET history)
- Add tests mirroring market data structure: `backend/tests/portfolio/test_*.py`

**New Watchlist CRUD (add/remove tickers):**

- Add mutation functions to `backend/app/db/watchlist.py` (add_ticker, remove_ticker with validation)
- Add route handlers at `backend/app/routes/watchlist.py` (POST add, DELETE remove)
- Add tests at `backend/tests/watchlist/` — validate against `source.is_valid_ticker()`

**New LLM Integration:**

- Implement chat service at `backend/app/llm/service.py` (call OpenRouter via LiteLLM, parse structured outputs)
- Add database function to store messages at `backend/app/db/` (insert into chat_messages)
- Add route handler at `backend/app/routes/chat.py` (POST message, GET history)
- Add tests at `backend/tests/llm/`

**New HTTP Route:**

- Add handler to appropriate `backend/app/routes/*.py` file (or create new file if new concern)
- Register with `app.include_router()` in `backend/app/main.py`
- Test in `backend/tests/routes/test_*.py` — use FastAPI TestClient

**Frontend (Next.js):**

- Create at `frontend/` (separate Next.js project, not built yet)
- Static export (`output: 'export'`) to `frontend/out/`
- Dockerfile copies `out/` into Python stage for serving
- Communication: HTTP to `/api/*` on same origin

## Special Directories

**backend/.venv/:**

- Purpose: Python virtual environment created by `uv sync`
- Generated: Yes (by uv)
- Committed: No (git-ignored)

**backend/__pycache__/** and **tests/__pycache__/:**

- Purpose: Python bytecode cache
- Generated: Yes (by Python)
- Committed: No (git-ignored)

**backend/.pytest_cache/:**

- Purpose: Pytest test run cache
- Generated: Yes (by pytest)
- Committed: No (git-ignored)

**db/:**

- Purpose: Runtime SQLite database file
- Generated: Yes (by backend on first request)
- Committed: No (git-ignored) — `db/.gitkeep` ensures directory exists in repo

**test/node_modules/:**

- Purpose: Playwright dependencies for E2E tests (not yet active)
- Generated: Yes (by npm)
- Committed: No (git-ignored)

---

*Structure analysis: 2026-09-15*
