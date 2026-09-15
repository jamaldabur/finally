---
last_mapped_commit: 20fd6385728d5909231f6772c7abc2d5c3111cb7
last_mapped_at: 2026-09-15
---
# Coding Conventions

**Analysis Date:** 2026-09-15

## Naming Patterns

**Files:**

- Modules use `snake_case`: `watchlist.py`, `simulator.py`, `stream.py`
- Test files match implementation with `test_` prefix: `test_simulator.py`, `test_watchlist.py`
- Private/internal module marker: Leading underscore for utility functions (e.g., `_gbm_step()`, `_maybe_apply_event()`)

**Functions:**

- All functions use `snake_case`
- Async functions have no special prefix — async keyword is explicit
- Private functions (module-level helpers) prefixed with single underscore
- Factory functions named `build_*` or `create_*` (e.g., `build_market_data_source()`, `create_app()`)

**Variables:**

- Local variables and parameters: `snake_case`
- Instance variables prefixed with underscore: `self._prices`, `self._client`, `self._latest`
- Constants: `UPPERCASE_WITH_UNDERSCORES` (e.g., `DEFAULT_WATCHLIST`, `TICKER_UNIVERSE`, `SSE_BROADCAST_SECONDS`)

**Types:**

- Classes use `PascalCase`: `SimulatorMarketDataSource`, `MassiveMarketDataSource`, `PriceCache`, `PriceTick`
- Enums use `PascalCase`: `ChangeDirection`
- Dataclasses use `PascalCase` and are frozen (`@dataclass(frozen=True)`) when representing immutable values

## Code Style

**Formatting:**

- Line length: Observed 88-100 character soft limit (no explicit formatter configured, but consistent formatting throughout)
- Indentation: 4 spaces
- String quotes: Double quotes preferred for docstrings and regular strings
- Imports: Grouped in standard order (stdlib, third-party, local), separated by blank lines

**Type Hints:**

- Full type annotations on function signatures are mandatory
- Return types explicitly annotated (e.g., `-> dict[str, float]`, `-> PriceTick | None`)
- Parameter types always specified (e.g., `tickers: list[str]`)
- Union types use pipe syntax: `int | None`, `dict[str, float] | None`
- No `type: ignore` comments observed — full type compliance expected

**Docstrings:**

- Module-level docstrings required for all files (triple-quoted)
- Describe purpose, design rationale, and references to planning docs
- Class docstrings explain responsibilities and invariants
- Function docstrings document contract: parameters, return value, and any side effects
- Example: `"""Return the latest known price for each requested ticker. Tickers this source has no data for are simply omitted from the result dict — callers must not treat a missing key as an error."""`

## Import Organization

**Order:**

1. `from __future__ import annotations` (if used for forward references)
2. Standard library (`asyncio`, `os`, `json`, `sqlite3`, `datetime`, etc.)
3. Third-party (`fastapi`, `httpx`, `pytest`, etc.)
4. Local application (`.base`, `..db.watchlist`, relative imports within package)

**Path Aliases:**

- No path aliases (no `@` prefixes like `@app/`) in backend — all imports relative within package hierarchy

**Example:**

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

import httpx

from .base import MarketDataSource
from ..market.cache import PriceCache
```

## Error Handling

**Patterns:**

1. **Graceful degradation (Massive client):** Network errors, malformed responses, rate limits do NOT raise — they log and return empty results. The update loop continues without crashing:
   ```python
   except httpx.HTTPStatusError as exc:
       logger.error("Massive returned HTTP %s: %s", exc.response.status_code, exc)
       return {}
   ```

2. **Defensive loop wrapping (update_loop):** The market data update loop catches all exceptions to prevent a single bad `get_prices()` call from killing the loop:
   ```python
   except Exception:
       logger.exception("market data update loop iteration failed")
   ```

3. **Precondition assertions:** Used for internal invariants that should never fail in production (e.g., client must be initialized after `start()`):
   ```python
   assert self._client is not None, "start() must be called before get_prices()"
   ```

4. **Contract violations:** Methods document their contracts (e.g., empty tickers omitted from result) and trust callers to honor them; no defensive input validation.

## Logging

**Framework:** Python standard `logging` module

**Pattern:**

- Module-level logger: `logger = logging.getLogger(__name__)`
- Used in `massive.py` and `loop.py` for error reporting and debugging
- Log levels:
  - `logger.warning()` — transient failures (retrying, rate limits)
  - `logger.error()` — persistent failures (auth errors, malformed responses)
  - `logger.exception()` — unexpected exceptions in critical loops

**Example:**

```python
logger.warning(
    "Massive request failed (%s), retrying (%d/%d)",
    exc,
    attempt + 1,
    self.MAX_TRANSIENT_RETRIES,
)
```

## Comments

**When to Comment:**

- Complex mathematical logic: GBM step calculation, sector correlation factors — explain the "why"
- Non-obvious design decisions: Why `previous_price` carries forward on heartbeat (preventing false flash animations)
- References to external docs: PLAN.md §6, planning/MARKET_DATA_DESIGN.md
- Edge cases and workarounds: Why events are disabled in certain tests, retry backoff logic

**Avoiding Comments:**

- Code that reads clearly (good naming) needs no comment
- Avoid restating the code: Don't comment `x = y  # assign y to x`

