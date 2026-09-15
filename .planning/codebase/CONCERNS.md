---
last_mapped_commit: 20fd6385728d5909231f6772c7abc2d5c3111cb7
last_mapped_at: 2026-09-15
---
<!-- refreshed: 2026-09-15 -->

# Codebase Concerns

**Analysis Date:** 2026-09-15

## Scope & Coverage

### Significant Missing Implementation

**Core application layers incomplete:**

- Files: Frontend (`frontend/`) is empty; portfolio management endpoints not started; LLM chat integration not started
- Impact: The application is ~40-50% complete. Only the market data layer (price streaming, simulator, Massive API client) is functional. Features described in PLAN.md §3-9 (portfolio, trades, watchlist mutations, chat, trade execution) remain unimplemented.
- Status: Expected — project is early-stage, market data was the first deliverable. This is not a bug; it's scope tracking.

**Deployment infrastructure missing:**

- Files: No `Dockerfile`, `docker-compose.yml`, `scripts/start_mac.sh`, `scripts/stop_mac.sh`, `scripts/start_windows.ps1`, `scripts/stop_windows.ps1`
- Impact: Cannot deploy or run the application yet. PLAN.md §11 describes a multi-stage build and start/stop scripts — these are critical for the project's "single Docker command" vision but do not exist.
- Priority: High — blocks testing and deployment

**Environment documentation incomplete:**

- Files: `.env.example` is missing
- Impact: New developers or CI/CD pipelines lack a reference for required environment variables. PLAN.md §5 specifies `OPENROUTER_API_KEY` (required) and `MASSIVE_API_KEY` (optional), but there's no `.env.example` showing the template.
- Fix approach: Create `.env.example` listing `OPENROUTER_API_KEY`, `MASSIVE_API_KEY`, `LLM_MOCK`, and any others referenced in the backend code.

## Tech Debt & Architectural Decisions

### Database Layer Fragility

**Synchronous SQLite ops wrapped in asyncio threads:**

- Issue: All database operations (`init_db()`, `get_watchlist_tickers()`) are sync functions called via `asyncio.to_thread()`. Every read/write incurs thread pool overhead.
- Files: `backend/app/db/watchlist.py` (lines 51-83)
- Impact: Performance is acceptable for single-user demo scale, but this pattern is not suitable for production multi-user or high-frequency trading scenarios. Thread pool can become a bottleneck.
- Scaling path: Migrate to an async SQLite library (e.g., `aiosqlite`) or switch to an async-first database (PostgreSQL + asyncpg).

**SQLite connection pooling absent:**

- Issue: Every sync database call creates a new connection via `sqlite3.connect()` (line 48).
- Files: `backend/app/db/watchlist.py`, line 48
- Impact: For single-user demo this is fine; for production multi-user it becomes inefficient and may hit connection limits.
- Mitigation: Use a connection pool or persistent connection. Not urgent for current scope.

**Schema initialization race condition:**

- Issue: `init_db()` is called once during app lifespan, but if multiple concurrent requests arrive during initialization, `asyncio.to_thread()` could dispatch multiple sync calls to `_init_db_sync()` simultaneously.
- Files: `backend/app/db/watchlist.py`, `backend/app/main.py` (line 25)
- Impact: SQLite serializes writes, but redundant schema creation and seed inserts are wasteful. Not a crash risk, but inefficient.
- Safe modification: Use a file lock or single async lock (not ideal with sync code) — acceptable as-is for demo scale.

**Schema defined inline, not in a dedicated migration:**

- Issue: Schema SQL is hardcoded in `_init_db_sync()` rather than in a schema file or migration system.
- Files: `backend/app/db/watchlist.py` (lines 35-42)
- Impact: Future schema changes require code edits and re-deployment. PLAN.md §7 mentions a `backend/schema/` directory for "schema SQL definitions and seed logic" — this is a placeholder that hasn't been filled.
- Fix approach: Extract schema to `backend/app/schema/` with separate files for each table definition, plus a migration registry.

### Incomplete Module Structure

**Empty placeholder directories:**

- Issue: `backend/app/llm/`, `backend/app/portfolio/`, `backend/app/watchlist/` exist as directories but contain no Python files (only `__pycache__`).
- Files: Directories exist; see structure
- Impact: The main app imports from these (indirectly via route organization), but they're not actually wired yet. This is expected scaffolding, not a bug.
- Priority: Low — these are intended for future phases.

**Watchlist module is read-only:**

