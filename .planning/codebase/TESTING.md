---
last_mapped_commit: 20fd6385728d5909231f6772c7abc2d5c3111cb7
last_mapped_at: 2026-09-15
---
# Testing Patterns

**Analysis Date:** 2026-09-15

## Test Framework

**Runner:**

- pytest 8.0+
- Config: `backend/pyproject.toml` (see `[tool.pytest.ini_options]`)

**Async Support:**

- pytest-asyncio 0.24+
- Mode: `asyncio_mode = "auto"` — automatically detects and runs async tests
- Mark: `@pytest.mark.asyncio` on all async test functions

**Assertion Library:**

- pytest built-in (`assert` statements)
- Special: `pytest.approx()` for floating-point comparisons (e.g., GBM math)

**HTTP Mocking:**

- respx 0.21+ — mocks httpx requests without hitting real network
- Used for `MassiveMarketDataSource` tests and integration tests

**Run Commands:**

```bash
pytest                      # Run all tests (backend/tests/)
pytest -v                   # Verbose output
pytest tests/market/test_simulator.py  # Single file
pytest --asyncio-mode=auto # Explicit async mode
```

## Test File Organization

**Location:**

- Co-located under `backend/tests/` parallel to `backend/app/`
- Structure mirrors implementation: `tests/market/` for `app/market/`, `tests/routes/` for `app/routes/`, `tests/db/` for `app/db/`

**Naming:**

- Test files: `test_<module>.py`
- Test functions: `test_<what_is_being_tested>()`
- Example: `test_simulator.py` tests `app/market/simulator.py`; `test_get_prices_omits_untracked_tickers()` documents the `get_prices()` contract

**File Structure:**

```
backend/
├── app/
│   ├── market/
│   ├── routes/
│   └── db/
├── tests/
│   ├── market/
│   │   ├── test_simulator.py
│   │   ├── test_massive.py
│   │   ├── test_cache.py
│   │   ├── test_factory.py
│   │   ├── test_interface_conformance.py
│   │   └── test_loop.py
│   ├── routes/
│   │   ├── test_health.py
│   │   └── test_stream.py
│   ├── db/
│   │   └── test_watchlist.py
│   └── test_main.py
└── pyproject.toml
```

## Test Structure

**Suite Organization:**

Tests are organized by behavior concern with clear section comments:

```python

# --- GBM math correctness -----------------------------------------------

def test_gbm_step_matches_closed_form_with_zero_shock():
    price, mu, sigma = 100.0, 0.0003, 0.02
    result = _gbm_step(price, mu, sigma, DT, z=0.0, sector_factor=0.0)
    expected = price * math.exp((mu - 0.5 * sigma**2) * DT)
    assert result == pytest.approx(expected)
```

**Patterns:**

1. **Arrange-Act-Assert:**
   ```python
   @pytest.mark.asyncio
   async def test_price_increase_reports_up_direction():
       # Arrange
       cache = PriceCache()
       await cache.update("AAPL", 190.00)
       
       # Act
       tick = await cache.update("AAPL", 190.42)
       
       # Assert
       assert tick.price == 190.42
       assert tick.previous_price == 190.00
       assert tick.direction == ChangeDirection.UP
   ```

2. **Setup/Teardown with Async:**
   ```python
   @pytest.mark.asyncio
   @respx.mock
   async def test_get_prices_parses_snapshot():
       respx.get(url__regex=SNAPSHOT_URL_REGEX).mock(...)  # Setup
       source = MassiveMarketDataSource(api_key="test-key")
       await source.start()  # Fixture-like init
       
       prices = await source.get_prices(["AAPL"])  # Act
       
       assert prices == {"AAPL": 190.42}  # Assert
       await source.stop()  # Teardown
   ```

3. **Test with Comments Explaining Non-Obvious Behavior:**
   ```python
   @pytest.mark.asyncio
   async def test_same_sector_tickers_are_positively_correlated(monkeypatch):
       """This is the behavior most likely to silently break (e.g. if the
       sector factor were accidentally redrawn per-ticker instead of shared) —
       verify via Pearson correlation over a simulated return series.
       ..."""
       monkeypatch.setattr(simulator_module, "EVENT_PROBABILITY_PER_TICK", 0.0)
       # ... rest of test
   ```

## Fixtures

**pytest Fixtures Used:**

1. **`monkeypatch`** — Modify environment variables and module attributes:
   ```python
   def test_lifespan_wires_simulator_by_default(monkeypatch, tmp_path):
       monkeypatch.setattr("app.db.watchlist.DB_PATH", tmp_path / "finally.db")
       monkeypatch.delenv("MASSIVE_API_KEY", raising=False)
   ```

