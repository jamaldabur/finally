# Phase 1: Backend Trading Engine - Research

**Researched:** 2026-09-16
**Domain:** FastAPI + SQLite backend trading engine (portfolio math, trade execution, watchlist mutation)
**Confidence:** HIGH

## Summary

Phase 1 extends the existing, fully-built market data layer (`backend/app/market/`, `backend/app/db/watchlist.py`) with five new SQLite tables and a full read/write trading engine: cash/position persistence, market-order buy/sell execution with average-cost accounting, portfolio valuation, periodic snapshotting for P&L history, and watchlist mutation. There is no frontend in this phase — everything is exercised via HTTP (FastAPI `TestClient`) and pytest.

The codebase's existing conventions are unusually well-documented in code comments and are the primary source of truth for this research: lazy schema init (`CREATE TABLE IF NOT EXISTS` + idempotent seed) per concern-module, sync `sqlite3` wrapped in `asyncio.to_thread()`, state stored on `app.state` (never module globals), `asyncio.Lock`-guarded shared mutable state, and background tasks started via `asyncio.create_task()` inside the `lifespan` context manager and cancelled after `yield`. Phase 1 should **replicate these patterns exactly** for the five new tables rather than introducing a different persistence or concurrency style (e.g. `aiosqlite`, ORM, or a task scheduler library) — `CONCERNS.md` explicitly marks the sync-SQLite-via-threads pattern as accepted debt, not something to fix in this milestone.

The one genuinely new risk this phase introduces is **shared mutable state under concurrency**: `cash_balance` and a ticker's `positions` row must be read-modified-written atomically across a buy/sell, and the existing codebase's only precedent for this (`PriceCache`) uses an `asyncio.Lock`. Trade execution should follow the same pattern with its own lock, because two concurrent trade requests (a real possibility once Phase 3 adds an LLM that can also invoke the same code path) could otherwise race on `cash_balance`.

**Primary recommendation:** One new SQLite table module per concern (`app/db/users_profile.py`, `positions.py`, `trades.py`, `portfolio_snapshots.py`, `chat_messages.py`), all sharing the *existing* `DB_PATH`/`_connect()` defined in `app/db/watchlist.py` (import the function, not the value — see Pitfall 1), a new `app/portfolio/service.py` housing the single trade-validation-and-execution function that both the trade-bar route (this phase) and the chat route (Phase 3) will call, and two new route modules (`app/routes/portfolio.py`, `app/routes/watchlist.py`) wired into `app/main.py` exactly like `health.py`/`stream.py` are today.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DATA-01 | Persist user profile (cash balance, default $10,000) in `users_profile` | Schema §7 quoted below; `app/db/users_profile.py` module pattern |
| DATA-02 | Persist positions (ticker, quantity, avg_cost) in `positions` | Schema §7 quoted below; avg-cost formulas in Code Examples |
| DATA-03 | Append-only trade history in `trades` | Schema §7 quoted below; write-once-on-execution pattern |
| DATA-04 | Portfolio snapshots every 30s + after each trade in `portfolio_snapshots` | Background-task pattern (Architecture Patterns §2); snapshot-on-trade call site in service layer |
| DATA-05 | Persist chat history (role, content, actions) in `chat_messages` | Schema §7 quoted below — table created now, populated in Phase 3 |
| DATA-06 | Watchlist add/remove persisted, extends read-only `watchlist` table | `add_watchlist_ticker`/`remove_watchlist_ticker` design in Architecture Patterns |
| PORT-01 | Market buy order, instant fill, no fees/confirmation | Trade execution flow (Code Examples); price sourced from `PriceCache` |
| PORT-02 | Market sell order, instant fill, no fees/confirmation | Same flow, sell branch |
| PORT-03 | Buy rejected with clear error if cash insufficient | Validation ordering in Code Examples; `TradeResult` error shape |
| PORT-04 | Sell rejected with clear error if shares insufficient | Same, with epsilon-tolerant quantity comparison (Pitfall 4) |
| PORT-05 | `GET /api/portfolio` — positions, cash, total value, unrealized P&L | Response shape in Code Examples |
| PORT-06 | `GET /api/portfolio/history` — value over time | `portfolio_snapshots` read query |
| WLST-01 | `POST /api/watchlist` add, reject unrecognized ticker with 400 | `is_valid_ticker()` reuse (verified in `app/market/base.py`); case-normalization pitfall |
| WLST-02 | `DELETE /api/watchlist/{ticker}` remove | `remove_watchlist_ticker()` design |
| WLST-03 | `GET /api/watchlist` current watchlist with latest prices | Joins `get_watchlist_tickers()` output with `PriceCache.snapshot()` |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **Single Docker container, single port (8000)** — not relevant to this phase's routes directly, but no route should assume multiple processes/workers.
- **SQLite only, no external DB server** — confirmed; extend `sqlite3` stdlib usage, do not introduce Postgres/SQLAlchemy.
- **Market orders only** — no limit orders, no partial fills, no order book. Simplifies trade execution to a single validate-then-apply step.
- **No fees, no confirmation dialogs** — trade executes synchronously within the request; no async approval step.
- **`user_id` hardcoded to `"default"`** on every table — no auth code this phase.
- **SSE over WebSockets; already built** — Phase 1 must not modify `app/routes/stream.py` behavior; it only *reads* from the same `PriceCache` the stream route reads from.
- **`uv` for Python** — `backend/pyproject.toml` is the dependency source of truth; new deps must be added there (see Package Legitimacy Audit — none are actually required this phase).
- **LiteLLM/OpenRouter chat integration** — explicitly Phase 3, not this phase. `chat_messages` table is created now for schema completeness only (per phase description) — do not build `app/llm/` this phase.
- **Litellm-stream skill** — not applicable to Phase 1 (no LLM calls in this phase).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Trade validation & execution | API / Backend | Database / Storage | Business rules (cash/shares sufficiency, avg-cost math) run in-process; persisted result written to SQLite |
| Fill-price lookup | API / Backend | — | Reads the already-in-memory `PriceCache` on `app.state`; no new I/O, no DB round-trip for price |
| Portfolio valuation (P&L, total value) | API / Backend | Database / Storage | Computed on read from `positions` + live `PriceCache`, not stored per-position; `portfolio_snapshots` persists only the aggregate total |
| Watchlist mutation | API / Backend | Database / Storage | Validates against `MarketDataSource.is_valid_ticker()` (in-process), then persists to `watchlist` table |
| Periodic snapshot recording | API / Backend (background task) | Database / Storage | Same lifespan-managed background-task pattern as the existing price update loop |
| Chat history persistence | Database / Storage | — | Phase 1 only creates the table; no read/write logic yet (Phase 3) |