- Issue: `backend/app/db/watchlist.py` only implements `get_watchlist_tickers()` and `init_db()`. Add and remove operations are not implemented, despite PLAN.md §8 describing POST/DELETE endpoints for watchlist mutation.
- Files: `backend/app/db/watchlist.py`; missing: `add_watchlist_ticker()`, `remove_watchlist_ticker()`
- Impact: Watchlist is hardcoded to the default 10 tickers. Users and the LLM cannot add/remove tickers manually or via chat.
- Blocks: Chat feature, part of portfolio/watchlist UI
- Fix approach: Implement `add_watchlist_ticker(user_id, ticker, source)` and `remove_watchlist_ticker(user_id, ticker)` that validate ticker against the active data source, then insert/delete rows.

**Portfolio and LLM modules stubbed but not yet routed:**

- Issue: Directories exist; routes don't import or wire them into the app.
- Files: `backend/app/main.py` only includes `health` and `stream` routers; no portfolio or chat routers
- Impact: Portfolio endpoints (`GET /api/portfolio`, `POST /api/portfolio/trade`, `GET /api/portfolio/history`) and chat endpoints (`GET /api/chat`, `POST /api/chat`) are not implemented.
- Blocks: Core trading, LLM integration, UI
- Priority: Critical for MVP — these are next phases.

## Known Issues & Limitations

### Market Data

**Simulator ticker universe is closed and hardcoded:**

- Issue: `SimulatorMarketDataSource.is_valid_ticker()` checks membership in `TICKER_UNIVERSE` dict. Only the 30 hardcoded tickers (PLAN.md §6 specifies ~20-30) can be added to the watchlist; any other ticker is rejected.
- Files: `backend/app/market/simulator.py` (lines 37-68, 119-120)
- Impact: Feature completeness — users cannot add arbitrary tickers. This is by design (PLAN.md §8 "rejected with an error rather than silently accepted"), not a bug, but limits extensibility.
- Workaround: Add more tickers to `TICKER_UNIVERSE` if needed. This is a data-driven design choice, not a code defect.

**Massive API rate limit 403 not fully handled:**

- Issue: 403 responses are logged as an error with advice to check the key/plan (line 78-81), but the backend does not automatically fall back to the simulator. If Massive is configured but the key lacks entitlements, all price data silently fails.
- Files: `backend/app/market/massive.py` (lines 77-82)
- Impact: In production, a plan downgrade or entitlement loss would break the live feed with no automatic recovery. The app would silently serve stale prices.
- Mitigation: Add a fallback mechanism or explicit alerting. For current demo scale, acceptable as a limitation.
- Fix approach: Add a fallback data source or circuit breaker that switches back to simulator on persistent 403s.

**Massive API does not implement backoff for rate limits:**

- Issue: `get_prices()` returns empty dict on 429, relying on the poll interval (15s free tier) to avoid re-hammering immediately. But there's no adaptive backoff if the rate limit is persistent.
- Files: `backend/app/market/massive.py` (lines 70-76)
- Impact: If multiple API calls from other services hit the same tier, the app may stay rate-limited. Not a crash, but quality of service degrades.
- Fix approach: Implement exponential backoff or a circuit breaker for 429 responses.

### Concurrency & Synchronization

**PriceCache lock contention in high-concurrency scenarios:**

- Issue: All SSE connections and the update loop contend for a single asyncio.Lock in `PriceCache`.
- Files: `backend/app/market/cache.py` (lines 21, 30)
- Impact: At thousands of concurrent SSE clients, the lock becomes a bottleneck. However, for single-user demo, this is a non-issue. The lock is correctly placed and small; operations are fast.
- Scaling path: Partition cache by ticker, use read-write locks, or switch to a lock-free data structure if concurrency becomes a concern.
- Current risk: Low — acceptable for current scope.

**SSE stream generator has no keepalive or heartbeat:**

- Issue: The SSE endpoint broadcasts all tickers every 500ms (line 41 in `stream.py`). If the price cache is empty, clients receive empty tick lists. There's no explicit keepalive comment (e.g., `:` heartbeat) if the price stream stalls.
- Files: `backend/app/routes/stream.py` (lines 34-41)
- Impact: If the market data loop crashes, SSE clients may not notice for a long time (they continue receiving the last-known prices). A heartbeat comment every 5-10s would increase observability.
- Fix approach: Add an optional `:` keepalive comment every N seconds, or add a "status" event type.

**No explicit error handling for app.state access:**

