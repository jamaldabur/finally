---
last_mapped_commit: 20fd6385728d5909231f6772c7abc2d5c3111cb7
last_mapped_at: 2026-09-15
---
<!-- refreshed: 2026-09-15 -->

# Architecture

**Analysis Date:** 2026-09-15

## System Overview

The FinAlly backend is a FastAPI application structured around a market data streaming pipeline. Currently, only the market data component is implemented; the frontend, portfolio management, and LLM integration layers described in `planning/PLAN.md` are not yet built.

```text
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI Application                    │
│                     `app/main.py` (entry)                   │
├────────────┬───────────────────┬──────────────┬─────────────┤
│ Market     │   Price Cache     │   HTTP       │   Database  │
│ Sources    │   `cache.py`      │   Routes     │   `db/`     │
│ `market/`  │                   │   `routes/`  │             │
└────────┬───┴──────────┬────────┴────┬─────────┴──────┬──────┘
         │              │             │                │
         ▼              ▼             ▼                ▼
    ┌─────────────────────────────────────────────────────────┐
    │          Update Loop (`loop.py`)                         │
    │          - Polls market data source                      │
    │          - Writes to price cache                         │
    │          - Runs as background task                       │
    └──────────┬──────────────────────────────┬────────────────┘
               │                              │
    ┌──────────▼──────────┐      ┌───────────▼──────────────┐
    │  Market Data Source │      │    Price Cache            │
    │  (Abstract Base)    │      │    (Shared In-Memory)     │
    │  `base.py`          │      │    Thread-safe via Lock   │
    └──────────┬──────────┘      └───────────┬──────────────┘
               │                              │
    ┌──────────┴──────────────────────────────┴─────────────┐
    │                                                        │
    ▼  Simulator (default)        ▼  Massive API (optional) │
    │  `simulator.py`              │  `massive.py`          │
    │  - GBM price generation      │  - REST polling         │
    │  - In-process, no network    │  - Requires API key     │
    └────────────────────────────────────────────────────────┘
               │                              │
               └──────────────┬───────────────┘
                              │
                   ┌──────────▼────────────┐
                   │    SSE Endpoint       │
                   │  `/api/stream/prices` │
                   │  `routes/stream.py`   │
                   └───────────────────────┘
                              │
                              ▼
                         (Frontend client)
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

**Overall:** Layered architecture with a data source abstraction layer, an in-memory cache as a single source of truth, a background task driving updates, and HTTP routes exposing the cache to clients.

**Key Characteristics:**

- **Abstraction-first**: `MarketDataSource` ABC ensures swappable implementations (simulator ↔ Massive) with zero coupling in downstream code
- **Single writer, multiple readers**: Only `run_update_loop` writes to `PriceCache`; all readers (SSE clients, future trade execution) read immutably from app.state
- **Lazy initialization**: SQLite schema and seed data created on first app startup, idempotent, no migrations
- **No global state**: All long-lived state stored on `app.state` (FastAPI's lifespan pattern), not module-level singletons

## Layers

**HTTP Entry Point:**

- Purpose: FastAPI application listening on port 8000, serves static files (frontend, once built) and API routes
- Location: `app/main.py`
- Contains: FastAPI app factory, lifespan context manager
- Depends on: All layers below
- Used by: Uvicorn server process

**Market Data Source Layer:**

- Purpose: Abstracts where prices come from (simulator or real API)
- Location: `app/market/base.py` (abstract), `app/market/simulator.py` and `app/market/massive.py` (implementations), `app/market/factory.py` (selection logic)
- Contains: `MarketDataSource` ABC, `SimulatorMarketDataSource`, `MassiveMarketDataSource`
- Depends on: None (simulator is stateless; Massive uses only stdlib and httpx)
- Used by: Update loop, factory during startup

**Price Cache Layer:**

- Purpose: Single source of truth for current prices; computes previous price and price direction for frontend flash animations
- Location: `app/market/cache.py`
- Contains: `PriceCache` class with async lock-protected read/write
- Depends on: `MarketDataSource` (only via type annotations, not at runtime)
- Used by: Update loop (writer), SSE route (reader), future trade execution (reader)

**Update Loop:**

- Purpose: Background task that fetches prices from the active source and feeds them into the cache at fixed intervals
- Location: `app/market/loop.py`
- Contains: `run_update_loop()` coroutine, configurable intervals per source type
- Depends on: `MarketDataSource`, `PriceCache`, `get_watchlist_tickers()`
- Used by: App lifespan (started at startup, cancelled at shutdown)

**Database Layer:**

- Purpose: Persistent storage of watchlist (currently); scaffolding for future portfolio/trades/snapshots tables
- Location: `app/db/watchlist.py`
- Contains: Schema definition, seed data, read path (`get_watchlist_tickers`)
- Depends on: None (uses only stdlib sqlite3)
- Used by: Update loop (reads watchlist on each cycle)

**HTTP Routes:**

- Purpose: REST and SSE endpoints exposing market data and system health
- Location: `app/routes/`
- Contains: `stream.py` (SSE `/api/stream/prices`), `health.py` (GET `/api/health`)
- Depends on: `PriceCache` (via app.state)
- Used by: FastAPI router, clients (browser, curl, etc.)

## Data Flow

### Primary Request Path (SSE Price Stream)

1. **Client connects** → Browser calls `new EventSource('/api/stream/prices')`
2. **Route entry** (`routes/stream.py:stream_prices`) → Retrieves `PriceCache` from `app.state`
3. **Generator loop** → `_price_event_generator()` wakes every 500ms
4. **Cache read** → `await cache.snapshot()` retrieves all current tickers as list of `PriceTick` objects
5. **Serialization** → Each tick converted to dict: `{ticker, price, previous_price, timestamp, direction}`
6. **SSE emit** → `yield` SSE event with JSON payload: `event: prices\ndata: {...}\n\n`
7. **Client receives** → Browser's EventSource fires `message` event with parsed JSON

### Background Update Cycle

1. **Timer fires** → `run_update_loop` wakes every 0.5s (simulator) or 15s (Massive free tier)
2. **Read watchlist** → Calls `get_watchlist_tickers()` to fetch list of currently watched symbols
3. **Fetch prices** → Awaits `source.get_prices(tickers)` — returns `{ticker: price}` dict
4. **Update cache** → For each fetched price, calls `await cache.update(ticker, price)`
5. **Compute direction** → Cache compares new price to last *different* price, emits `UP`, `DOWN`, or `UNCHANGED`
6. **Store on app.state** → Cache maintains single in-memory `_latest` dict, guarded by asyncio lock

### Startup Initialization

1. **FastAPI lifespan context** (`main.py:lifespan`) begins
2. **Database init** → `await init_db()` creates `watchlist` table if missing, seeds 10 default tickers
3. **Factory selection** → `build_market_data_source()` checks `MASSIVE_API_KEY` env var
4. **Source startup** → `await source.start()` — simulator spawns internal tick loop, Massive creates HTTP client
5. **Cache creation** → Instantiate new `PriceCache()`
6. **Update loop start** → `asyncio.create_task(run_update_loop(...))` with appropriate interval
7. **Store on app.state** → `app.state.market_source` and `app.state.price_cache` accessible to routes
8. **Yield control** → App is now ready to serve requests

### Shutdown Teardown

1. **Server receives SIGTERM** or lifespan context exits
2. **Update task cancellation** → `update_task.cancel()` stops the background loop
3. **Source stop** → `await source.stop()` closes Massive HTTP client or cancels simulator tick task
4. **Exit** → Lifespan context exits, app shuts down

**State Management:**

- **Simulator**: State lives entirely in `SimulatorMarketDataSource._prices` dict and RNG; no persistent storage
- **Massive**: State is just the `httpx.AsyncClient`; prices not stored (fetched fresh each poll)
- **Cache**: In-memory dict, not persisted; rebuilds on each startup (frontend accumulates its own sparkline data)
- **Database**: SQLite file (`db/finally.db` volume mount); watchlist and future portfolio data persists across restarts

## Key Abstractions

**MarketDataSource (Abstract Base Class):**

- Purpose: Defines contract for any source that can provide prices and validate tickers
- Examples: `SimulatorMarketDataSource`, `MassiveMarketDataSource`
- Pattern: Abstract base class with four async methods (`start`, `stop`, `get_prices`, `is_valid_ticker`)
- Rationale: Allows swapping implementations at startup with zero downstream coupling; every route, the cache, and the loop code only reference the abstract type

**PriceTick (Immutable Data Class):**

- Purpose: Bundles price, previous price, timestamp, and direction for one ticker
- Examples: Emitted by `cache.update()`, returned by `cache.snapshot()`, serialized in SSE events
- Pattern: Frozen dataclass ensures immutability
- Rationale: Prevents accidental mutation of price history; safe to share across async tasks

**PriceCache (Thread-Safe In-Memory Store):**

- Purpose: Single source of truth for "what's the current price, and did it go up or down?"
- Examples: Snapshot read in SSE route, single-ticker lookup for future trade execution
- Pattern: Async lock guards the internal dict; all mutations are atomic
- Rationale: Multiple concurrent readers (SSE clients) and one writer (update loop) need serialization; atomicity ensures `previous_price` never falls behind actual history

## Entry Points

**FastAPI Application:**

- Location: `app/main.py:create_app()` → `app = create_app()` module-level instantiation
- Triggers: `uvicorn app.main:app` command starts the server
- Responsibilities: Orchestrates startup (source, cache, loop), serves routes, orchestrates shutdown
- Used by: Uvicorn ASGI server

**SSE Stream Endpoint:**

- Location: `app/routes/stream.py:stream_prices()`
- Triggers: Browser's `new EventSource('/api/stream/prices')`
- Responsibilities: Retrieves cache from app.state, yields price snapshots every 500ms
- Used by: Frontend, test clients (curl -N)

**Health Check Endpoint:**

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

**What would happen:** Routes checking `if isinstance(source, MassiveMarketDataSource)` to adjust parsing or error handling.

**Why it's wrong:** Couples route/cache/loop logic to specific implementations; makes swapping sources fragile and error-prone.

**What we do instead:** All code above the source layer depends only on `MarketDataSource` ABC. Selection logic is isolated in `factory.py`.

### Avoided: Global module-level source or cache

**What would happen:** `market_source = None` and `price_cache = None` at module level, set during `init()`.

**Why it's wrong:** Complicates testing (can't instantiate multiple isolated apps), breaks FastAPI's lifespan model, makes the app's state implicit and hidden.

**What we do instead:** Store on `app.state` within lifespan; tests construct fresh `create_app()` instances with their own state.

### Avoided: Caching prices in the update loop

**What would happen:** `loop.py` keeps a shadow copy of `_prices` to avoid repeated PriceCache lookups.

**Why it's wrong:** Splits the source of truth; divergent copies lead to staleness and hard-to-debug flicker.

**What we do instead:** Cache is the single writer's only destination; lookers always read from cache.

## Error Handling

**Strategy:** Fail gracefully; never crash the loop or drop an SSE client.

**Patterns:**

- **Update loop errors**: Wrapped in try/except that logs but does not re-raise. If `source.get_prices()` raises (violates contract), the loop logs and sleeps; prices go stale but the app stays up. Tests ensure this doesn't happen in practice.
- **Source errors**: Both `SimulatorMarketDataSource` and `MassiveMarketDataSource` never raise; rate limits, network errors, malformed JSON are caught and returned as `{}` (no update this cycle).
- **SSE client disconnect**: Checked on each yield via `if await request.is_disconnected()`. Client closes stream cleanly; server stops sending.
- **Database errors**: `_connect()` creates DB file and parent dirs on demand; `init_db()` idempotently creates schema. Sync calls run on `asyncio.to_thread()` so don't block the event loop.

## Cross-Cutting Concerns

**Logging:** Uses Python stdlib logging. Update loop logs exceptions at ERROR level. Source implementations log retries/fallbacks at DEBUG level. Routes do not log (except framework-level FastAPI logging).

**Validation:** Ticker validity checked only at add-time (not yet built, but foundation is `source.is_valid_ticker()`). For the update loop, tickers from watchlist table are assumed valid; they were validated at add-time.

**Authentication:** Not applicable — single-user demo app (PLAN.md §7 notes `user_id` default is hardcoded `"default"`).

---

*Architecture analysis: 2026-09-15*
