---
last_mapped_commit: 20fd6385728d5909231f6772c7abc2d5c3111cb7
last_mapped_at: 2026-09-15
---
# Technology Stack

**Analysis Date:** 2026-09-15

## Languages

**Primary:**

- Python 3.12 — Backend API, market data simulation, database operations
- TypeScript (planned) — Frontend UI (Next.js) — not yet implemented

## Runtime

**Environment:**

- Python 3.12.12 (async-first)
- Node.js 20 (planned for frontend — not yet implemented)

**Package Manager:**

- `uv` 0.x — Python dependency manager, produces lockfile (`uv.lock`)
- `npm` (planned) — Frontend dependency manager for Next.js

**Lockfiles:**

- `backend/uv.lock` — Production and development Python dependencies locked
- `package.json` (planned) — Frontend dependencies

## Frameworks

**Core:**

- FastAPI 0.141.1 — REST API, SSE streaming, application lifecycle management
  - Built on Starlette 0.37.x for ASGI
  - Pydantic for request/response validation

**Frontend (Planned):**

- Next.js (planned) — Static export build for deployment with FastAPI
  - Tailwind CSS for styling (per PLAN.md)
  - Canvas-based charting library (Lightweight Charts or Recharts planned)

**Testing:**

- pytest 8.0+ — Python unit test runner
- pytest-asyncio 0.24+ — Async test support for FastAPI
- respx 0.21+ — Mock HTTP client for market data API testing
- Playwright (planned) — E2E browser testing in `test/docker-compose.test.yml`

**Development/Utilities:**

- rich 13.0+ — Terminal UI library (used in `scripts/demo_simulator.py`)
- uvicorn 0.30+ (with standard extras) — ASGI server for FastAPI

## Key Dependencies

**Critical (Direct):**

- `fastapi >= 0.115` — Web framework, handles HTTP routing, SSE, app lifespan
- `httpx >= 0.27` — Async HTTP client for Massive API polling
- `uvicorn[standard] >= 0.30` — ASGI server with uvloop and watchfiles
- `pydantic` — Data validation via FastAPI, used for structured outputs (planned for LLM integration)

**Runtime (Transitive):**

- `starlette` — ASGI toolkit underlying FastAPI
- `typing-extensions` — Type hints backports
- `annotated-doc` — Annotations support for FastAPI
- `typing-inspection` — Runtime type introspection
- `anyio` — Async abstraction layer
- `certifi` — SSL/TLS certificates
- `uvloop` — High-performance event loop (via uvicorn[standard])
- `httpcore` — Low-level HTTP transport
- `pydantic-core` — Pydantic's C extension

**Development (Direct):**

- `pytest` — Test framework
- `pytest-asyncio` — Pytest plugin for async tests
- `respx` — HTTP mock client for testing
- `rich` — Terminal formatting and tables
- `python-dotenv` — Load environment variables from `.env` file

## Configuration

**Environment Variables:**

- `OPENROUTER_API_KEY` — LiteLLM authentication key for LLM integration (required for chat, not yet used)
- `MASSIVE_API_KEY` — Polygon.io/Massive API key for real market data (optional; simulator used if absent)
- `LLM_MOCK` — Set to `"true"` for deterministic mock LLM responses in testing
- `FINALLY_DB_PATH` — SQLite database file path (default: `<repo-root>/db/finally.db`)

**Python Configuration:**

- `pyproject.toml` — Project metadata, dependencies, build system, pytest configuration
- `pytest.ini_options` — asyncio_mode: auto, testpaths: tests, pythonpath: ["."]

**Build System:**

- Hatchling — Python build backend

## Platform Requirements

**Development:**

- Python 3.12+
- `uv` package manager
- Git
- Bash (for `scripts/start_mac.sh`, `scripts/stop_mac.sh`) or PowerShell (for Windows scripts)

**Runtime:**

- Docker (recommended for production)
- Docker volume for SQLite persistence (`db/` mount point)
- Port 8000 (single container, single port per PLAN.md §3)

**Production/Deployment:**

- Docker container with:
  - Node 20 (for static Next.js export build)
  - Python 3.12 (for FastAPI runtime)
- SQLite database (zero external DB dependencies)
- Environment variables passed via `--env-file .env`

## Architecture Overview

```
Backend (Python/FastAPI) — Single container, port 8000
├── Market Data Layer
│   ├── SimulatorMarketDataSource (default)
│   └── MassiveMarketDataSource (optional, REST polling)
├── Database Layer
│   └── SQLite (watchlist schema, future: portfolio/trades/chat)
├── HTTP Routes
│   ├── GET /api/stream/prices (SSE)
│   ├── GET /api/health (liveness)
│   └── (portfolio, trades, chat routes — not yet built)
└── Background Tasks
    └── PriceCache update loop (0.5s simulator, 15s Massive free tier)

Frontend (Next.js) — Not yet built
├── Static export (no Node at runtime)
├── SSE client for /api/stream/prices
└── Served as static files by FastAPI
```

## Database

**SQLite (self-contained, no external server):**

- File: `db/finally.db` (volume-mounted in Docker)
- Lazy initialization on first request — schema created automatically
- Single user model (no authentication)
- `user_id` column reserved for future multi-user support

**Current Schema:**

- `watchlist` — Tickers user is watching (implemented)
- (Planned) `users_profile`, `positions`, `trades`, `portfolio_snapshots`, `chat_messages`

## External SDK/Services (Planned/Used)

**Market Data:**

- Massive REST API (`api.massive.com/v2/snapshot/...`) — Optional, polled via `httpx`
- No WebSocket or dedicated SDK — plain HTTP REST

**LLM Integration (Not yet implemented):**

- LiteLLM (planned dependency) — Abstraction layer over LLM providers
- OpenRouter API — LLM provider (model: `openrouter/openai/gpt-oss-120b`)
- No real code yet; infrastructure scaffolded only

**No external services for:**

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

---

*Stack analysis: 2026-09-15*