- Issue: `stream.py` line 46 and other routes directly access `request.app.state.price_cache` and `request.app.state.market_source` without checking if they exist. If lifespan setup fails or a route is hit before startup, a 500 error occurs.
- Files: `backend/app/routes/stream.py` (line 46)
- Impact: Unlikely in normal operation, but fragile if startup logic changes. A missing state attribute results in an AttributeError.
- Fix approach: Add an assertion or defensive check with a clear error message.

## Error Handling Gaps

### Broad Exception Catching

**Market data loop catches all Exceptions:**

- Issue: `run_update_loop()` has a bare `except Exception:` block (line 36 in `loop.py`).
- Files: `backend/app/market/loop.py` (line 36)
- Impact: Hides unexpected errors (e.g., programming bugs) behind "market data update loop iteration failed" logs. Makes debugging harder.
- Fix approach: Catch specific exceptions (e.g., `asyncio.TimeoutError`, `ValueError`) and re-raise or escalate unexpected errors. At minimum, log a stack trace.

**Massive API error logging is verbose but not structured:**

- Issue: Various error conditions are logged as warnings or errors, but there's no structured logging (no JSON logs or tags for aggregation).
- Files: `backend/app/market/massive.py` (lines 59-86)
- Impact: Works for dev/debugging; harder to parse in production log aggregation systems.
- Fix approach: Use structured logging (e.g., `python-json-logger`) if production use is expected.

## Test Coverage Concerns

### E2E Testing Missing

**No Playwright E2E tests implemented:**

- Issue: `test/` directory exists (per PLAN.md §12) but is empty. No `docker-compose.test.yml` or E2E test files.
- Files: `test/` is empty
- Impact: No automated testing of the full request→SSE→price cache→response flow. No verification that the Docker container runs correctly.
- Blocks: Deployment confidence, CI/CD
- Priority: Medium — E2E tests are a "nice-to-have" for demo scale, but essential for production.

**No integration tests of database + routes:**

- Issue: Unit tests cover simulator, Massive client, and cache in isolation. No tests for the full stack: watchlist read, cache update, SSE serialization, etc.
- Files: `backend/tests/routes/test_stream.py` (exists but likely minimal)
- Impact: Bugs can hide in integration seams. For example, if watchlist query returns zero tickers, the update loop silently skips — but no test verifies the SSE stream handles this gracefully.
- Fix approach: Add integration tests that spin up a real app, hit endpoints, verify SSE output.

**No frontend tests:**

- Issue: Frontend doesn't exist yet, but when it does, there will be zero test fixtures.
- Impact: Future work will need to establish testing patterns from scratch.
- Fix approach: Plan React/Next.js test setup (React Testing Library, Playwright) as part of frontend implementation.

### Unit Test Gaps

**No tests for SSE stream disconnection recovery:**

- Issue: `test_stream.py` likely doesn't test what happens if a client disconnects mid-stream or if the price cache is empty.
- Files: `backend/tests/routes/test_stream.py`
- Impact: Edge cases like "client disconnects then reconnects" are untested.
- Fix approach: Add tests for request.is_disconnected() behavior and empty cache scenarios.

**No race condition tests for concurrent watchlist reads:**

- Issue: No test exercises multiple concurrent `get_watchlist_tickers()` calls.
- Impact: A race bug in concurrent reads would go undetected.
- Fix approach: Add a pytest fixture that spins up multiple async tasks calling watchlist methods concurrently.

**Simulator tests use monkeypatch on module-level path:**

- Issue: Tests modify `app.db.watchlist.DB_PATH` via monkeypatch (see `test_main.py`). This is fragile if the module organization changes.
- Files: `backend/tests/test_main.py` (line 12)
- Impact: Low risk, but refactoring the watchlist module could break tests.
- Fix approach: Use a dependency injection pattern or factory with a config object instead.

## Security Considerations

### No Authentication or Authorization

**API endpoints have no authentication:**

- Issue: All endpoints (`/api/stream/prices`, `/api/health`, future `/api/portfolio`, `/api/chat`) are public and unauthenticated.
- Files: All routes
- Impact: In single-user demo mode, this is fine. In production multi-user, the entire portfolio and chat history of all users would be accessible to anyone.
- Mitigation: PLAN.md specifies single-user ("default") for now. Multi-user auth is a future phase.
- For production: Add JWT or session-based auth, user isolation on all queries.

**No rate limiting:**

- Issue: No rate limit middleware on any endpoint.
- Files: All routes
- Impact: A malicious client could flood the server with requests, causing DoS. SSE connection accumulation could exhaust resources.
- Mitigation: For demo scale, acceptable. Add rate limiting (e.g., `slowapi`) before production release.

