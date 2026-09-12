# MARKET_INTERFACE.md — Unified Market Data Interface Design

This document specifies the abstract Python interface that both the market simulator
(`MARKET_SIMULATOR.md`) and the Massive-backed client (`MASSIVE_API.md`) implement, per
`PLAN.md` §6 ("Two Implementations, One Interface"). It is the shared contract the rest of the
backend (SSE streaming, watchlist validation, trade execution) codes against — nothing downstream
should ever import or branch on `SimulatorMarketDataSource` vs. `MassiveMarketDataSource`
directly.

This document also resolves three open ambiguities carried over from `REVIEW.md` Review 1
(§A1/A2, §B1, §B2), since they all live at this interface boundary. Each resolution is called out
inline where relevant.

---

## 1. Design Goals

- One `MarketDataSource` abstract interface; two concrete implementations selected at startup by
  environment variable, per `PLAN.md` §5.
- Everything above the interface — the price cache, the SSE stream, watchlist validation, trade
  fills — is source-agnostic. Swapping simulator ↔ Massive should never require touching any of
  those layers.
- The interface is intentionally small: it needs to support exactly what FinAlly does (poll/stream
  a watchlist's worth of tickers, validate whether a ticker can be added), not the full breadth of
  either backend's real capabilities.

---

## 2. The Abstract Interface

```python
# backend/app/market/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class ChangeDirection(str, Enum):
    UP = "up"
    DOWN = "down"
    UNCHANGED = "unchanged"


@dataclass(frozen=True)
class PriceTick:
    ticker: str
    price: float
    previous_price: float
    timestamp: datetime
    direction: ChangeDirection


class MarketDataSource(ABC):
    """Common interface for both the simulator and the Massive-backed client.

    Exactly one instance of one implementation is constructed at app startup
    (see §5) and driven by a single background task that feeds the shared
    PriceCache (§3). No other code should hold a reference to more than one
    MarketDataSource instance at a time.
    """

    @abstractmethod
    async def start(self) -> None:
        """Called once at app startup. Simulator: spawns its internal tick
        loop. Massive: performs no polling itself — see §4 for why polling
        is driven externally for that implementation."""

    @abstractmethod
    async def stop(self) -> None:
        """Called once at app shutdown. Releases any resources (HTTP client,
        background tasks)."""

    @abstractmethod
    async def get_prices(self, tickers: list[str]) -> dict[str, float]:
        """Return the latest known price for each requested ticker. Tickers
        this source has no data for are simply omitted from the result dict
        — callers must not treat a missing key as an error."""

    @abstractmethod
    async def is_valid_ticker(self, ticker: str) -> bool:
        """Whether `ticker` can be added to the watchlist under this data
        source. See §6 for what 'valid' means for each implementation —
        it differs by design, not by oversight."""
```

`get_prices` and `is_valid_ticker` are `async` even though the simulator's implementations are
synchronous in practice (in-memory dict lookups) — this keeps the interface uniform, since the
Massive implementation's `is_valid_ticker` genuinely needs to make a network call (§6.2).

---

## 3. The Shared Price Cache

The cache is the single source of truth that the SSE endpoint reads from. It is populated by
whichever `MarketDataSource` is active, and it — not the data source — is what computes
"previous price" and "direction," because that comparison (§4 of `PLAN.md`'s SSE section) is
about *what the frontend has already seen*, not about anything either backend knows natively.

```python
# backend/app/market/cache.py
import asyncio
from datetime import datetime, timezone

from .base import ChangeDirection, PriceTick


class PriceCache:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._latest: dict[str, PriceTick] = {}

    async def update(self, ticker: str, price: float) -> PriceTick:
        """Record a new observed price. If it equals the last known price,
        the emitted tick keeps the OLD previous_price/direction rather than
        collapsing to UNCHANGED-vs-itself — see the worked example below."""
        async with self._lock:
            prior = self._latest.get(ticker)
            now = datetime.now(timezone.utc)
            if prior is None:
                tick = PriceTick(ticker, price, price, now, ChangeDirection.UNCHANGED)
            elif price == prior.price:
                # Heartbeat with no real change: keep the last *different*
                # previous_price so the frontend's price !== previous_price
                # flash check still reflects the last real move, not this
                # no-op tick. Direction likewise carries forward unchanged.
                tick = PriceTick(ticker, price, prior.previous_price, now, prior.direction)
            else:
                direction = ChangeDirection.UP if price > prior.price else ChangeDirection.DOWN
                tick = PriceTick(ticker, price, prior.price, now, direction)
            self._latest[ticker] = tick
            return tick

    async def snapshot(self) -> list[PriceTick]:
        """All tickers currently tracked, for one SSE broadcast tick."""
        async with self._lock:
            return list(self._latest.values())

    async def get(self, ticker: str) -> PriceTick | None:
        async with self._lock:
            return self._latest.get(ticker)
```

Worked example (this is the mechanism behind `PLAN.md`'s "`previous price` reflects the last
*different* price, not simply the prior event" requirement):

| Tick | Incoming price | Stored `price` | Stored `previous_price` | Frontend flashes? |
|---|---|---|---|---|
| 1 | 190.00 | 190.00 | 190.00 | no (first tick) |
| 2 | 190.42 | 190.42 | 190.00 | **yes** (190.42 ≠ 190.00) |
| 3 | 190.42 (heartbeat, no change) | 190.42 | 190.00 (carried forward) | **yes** — wait, see note below |

Note on row 3: the frontend's own flash logic compares the *current SSE event's* `price` against
*that same event's* `previous_price`. Since row 3's event still reports `previous_price: 190.00`
while `price: 190.42`, a naive frontend re-check would flash again on an unchanged price. To
prevent that, the frontend must track the last price it already rendered client-side (trivial — it
already has to, to draw the sparkline) and only flash when the incoming `price` differs from *that*,
not from the event's `previous_price` field. The `previous_price` field's job is solely to let the
frontend compute daily-change-style deltas correctly across reconnects, not to gate the flash
animation by itself. **This is a frontend implementation detail worth stating explicitly in
`PLAN.md` §10 or the Frontend agent's notes**, since it's a subtle point where a literal reading of
the SSE payload could produce a flashing-every-heartbeat bug.

---

## 4. Background Task & Update Loop

One asyncio background task per running app, started at FastAPI startup:

```python
# backend/app/market/loop.py
import asyncio

from .base import MarketDataSource
from .cache import PriceCache

SIMULATOR_TICK_SECONDS = 0.5   # matches PLAN.md §6 "~500ms"
MASSIVE_POLL_SECONDS = 15      # matches PLAN.md §6 free-tier cadence

async def run_update_loop(
    source: MarketDataSource,
    cache: PriceCache,
    get_watchlist_tickers: callable,  # async () -> list[str], reads current watchlist from DB
    interval_seconds: float,
) -> None:
    while True:
        tickers = await get_watchlist_tickers()
        if tickers:
            prices = await source.get_prices(tickers)
            for ticker, price in prices.items():
                await cache.update(ticker, price)
        await asyncio.sleep(interval_seconds)
```

- **Simulator**: `interval_seconds=0.5`. `source.get_prices` is a cheap in-memory GBM step —
  see `MARKET_SIMULATOR.md`.
- **Massive**: `interval_seconds=15` (free tier) — `source.get_prices` makes one snapshot API call
  for the whole watchlist (`MASSIVE_API.md` §3.1), regardless of how many tickers are watched, up
  to Massive's 250-ticker snapshot limit (never a concern at this project's scale).
- This is why `MarketDataSource.start()`/`stop()` are separate from the loop itself: `start()` is
  for implementation-internal setup (simulator: nothing beyond `__init__`; Massive: constructing
  the shared `httpx.AsyncClient`), while `run_update_loop` — a plain function, not a method on the
  interface — owns the actual cadence and is what changes between the two sources. Keeping the
  interval a startup-time constant (rather than a method on `MarketDataSource`) keeps the interface
  from needing an "interval" concept it doesn't otherwise care about; only `main.py`'s wiring code
  needs to know which number to use for which source.
- A separate SSE broadcast tick (also ~500ms, matching `PLAN.md`'s "regular cadence... steady
  heartbeat") reads `cache.snapshot()` and pushes to connected clients — this runs independently
  of the update loop's interval, which is exactly what makes the Massive case's "most heartbeats
  resend the last known price unchanged" behavior (`PLAN.md` §6) fall out naturally: the SSE
  heartbeat is fast and constant; the underlying cache only actually changes every 15s.

---

## 5. Selecting the Implementation at Startup

```python
# backend/app/market/factory.py
import os

from .base import MarketDataSource
from .simulator import SimulatorMarketDataSource
from .massive import MassiveMarketDataSource


def build_market_data_source() -> MarketDataSource:
    api_key = os.environ.get("MASSIVE_API_KEY", "").strip()
    if api_key:
        return MassiveMarketDataSource(api_key=api_key)
    return SimulatorMarketDataSource()
```

This is the entire selection logic `PLAN.md` §5 describes ("if set and non-empty → Massive, else
simulator"). Nothing else in the app should re-check `os.environ["MASSIVE_API_KEY"]` — a single
constructed `MarketDataSource` is stored on app state (`app.state.market_source`) and injected
wherever needed (the update loop, the watchlist-add validation endpoint).

---

## 6. Resolving A1/A2: What "Valid Ticker" Means Per Source

`REVIEW.md` Review 1 flagged that `PLAN.md` §6's whitelist rule ("only tickers with a defined seed
price/sector are supported... unrecognized ticker rejected") was written under the "Simulator"
heading but phrased as if it were the one shared validation path — leaving unclear whether it also
caps what's addable when Massive is active, and contradicting §9's own example of adding `PYPL`,
a ticker outside the original 10-ticker seed set.

**Resolution — the rule is source-specific, not global:**

### 6.1 Simulator: closed universe

`SimulatorMarketDataSource.is_valid_ticker(ticker)` checks membership in a **fixed, hardcoded
ticker table** — the simulator can only generate prices for symbols it has seed price/sector/drift
data for, because that data *is* the simulation. `MARKET_SIMULATOR.md` defines this table with
~30 tickers across 5 sectors (including `PYPL`), which is enough headroom that `PLAN.md` §9's
example (adding `PYPL`) succeeds as written, closing the direct contradiction Review 1 identified.
Attempting to add anything outside that table returns the 400 error `PLAN.md` §8 specifies for
`POST /api/watchlist`.

### 6.2 Massive: open universe, validated against the real API

`MassiveMarketDataSource.is_valid_ticker(ticker)` does **not** consult any local whitelist — it
asks Massive whether the symbol exists, e.g. by requesting a snapshot for that one ticker
(`MASSIVE_API.md` §3.1) and checking whether it comes back non-empty. This means: **when
`MASSIVE_API_KEY` is set, a user can watch any real, currently-listed US equity symbol Massive
recognizes** — not just the demo's original 10 (or the simulator's expanded 30). This is the
behavior that actually makes the Massive integration worth having; capping it at a hardcoded list
in this mode (as Review 1's A2 worried the doc implied) would make real market data strictly less
useful than the simulator, which isn't the intent.

Practical consequence: the *seed* watchlist (`PLAN.md` §7, 10 default tickers) is identical either
way, since all 10 defaults exist in both the simulator's table and on the real market — but what a
user or the LLM can subsequently *add* differs by data source. Document this once, here, rather
than leaving it ambiguous per-endpoint.

### 6.3 Where validation is called from

Per `PLAN.md` §9 step 6 ("exactly one code path validates... whether it originates from the trade
bar or from chat"), `is_valid_ticker` is called from a single watchlist-service function used by
both `POST /api/watchlist` and the LLM's `watchlist_changes` auto-execution — never duplicated.

---

## 7. Resolving B1: Trading a Ticker Not on the Watchlist

Review 1 flagged that `POST /api/portfolio/trade` had no stated rule for what happens if a trade
targets a ticker with no price in the cache.

**Resolution**: trades are restricted to tickers currently present in the price cache — which, in
the single-user model, means currently on the watchlist (`PLAN.md` §6 already establishes this
equivalence for SSE purposes; extending it to trades keeps one definition of "tradable universe"
instead of two). A trade request for a ticker not in the cache is rejected before any cash/position
mutation, with the same 400-style validation-error shape used for other trade failures (insufficient
cash, oversell, etc. — `PLAN.md` §8/§9's shared error-annotation path).

Rationale for this over the alternatives considered:
- **Implicit watchlist add on trade** was considered and rejected — it would let a chat-driven
  trade silently grow the watchlist as a side effect, which conflicts with §9's step 6 "one
  validation function" framing (trade validation would now also need write access to the
  watchlist table) and would surprise a user who didn't ask to start watching a new ticker.
  Executing a trade should not require an implicit "and also do this other unrelated
  watchlist mutation" behavior; either mutation should be an explicit, singular ask.
- **Fetching a price on-demand outside the cache** was considered and rejected — it reintroduces
  a second code path for "get a price" (cache read vs. live fetch) that the rest of this
  document works to avoid, and for Massive specifically would mean an uncached, unrate-limited
  API call triggerable by every trade attempt.
- Requiring watchlist membership first is simple, matches the mental model users already have
  ("I can only trade what I'm watching"), and gives the LLM a clear, checkable precondition: if it
  wants to trade a ticker not yet watched, it should emit a `watchlist_changes` add *and* the trade
  in the same response — both validated independently, so the add succeeds/fails on its own merits
  and the trade succeeds/fails on whether the ticker is now known.

---

## 8. Resolving B2: SSE Wire Format

Review 1 flagged that the SSE payload shape (one event per tick vs. per ticker; exact field names;
`direction` enum values) was unstated. This interface makes the answer straightforward: the SSE
endpoint calls `cache.snapshot()` once per broadcast tick and emits **one SSE event containing the
full array of all tracked tickers**, not one event per ticker — this is simpler for the frontend
(one `onmessage` handler, one array to diff against its local state) and matches "pushes an event
for all tickers known to the system at a regular cadence" (`PLAN.md` §6) most literally.

```
event: prices
data: {"ticks": [{"ticker": "AAPL", "price": 190.42, "previous_price": 190.00, "timestamp": "2026-09-12T14:32:00.123Z", "direction": "up"}, {"ticker": "GOOGL", "price": 175.10, "previous_price": 175.10, "timestamp": "2026-09-12T14:32:00.123Z", "direction": "unchanged"}]}

```

- `direction` is exactly the three `ChangeDirection` values from §2: `"up" | "down" | "unchanged"`
  — always present, never omitted, so the frontend never has to treat a missing field as a third
  state.
- `timestamp` is ISO-8601 UTC (`datetime.isoformat()` with a `Z`/offset), matching the ISO
  timestamp convention already used for every other table in `PLAN.md` §7.
- FastAPI's `EventSourceResponse` (or an equivalent hand-rolled `text/event-stream` generator)
  serializes `cache.snapshot()` results to this shape once per broadcast tick, independent of the
  update loop's own interval (§4).

---

## 9. Implementation Skeletons

For concrete internals see `MARKET_SIMULATOR.md` (simulator) and `MASSIVE_API.md` (Massive
endpoint details); this section shows only how each fits the interface shape from §2.

```python
# backend/app/market/massive.py
import httpx
from .base import MarketDataSource

class MassiveMarketDataSource(MarketDataSource):
    BASE_URL = "https://api.massive.com"

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._client: httpx.AsyncClient | None = None

    async def start(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={"Authorization": f"Bearer {self._api_key}"},
            timeout=10.0,
        )

    async def stop(self) -> None:
        if self._client:
            await self._client.aclose()

    async def get_prices(self, tickers: list[str]) -> dict[str, float]:
        resp = await self._client.get(
            "/v2/snapshot/locale/us/markets/stocks/tickers",
            params={"tickers": ",".join(tickers)},
        )
        resp.raise_for_status()
        data = resp.json()
        return {
            t["ticker"]: t["lastTrade"]["p"]
            for t in data.get("tickers", [])
            if t.get("lastTrade")
        }

    async def is_valid_ticker(self, ticker: str) -> bool:
        resp = await self._client.get(
            "/v2/snapshot/locale/us/markets/stocks/tickers",
            params={"tickers": ticker},
        )
        if resp.status_code != 200:
            return False
        return len(resp.json().get("tickers", [])) > 0
```

`SimulatorMarketDataSource` follows the same shape but with no I/O — see `MARKET_SIMULATOR.md` §4
for its full implementation.

---

## Summary of Decisions Made in This Document

| Open question (from REVIEW.md) | Resolution |
|---|---|
| A1/A2 — ticker whitelist scope | Simulator: closed ~30-ticker table (`MARKET_SIMULATOR.md`). Massive: open, validated live against the API. |
| B1 — trading an unwatched ticker | Rejected with a validation error; no implicit watchlist mutation, no on-demand out-of-cache fetch. |
| B2 — SSE wire format | One event per broadcast tick, `{"ticks": [...]}` array, fields `ticker/price/previous_price/timestamp/direction`, `direction ∈ {up, down, unchanged}` always present. |
| (new) Massive free-tier real-time gap | Documented in `MASSIVE_API.md` §2 — Basic plan is EOD-only; the existing "heartbeat may resend unchanged price" spec language already accommodates this without further changes here. |
