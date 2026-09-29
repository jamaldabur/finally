# Phase 1: Backend Trading Engine - Pattern Map

**Mapped:** 2026-09-16
**Files analyzed:** 14 (5 db modules, 1 service, 2 routes, main.py edit, conftest.py, ~6 test files)
**Analogs found:** 14 / 14

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `backend/app/db/users_profile.py` | model | CRUD | `backend/app/db/watchlist.py` | exact |
| `backend/app/db/positions.py` | model | CRUD | `backend/app/db/watchlist.py` | exact |
| `backend/app/db/trades.py` | model | CRUD (append-only) | `backend/app/db/watchlist.py` | exact |
| `backend/app/db/portfolio_snapshots.py` | model | CRUD (append-only) | `backend/app/db/watchlist.py` | exact |
| `backend/app/db/chat_messages.py` | model | CRUD (schema-only this phase) | `backend/app/db/watchlist.py` | exact |
| `backend/app/db/watchlist.py` (extend) | model | CRUD | itself (extend in place) | exact |
| `backend/app/portfolio/service.py` | service | request-response (validate+apply) | `backend/app/market/cache.py` (lock pattern) + `backend/app/market/loop.py` (defensive/structured-result style) | role-match |
| `backend/app/routes/portfolio.py` | route/controller | request-response | `backend/app/routes/stream.py` (state access) + `backend/app/routes/health.py` (route shape) | role-match |
| `backend/app/routes/watchlist.py` | route/controller | CRUD/request-response | `backend/app/routes/health.py` | role-match |
| `backend/app/main.py` (extend lifespan) | config/bootstrap | event-driven (startup/shutdown) | itself (extend in place) | exact |
| `backend/tests/conftest.py` | test | — | `backend/tests/db/test_watchlist.py` (fixture to extract) | exact |
| `backend/tests/db/test_users_profile.py` etc. (5 files) | test | CRUD | `backend/tests/db/test_watchlist.py` | exact |
| `backend/tests/portfolio/test_service.py` | test | request-response | `backend/tests/market/test_cache.py` (lock/state test style) | role-match |
| `backend/tests/routes/test_portfolio.py`, `test_watchlist.py` | test | request-response | `backend/tests/routes/test_health.py` | exact |

## Pattern Assignments

### `backend/app/db/users_profile.py`, `positions.py`, `trades.py`, `portfolio_snapshots.py`, `chat_messages.py` (model, CRUD)

**Analog:** `backend/app/db/watchlist.py` (full file, 84 lines — read in full above)

**Module docstring convention** — every db module opens with a triple-quoted docstring explaining purpose/lazy-init contract, e.g. (lines 1-13):
```python
"""SQLite-backed watchlist storage.

Lazily initializes its own table and seeds PLAN.md §7's 10 default tickers
on first use — no separate migration step (PLAN.md §7 "Lazy Initialization").
...
"""

from __future__ import annotations

import asyncio
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
```

**Critical: import `_connect` by function, not `DB_PATH` by value** (Pitfall 1 from RESEARCH.md). Every new module must do:
```python
from .watchlist import _connect
```
NOT define its own `DB_PATH`/`_connect()`. This preserves the three existing tests' `monkeypatch.setattr("app.db.watchlist.DB_PATH", ...)` / `monkeypatch.setattr(watchlist_module, "DB_PATH", ...)` isolation.