## Standard Stack

### Core

No new runtime dependencies are required. Phase 1 is buildable entirely on what `backend/pyproject.toml` already locks.

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|---------------|
| `fastapi` | `>=0.115` (locked: 0.141.1) [VERIFIED: backend/pyproject.toml:7] | Route definitions, dependency injection via `app.state`, request/response validation | Already the project's only web framework; adding routes follows `health.py`/`stream.py` precedent |
| `pydantic` | 2.13.5, resolved transitively via `fastapi` [VERIFIED: backend/uv.lock:69,243-245 — line 69 lists `{ name = "pydantic" }` under fastapi's dependency block, line 243-245 shows `name = "pydantic"` / `version = "2.13.5"`] | Request/response body models for the new routes | FastAPI's native validation layer; not currently imported anywhere in `app/` [VERIFIED: `grep pydantic\|BaseModel` over `backend/` matched only `backend/uv.lock`] but already installed and importable (confirmed via `uv run python -c "import pydantic"` → `2.13.5`) |
| `sqlite3` (stdlib) | Python 3.12 stdlib | All five new tables | Matches `app/db/watchlist.py`'s existing pattern exactly; `CONCERNS.md` marks moving off sync sqlite3 as explicit non-goal for this milestone |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `uuid` (stdlib) | — | Primary key generation for all new tables (`TEXT PRIMARY KEY`) | Matches `watchlist.py`'s `str(uuid.uuid4())` pattern exactly |
| `datetime` (stdlib) | — | ISO-8601 timestamps for `added_at`/`executed_at`/`recorded_at`/`created_at`/`updated_at` | Matches `datetime.now(timezone.utc).isoformat()` already used in `watchlist.py` |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Sync `sqlite3` + `asyncio.to_thread` | `aiosqlite` | Rejected — `CONCERNS.md` explicitly scopes this as accepted debt not to fix in this milestone; introducing a second DB access style mid-project would be inconsistent, not an improvement |
| Plain Pydantic `BaseModel`s per route | A shared `app/schemas.py` module | Either works; `app/schemas.py` (or per-domain `app/portfolio/schemas.py`, `app/watchlist/schemas.py`) is recommended purely for organization as the model count grows past ~6 |
| Hand-rolled read-modify-write for `positions`/`users_profile` | SQLite `INSERT ... ON CONFLICT DO UPDATE` (upsert) | Recommended for `positions` upsert-on-buy (see Code Examples) — atomic, avoids a separate SELECT+INSERT/UPDATE branch, supported since SQLite 3.24 [CITED: sqlite.org/lang_conflict.html, sqlitetutorial.net/sqlite-upsert] |

**Installation:** None required. If the team wants `pydantic` to appear explicitly (rather than only transitively) in `backend/pyproject.toml`'s `dependencies` list for clarity, add `"pydantic>=2.9"` — optional, not functionally necessary since it's already resolved and importable.

**Version verification:** `fastapi` version confirmed via `backend/pyproject.toml:7` (`fastapi>=0.115`) and `STACK.md`'s prior audit records the resolved version as 0.141.1. `pydantic` version confirmed live this session: `uv run python -c "import pydantic; print(pydantic.VERSION)"` → `2.13.5`, and cross-checked against `backend/uv.lock` lines 243-245.

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|--------------|---------|-------------|
| `pydantic` | PyPI | Latest release 2026-08-28 per registry metadata; project itself is long-established (pre-dates this project by years) | Not reported by the legitimacy tool (`weeklyDownloads: null`) | `github.com/pydantic/pydantic` | `SUS` (heuristic reasons: `too-new`, `unknown-downloads`) | **Approved — heuristic false positive.** `pydantic` is already resolved and locked as a transitive dependency of `fastapi` in `backend/uv.lock` (verified this session, lines 69 and 243-245) and is importable in the project's own `.venv` today (`uv run python -c "import pydantic"` succeeded, version 2.13.5). The "too-new" signal reflects pydantic's latest *release* date, not the package's actual age/trust; no new install action is being taken. No `checkpoint:human-verify` needed. |

**Packages removed due to [SLOP] verdict:** none.
**Packages flagged as suspicious [SUS]:** `pydantic` — flagged above as a heuristic false positive with verification evidence; planner does not need to gate this behind a checkpoint given the in-repo evidence, but may note it in the plan for auditability.

*No other packages were evaluated because no other new packages are required for this phase.*

## Architecture Patterns

### System Architecture Diagram

```
                         ┌────────────────────────────┐
                         │   POST /api/portfolio/trade │
                         │   {ticker, side, quantity}  │
                         └──────────────┬───────────────┘
                                        │
                                        ▼
                         ┌────────────────────────────┐
                         │  app/routes/portfolio.py    │  parses request,
                         │  (thin HTTP adapter)        │  translates TradeResult -> HTTP
                         └──────────────┬───────────────┘
                                        │ await
                                        ▼
        ┌───────────────────────────────────────────────────────┐
        │  app/portfolio/service.py :: execute_trade()           │
        │                                                         │
        │  1. price = await app.state.price_cache.get(ticker)    │  <- reused, NOT re-fetched
        │     -> 400 if None ("no live price; add to watchlist")  │     from market source
        │  2. validate quantity > 0, side in {buy, sell}          │
        │  3. under portfolio lock:                                │
        │       read users_profile.cash_balance                   │
        │       read positions row for ticker (if any)             │
        │       BUY:  cash >= price*qty ? else reject (PORT-03)   │
        │       SELL: position.qty >= qty ? else reject (PORT-04) │
        │       recompute avg_cost (buy) / leave avg_cost (sell)   │
        │       upsert positions, update users_profile.cash_balance│
        │       insert trades row (append-only)                    │
        │       insert portfolio_snapshots row (immediate, DATA-04)│
        └───────────────────────────────┬───────────────────────┘
                                        │
                                        ▼
                         ┌────────────────────────────┐
                         │   SQLite (db/finally.db)    │
                         │   positions / trades /      │
                         │   users_profile /            │
                         │   portfolio_snapshots        │
                         └────────────────────────────┘

  (parallel, independent path)
        app lifespan
          │
          ▼
  asyncio.create_task(run_portfolio_snapshot_loop())  <- every 30s (DATA-04)
          │  reads: users_profile.cash_balance, positions x PriceCache
          ▼
  writes: portfolio_snapshots row

  GET /api/portfolio  ─────►  reads users_profile + positions, joins with
                               PriceCache for current price -> computes
                               unrealized P&L / % change on the fly (not stored)

  GET /api/portfolio/history ─────► reads portfolio_snapshots ordered by recorded_at

  GET /api/watchlist  ─────►  reads watchlist table, joins with PriceCache
  POST /api/watchlist  ────►  await market_source.is_valid_ticker(ticker) -> 400 or insert
  DELETE /api/watchlist/{t} ► delete from watchlist table
```

### Recommended Project Structure

```
backend/app/
├── db/
│   ├── watchlist.py          # EXTEND: add add_watchlist_ticker(), remove_watchlist_ticker()
│   │                          #         keep DB_PATH/_connect() here — canonical connection source
│   ├── users_profile.py      # NEW: schema + init_db() + get_cash_balance()/update_cash_balance()
│   ├── positions.py          # NEW: schema + init_db() + get_position()/upsert_position()/delete_position()
│   ├── trades.py             # NEW: schema + init_db() + insert_trade()
│   ├── portfolio_snapshots.py# NEW: schema + init_db() + insert_snapshot()/get_snapshots()
│   └── chat_messages.py      # NEW: schema + init_db() only (Phase 3 adds read/write logic)
├── portfolio/
│   └── service.py            # NEW: execute_trade(), compute_portfolio_view() — the ONE validation
│                              #      path reused by the trade bar (this phase) and chat (Phase 3)
├── routes/
│   ├── portfolio.py          # NEW: GET /api/portfolio, POST /api/portfolio/trade, GET /api/portfolio/history
│   └── watchlist.py          # NEW: GET/POST/DELETE /api/watchlist — thin, calls db/watchlist.py directly
└── main.py                    # EXTEND: register new routers, start snapshot background task in lifespan
```

Note: `app/watchlist/` and `app/llm/` placeholder directories exist [VERIFIED: `ls backend/app/{llm,portfolio,watchlist}` this session — all three contain only `__pycache__`, no `.py` files] but per `STRUCTURE.md`'s own "Where to Add New Code" guidance, watchlist mutation logic is thin enough to live directly in `app/db/watchlist.py` + `app/routes/watchlist.py` without a separate service module — leave `app/watchlist/` unused this phase (it may still get a `__init__.py` if the linter/packaging requires it, but no business logic belongs there). `app/portfolio/` **is** used (for `service.py`) because trade execution has real branching logic that must be shared with Phase 3's chat flow. `app/llm/` stays empty — Phase 3's concern.

### Pattern 1: Per-table module with self-contained schema + idempotent init

**What:** Every new table gets its own file mirroring `app/db/watchlist.py`'s structure: a `_SCHEMA` constant (`CREATE TABLE IF NOT EXISTS ...`), a private sync `_init_*_sync()` run through `asyncio.to_thread`, and an `async def init_db()`.

**When to use:** Every one of the five new tables.

**Example (verified pattern from the existing codebase):**
```python
# Source: backend/app/db/watchlist.py (this session, lines 35-53) — pattern to replicate
_SCHEMA = """
CREATE TABLE IF NOT EXISTS watchlist (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL DEFAULT 'default',
    ticker TEXT NOT NULL,
    added_at TEXT NOT NULL,
    UNIQUE(user_id, ticker)
);
"""

def _init_db_sync() -> None:
    with _connect() as conn:
        conn.execute(_SCHEMA)
        # ... idempotent seed check ...

async def init_db() -> None:
    await asyncio.to_thread(_init_db_sync)
```
Apply the same shape to `users_profile`, `positions`, `trades`, `portfolio_snapshots`, `chat_messages`, using the exact column definitions from `planning/PLAN.md` §7 (quoted verbatim below under Code Examples).

**`app/main.py` lifespan must call every module's `init_db()`** before the update loop or the new snapshot task starts:
```python
await watchlist.init_db()
await users_profile.init_db()
await positions.init_db()
await trades.init_db()
await portfolio_snapshots.init_db()
await chat_messages.init_db()
```
Order among these six calls does not matter — none of PLAN.md §7's table definitions declare a `FOREIGN KEY` constraint (all cross-table references are plain `TEXT` columns, e.g. `positions.ticker`, `trades.user_id`), so SQLite has no creation-order dependency to satisfy. [VERIFIED: PLAN.md §7 schema definitions, quoted in full in Code Examples below, contain no `REFERENCES`/`FOREIGN KEY` clause on any of the six tables]

### Pattern 2: Single shared DB connection helper, reused by function reference (not by value)

**What:** All new `app/db/*.py` modules import the connect *function*, not the `DB_PATH` value, from `watchlist.py`:
```python
from .watchlist import _connect
```
**When to use:** Every new db module's `_init_*_sync()` and CRUD functions.

**Why this exact pattern, not a `connection.py` extraction:** see Pitfall 1 below — this is the only option that requires zero changes to the three existing test files that already monkeypatch `app.db.watchlist.DB_PATH`.

### Pattern 3: Service layer returns a structured result, not an HTTP exception

**What:** `app/portfolio/service.py::execute_trade()` returns a `TradeResult` (or similar dataclass/TypedDict) with `status: Literal["executed", "error"]` and a `reason: str | None` — it does **not** raise `HTTPException` itself.

**When to use:** Any function in `app/portfolio/service.py` that Phase 3's chat flow will also call.

**Why:** PLAN.md §9 requires the chat flow to "annotate each requested trade/watchlist change with its outcome (executed or error + reason)" and return that as structured data *alongside* the chat message — not as a thrown exception that aborts the whole chat response. If `execute_trade()` raises `HTTPException` directly, Phase 3 will have to either catch FastAPI-specific exceptions in non-HTTP code (wrong layering) or refactor this function. Returning a plain result object now avoids that rework.

```python
# app/routes/portfolio.py — the ONLY place that knows about HTTP status codes
result = await execute_trade(app_state, ticker=body.ticker, side=body.side, quantity=body.quantity)
if result.status == "error":
    raise HTTPException(status_code=400, detail=result.reason)
return result.trade
```

### Anti-Patterns to Avoid

- **Re-fetching price from the market source during trade execution:** Trade fills must read from `app.state.price_cache.get(ticker)` (the existing `PriceCache.get()` method, already built for exactly this — its docstring says "Single-ticker lookup — used by trade fill-price resolution" [VERIFIED: backend/app/market/cache.py:48-51, quoted verbatim: `async def get(self, ticker: str) -> PriceTick | None:\n        """Single-ticker lookup — used by trade fill-price resolution."""\n        async with self._lock:\n            return self._latest.get(ticker)`]). Calling `market_source.get_prices([ticker])` directly from trade execution would bypass the single-writer cache discipline the codebase already establishes and could return a different price than what the user's UI is currently displaying.
- **A second `DB_PATH`/`_connect()` per new module:** breaks the existing tests' monkeypatch target (see Pitfall 1).
- **Storing computed P&L/% change as columns on `positions`:** PLAN.md §7's `positions` schema has no such columns (`id`, `user_id`, `ticker`, `quantity`, `avg_cost`, `updated_at` only) — P&L must be computed on read from `positions.avg_cost` + live price, never persisted redundantly (would go stale the instant the price ticks).
- **Deleting a position row by setting `quantity = 0` and leaving the row:** ambiguous with "owns zero shares but is tracked" vs. "never owned this ticker" — PLAN.md doesn't define that state. Delete the row when a sell fully closes the position (see Code Examples).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|--------------|-----|
| Atomic upsert of a `positions` row on buy | Manual `SELECT` then branch `INSERT`/`UPDATE` | SQLite `INSERT ... ON CONFLICT(user_id, ticker) DO UPDATE SET ...` | Atomic within one statement against the existing `UNIQUE(user_id, ticker)` constraint pattern already used by `watchlist` [CITED: sqlite.org/lang_conflict.html] — avoids a TOCTOU window between the SELECT and the write |
| Concurrency control across a buy/sell's read-modify-write of `cash_balance` + `positions` | A hand-rolled retry loop or "just hope requests don't overlap" | An `asyncio.Lock` around the whole validate-and-apply critical section, stored on `app.state` next to `price_cache`, mirroring `PriceCache`'s own `self._lock = asyncio.Lock()` pattern [VERIFIED: backend/app/market/cache.py:20-21, quoted: `def __init__(self) -> None:\n        self._lock = asyncio.Lock()\n        self._latest: dict[str, PriceTick] = {}`] | The codebase already has exactly one precedent for guarding shared mutable state under concurrent async access — reuse it rather than inventing a second concurrency idiom |
| Portfolio value/% change math | A finance library (e.g. `ffn`, `empyrical`) | Plain arithmetic (see Code Examples) | The formulas are two lines each (`(current - avg_cost) * qty`, `(current/avg_cost - 1) * 100`); pulling in a dependency for this is unjustified for a single-user demo |

**Key insight:** Every "don't hand-roll" item above already has a same-codebase precedent (the `UNIQUE` constraint pattern, the `asyncio.Lock` pattern) — the risk in this phase isn't reaching for an exotic external library, it's *not* reusing the patterns already proven in `app/market/`.

## Runtime State Inventory

*(Section included per protocol trigger check — this phase is additive schema/route work, not a rename/refactor/migration. Confirming explicitly: nothing here.)*

- **Stored data:** N/A — no renamed keys/collections/IDs; new tables only, no existing data migrated.
- **Live service config:** N/A — no external services involved.
- **OS-registered state:** N/A.
- **Secrets/env vars:** N/A — no new env vars introduced this phase (`FINALLY_DB_PATH` already exists and is unaffected).
- **Build artifacts:** N/A — no package/module renames.

## Common Pitfalls

### Pitfall 1: A second `DB_PATH` breaks the three existing test monkeypatches
**What goes wrong:** If a new module (e.g. `app/db/positions.py`) defines its *own* `DB_PATH = Path(...)` and `_connect()` (copy-pasting `watchlist.py`'s top), or if `DB_PATH`/`_connect()` are extracted into a new `app/db/connection.py` and `watchlist.py` does `from .connection import DB_PATH`, then `monkeypatch.setattr("app.db.watchlist.DB_PATH", tmp_path / "finally.db")` — used in three existing test files — silently stops isolating the database. Tests would write to (or worse, read stale state from) the real `db/finally.db` instead of a throwaway path, or (if `DB_PATH` is removed from `watchlist.py` entirely) the `monkeypatch.setattr` calls raise `AttributeError` since none of the three call sites pass `raising=False`.
**Why it happens:** `monkeypatch.setattr(module, "X", value)` only ever patches the attribute binding *on that specific module object*. `from other_module import X` copies the reference at import time into the importing module's own namespace — patching the origin later does not propagate.
**How to avoid:** Keep `DB_PATH` and `_connect()` defined exactly where they are today, in `app/db/watchlist.py`. Every new db module does `from .watchlist import _connect` and calls the **function** (never reads `DB_PATH` as a value itself). Because `_connect()`'s body reads the module-global `DB_PATH` name at *call time* (Python late-binding), any module invoking `watchlist._connect()` — even indirectly via `from .watchlist import _connect` — correctly picks up whatever `watchlist.DB_PATH` currently is, including a monkeypatched value, with zero changes to the three existing test files.
**Warning signs:** A new test passes locally but writes to the real `db/finally.db`; existing watchlist tests start failing after adding new db modules; `AttributeError: <module 'app.db.watchlist'> does not have the attribute 'DB_PATH'`.
**Verified test call sites that constrain this:** `backend/tests/test_main.py:12,29`, `backend/tests/db/test_watchlist.py:11`, `backend/tests/routes/test_health.py:7` — all four patch `app.db.watchlist.DB_PATH` [VERIFIED: grep across `backend/tests/` this session, all four lines quoted: `monkeypatch.setattr("app.db.watchlist.DB_PATH", tmp_path / "finally.db")` (test_main.py x2, test_health.py x1) and `monkeypatch.setattr(watchlist_module, "DB_PATH", tmp_path / "finally.db")` (test_watchlist.py)].

### Pitfall 2: Ticker case-sensitivity on watchlist add
**What goes wrong:** `TICKER_UNIVERSE` keys are uppercase (`"AAPL"`, `"GOOGL"`, ...) [VERIFIED: backend/app/market/simulator.py:37-67, keys quoted: `"AAPL"`, `"GOOGL"`, `"MSFT"`, `"AMZN"`, `"NVDA"`, `"META"`, `"ORCL"`, `"CRM"`, `"AMD"`, `"CSCO"`, `"JPM"`, `"V"`, `"BAC"`, `"GS"`, `"MA"`, `"PYPL"`, `"TSLA"`, `"NFLX"`, `"DIS"`, `"NKE"`, `"SBUX"`, `"PEP"`, `"KO"`, `"COST"`, `"JNJ"`, `"PFE"`, `"UNH"`, `"LLY"`, `"XOM"`, `"CVX"`]. `is_valid_ticker()` does `ticker in TICKER_UNIVERSE` [VERIFIED: backend/app/market/simulator.py:119-120: `async def is_valid_ticker(self, ticker: str) -> bool:\n        return ticker in TICKER_UNIVERSE`] — a plain, case-sensitive dict membership check. A user or the LLM (Phase 3) submitting `"aapl"` gets rejected as invalid even though `AAPL` is clearly supported.
**Why it happens:** No normalization exists anywhere in the current codebase (the watchlist seed data is inserted pre-normalized from `DEFAULT_WATCHLIST`, which is already uppercase).
**How to avoid:** Normalize (`ticker.strip().upper()`) in the route handler (`app/routes/watchlist.py`) before calling `is_valid_ticker()` and before persisting/deleting, so the stored, validated, and displayed ticker string is always canonical uppercase.
**Warning signs:** WLST-01 tests pass for `"AAPL"` but a lowercase-input test (if the planner adds one) fails with an unexpected 400.

### Pitfall 3: Trading a ticker not currently on the watchlist has no price to fill at
**What goes wrong:** `run_update_loop` only fetches prices for `await get_watchlist_tickers()` [VERIFIED: backend/app/market/loop.py:29-38, quoted: `tickers = await get_watchlist_tickers()\n            if tickers:\n                prices = await source.get_prices(tickers)\n                for ticker, price in prices.items():\n                    await cache.update(ticker, price)`]. `PriceCache` therefore only ever holds ticks for tickers currently on someone's watchlist. If a trade request names a ticker that is `is_valid_ticker()`-valid (in `TICKER_UNIVERSE`) but not on the watchlist, `cache.get(ticker)` returns `None` — there is no price to fill the market order at.
**Why it happens:** Ticker validity (can it ever be traded/watched) and ticker "livened" (is it currently being priced) are two different concepts in this codebase, and PLAN.md doesn't explicitly reconcile them for the trade endpoint.
**How to avoid:** In `execute_trade()`, treat "no cached price" as its own 400 error distinct from insufficient-cash/insufficient-shares, e.g. `"No live price available for {ticker} — add it to your watchlist first."` This is a genuine open question the planner should confirm with the user rather than silently deciding (see Open Questions).
**Warning signs:** A trade for a technically-valid-but-unwatched ticker either 500s (`NoneType` used as a number) or silently fills at a stale/zero price if this isn't handled explicitly.

### Pitfall 4: Float equality for "position fully closed"
**What goes wrong:** `positions.quantity` is `REAL` (fractional shares supported per PLAN.md §7). After a sell, checking `new_qty == 0` to decide whether to delete the row is unreliable with floating point (e.g. `10.1 - 10.1` may not be bit-exact `0.0` after intermediate float ops, though in this specific subtraction it usually is — the risk compounds across multiple partial buys/sells feeding into the average).
**Why it happens:** Standard IEEE-754 float behavior; the existing codebase already documents awareness of float precision risk elsewhere ("Cent precision, rounded once here... so no float-precision flicker reaches the frontend" [VERIFIED: backend/app/market/simulator.py:110-114, quoted: `# Cent precision, rounded once here (not per-read), so every\n            # consumer sees the same value and no float-precision flicker\n            # reaches the frontend. GBM is multiplicative, so prices can\n            # never go negative — no floor/clamp needed.\n            self._prices[ticker] = round(new_price, 2)`]) but that precedent covers *prices*, not *quantities* — there is no existing precedent for comparing summed fractional-share quantities.
**How to avoid:** Use an epsilon tolerance, e.g. `abs(new_qty) < 1e-9`, when deciding whether a sell fully closes a position (delete row) vs. leaves a residual (update row). Reject a sell whose `quantity` exceeds the held quantity using the same tolerance (`sell_qty > position.quantity + 1e-9` → reject), so a sell-all request expressed as a slightly-imprecise float doesn't spuriously fail PORT-04.
**Warning signs:** A "sell all shares" trade leaves a `positions` row with `quantity: 1e-14` instead of deleting it; `GET /api/portfolio` shows a phantom near-zero position.

### Pitfall 5: Forgetting to cancel the new background task on shutdown
**What goes wrong:** `app/main.py`'s `lifespan` already has one `asyncio.create_task(...)` for the price update loop, explicitly cancelled after `yield`: `update_task.cancel(); await source.stop()` [VERIFIED: backend/app/main.py:36-49, quoted: `update_task = asyncio.create_task(\n        run_update_loop(source, cache, get_watchlist_tickers, interval)\n    )\n    ...\n    yield\n\n    update_task.cancel()\n    await source.stop()`]. Adding the 30-second snapshot task without also storing its reference and cancelling it after `yield` leaves a dangling task on shutdown (harmless in a single dev process, but a task leak / resource warning under test-suite teardown where many `TestClient` instances are created and destroyed across the test run).
**Why it happens:** Easy to add a second `asyncio.create_task(...)` call and forget the matching cancel — there's no automatic cleanup for tasks not tracked.
**How to avoid:** Store the new task the same way: `snapshot_task = asyncio.create_task(run_portfolio_snapshot_loop(...)); ... ; snapshot_task.cancel()` alongside the existing `update_task.cancel()`.
**Warning signs:** `pytest` warnings about "Task was destroyed but it is pending" when running the new test suite; test isolation issues from a snapshot loop writing to the *next* test's throwaway DB path after teardown.

### Pitfall 6: `init_db()` for the new tables must run before the new background task starts
**What goes wrong:** If `run_portfolio_snapshot_loop`'s task is created before `users_profile.init_db()`/`positions.init_db()` complete, its first tick could hit `sqlite3.OperationalError: no such table` — mirrors the exact hazard `watchlist.py`'s own test documents: `test_get_watchlist_tickers_before_init_is_empty_not_an_error` explicitly shows querying before `init_db()` raises [VERIFIED: backend/tests/db/test_watchlist.py:30-40, quoted: `with pytest.raises(Exception):\n        # Querying a table that was never created does raise (sqlite3\n        # OperationalError) — this documents that init_db() is a required\n        # precondition, not something get_watchlist_tickers() defends against\n        # itself. app/main.py's lifespan always calls init_db() first.\n        await watchlist_module.get_watchlist_tickers()`].
**Why it happens:** Ordering in `lifespan` is manual; nothing enforces "all `init_db()` calls before any task creation" except discipline.
**How to avoid:** In `app/main.py`'s `lifespan`, call every table module's `init_db()` (all six, including the now-extended `watchlist.init_db()`) before `asyncio.create_task(run_update_loop(...))` and before `asyncio.create_task(run_portfolio_snapshot_loop(...))`.
**Warning signs:** Intermittent startup failures that only reproduce when the snapshot task's first tick races app startup.

## Code Examples

### Verbatim schema definitions (source of truth: `planning/PLAN.md` §7)

These are the exact column definitions Phase 1 must implement — quoted verbatim, not paraphrased, per PLAN.md §7 (already loaded into this session via the project's `CLAUDE.md` `@planning/PLAN.md` include):

```
users_profile — User state (cash balance)
- id TEXT PRIMARY KEY (default: "default")
- cash_balance REAL (default: 10000.0)
- created_at TEXT (ISO timestamp)

positions — Current holdings (one row per ticker per user)
- id TEXT PRIMARY KEY (UUID)
- user_id TEXT (default: "default")
- ticker TEXT
- quantity REAL (fractional shares supported)
- avg_cost REAL
- updated_at TEXT (ISO timestamp)
- UNIQUE constraint on (user_id, ticker)

trades — Trade history (append-only log)
- id TEXT PRIMARY KEY (UUID)
- user_id TEXT (default: "default")
- ticker TEXT
- side TEXT ("buy" or "sell")
- quantity REAL (fractional shares supported)
- price REAL
- executed_at TEXT (ISO timestamp)

portfolio_snapshots — Portfolio value over time (for P&L chart). Recorded every 30
seconds by a background task, and immediately after each trade execution. Rows are
never pruned.
- id TEXT PRIMARY KEY (UUID)
- user_id TEXT (default: "default")
- total_value REAL
- recorded_at TEXT (ISO timestamp)

chat_messages — Conversation history with LLM
- id TEXT PRIMARY KEY (UUID)
- user_id TEXT (default: "default")
- role TEXT ("user" or "assistant")
- content TEXT
- actions TEXT (JSON — trades executed, watchlist changes made; null for user messages)
- created_at TEXT (ISO timestamp)
```

Translate each into a `CREATE TABLE IF NOT EXISTS` matching `watchlist`'s SQL style (`TEXT`/`REAL` types, inline `UNIQUE(...)` where specified, no `FOREIGN KEY` clauses — none are specified in PLAN.md §7).

### Average-cost accounting (buy)

```python
# On a BUY of `buy_qty` shares at `fill_price`:
if existing_position is None:
    new_qty = buy_qty
    new_avg_cost = fill_price
else:
    new_qty = existing_position.quantity + buy_qty
    new_avg_cost = (
        existing_position.avg_cost * existing_position.quantity
        + fill_price * buy_qty
    ) / new_qty
# cash_balance -= fill_price * buy_qty
```
Standard weighted-average cost basis: `average_price = total_cost / total_shares`, with each purchase's price weighted by its own share count [CITED: omnicalculator.com/finance/stock-average, inchcalculator.com/stock-average-calculator — both describe the same `(p1*s1 + p2*s2 + ... ) / (s1 + s2 + ...)` formula].

### Average-cost accounting (sell) — avg_cost does NOT change

```python
# On a SELL of `sell_qty` shares at `fill_price`:
# avg_cost is UNCHANGED by a sell under the average-cost method — selling
# realizes P&L against the existing average, it doesn't alter the average
# for the shares that remain.
new_qty = existing_position.quantity - sell_qty
if abs(new_qty) < 1e-9:
    # fully closed — DELETE the row, don't leave a zero-quantity row
    delete_position(user_id, ticker)
else:
    update_position(user_id, ticker, quantity=new_qty, avg_cost=existing_position.avg_cost)
# cash_balance += fill_price * sell_qty
# realized_pnl_this_trade = (fill_price - existing_position.avg_cost) * sell_qty  (not persisted
#   anywhere per PLAN.md §7 — no realized_pnl column exists on any table; compute only if the
#   route response needs to surface it, otherwise it's derivable from the trades log at read time)
```
[CITED: SQLite upsert docs (sqlite.org/lang_conflict.html) for the atomic upsert form on buy; average-cost-does-not-change-on-sell is standard brokerage accounting, confirmed via WebSearch this session against multiple cost-basis explainer sources]

### Unrealized P&L / % change (computed on every `GET /api/portfolio` read, never persisted)

```python
unrealized_pnl = (current_price - position.avg_cost) * position.quantity
pct_change = (current_price / position.avg_cost - 1) * 100 if position.avg_cost else 0.0
total_value = cash_balance + sum(
    position.quantity * price_cache_lookup(position.ticker) for position in positions
)
```

### SQLite upsert for `positions` on buy

```python
# Source: SQLite ON CONFLICT documentation (sqlite.org/lang_conflict.html), adapted to
# this project's TEXT-id/UUID pattern — positions has UNIQUE(user_id, ticker) per PLAN.md §7
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
Note: the caller must compute `new_qty`/`new_avg_cost` in Python first (reading the existing row within the same locked critical section) since the upsert's `excluded.*` values are exactly what you pass in — SQLite's `ON CONFLICT DO UPDATE` does not itself do the weighted-average math.

### Periodic background task, following the existing lifespan/update-loop pattern

```python
# Source: backend/app/main.py (this session, lines 23-56) — pattern to replicate for the
# 30-second portfolio_snapshots task (DATA-04), confirmed against the general FastAPI
# lifespan + asyncio.create_task() idiom [CITED: shiporkill.com/blog/fastapi-lifespan-pattern,
# techoral.com/python/fastapi-background-tasks.html]
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()               # existing: watchlist
    await users_profile.init_db()
    await positions.init_db()
    await trades.init_db()
    await portfolio_snapshots.init_db()
    await chat_messages.init_db()

    source = build_market_data_source()
    cache = PriceCache()
    await source.start()

    update_task = asyncio.create_task(run_update_loop(source, cache, get_watchlist_tickers, interval))
    snapshot_task = asyncio.create_task(run_portfolio_snapshot_loop(cache, interval_seconds=30))

    app.state.market_source = source
    app.state.price_cache = cache
    app.state.portfolio_lock = asyncio.Lock()   # new — guards trade execution critical section

    yield

    update_task.cancel()
    snapshot_task.cancel()
    await source.stop()
```

## State of the Art

Not applicable in the "framework changed recently" sense — this is standard, stable FastAPI/SQLite/Python patterns. No deprecated approaches identified; the codebase's existing conventions (verified this session) are themselves current best practice for this stack.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|-----------------|
| A1 | Trading a ticker not currently on the watchlist should be rejected with a distinct 400 ("no live price, add to watchlist first") rather than implicitly auto-adding it to the watchlist | Pitfall 3, Open Questions | If the intended behavior is auto-add-then-fill, the planner needs a different trade-route design (calling the watchlist-add path before/within `execute_trade()`) |
| A2 | `trades` (append-only log) only receives a row on **successful** execution, not on rejected/error attempts | Code Examples, PORT-03/04 | If rejected attempts should also be logged (e.g. for an audit trail), schema is unaffected but `execute_trade()`'s write path needs an extra branch |
| A3 | `GET /api/portfolio` response includes per-position `unrealized_pnl`/`pct_change` computed on read (not stored); PLAN.md §10 (frontend) references these same fields for the positions table, but §8 doesn't give an exact JSON shape for `GET /api/portfolio` | Code Examples, PORT-05 | Low risk — any reasonable JSON shape satisfies PORT-05's requirement ("positions, cash balance, total value, unrealized P&L"); mainly affects Phase 2's frontend integration ease |
| A4 | New `app/db/*.py` modules should import `_connect` from `watchlist.py` (Pattern 2) rather than the team choosing to do a proper `connection.py` extraction + update the 3 existing test monkeypatch targets | Pitfall 1, Architecture Patterns | Low risk either way — both are functionally correct; A4 is a maintainability/elegance tradeoff (semantic awkwardness of `positions.py` depending on `watchlist.py`) vs. a slightly larger diff (editing 3 test files). Flagging so the planner can consciously choose. |

**If this table is empty:** N/A — see entries above; all are moderate-confidence design recommendations resting on reasonable inference from PLAN.md + existing code, not hard external facts, so tagging them for confirmation is appropriate rather than asserting them as locked.

## Open Questions

1. **Should a trade for a valid-but-unwatched ticker auto-add it to the watchlist, or reject outright?**
   - What we know: `PriceCache` only holds prices for watchlist tickers (verified in `loop.py`); PLAN.md §8 only specifies watchlist-add rejects *invalid* tickers, and is silent on the trade endpoint's behavior for valid-but-unwatched tickers.
   - What's unclear: Whether "instant fill" (PORT-01/02) is expected to work for any of the 30 `TICKER_UNIVERSE` tickers, or only for watchlist tickers.
   - Recommendation: Reject with a clear 400 (simplest, matches "market orders only, no magic side effects" spirit of the spec) unless the user/planner decides otherwise during plan review. This is Assumption A1.

2. **Exact JSON response shape for `GET /api/portfolio` and `GET /api/portfolio/history`.**
   - What we know: PLAN.md §8 names the endpoints and gives a prose description of their contents; §10 (frontend) lists the fields the positions table needs (ticker, qty, avg cost, current price, unrealized P&L, % change).
   - What's unclear: No exact field names/JSON schema is specified anywhere in PLAN.md.
   - Recommendation: The planner should lock a concrete Pydantic response model as part of plan authoring (using the field list in Code Examples as a starting point) since Phase 2 (frontend) will consume this contract directly.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|--------------|-----------|---------|----------|
| `uv` | Running/testing the backend | ✓ | 0.10.9 [VERIFIED: `uv --version` this session] | — |
| Python 3.12 (via `uv`) | Backend runtime | ✓ | Managed by `uv`; `requires-python = ">=3.12"` in `backend/pyproject.toml` [VERIFIED: backend/pyproject.toml:5] | — |
| `pytest` / `pytest-asyncio` | Test suite (nyquist validation) | ✓ | `pytest>=8.0`, `pytest-asyncio>=0.24` [VERIFIED: backend/pyproject.toml:14-15]; 73 tests currently collect successfully (`uv run pytest --collect-only` this session) | — |
| SQLite (stdlib `sqlite3`) | All persistence this phase | ✓ | Bundled with Python 3.12 | — |
| Docker | Not needed this phase (Phase 5) | — | — | — |
| Node.js | Not needed this phase (no frontend) | ✓ (v22.13.0 present) [VERIFIED: `node --version` this session] | — | — |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** none — everything this phase needs is already present and verified working in the local environment.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ with pytest-asyncio 0.24+ (`asyncio_mode = "auto"`) [VERIFIED: backend/pyproject.toml:20-23] |
| Config file | `backend/pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `cd backend && uv run pytest tests/db tests/portfolio tests/routes -q` |
| Full suite command | `cd backend && uv run pytest` (73 tests currently pass; this phase adds more) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|---------------------|--------------|
| DATA-01 | `users_profile` schema created + seeded with $10,000 | unit | `uv run pytest tests/db/test_users_profile.py -x` | ❌ Wave 0 |
| DATA-02 | `positions` schema created, UNIQUE(user_id, ticker) enforced | unit | `uv run pytest tests/db/test_positions.py -x` | ❌ Wave 0 |
| DATA-03 | `trades` schema created, append-only insert works | unit | `uv run pytest tests/db/test_trades.py -x` | ❌ Wave 0 |
| DATA-04 | Snapshot recorded every 30s + immediately after trade | unit + integration | `uv run pytest tests/db/test_portfolio_snapshots.py tests/portfolio/test_service.py -x` | ❌ Wave 0 |
| DATA-05 | `chat_messages` schema created (unused this phase) | unit | `uv run pytest tests/db/test_chat_messages.py -x` | ❌ Wave 0 |
| DATA-06 | `add_watchlist_ticker`/`remove_watchlist_ticker` persist | unit | `uv run pytest tests/db/test_watchlist.py -x` (extend existing file) | ✓ (extend) |
| PORT-01/02 | Buy/sell market order fills at cached price, updates cash+positions | unit | `uv run pytest tests/portfolio/test_service.py -x` | ❌ Wave 0 |
| PORT-03 | Buy rejected, insufficient cash | unit | `uv run pytest tests/portfolio/test_service.py -k insufficient_cash -x` | ❌ Wave 0 |
| PORT-04 | Sell rejected, insufficient shares | unit | `uv run pytest tests/portfolio/test_service.py -k insufficient_shares -x` | ❌ Wave 0 |
| PORT-05 | `GET /api/portfolio` shape + values | integration (route) | `uv run pytest tests/routes/test_portfolio.py -x` | ❌ Wave 0 |
| PORT-06 | `GET /api/portfolio/history` returns snapshots | integration (route) | `uv run pytest tests/routes/test_portfolio.py -k history -x` | ❌ Wave 0 |
| WLST-01 | `POST /api/watchlist` add, 400 on unrecognized ticker | integration (route) | `uv run pytest tests/routes/test_watchlist.py -x` | ❌ Wave 0 |
| WLST-02 | `DELETE /api/watchlist/{ticker}` remove | integration (route) | `uv run pytest tests/routes/test_watchlist.py -k delete -x` | ❌ Wave 0 |
| WLST-03 | `GET /api/watchlist` with latest prices | integration (route) | `uv run pytest tests/routes/test_watchlist.py -k get -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** the relevant quick-run subset (e.g. `uv run pytest tests/portfolio -q` after a trade-execution task)
- **Per wave merge:** `cd backend && uv run pytest` (full suite)
- **Phase gate:** full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/conftest.py` — shared `isolated_db` fixture (currently duplicated per-file in `test_watchlist.py`, `test_main.py`, `test_health.py`; with 5+ new table modules this duplication grows significantly — worth centralizing now) [Confirmed no `conftest.py` currently exists anywhere under `backend/tests/` this session]
- [ ] `backend/tests/db/test_users_profile.py`, `test_positions.py`, `test_trades.py`, `test_portfolio_snapshots.py`, `test_chat_messages.py` — one per new table
- [ ] `backend/tests/portfolio/test_service.py` — trade execution logic, avg-cost math, insufficient-cash/shares edge cases
- [ ] `backend/tests/routes/test_portfolio.py` — new route module
- [ ] `backend/tests/routes/test_watchlist.py` — new route module (distinct from the existing `tests/db/test_watchlist.py`, which tests the db layer only)
- [ ] Framework install: none — pytest/pytest-asyncio already present

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|----------------|---------|---------------------|
| V2 Authentication | No | Out of scope — single hardcoded `user_id="default"`, no auth this milestone per REQUIREMENTS.md "Out of Scope" |
| V3 Session Management | No | Same as above |
| V4 Access Control | No | Same as above — no per-user isolation to enforce yet |
| V5 Input Validation | **Yes** | Pydantic request models (`quantity: float = Field(gt=0)`, `side: Literal["buy", "sell"]`, ticker normalization per Pitfall 2) on every new route body |
| V6 Cryptography | No | No secrets/crypto introduced this phase |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|------------------------|
| SQL injection via ticker/quantity in raw SQL strings | Tampering | Parameterized queries with `?` placeholders — already the established pattern in `watchlist.py` [VERIFIED: backend/app/db/watchlist.py:54-56,60-61,67-69, all three SQL statements use `?` placeholders with a separate params tuple, e.g. `conn.execute("SELECT COUNT(*) FROM watchlist WHERE user_id = ?", (DEFAULT_USER_ID,))`]; every new query must follow the same style, never f-string/`.format()` interpolation of user input into SQL |
| Race condition on concurrent trade requests double-spending cash or over-selling shares | Tampering | `asyncio.Lock` around the full validate-and-apply critical section in `execute_trade()` (see Don't Hand-Roll, Architecture Patterns) |
| Negative or zero trade quantity accepted | Tampering / Repudiation | Pydantic `Field(gt=0)` on the request model rejects at the FastAPI validation layer before it reaches business logic |
| Unrecognized/malformed ticker accepted into `positions`/`trades` | Tampering | Reuse `is_valid_ticker()` (already required by WLST-01) for any ticker that reaches persistence — including trade execution, not just watchlist add |
| Float/JSON precision on `quantity`/`price` fields silently truncating fractional shares | Tampering (data integrity) | Use `float`/`REAL` consistently end-to-end (Pydantic `float`, SQLite `REAL`); avoid casting through `int` anywhere in the trade path |

## Sources

### Primary (HIGH confidence)
- `backend/app/db/watchlist.py`, `backend/app/main.py`, `backend/app/market/cache.py`, `backend/app/market/base.py`, `backend/app/market/simulator.py`, `backend/app/market/loop.py`, `backend/app/routes/stream.py`, `backend/app/routes/health.py`, `backend/tests/db/test_watchlist.py`, `backend/tests/test_main.py`, `backend/tests/routes/test_health.py`, `backend/pyproject.toml`, `backend/uv.lock` — all read directly this session
- `planning/PLAN.md` §§3-11 (loaded via project `CLAUDE.md` include) — authoritative spec, schema, API contract
- `.planning/REQUIREMENTS.md`, `.planning/STATE.md`, `.planning/PROJECT.md`, `.planning/codebase/{ARCHITECTURE,STACK,CONVENTIONS,CONCERNS,STRUCTURE}.md` — read this session

### Secondary (MEDIUM confidence)
- SQLite `ON CONFLICT` / upsert syntax — sqlite.org/lang_conflict.html, sqlitetutorial.net/sqlite-upsert (WebSearch, cross-checked against multiple independent pages, standard/stable SQL feature since SQLite 3.24)
- FastAPI lifespan + `asyncio.create_task()` periodic background task pattern — shiporkill.com/blog/fastapi-lifespan-pattern, techoral.com/python/fastapi-background-tasks.html (WebSearch; confirmed this matches the exact pattern already implemented in `app/main.py`, so treated as corroborating an already-verified in-repo pattern rather than introducing a new one)
- Weighted-average cost basis formula — omnicalculator.com/finance/stock-average, inchcalculator.com/stock-average-calculator (WebSearch; standard, uncontested brokerage-accounting formula)
- FastAPI Pydantic request/response model conventions — fastapi.tiangolo.com/tutorial/response-model/ and related pages (WebSearch)

### Tertiary (LOW confidence)
- None used without cross-checking — all WebSearch findings above were corroborated across multiple independent result pages before being cited.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; extending an already-verified, already-tested in-repo pattern
- Architecture: HIGH — directly derived from reading the actual source files this session, not inferred
- Pitfalls: HIGH for Pitfalls 1, 3, 5, 6 (all directly verified against source/tests this session); MEDIUM for Pitfalls 2 and 4 (correct reasoning from verified facts, but the specific failure mode is a prediction, not something reproduced this session)

**Research date:** 2026-09-16
**Valid until:** 2026-10-16 (30 days — stable stdlib/FastAPI/SQLite patterns, no fast-moving dependencies in this phase)
