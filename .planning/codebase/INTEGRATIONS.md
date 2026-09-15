---
last_mapped_commit: 20fd6385728d5909231f6772c7abc2d5c3111cb7
last_mapped_at: 2026-09-15
---
# External Integrations

**Analysis Date:** 2026-09-15

## APIs & External Services

**Market Data (Polygon.io / Massive):**

- **Massive REST API** — Optional real-time market data provider
  - Base URL: `https://api.massive.com`
  - Endpoint: `/v2/snapshot/locale/us/markets/stocks/tickers`
  - Method: REST (no WebSocket) with bearer token auth
  - Client library: `httpx` (async HTTP client)
  - Environment variable: `MASSIVE_API_KEY`
  - Polling interval: 15 seconds (free tier), 2-15 seconds (paid tiers)
  - Fallback: Built-in market simulator (GBM) if key not provided
  - Error handling: Graceful degradation on rate limits (429), entitlement errors (403), malformed responses — logs and skips cycle rather than crashing
  - Implemented in: `backend/app/market/massive.py`

**LLM / AI Assistant (Not yet implemented):**

- **OpenRouter** — LLM provider gateway
  - Provider: `openrouter/openai/gpt-oss-120b` (per PLAN.md §9)
  - Integration method: LiteLLM (abstraction layer — not yet in dependencies)
  - Environment variable: `OPENROUTER_API_KEY`
  - Planned usage: Chat endpoint (`POST /api/chat`) for portfolio analysis and trade execution
  - Request format: Structured JSON with system prompt, portfolio context, conversation history
  - Response format: Structured JSON with `message`, `trades[]`, `watchlist_changes[]`
  - Status: Infrastructure planned in PLAN.md, no code yet

## Data Storage

**Databases:**

- **SQLite** — Single-file relational database
  - Location: `db/finally.db` (volume-mounted in Docker)
  - Connection: Python built-in `sqlite3` module
  - No external server required
  - Lazy initialization: Tables created on first request if not present
  - Persistence: Docker named volume `finally-data` (production)

**File Storage:**

- None — All data in SQLite; no file uploads or cloud storage

**Caching:**

- **In-memory only** — `PriceCache` class in `backend/app/market/cache.py`
- Single instance per process, stored in `app.state.price_cache`
- Holds latest price, previous price, and direction for each ticker
- No distributed cache, no Redis, no memcached

## Authentication & Identity

**Auth Provider:**

- None — Single-user model with hardcoded `user_id="default"`
- No login, no signup, no session management
- All portfolio/watchlist data belongs to the default user
- Future multi-user support planned but not implemented (per PLAN.md §7)

**Environment Authentication:**

- `OPENROUTER_API_KEY` — Bearer token for LLM service (not yet used)
- `MASSIVE_API_KEY` — Bearer token for Massive API (`Authorization: Bearer {key}` header)

## Monitoring & Observability

**Error Tracking:**

- None — No Sentry, no third-party error monitoring
- Errors logged via Python `logging` module to stderr

**Logs:**

- Python standard `logging` module (no external logging service)
- Async-safe logging in market data components
- Example: `logger.getLogger(__name__)` in `massive.py`, `loop.py`

**Health Check:**

- `GET /api/health` — Returns `{"status": "ok"}`
- No external health monitoring service

## CI/CD & Deployment

**Hosting:**

- Docker container (single image)
- Port: 8000 (FastAPI + static frontend serving)
- Platform: Any container runtime (AWS App Runner, Render, Heroku, self-hosted, local Docker)

**CI Pipeline:**

- Not visible in current codebase
- No `.github/workflows/` for automated builds detected
- Scripts exist: `scripts/start_mac.sh`, `scripts/stop_mac.sh` (for manual local deployment)

**Deployment Artifacts:**

- Dockerfile (planned but not yet created — per PLAN.md §11)
- `docker-compose.yml` (optional convenience wrapper — not yet created)
- `docker-compose.test.yml` (for E2E tests in Playwright — not yet created)

## Environment Configuration

**Required Environment Variables:**

- `OPENROUTER_API_KEY` — LLM API key (required for chat feature, not yet used in code)

**Optional Environment Variables:**

- `MASSIVE_API_KEY` — Polygon.io API key for real market data (simulator used if absent)
- `LLM_MOCK` — Set to `"true"` for deterministic mock LLM responses (for testing)
- `FINALLY_DB_PATH` — Custom SQLite database file location (default: `<repo-root>/db/finally.db`)

**Secrets Location:**

