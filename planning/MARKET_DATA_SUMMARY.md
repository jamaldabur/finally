# MARKET_DATA_SUMMARY.md — Market Data Component Status

A snapshot of what exists today in `backend/app/market/` and its supporting
pieces (`app/db/watchlist.py`, `app/routes/`, `app/main.py`), what's tested,
and what's still missing before the component is a fully usable feature.
Design rationale lives in the archived docs (`MARKET_INTERFACE.md`,
`MARKET_SIMULATOR.md`, `MASSIVE_API.md`, `MARKET_DATA_DESIGN.md`); this
document is the current-state summary, not the design spec.

---

## 1. What It Is

The market data component is FinAlly's price feed: one abstract
`MarketDataSource` interface with two implementations (a built-in GBM
simulator, and an optional Massive/Polygon.io REST client), a shared
in-memory cache that tracks "previous price" and up/down/unchanged direction
per ticker, a background task that keeps the cache fresh, and an SSE HTTP
endpoint that streams the cache's contents to any connected client.

## 2. What's Implemented

### Core engine (`app/market/`)
- **`base.py`** — the `MarketDataSource` ABC (`start`, `stop`, `get_prices`,
  `is_valid_ticker`), plus `PriceTick` and `ChangeDirection`.
- **`cache.py`** — `PriceCache`, the single source of truth for "previous
  price"/direction. Correctly carries the last *different* price forward
  across unchanged heartbeats, so the frontend's flash animation won't
  re-trigger on a no-op tick.
- **`simulator.py`** — the default source. ~30-ticker universe (10 seeded on
  the default watchlist, 20 more addable), geometric Brownian motion with
  per-sector correlated moves and occasional random 2-5% "events." No
  network dependency.
- **`massive.py`** — the optional Massive REST client, active whenever
  `MASSIVE_API_KEY` is set. Never raises: rate limits (429), entitlement
  gaps (403), malformed responses, and transient network errors all degrade
  to "no update this cycle" rather than crashing anything.
- **`factory.py`** — `build_market_data_source()`, the one place that reads
  `MASSIVE_API_KEY` to pick an implementation.
- **`loop.py`** — `run_update_loop()`, the background task that polls/ticks
  the active source into the cache on a fixed interval (0.5s simulator, 15s
  Massive free tier), wrapped in its own try/except so a bug in either
  source can't silently kill price updates for the rest of the session.

### Persistence (`app/db/watchlist.py`)
- Lazily initializes a `watchlist` SQLite table and seeds the 10 default
  tickers on first use — no separate migration step.
- `get_watchlist_tickers()` is what `run_update_loop` reads each cycle to
  know what to fetch.
- **Read-only for now** — there's no `add_ticker`/`remove_ticker` yet (see
  §3 Gaps).

### HTTP surface (`app/main.py`, `app/routes/`)
- **`app/main.py`** — `create_app()` factory wires everything together: on
  startup, initializes the DB, builds the market data source, starts it,
  and launches the background update loop; on shutdown, cancels the loop
  and stops the source. `app = create_app()` is what Uvicorn serves.
- **`GET /api/stream/prices`** (`routes/stream.py`) — the SSE endpoint. One
  event per ~500ms broadcast tick, containing the full array of currently
  tracked tickers (`{"ticks": [...]}`), each with `ticker`, `price`,
  `previous_price`, `timestamp`, and `direction`.
- **`GET /api/health`** (`routes/health.py`) — trivial liveness check.

Verified end-to-end with a real running server (not just mocked tests):
`uv run uvicorn app.main:app` seeds the DB, starts streaming real simulated
prices for the 10 default tickers, and `GET /api/health` responds
`{"status": "ok"}`.

### Demo & tests
- **`scripts/demo_simulator.py`** — live Rich terminal table driven through
  the same `PriceCache`/`run_update_loop` path as the real app.
- **73 passing tests** (`uv run pytest`) covering: cache semantics
  (including the previous-price-carries-forward edge case), GBM math and
  sector correlation, ticker-universe validation, Massive error handling
  (rate limits, entitlement errors, malformed JSON, retry/backoff),
  cross-implementation interface conformance, the update loop's resilience
  to a source or DB failure, watchlist DB seeding/idempotency, and the SSE
  generator/route (tested by driving the generator directly with a fake
  request rather than through a live streaming HTTP client — Starlette's
  `TestClient` doesn't reliably signal ASGI disconnect back to a
  deliberately-infinite generator, so that path is exercised at the
  function level instead of through a full streaming round-trip).

## 3. Gaps — Not Yet Built

- **No watchlist mutation.** `POST /api/watchlist` and
  `DELETE /api/watchlist/{ticker}` don't exist. The DB layer only supports
  reading the current watchlist; there's no validated add/remove path yet
  (`MARKET_DATA_DESIGN.md` §10.1 specifies the intended service functions,
  built on `MarketDataSource.is_valid_ticker`, but they aren't implemented).
- **No trade integration.** The fill-price lookup against `PriceCache`
  (`MARKET_DATA_DESIGN.md` §10.2) isn't implemented — there's no portfolio
  or trade module at all yet.
- **No `GET /api/watchlist`.** Nothing currently exposes the watchlist (with
  live prices) as a REST resource; it's only consumed internally by the
  update loop.
- **DB is watchlist-only.** `users_profile`, `positions`, `trades`,
  `portfolio_snapshots`, and `chat_messages` (`PLAN.md` §7) don't exist —
  out of scope for the market data component specifically, but worth noting
  since `app/db/watchlist.py` will likely need to become part of a larger
  DB module once those land.
- **No Dockerfile / production wiring.** Runs today via `uv run uvicorn`
  only; the container build, static frontend serving, and volume mount
  (`PLAN.md` §11) haven't been built.
- **No frontend.** Nothing yet consumes `/api/stream/prices` from a browser
  — it's been validated with `curl` and the terminal demo only.

## 4. How to Run It Today

```bash
cd backend
uv sync
uv run uvicorn app.main:app --port 8000    # real server, simulator by default
curl http://127.0.0.1:8000/api/health
curl -N http://127.0.0.1:8000/api/stream/prices   # -N: don't buffer, see it stream

uv run scripts/demo_simulator.py           # terminal UI instead of curl
uv run pytest                              # 73 tests
```

Set `MASSIVE_API_KEY` in the environment to switch to real market data
(subject to the plan-tier caveats in the archived `MASSIVE_API.md`).
`FINALLY_DB_PATH` overrides the default `db/finally.db` location if needed.

## 5. Bottom Line

The market data *engine* (interface, simulator, Massive client, cache,
background loop) and its *HTTP delivery* (FastAPI app, SSE endpoint, health
check) are both complete, tested, and verified working end-to-end. What's
missing is everything one layer up: watchlist CRUD, trade execution, the
rest of the schema, and the frontend that would actually consume any of
this. As a standalone component, market data is done; as a feature of the
full FinAlly app, it's the one finished pillar among several not yet
started.
