# FinAlly Backend

FastAPI backend for FinAlly, managed as a `uv` project.

## Market Data (`app/market/`)

Implements `planning/MARKET_DATA_DESIGN.md`: one abstract `MarketDataSource`
interface (`base.py`) with two implementations selected at startup by the
`MASSIVE_API_KEY` environment variable (`factory.py`):

- **`simulator.py`** — the default, dependency-free market data source. Generates
  prices for a fixed ~30-ticker universe using geometric Brownian motion, with
  correlated per-sector moves and occasional random "events."
- **`massive.py`** — polls the Massive (formerly Polygon.io) REST API for
  real market data when `MASSIVE_API_KEY` is set. Degrades gracefully (never
  raises) on rate limits, entitlement gaps, or transient network errors.
- **`cache.py`** — the shared in-memory `PriceCache` that both implementations
  feed into via `loop.py`'s `run_update_loop`; this is what the SSE stream and
  trade fill-price lookups read from.

Only these two implementations should ever be imported by the rest of the
backend — everything else should code against `MarketDataSource`.

## Development

```bash
cd backend
uv sync                 # install dependencies (including dev group)
uv run pytest           # run the full test suite
```

Tests live in `tests/`, mirroring the `app/` package layout. `tests/market/`
covers the price cache, the simulator (GBM correctness, sector correlation,
ticker-universe membership), the Massive client (mocked via `respx`, including
rate-limit/error/retry handling), the startup factory, the update loop, and
cross-implementation interface conformance.