- `.env` file (gitignored) — Development and production secrets
- `.env.example` (planned) — Template with required keys (not yet in repo)
- Docker: `--env-file .env` flag at runtime, or secrets injected via platform (AWS Secrets Manager, etc.)

## Webhooks & Callbacks

**Incoming:**

- None — API is REST/SSE, no webhook endpoints

**Outgoing:**

- None — No webhooks sent to external services
- Future: Chat actions (trades, watchlist changes) are auto-executed locally, not sent externally

## API Endpoints (Current)

**Market Data Stream:**

- `GET /api/stream/prices` — Server-Sent Events (SSE) stream of ticker prices
  - Connection: Long-lived, maintained by browser's `EventSource` API
  - Response format: JSON with `ticks: [{ticker, price, previous_price, timestamp, direction}]`
  - Broadcast interval: ~500ms
  - Implementation: `backend/app/routes/stream.py`

**Health Check:**

- `GET /api/health` — Liveness check for Docker/Kubernetes
  - Response: `{"status": "ok"}`
  - Implementation: `backend/app/routes/health.py`

**Planned API Endpoints (Not Yet Built):**

- `GET /api/portfolio` — Current positions, cash, P&L
- `POST /api/portfolio/trade` — Execute buy/sell order
- `GET /api/portfolio/history` — Portfolio snapshots for P&L chart
- `GET /api/watchlist` — Current watched tickers with live prices
- `POST /api/watchlist` — Add ticker (validated against `MarketDataSource.is_valid_ticker()`)
- `DELETE /api/watchlist/{ticker}` — Remove ticker
- `GET /api/chat` — Conversation history
- `POST /api/chat` — Send message, auto-execute trades/watchlist changes

## Data Flow

**Market Data Integration:**

1. Backend startup → `factory.build_market_data_source()` checks `MASSIVE_API_KEY`
2. If set → `MassiveMarketDataSource` created; if not → `SimulatorMarketDataSource` created
3. Background task `run_update_loop()` polls/ticks source on interval (15s Massive free tier, 0.5s simulator)
4. Results written to `PriceCache` (in-memory)
5. SSE endpoint reads from cache, broadcasts to connected clients every ~500ms
6. Implementation files:
   - `backend/app/market/factory.py` — Selection logic
   - `backend/app/market/massive.py` — Massive client (REST polling)
   - `backend/app/market/simulator.py` — GBM simulator
   - `backend/app/market/cache.py` — Price cache
   - `backend/app/market/loop.py` — Update loop
   - `backend/app/routes/stream.py` — SSE endpoint

**LLM Integration (Planned):**

1. User sends chat message to `POST /api/chat`
2. Backend loads portfolio context, chat history from database
3. Constructs prompt with system message, context, conversation history
4. Calls LiteLLM → OpenRouter (`openrouter/openai/gpt-oss-120b`)
5. LiteLLM receives structured output schema (trades, watchlist_changes, message)
6. Backend validates and executes trades/watchlist changes
7. Stores message + annotated outcomes in `chat_messages` table
8. Returns complete JSON response to frontend
9. Implementation: `backend/app/llm/` (not yet implemented)

## Testing Integrations

**Market Data Testing:**

- `respx` mock library mocks HTTP requests to Massive API
- Tests verify rate limit handling (429), entitlement errors (403), malformed responses, retry/backoff
- Simulator tests verify GBM math, sector correlation, ticker universe validation
- Implementation: `backend/tests/test_market_*.py` (73 passing tests)

**Database Testing:**

- SQLite in-memory database for unit tests (not using mocks)
- Watchlist schema creation and seed data tested
- Implementation: `backend/tests/test_db_*.py`

**E2E Testing (Planned):**

- Playwright in separate Docker container (`test/docker-compose.test.yml`)
- LLM_MOCK=true for deterministic responses
- Test scenarios: watchlist CRUD, trading, portfolio display, SSE resilience
- Implementation: `test/` (not yet implemented)

## Security Considerations

**Secrets Management:**

- `.env` file excluded from git (per `.gitignore`)
- API keys (`OPENROUTER_API_KEY`, `MASSIVE_API_KEY`) stored in environment only
- SQLite database contains no sensitive data (prices, trades, watchlist only)

**No External Threats:**

- Single-user model — no authentication bypass risk
- Market simulator has no network dependency
- Massive API errors degrade gracefully, never crash
- No user input validation issues yet (simple API surface)

**Future Considerations:**

- LLM integration (`POST /api/chat`) should validate user input and sandbox trade execution
- SQLite file permissions in Docker volume should restrict access
- No HTTPS enforcement yet (single-container localhost by default)

---

*Integration audit: 2026-09-15*