**Schema + idempotent init pattern** (lines 35-62):
```python
DEFAULT_USER_ID = "default"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS watchlist (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL DEFAULT 'default',
    ticker TEXT NOT NULL,
    added_at TEXT NOT NULL,
    UNIQUE(user_id, ticker)
);
"""


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH, timeout=5.0)


def _init_db_sync() -> None:
    with _connect() as conn:
        conn.execute(_SCHEMA)
        (count,) = conn.execute(
            "SELECT COUNT(*) FROM watchlist WHERE user_id = ?", (DEFAULT_USER_ID,)
        ).fetchone()
        if count == 0:
            now = datetime.now(timezone.utc).isoformat()
            conn.executemany(
                "INSERT INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
                [(str(uuid.uuid4()), DEFAULT_USER_ID, ticker, now) for ticker in DEFAULT_WATCHLIST],
            )
```
For `users_profile.py`, the seed check is a single-row upsert-if-missing (analogous idempotent-seed idea, adapted to one row instead of `executemany`):
```python
def _init_db_sync() -> None:
    with _connect() as conn:
        conn.execute(_SCHEMA)
        row = conn.execute(
            "SELECT id FROM users_profile WHERE id = ?", (DEFAULT_USER_ID,)
        ).fetchone()
        if row is None:
            now = datetime.now(timezone.utc).isoformat()
            conn.execute(
                "INSERT INTO users_profile (id, cash_balance, created_at) VALUES (?, ?, ?)",
                (DEFAULT_USER_ID, 10000.0, now),
            )
```

**Sync-wrapped-in-`asyncio.to_thread` async wrapper pattern** (lines 73-84):
```python
async def init_db() -> None:
    """Called once at app startup (see app/main.py's lifespan). Creates the
    watchlist table if missing and seeds the default tickers if empty —
    idempotent, safe to call on every startup."""
    await asyncio.to_thread(_init_db_sync)


async def get_watchlist_tickers(user_id: str = DEFAULT_USER_ID) -> list[str]:
    """Matches the zero-arg `Callable[[], Awaitable[list[str]]]` shape
    run_update_loop expects, via the default argument."""
    return await asyncio.to_thread(_get_watchlist_tickers_sync, user_id)
```
Apply this exact `_xxx_sync()` + `async def xxx()` pairing to every CRUD function in the five new modules (`get_cash_balance`/`update_cash_balance`, `get_position`/`upsert_position`/`delete_position`, `insert_trade`, `insert_snapshot`/`get_snapshots`). All SQL must use `?` placeholders (parameterized queries) — never string interpolation, per the codebase's established SQL-injection mitigation (Security Domain section of RESEARCH.md).

**`positions.py` upsert (SQLite ON CONFLICT)** — new pattern not present in `watchlist.py` but specified in RESEARCH.md Code Examples, following the same `_connect()`/parameterized-query style:
```python
conn.execute(
    """
    INSERT INTO positions (id, user_id, ticker, quantity, avg_cost, updated_at)
    VALUES (?, ?, ?, ?, ?, ?)
    ON CONFLICT(user_id, ticker) DO UPDATE SET
        quantity = excluded.quantity,
        avg_cost = excluded.avg_cost,
        updated_at = excluded.updated_at
    """,
    (str(uuid.uuid4()), user_id, ticker, new_qty, new_avg_cost, now),
)
```

---

### `backend/app/db/watchlist.py` (extend — add `add_watchlist_ticker`, `remove_watchlist_ticker`)

**Analog:** itself. Add two new functions following the exact `_xxx_sync` / `async def xxx` pairing already used by `_get_watchlist_tickers_sync`/`get_watchlist_tickers` (lines 65-70, 80-83 above). Reuse `_connect()`, `DEFAULT_USER_ID`, and the `?`-parameterized `INSERT`/`DELETE` style. Ticker normalization (`ticker.strip().upper()`) belongs in the route layer per Pitfall 2, not in this db module (keep this module a thin persistence layer, matching its existing division of responsibility).

---

### `backend/app/portfolio/service.py` (service, request-response)

**No direct analog exists** (no service-layer module currently in the codebase — `app/market/loop.py` is the closest structural precedent for "orchestration function with defensive error handling," and `app/market/cache.py` is the closest precedent for the lock-guarded critical section).