**Example of Good Comment:**

```python

# Cent precision, rounded once here (not per-read), so every

# consumer sees the same value and no float-precision flicker

# reaches the frontend. GBM is multiplicative, so prices can

# never go negative — no floor/clamp needed.

self._prices[ticker] = round(new_price, 2)
```

## Function Design

**Size:** Small functions with single responsibility (e.g., `_gbm_step()`, `_maybe_apply_event()` isolated from `_advance_all()`)

**Parameters:** Explicit, typed parameters preferred over config objects. Example:

```python
async def run_update_loop(
    source: MarketDataSource,
    cache: PriceCache,
    get_watchlist_tickers: Callable[[], Awaitable[list[str]]],
    interval_seconds: float,
) -> None:
```

**Return Values:**

- Explicit return types on all functions
- `None` return implies side effect only (e.g., `async def start(self) -> None`)
- Dictionary returns document what keys are present and which may be missing (e.g., "unknown tickers omitted from result dict")

**Async/Await:**

- All I/O operations are async (no blocking calls)
- Synchronous utility functions (GBM math, random events) remain sync — no unnecessary async wrappers
- Database access wrapped via `asyncio.to_thread()` to keep it off the event loop

## Module Design

**Exports:**

- Each module exports its public interface clearly in imports (`from app.market.base import MarketDataSource`)
- Private functions/classes (leading `_`) are not for external import
- Concrete implementations (`SimulatorMarketDataSource`, `MassiveMarketDataSource`) exported for testing; consumers use via abstract `MarketDataSource`

**Module Organization:**

- `app/market/base.py`: Abstract interface (`MarketDataSource`, `PriceTick`, `ChangeDirection`)
- `app/market/simulator.py`: Concrete implementation with all GBM math and constants
- `app/market/massive.py`: Concrete implementation with HTTP client and error handling
- `app/market/cache.py`: Shared in-memory store (not a data source)
- `app/market/loop.py`: Orchestration (drives either data source into cache)
- `app/market/factory.py`: Dependency selection based on environment
- `app/db/watchlist.py`: Persistence layer for watchlist tickers
- `app/routes/health.py`, `app/routes/stream.py`: FastAPI endpoints
- `app/main.py`: FastAPI app factory and lifespan management

**No Barrel Files:** Each module imported directly by full path (e.g., `from app.market.base import ...`, not `from app.market import ...`)

## Async Patterns

**Locks for Concurrent Access:**

```python
class PriceCache:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._latest: dict[str, PriceTick] = {}

    async def update(self, ticker: str, price: float) -> PriceTick:
        async with self._lock:
            # ... modify _latest safely
```

**Background Tasks:**

- Created via `asyncio.create_task()` in lifespan
- Stored on `app.state` for access by routes
- Cancelled on shutdown via `task.cancel()`

**Event Loop Integration:**

- Blocking sync operations (DB, math) use `asyncio.to_thread()` to prevent blocking the event loop
- Example: `await asyncio.to_thread(_init_db_sync)`

## Testing Conventions (See TESTING.md)

Key conventions:

- Use `pytest.mark.asyncio` for async test functions
- `monkeypatch` fixture for environment variables and module constants
- `tmp_path` fixture for isolated database files
- Type hints in test code as well
- Clear, descriptive test names

---

*Convention analysis: 2026-09-15*