2. **`tmp_path`** — Temporary directory for isolated database files:
   ```python
   @pytest.fixture(autouse=True)
   def isolated_db(monkeypatch, tmp_path):
       """Every test in this module gets its own throwaway SQLite file"""
       monkeypatch.setattr(watchlist_module, "DB_PATH", tmp_path / "finally.db")
   ```

3. **`request`** (parametrized fixtures) — Test multiple implementations with one test:
   ```python
   @pytest.fixture(params=["simulator", "massive"])
   async def source(request):
       if request.param == "simulator":
           src = SimulatorMarketDataSource(seed=42)
           await src.start()
           yield src
           await src.stop()
       else:
           with respx.mock:
               # ...
               src = MassiveMarketDataSource(api_key="test-key")
               # ...
   ```

4. **`autouse=True` fixtures** — Run before every test without explicit request:
   ```python
   @pytest.fixture(autouse=True)
   def fast_broadcast(monkeypatch):
       """Speed up SSE broadcast timing for tests"""
       monkeypatch.setattr(stream_module, "SSE_BROADCAST_SECONDS", 0.001)
   ```

## Mocking

**HTTP Mocking with respx:**

```python
@pytest.mark.asyncio
@respx.mock
async def test_get_prices_parses_multiple_tickers():
    respx.get(url__regex=SNAPSHOT_URL_REGEX).mock(
        return_value=httpx.Response(
            200,
            json={
                "tickers": [
                    {"ticker": "AAPL", "lastTrade": {"p": 190.42}},
                    {"ticker": "GOOGL", "lastTrade": {"p": 175.10}},
                ]
            },
        )
    )
    source = MassiveMarketDataSource(api_key="test-key")
    await source.start()
    prices = await source.get_prices(["AAPL", "GOOGL"])
    assert prices == {"AAPL": 190.42, "GOOGL": 175.10}
    await source.stop()
```

**Stub Classes for Unit Testing:**

Custom stub implementations replace real dependencies:

```python
class StubSource(MarketDataSource):
    """A minimal in-memory MarketDataSource stand-in for exercising the
    update loop's orchestration without depending on the simulator or a
    mocked HTTP client."""

    def __init__(self, prices: dict[str, float] | None = None, raise_on_get: bool = False):
        self.prices = prices or {}
        self.raise_on_get = raise_on_get
        self.calls = 0

    async def get_prices(self, tickers: list[str]) -> dict[str, float]:
        self.calls += 1
        if self.raise_on_get:
            raise RuntimeError("boom")
        return {t: self.prices[t] for t in tickers if t in self.prices}
```

**Fake Request for SSE Testing:**

```python
class _FakeRequest:
    """Reports disconnected after `max_iterations` truthy checks, so a loop
    keyed on `await request.is_disconnected()` terminates deterministically."""

    def __init__(self, max_iterations: int, app=None):
        self._remaining = max_iterations
        self.app = app

    async def is_disconnected(self) -> bool:
        if self._remaining <= 0:
            return True
        self._remaining -= 1
        return False
```

**Stub RNG for Deterministic Event Testing:**

```python
class StubRng:
    def random(self):
        return 0.0  # always below the probability threshold

    def uniform(self, lo, hi):
        return hi  # max magnitude, deterministic

    def choice(self, seq):
        return seq[0]  # -1
```

**What to Mock:**

- HTTP calls (respx for httpx)
- Environment variables (monkeypatch)
- Module constants for testing (monkeypatch)
- Database paths (monkeypatch with tmp_path)

**What NOT to Mock:**

- Pure math functions — test with real arguments
- Data structure operations (dict, list) — test with real collections
- Async flow control — use real asyncio

## Test Types

**Unit Tests:**

- Math correctness: `test_gbm_step_*()` functions in `test_simulator.py`
- Data structure behavior: `test_*` in `test_cache.py`, `test_watchlist.py`
- Parsing and logic: `test_serialize_tick_*()`, factory selection tests
- Scope: Single function or class method in isolation
- Mocking: RNG, HTTP, environment variables
- Examples: `backend/tests/market/test_simulator.py`, `backend/tests/market/test_cache.py`

**Interface Conformance Tests:**

- Verify both `SimulatorMarketDataSource` and `MassiveMarketDataSource` implement the same contract
- File: `backend/tests/market/test_interface_conformance.py`
- Parametrized fixture tests both implementations with identical assertions:
  ```python
  @pytest.mark.asyncio
  async def test_get_prices_omits_unknown_tickers(source):
      prices = await source.get_prices(["AAPL", "ZZZZ_NOT_REAL"])
      assert "AAPL" in prices
      assert "ZZZZ_NOT_REAL" not in prices
  ```

**Integration Tests:**

- FastAPI app startup and lifespan: `backend/tests/test_main.py`
- HTTP routes with TestClient: `backend/tests/routes/test_stream.py`, `backend/tests/routes/test_health.py`
- Database initialization and persistence: `backend/tests/db/test_watchlist.py`
- Scope: Multiple components working together
- Mocking: Minimal (respx for external APIs, monkeypatch for env/paths)
- Examples: `test_lifespan_wires_simulator_by_default()` in `test_main.py`