**Lock-guarded shared mutable state pattern** — analog `backend/app/market/cache.py` (lines 16-41, full class shown above):
```python
class PriceCache:
    """Guarded by a lock since multiple SSE connections and the update loop
    can all await it concurrently."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._latest: dict[str, PriceTick] = {}

    async def update(self, ticker: str, price: float) -> PriceTick:
        async with self._lock:
            ...
```
`execute_trade()` must acquire `app.state.portfolio_lock` (a new `asyncio.Lock()` stored on `app.state`, mirroring how `price_cache`/`market_source` are stored — see `main.py` lines 43-44) around the full read-modify-write of `users_profile.cash_balance` + `positions`.

**Structured-result-not-exception pattern** (RESEARCH.md Pattern 3, no in-repo precedent yet but consistent with the "contract violations documented, not defended" convention in CONVENTIONS.md §Error Handling): `execute_trade()` returns a `TradeResult` dataclass (`status: Literal["executed","error"]`, `reason: str | None`), never raises `HTTPException` — the caller (`routes/portfolio.py`) is the only place translating to HTTP.

**Fill-price lookup** — must call `app.state.price_cache.get(ticker)` (the existing method, docstring: "Single-ticker lookup — used by trade fill-price resolution", `cache.py` line 49), never re-fetch from `market_source`.

**Type hints / small function style** — follow CONVENTIONS.md: full type annotations, explicit return types, `snake_case`, small single-responsibility functions (e.g. separate `_apply_buy()`/`_apply_sell()` helpers analogous to `_gbm_step()`/`_maybe_apply_event()` decomposition in `simulator.py`).

---

### `backend/app/routes/portfolio.py`, `backend/app/routes/watchlist.py` (route/controller, request-response)

**Analog:** `backend/app/routes/health.py` (full file, 11 lines) for route/router shape; `backend/app/routes/stream.py` for `app.state` access pattern.

**Router + endpoint shape** (`health.py` lines 1-10):
```python
"""System health check (PLAN.md §8 "System")."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
```

**Reading shared state off `request.app.state` / route function signature** (`stream.py` lines 44-46):
```python
@router.get("/api/stream/prices")
async def stream_prices(request: Request):
    cache: PriceCache = request.app.state.price_cache
```
New routes needing `price_cache`, `portfolio_lock`, etc. should follow this same `request.app.state.X` access style (or FastAPI `Request` dependency), not a module-level global.

**HTTP-exception translation** (RESEARCH.md Pattern 3 — the only place in the whole request path allowed to raise `HTTPException`):
```python
result = await execute_trade(app_state, ticker=body.ticker, side=body.side, quantity=body.quantity)
if result.status == "error":
    raise HTTPException(status_code=400, detail=result.reason)
return result.trade
```

**Pydantic request/response models** — new for this phase (no `pydantic.BaseModel` currently imported anywhere in `app/`), but must follow the same full-type-annotation discipline as everything else, e.g. `quantity: float = Field(gt=0)`, `side: Literal["buy", "sell"]`.

**Ticker normalization at the route boundary** (Pitfall 2) — `POST /api/watchlist` and the trade route must `ticker.strip().upper()` before calling `is_valid_ticker()` or persisting, mirroring how `TICKER_UNIVERSE` keys are uppercase in `backend/app/market/simulator.py`.

---

### `backend/app/main.py` (extend lifespan)

**Analog:** itself, lines 23-56 (full file read above).

Current lifespan:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()

    source = build_market_data_source()
    cache = PriceCache()
    await source.start()

    interval = (...)
    update_task = asyncio.create_task(
        run_update_loop(source, cache, get_watchlist_tickers, interval)
    )

    app.state.market_source = source
    app.state.price_cache = cache

    yield

    update_task.cancel()
    await source.stop()