**API key exposure risk:**

- Issue: The Massive API key is read from the environment and passed to the `MassiveMarketDataSource` class. If a secrets leak occurs (e.g., in logs or error messages), the key is compromised.
- Files: `backend/app/market/factory.py` (line 15)
- Impact: If the key is exposed, an attacker can use the Massive API quota.
- Mitigation: Never log the key (currently compliant — key is not logged). Mark as secrets in error messages (currently compliant — errors refer to key generically).

**SQLite database file is gitignored but could be committed accidentally:**

- Issue: `.gitignore` should exclude `db/finally.db`, but if the rule is misconfigured, a production database dump could end up in git.
- Files: Check `.gitignore`
- Impact: Potential data leak if trading histories or user balances are ever sensitive.
- Mitigation: `.gitignore` should have a rule for `db/` or `db/finally.db`. Verify this is in place.

## Performance Bottlenecks

### Market Data

**GBM simulator re-computes sector factors every tick:**

- Issue: `_advance_all()` (line 99-114 in `simulator.py`) recomputes sector factors for each of 30 tickers every 500ms.
- Files: `backend/app/market/simulator.py` (lines 98-114)
- Impact: Negligible for 30 tickers; non-issue. If ticker universe grows to thousands, this becomes a hotspot.
- Optimization path: Pre-compute sector factors once per tick, reuse across all tickers in that sector.

**Watchlist query on every market update loop cycle:**

- Issue: `run_update_loop()` calls `get_watchlist_tickers()` every cycle (every 500ms for simulator, every 15s for Massive). This queries the database every cycle.
- Files: `backend/app/market/loop.py` (line 31)
- Impact: For single user with 10 tickers, negligible. For multi-user with thousands of watchlists, database load spikes.
- Optimization path: Cache watchlist in memory and invalidate on mutation, rather than querying every cycle.

### API Layer

**No caching of portfolio calculations:**

- Issue: When the portfolio endpoint is implemented, it will recompute P&L on every request. With frequent requests or large positions, this could be slow.
- Files: Not yet implemented; `backend/app/portfolio/` is empty
- Impact: High request volume → high CPU. Acceptable for demo.
- Mitigation: Cache portfolio snapshots and invalidate only on trades or price updates.

## Fragile Areas

### Watchlist Initialization

**Files: `backend/app/db/watchlist.py`, specifically:**

- DB_PATH computation is fragile: assumes the module is at `backend/app/db/watchlist.py` and uses `parents[3]` to reach the repo root (line 30).
- If the code is reorganized, the path breaks silently, defaulting to a wrong location.
- Risk: Initialization creates the DB in an unexpected location or fails.
- Safe modification: Add a test that verifies DB_PATH is computed correctly in the expected layout.

**Seed data is hardcoded:**

- Issue: DEFAULT_WATCHLIST is imported from `market.simulator.py` (line 24).
- If the simulator is not used, there's a hard dependency on simulator module just to seed the watchlist.
- Risk: If simulator ever becomes optional, this import breaks.
- Fix approach: Move DEFAULT_WATCHLIST to `backend/app/schema/` or a config module, not the simulator.

### Event Serialization

**No version control on SSE event schema:**

- Issue: The SSE event format (`_serialize_tick` in `stream.py`) is hardcoded. If the schema changes (e.g., adding a field), old frontend clients break.
- Files: `backend/app/routes/stream.py` (lines 24-31)
- Impact: Frontend backward compatibility issues during updates.
- Fix approach: Add a schema version field to SSE events or use a HATEOAS-style versioned API.

### Async Cleanup

**Market data source stop() is not awaited on exception:**

- Issue: If lifespan encounters an exception during setup, the finally block still tries to cancel the update_task and stop the source. If startup fails partway, the source might not be started yet, so stop() might be called in an inconsistent state.
- Files: `backend/app/main.py` (lines 48-49)
- Impact: Unlikely but possible edge case. The Massive client's stop() is idempotent (checks if _client is None), so it's safe. But risky pattern.
- Fix approach: Wrap setup logic in try/except and only cleanup what was successfully started.

## Missing Critical Features

### Incomplete PLAN.md Implementation

**Database schema incomplete:**