**E2E Tests:**

- Not yet implemented in backend (test/ directory contains Playwright tests for frontend/browser scenarios, not backend)
- When added: Full Docker container integration, real WebSocket/SSE flow

## Common Patterns

**Async Testing:**

```python
@pytest.mark.asyncio
async def test_prices_stay_positive_and_bounded_over_many_ticks():
    sim = SimulatorMarketDataSource(seed=42)
    for _ in range(500):
        sim._advance_all(DT)
    for ticker, params in TICKER_UNIVERSE.items():
        price = sim._prices[ticker]
        assert price > 0
        assert 0.5 * params.seed_price < price < 1.5 * params.seed_price
```

**Error Testing:**

```python
@pytest.mark.asyncio
@respx.mock
async def test_rate_limit_returns_empty_dict_not_raise():
    respx.get(url__regex=SNAPSHOT_URL_REGEX).mock(return_value=httpx.Response(429))
    source = MassiveMarketDataSource(api_key="test-key")
    await source.start()
    prices = await source.get_prices(["AAPL"])
    assert prices == {}
    await source.stop()
```

**Floating-Point Precision:**

```python
def test_gbm_step_matches_closed_form_with_zero_shock():
    result = _gbm_step(100.0, 0.0003, 0.02, DT, z=0.0, sector_factor=0.0)
    expected = 100.0 * math.exp((0.0003 - 0.5 * 0.02**2) * DT)
    assert result == pytest.approx(expected)  # Uses default relative/absolute tolerances
```

**Deterministic Seeds:**

```python
@pytest.mark.asyncio
async def test_advance_all_is_deterministic_given_a_seed():
    sim_a = SimulatorMarketDataSource(seed=7)
    sim_b = SimulatorMarketDataSource(seed=7)
    for _ in range(50):
        sim_a._advance_all(DT)
        sim_b._advance_all(DT)
    assert sim_a._prices == sim_b._prices
```

**Testing Loops/Long-Running Tasks:**

For infinite loops (update loop, SSE generator), tests run them briefly then cancel:

```python
async def _run_briefly(coro_task: asyncio.Task, seconds: float = 0.05) -> None:
    await asyncio.sleep(seconds)
    coro_task.cancel()
    try:
        await coro_task
    except asyncio.CancelledError:
        pass

@pytest.mark.asyncio
async def test_loop_writes_fetched_prices_into_cache():
    source = StubSource(prices={"AAPL": 190.00})
    cache = PriceCache()

    async def get_watchlist():
        return ["AAPL"]

    task = asyncio.create_task(run_update_loop(source, cache, get_watchlist, 0.01))
    await _run_briefly(task)

    tick = await cache.get("AAPL")
    assert tick is not None
    assert tick.price == 190.00
```

**Isolation with Database Monkeypatch:**

Every test that touches the database uses a temporary SQLite file:

```python
def test_health_returns_ok(monkeypatch, tmp_path):
    monkeypatch.setattr("app.db.watchlist.DB_PATH", tmp_path / "finally.db")
    monkeypatch.delenv("MASSIVE_API_KEY", raising=False)
    
    app = create_app()
    with TestClient(app) as client:
        resp = client.get("/api/health")
        assert resp.status_code == 200
```

## Coverage

**Enforcement:** Not currently enforced by CI (no pytest-cov plugin in pyproject.toml)

**Observed Coverage (Estimated):**

- Market data layer: >90% (simulator, massive, cache, loop thoroughly tested)
- Database layer: >90% (watchlist initialization and queries tested)
- Routes: ~70% (health and stream endpoints have tests; portfolio/watchlist/chat endpoints not yet implemented)
- Error paths: Well-tested in massive.py (rate limits, auth errors, malformed responses)

**Gaps:**

- No tests for future portfolio/trade endpoints (not yet implemented)
- No tests for chat/LLM integration (not yet implemented)
- No connection resilience tests (SSE reconnection behavior)

**View Coverage (when tool is added):**

```bash
pytest --cov=app --cov-report=html

# View coverage/index.html in browser

```

## Test Data & Fixtures

**Seed Data:**

- Simulator uses deterministic `seed` parameter for reproducible price sequences
- Watchlist seeded with `DEFAULT_WATCHLIST` from `app/market/simulator.py` (AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META, JPM, V, NFLX)
- Test fixtures use monkeypatch to override real paths/env vars

**Factories:**

- `SimulatorMarketDataSource(seed=42)` — Creates a seeded simulator for reproducible tests
- `MassiveMarketDataSource(api_key="test-key")` — Creates a client that respx mocks

---

*Testing analysis: 2026-09-15*