```
Extend by: (1) calling all five new `init_db()`s before any `create_task`, in the sequence documented in RESEARCH.md Pattern 1; (2) adding `app.state.portfolio_lock = asyncio.Lock()`; (3) creating `snapshot_task = asyncio.create_task(run_portfolio_snapshot_loop(...))` and cancelling it after `yield` alongside `update_task.cancel()` (Pitfall 5); (4) `app.include_router(portfolio.router)` / `app.include_router(watchlist.router)` in `create_app()` alongside the existing `health.router`/`stream.router` includes (lines 52-56).

---

### `backend/tests/conftest.py` (test, shared fixture — NEW, doesn't exist yet)

**Analog:** the `isolated_db` fixture currently duplicated in `backend/tests/db/test_watchlist.py` (lines 1-11 shown above) and similarly in `test_main.py`/`test_health.py`.

```python
import pytest

from app.db import watchlist as watchlist_module


@pytest.fixture(autouse=True)
def isolated_db(monkeypatch, tmp_path):
    """Every test gets its own throwaway SQLite file — never touch the real
    db/finally.db during tests."""
    monkeypatch.setattr(watchlist_module, "DB_PATH", tmp_path / "finally.db")
```
Centralize this once in `conftest.py` so every new test module (db, portfolio, routes) inherits it automatically without re-declaring — since all new db modules import `_connect` from `watchlist.py` (Pattern 2), patching `watchlist_module.DB_PATH` alone is sufficient to isolate all six tables.

---

### `backend/tests/db/test_users_profile.py`, `test_positions.py`, `test_trades.py`, `test_portfolio_snapshots.py`, `test_chat_messages.py` (test, CRUD)

**Analog:** `backend/tests/db/test_watchlist.py` (full file, 48 lines, shown above).

Pattern: `@pytest.mark.asyncio` async test functions, descriptive `test_<behavior>` names, assert against `init_db()` idempotency and seed correctness:
```python
@pytest.mark.asyncio
async def test_init_db_seeds_default_watchlist():
    await watchlist_module.init_db()
    tickers = await watchlist_module.get_watchlist_tickers()
    assert set(tickers) == set(DEFAULT_WATCHLIST)
    assert len(tickers) == len(DEFAULT_WATCHLIST)


@pytest.mark.asyncio
async def test_init_db_is_idempotent():
    await watchlist_module.init_db()
    await watchlist_module.init_db()  # must not duplicate the seed rows
    ...
```
For `test_users_profile.py`: assert seeded `cash_balance == 10000.0`. For `test_positions.py`: assert `UNIQUE(user_id, ticker)` upsert behavior (buy twice → one row, updated quantity). For `test_trades.py`/`test_portfolio_snapshots.py`: assert append-only inserts never collide/overwrite. For `test_chat_messages.py`: schema-creation-only test (no read/write logic this phase per DATA-05).

---

### `backend/tests/portfolio/test_service.py` (test, request-response)

**Analog (concurrency/state test style):** `backend/tests/market/test_cache.py` (not read in full this session, but its existence and role — testing `PriceCache`'s lock-guarded state — is the structural precedent for testing `execute_trade()`'s lock-guarded critical section). **Analog (fixture reuse):** `conftest.py`'s `isolated_db`.

Test cases required by RESEARCH.md's Phase Requirements → Test Map: buy/sell fills at cached price and updates cash+positions; `insufficient_cash` (PORT-03); `insufficient_shares` (PORT-04); avg-cost math across multiple buys; float-epsilon full-close-deletes-row (Pitfall 4). Use `pytest.mark.asyncio`, construct a `PriceCache` and seed it via `await cache.update(ticker, price)` before calling `execute_trade()`, per the existing test convention of exercising real async objects rather than mocking them.

---

### `backend/tests/routes/test_portfolio.py`, `backend/tests/routes/test_watchlist.py` (test, request-response)

**Analog:** `backend/tests/routes/test_health.py` (full file, 15 lines, shown above):
```python
from fastapi.testclient import TestClient

from app.main import create_app