- PLAN.md §7 specifies six tables: `users_profile`, `watchlist`, `positions`, `trades`, `portfolio_snapshots`, `chat_messages`.
- Currently implemented: Only `watchlist` table exists (partially; read-only).
- Missing: `users_profile`, `positions`, `trades`, `portfolio_snapshots`, `chat_messages` tables and all related queries.
- Files: `backend/app/schema/` directory doesn't exist; schema is inline in `watchlist.py`.
- Impact: Portfolio feature cannot be built without these tables.
- Priority: Critical for MVP.

**API endpoints incomplete:**

- PLAN.md §8 lists 11 endpoints. Currently implemented: 1 (`GET /api/health`) and partial (`GET /api/stream/prices` is core, but payload validation missing).
- Missing: All portfolio endpoints, all watchlist mutation endpoints, all chat endpoints.
- Files: Empty route modules in `backend/app/portfolio/`, `backend/app/llm/`, `backend/app/watchlist/`.
- Impact: No trading, no chat, no portfolio management.
- Priority: Critical for MVP.

**LLM integration missing:**

- PLAN.md §9 specifies structured outputs via LiteLLM → OpenRouter. No code implements this.
- Files: `backend/app/llm/` is empty
- Impact: Chat feature cannot function.
- Priority: Critical for MVP.

## Logging & Observability

**No structured logging:**

- Issue: All logging uses Python's standard `logging` module with default formatters. No JSON, no correlation IDs, no structured fields.
- Files: All modules that import `logging`
- Impact: Logs are readable for dev/debugging but hard to parse in production aggregation systems.
- Fix approach: Adopt a structured logging library (e.g., `structlog`, `python-json-logger`) as a stretch goal.

**No request tracing:**

- Issue: No correlation ID or request ID is attached to logs. If a single user action spawns multiple internal requests, tracing the chain is manual.
- Impact: Debugging production issues is harder.
- Fix approach: Add middleware to inject correlation IDs into all log records.

**Market data errors not monitored:**

- Issue: The update loop logs exceptions but there's no alerting mechanism. If Massive API goes down, the team won't know unless they check logs.
- Impact: Quality of service issues are reactive, not proactive.
- Fix approach: Integrate with a monitoring/alerting service (e.g., Sentry, DataDog) as a stretch goal.

## Dependency & Compatibility Concerns

### Python Version Lock

**Requires Python >=3.12:**

- Issue: `pyproject.toml` specifies `requires-python = ">=3.12"`.
- Impact: Not deployable on systems with Python <3.12. This is a deliberate choice (modern async/await features) and reasonable for 2026.
- Mitigation: Docker will pin Python 3.12; no issue for containerized deployment.

### Third-Party Dependency Risks

**httpx 0.27+ for Massive client:**

- Issue: `httpx>=0.27` is a relatively recent constraint. If Massive API changes the endpoint URL or auth scheme, the client may break.
- Files: `backend/app/market/massive.py`
- Impact: Low risk — Massive's API is stable, but worth monitoring release notes.
- Mitigation: Pin specific version in `pyproject.toml` (currently uses `>=0.27`, which is broad).

**FastAPI 0.115+ for app framework:**

- Issue: FastAPI is under active development. The `>=0.115` constraint allows updates that might introduce breaking changes.
- Files: `backend/pyproject.toml` (line 7)
- Impact: Deployment via `uv sync` might pull a newer version with incompatibilities.
- Mitigation: Use a tighter version constraint (e.g., `>=0.115,<0.116`) once the app is stable.

## Unfinished Deployment Setup

**Docker and container orchestration missing:**

- Issue: No `Dockerfile`, `docker-compose.yml`, or `docker-compose.test.yml`.
- Files: Should exist per PLAN.md §11
- Impact: Cannot run or test the app as a Docker container. The entire deployment model is unimplemented.
- Priority: Critical for the "single Docker command" vision.
- Fix approach: Implement the multi-stage Dockerfile and helper scripts per PLAN.md §11.

**Start/stop scripts missing:**

- Issue: `scripts/start_mac.sh`, `scripts/stop_mac.sh`, `scripts/start_windows.ps1`, `scripts/stop_windows.ps1` don't exist.
- Files: `scripts/` directory (if it exists) is empty or missing
- Impact: Users cannot easily start/stop the app without manual Docker commands.
- Priority: High for usability.

**Volume mount path not tested:**

- Issue: The app expects to mount a volume at `/app/db` and write `finally.db` there. This has never been tested in Docker.
- Impact: When Docker build is implemented, the mount might not work, breaking persistence.
- Fix approach: Test the Docker setup with actual volume mounts.

---

*Concerns audit: 2026-09-15*