def test_health_returns_ok(monkeypatch, tmp_path):
    monkeypatch.setattr("app.db.watchlist.DB_PATH", tmp_path / "finally.db")
    monkeypatch.delenv("MASSIVE_API_KEY", raising=False)

    app = create_app()
    with TestClient(app) as client:
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}
```
New route tests follow this exact `create_app()` + `TestClient` context-manager shape (which drives the real `lifespan`, so `init_db()` for all tables runs for free). Once `conftest.py` exists, the `monkeypatch.setattr(...)` line can be dropped in favor of the shared `isolated_db` fixture — but the `monkeypatch.delenv("MASSIVE_API_KEY", raising=False)` line should still be repeated per-test where relevant (env, not DB, isolation).

## Shared Patterns

### DB connection / DB_PATH isolation (all db + route tests)
**Source:** `backend/app/db/watchlist.py` lines 30-48 (`DB_PATH`, `_connect()`)
**Apply to:** All five new `app/db/*.py` modules (import `_connect` from `.watchlist`, never redefine); all new tests (via `conftest.py`'s `isolated_db` fixture patching `app.db.watchlist.DB_PATH`).

### Async-wrap-sync-sqlite (all db modules)
**Source:** `backend/app/db/watchlist.py` lines 51-77 (`_init_db_sync` / `init_db`, `_get_watchlist_tickers_sync` / `get_watchlist_tickers`)
**Apply to:** Every CRUD function in the five new db modules — `_xxx_sync()` does the blocking `sqlite3` work inside `with _connect() as conn:`, the public `async def xxx()` wraps it in `await asyncio.to_thread(_xxx_sync, ...)`.

### asyncio.Lock-guarded critical section (service layer)
**Source:** `backend/app/market/cache.py` lines 16-41 (`PriceCache.__init__`/`update`)
**Apply to:** `app/portfolio/service.py::execute_trade()` — acquire `app.state.portfolio_lock` around the read-modify-write of `cash_balance` + `positions` + the `trades` insert + the immediate `portfolio_snapshots` insert.

### Lifespan task lifecycle (background tasks)
**Source:** `backend/app/main.py` lines 23-49 (full `lifespan`)
**Apply to:** The new 30-second portfolio-snapshot background task — created via `asyncio.create_task()`, stored in a local variable, cancelled after `yield` alongside the existing `update_task.cancel()` (Pitfall 5); its `init_db()` dependency must run before task creation (Pitfall 6).

### Router registration
**Source:** `backend/app/main.py` lines 52-56 (`create_app()`)
**Apply to:** `app.include_router(portfolio.router)` and `app.include_router(watchlist.router)`, added the same way `health.router`/`stream.router` are today.

### Parameterized SQL only
**Source:** `backend/app/db/watchlist.py` lines 54-61, 67-69 (`?` placeholders throughout)
**Apply to:** Every SQL statement in every new db module — never f-string/`.format()` interpolation of `ticker`/`quantity`/`user_id` into SQL text.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `backend/app/portfolio/service.py` | service | request-response | No service-layer module exists yet in the codebase; synthesized from `cache.py`'s lock pattern + RESEARCH.md's `TradeResult` design (Pattern 3) — treat RESEARCH.md Code Examples as the primary source for this file's internal shape, not a codebase analog. |
| Pydantic request/response models (in `routes/portfolio.py`, `routes/watchlist.py`) | schema | request-response | No `pydantic.BaseModel` currently imported anywhere in `app/` (verified in RESEARCH.md's grep); use RESEARCH.md's field-list recommendations (Code Examples, Open Question 2) as the starting contract. |

## Metadata

**Analog search scope:** `backend/app/{db,routes,market,portfolio}/`, `backend/tests/{db,routes,market}/`
**Files scanned:** `watchlist.py`, `main.py`, `stream.py`, `health.py`, `cache.py`, `test_watchlist.py`, `test_health.py` (all read in full this session)
**Pattern extraction date:** 2026-09-16
