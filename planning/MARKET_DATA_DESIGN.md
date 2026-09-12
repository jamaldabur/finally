# MARKET_DATA_DESIGN.md — Market Data Backend Implementation Guide

This document is the consolidated, implementation-ready design for FinAlly's entire market data
backend: the unified `MarketDataSource` interface, the simulator, the Massive-backed client, and
every point where the rest of the backend (SSE streaming, watchlist validation, trade execution,
FastAPI startup) plugs into this layer.

It draws on and reconciles three prior documents — `MARKET_INTERFACE.md`, `MARKET_SIMULATOR.md`,
`MASSIVE_API.md` — into one file with consistent imports and file paths, so an implementer can
build `backend/app/market/` end-to-end from this document alone, without cross-referencing three
separate specs. Those three documents remain the detailed rationale/research backing each
decision (interface design tradeoffs, GBM math derivation, Massive API research); this document is
the build guide.

Everything here implements `PLAN.md` §6 ("Market Data") and closes the ambiguities `REVIEW.md`
Review 1 flagged against it (§A1/A2, §B1, §B2, §B11) — each resolution is cited inline.

---

## 1. Scope & Design Goals

- **One abstract interface, two implementations**, selected once at startup by environment
  variable (`PLAN.md` §5). Nothing above the interface — price cache, SSE stream, watchlist
  validation, trade fills — ever branches on which implementation is active.
- **A single shared, in-memory price cache** is the one source of truth the SSE endpoint reads
  from. It — not either data source — computes "previous price" and "direction," because that's
  about what the frontend has already seen, not something either backend knows natively.
- **Resilience over correctness-at-all-costs**: a failed Massive poll, a rate limit, or a
  malformed response must never crash the update loop or block the SSE stream. The cache simply
  keeps serving the last known-good price until the next successful update.
- **No new runtime dependencies beyond what's already implied** by the rest of the stack: `httpx`
  (already needed for LiteLLM/OpenRouter calls per the `litellm-stream` skill) and the standard
  library. No SSE helper library, no Massive SDK (rationale in `MASSIVE_API.md` §4).

---

## 2. File Layout

```
backend/
└── app/
    ├── main.py                    # FastAPI app, lifespan startup/shutdown wiring (§8)
    ├── market/
    │   ├── __init__.py
    │   ├── base.py                # MarketDataSource ABC, PriceTick, ChangeDirection (§3)
    │   ├── cache.py                # PriceCache (§4)
    │   ├── simulator.py            # SimulatorMarketDataSource + ticker universe (§5)
    │   ├── massive.py              # MassiveMarketDataSource (§6)
    │   ├── factory.py              # build_market_data_source() (§7)
    │   └── loop.py                 # run_update_loop() background task (§7)
    ├── routes/
    │   ├── stream.py                # GET /api/stream/prices (§9)
    │   └── watchlist.py             # POST/DELETE /api/watchlist (§10)
    ├── services/
    │   ├── watchlist_service.py     # single validation path, market-data slice (§10)
    │   └── trade_service.py         # fill-price lookup, market-data slice (§10)
    └── db/
        └── watchlist.py              # get_watchlist_tickers() etc. (SQLite; not detailed here)
```

---

## 3. Core Types & Abstract Interface

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
    (§7) and driven by a single background task (§7's run_update_loop) that
    feeds the shared PriceCache (§4). No other code should hold a reference
    to more than one MarketDataSource instance at a time.
    """

    @abstractmethod
    async def start(self) -> None:
        """Called once at app startup. Simulator: spawns its internal tick
        loop. Massive: constructs the shared httpx.AsyncClient — Massive
        performs no polling itself; run_update_loop (§7) drives its cadence
        externally."""

    @abstractmethod
    async def stop(self) -> None:
        """Called once at app shutdown. Releases any resources (HTTP client,
        background tasks)."""

    @abstractmethod
    async def get_prices(self, tickers: list[str]) -> dict[str, float]:
        """Return the latest known price for each requested ticker. Tickers
        this source has no data for are simply omitted from the result dict
        — callers must not treat a missing key as an error. Must never raise
        for ordinary failure modes (rate limits, transient network errors) —
        see §6 for how MassiveMarketDataSource honors this."""

    @abstractmethod
    async def is_valid_ticker(self, ticker: str) -> bool:
        """Whether `ticker` can be added to the watchlist under this data
        source. What 'valid' means differs by implementation, by design —
        see §5.1 (simulator: closed table) and §6 (Massive: live API check)."""
```

`get_prices` and `is_valid_ticker` are `async` even though the simulator's implementations are
synchronous in practice (in-memory dict lookups) — this keeps the interface uniform, since the
Massive implementation's `is_valid_ticker` genuinely needs to make a network call.

---

## 4. The Shared Price Cache

```python
# backend/app/market/cache.py
import asyncio
from datetime import datetime, timezone

from .base import ChangeDirection, PriceTick


class PriceCache:
    """Written to by run_update_loop (§7); read by the SSE endpoint (§9) and
    by trade fill-price lookups (§10). Guarded by a lock since multiple SSE
    connections and the update loop can all await it concurrently."""

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
        """Single-ticker lookup — used by trade fill-price resolution (§10)."""
        async with self._lock:
            return self._latest.get(ticker)
```

**Worked example** (the mechanism behind `PLAN.md`'s "`previous price` reflects the last
*different* price, not simply the prior event" requirement):

| Tick | Incoming price | Stored `price` | Stored `previous_price` | Direction |
|---|---|---|---|---|
| 1 | 190.00 | 190.00 | 190.00 | `unchanged` (first tick) |
| 2 | 190.42 | 190.42 | 190.00 | `up` |
| 3 | 190.42 (heartbeat, no change) | 190.42 | 190.00 (carried forward) | `up` (carried forward) |

> **Frontend implementation note** (not this doc's responsibility to build, but worth restating
> here since it's easy to get wrong from the wire format alone): the frontend must compare each
> incoming `price` against the last price *it already rendered*, not against that same event's
> `previous_price` field, or it will re-flash on every unchanged heartbeat. `previous_price` exists
> so the frontend can compute deltas correctly across reconnects — it doesn't gate the flash
> animation by itself. See `MARKET_INTERFACE.md` §3 for the full explanation.

---

## 5. Simulator Implementation

### 5.1 Ticker Universe

The simulator's complete, hardcoded set of tradable tickers (resolves `REVIEW.md` §A1/§B11 — see
`MARKET_SIMULATOR.md` §1 for the full rationale). `is_valid_ticker()` checks membership in this
table and nothing else.

| Ticker | Sector | Seed Price | μ (drift) | σ (volatility) |
|---|---|---:|---:|---:|
| AAPL | Tech | 190.00 | 0.0003 | 0.018 |
| GOOGL | Tech | 175.00 | 0.0003 | 0.020 |
| MSFT | Tech | 420.00 | 0.0003 | 0.017 |
| AMZN | Tech | 185.00 | 0.0004 | 0.021 |
| NVDA | Tech | 130.00 | 0.0006 | 0.032 |
| META | Tech | 560.00 | 0.0004 | 0.024 |
| ORCL | Tech | 175.00 | 0.0002 | 0.019 |
| CRM | Tech | 300.00 | 0.0002 | 0.020 |
| AMD | Tech | 165.00 | 0.0005 | 0.030 |
| CSCO | Tech | 58.00 | 0.0001 | 0.015 |
| JPM | Finance | 215.00 | 0.0002 | 0.015 |
| V | Finance | 285.00 | 0.0002 | 0.014 |
| BAC | Finance | 42.00 | 0.0002 | 0.017 |
| GS | Finance | 550.00 | 0.0002 | 0.018 |
| MA | Finance | 475.00 | 0.0002 | 0.014 |
| PYPL | Finance | 78.00 | 0.0001 | 0.022 |
| TSLA | Consumer | 250.00 | 0.0005 | 0.035 |
| NFLX | Consumer | 700.00 | 0.0004 | 0.025 |
| DIS | Consumer | 105.00 | 0.0001 | 0.019 |
| NKE | Consumer | 78.00 | 0.0001 | 0.020 |
| SBUX | Consumer | 95.00 | 0.0001 | 0.018 |
| PEP | Consumer | 168.00 | 0.0001 | 0.012 |
| KO | Consumer | 63.00 | 0.0001 | 0.011 |
| COST | Consumer | 900.00 | 0.0002 | 0.015 |
| JNJ | Healthcare | 155.00 | 0.0001 | 0.012 |
| PFE | Healthcare | 28.00 | 0.0000 | 0.017 |
| UNH | Healthcare | 500.00 | 0.0001 | 0.019 |
| LLY | Healthcare | 780.00 | 0.0005 | 0.021 |
| XOM | Energy | 115.00 | 0.0001 | 0.016 |
| CVX | Energy | 160.00 | 0.0001 | 0.016 |

Default seed watchlist (`PLAN.md` §7) is the first 10 rows in `PLAN.md`'s original order (AAPL,
GOOGL, MSFT, AMZN, TSLA, NVDA, META, JPM, V, NFLX). Everything else is addable but not pre-watched
— this is what makes `PLAN.md` §9's "add PYPL" example succeed.

### 5.2 Price Model — Geometric Brownian Motion

```
S(t+1) = S(t) * exp[ (μ - σ²/2) * dt + σ * sqrt(dt) * Z + sector_factor ]
```

- `dt` is the tick size **as a fraction of a trading day**: at a 500ms tick and a 6.5-hour trading
  day (23,400s), `dt = 0.5 / 23400 ≈ 2.14e-5`. This keeps per-tick moves visually subtle rather
  than treating each tick as "one day."
- `sector_factor` is a small shared shock added to every ticker in the same sector this tick (§5.3).
- The `-σ²/2` term is the standard Itô correction so the *expected* price path matches the stated
  drift despite the log-normal step.

### 5.3 Correlated Sector Moves & Random Events

Once per tick, one shared normal sample is drawn per sector and added to every ticker in that
sector's GBM step, scaled down (`SECTOR_FACTOR_SCALE = 0.35`) so co-movement is a visible tilt, not
a dominant force. Independently, each ticker has a small per-tick chance
(`EVENT_PROBABILITY_PER_TICK = 0.002`, ≈1 event per ticker every 4-5 minutes) of a sudden
uncorrelated 2-5% jump, applied multiplicatively after the GBM step.

### 5.4 Full Implementation

```python
# backend/app/market/simulator.py
import asyncio
import math
import random
from dataclasses import dataclass

from .base import MarketDataSource

TRADING_DAY_SECONDS = 6.5 * 3600
TICK_SECONDS = 0.5

SECTOR_FACTOR_SCALE = 0.35
EVENT_PROBABILITY_PER_TICK = 0.002
EVENT_MAGNITUDE_RANGE = (0.02, 0.05)


@dataclass(frozen=True)
class TickerParams:
    seed_price: float
    sector: str
    mu: float
    sigma: float


TICKER_UNIVERSE: dict[str, TickerParams] = {
    "AAPL": TickerParams(190.00, "Tech", 0.0003, 0.018),
    "GOOGL": TickerParams(175.00, "Tech", 0.0003, 0.020),
    "MSFT": TickerParams(420.00, "Tech", 0.0003, 0.017),
    "AMZN": TickerParams(185.00, "Tech", 0.0004, 0.021),
    "NVDA": TickerParams(130.00, "Tech", 0.0006, 0.032),
    "META": TickerParams(560.00, "Tech", 0.0004, 0.024),
    "ORCL": TickerParams(175.00, "Tech", 0.0002, 0.019),
    "CRM": TickerParams(300.00, "Tech", 0.0002, 0.020),
    "AMD": TickerParams(165.00, "Tech", 0.0005, 0.030),
    "CSCO": TickerParams(58.00, "Tech", 0.0001, 0.015),
    "JPM": TickerParams(215.00, "Finance", 0.0002, 0.015),
    "V": TickerParams(285.00, "Finance", 0.0002, 0.014),
    "BAC": TickerParams(42.00, "Finance", 0.0002, 0.017),
    "GS": TickerParams(550.00, "Finance", 0.0002, 0.018),
    "MA": TickerParams(475.00, "Finance", 0.0002, 0.014),
    "PYPL": TickerParams(78.00, "Finance", 0.0001, 0.022),
    "TSLA": TickerParams(250.00, "Consumer", 0.0005, 0.035),
    "NFLX": TickerParams(700.00, "Consumer", 0.0004, 0.025),
    "DIS": TickerParams(105.00, "Consumer", 0.0001, 0.019),
    "NKE": TickerParams(78.00, "Consumer", 0.0001, 0.020),
    "SBUX": TickerParams(95.00, "Consumer", 0.0001, 0.018),
    "PEP": TickerParams(168.00, "Consumer", 0.0001, 0.012),
    "KO": TickerParams(63.00, "Consumer", 0.0001, 0.011),
    "COST": TickerParams(900.00, "Consumer", 0.0002, 0.015),
    "JNJ": TickerParams(155.00, "Healthcare", 0.0001, 0.012),
    "PFE": TickerParams(28.00, "Healthcare", 0.0000, 0.017),
    "UNH": TickerParams(500.00, "Healthcare", 0.0001, 0.019),
    "LLY": TickerParams(780.00, "Healthcare", 0.0005, 0.021),
    "XOM": TickerParams(115.00, "Energy", 0.0001, 0.016),
    "CVX": TickerParams(160.00, "Energy", 0.0001, 0.016),
}


class SimulatorMarketDataSource(MarketDataSource):
    def __init__(self, seed: int | None = None) -> None:
        self._rng = random.Random(seed)
        self._prices: dict[str, float] = {
            ticker: params.seed_price for ticker, params in TICKER_UNIVERSE.items()
        }
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        self._task = asyncio.create_task(self._tick_forever())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()

    async def _tick_forever(self) -> None:
        dt = TICK_SECONDS / TRADING_DAY_SECONDS
        while True:
            self._advance_all(dt)
            await asyncio.sleep(TICK_SECONDS)

    def _advance_all(self, dt: float) -> None:
        sectors = {p.sector for p in TICKER_UNIVERSE.values()}
        factors = {
            sector: SECTOR_FACTOR_SCALE * 0.02 * math.sqrt(dt) * self._rng.gauss(0, 1)
            for sector in sectors
        }
        for ticker, params in TICKER_UNIVERSE.items():
            z = self._rng.gauss(0, 1)
            new_price = _gbm_step(
                self._prices[ticker], params.mu, params.sigma, dt, z, factors[params.sector]
            )
            new_price = _maybe_apply_event(new_price, self._rng)
            # Cent precision, rounded once here (not per-read), so every
            # consumer sees the same value and no float-precision flicker
            # reaches the frontend. GBM is multiplicative, so prices can
            # never go negative — no floor/clamp needed.
            self._prices[ticker] = round(new_price, 2)

    async def get_prices(self, tickers: list[str]) -> dict[str, float]:
        return {t: self._prices[t] for t in tickers if t in self._prices}

    async def is_valid_ticker(self, ticker: str) -> bool:
        return ticker in TICKER_UNIVERSE


def _gbm_step(price: float, mu: float, sigma: float, dt: float, z: float, sector_factor: float = 0.0) -> float:
    exponent = (mu - 0.5 * sigma**2) * dt + sigma * math.sqrt(dt) * z + sector_factor
    return price * math.exp(exponent)


def _maybe_apply_event(price: float, rng: random.Random) -> float:
    if rng.random() < EVENT_PROBABILITY_PER_TICK:
        magnitude = rng.uniform(*EVENT_MAGNITUDE_RANGE)
        direction = rng.choice([-1, 1])
        return price * (1 + direction * magnitude)
    return price
```

No locking is needed on `_prices`: a single asyncio task mutates it (`_tick_forever`), and reads
happen on the same event-loop thread between awaits — standard single-threaded asyncio safety.
The `seed` parameter exists for deterministic unit tests (§11).

---

## 6. Massive Implementation

Reference: `MASSIVE_API.md` for full endpoint research. This section is the implementation that
conforms to `MarketDataSource` and honors its resilience contract — every failure mode returns an
empty dict rather than raising, so a bad poll cycle degrades to "no update this cycle," never a
crash.

```python
# backend/app/market/massive.py
import asyncio
import logging

import httpx

from .base import MarketDataSource

logger = logging.getLogger(__name__)


class MassiveMarketDataSource(MarketDataSource):
    BASE_URL = "https://api.massive.com"
    SNAPSHOT_PATH = "/v2/snapshot/locale/us/markets/stocks/tickers"
    MAX_TRANSIENT_RETRIES = 2
    RETRY_BACKOFF_SECONDS = 1.0

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
        """One snapshot call for the whole watchlist. On any failure — rate
        limit, entitlement gap, transient network error — logs and returns
        {} rather than raising. run_update_loop (§7) then simply skips this
        cycle, and PriceCache keeps serving the last known-good price
        (MASSIVE_API.md §5)."""
        assert self._client is not None, "start() must be called before get_prices()"
        for attempt in range(self.MAX_TRANSIENT_RETRIES + 1):
            try:
                resp = await self._client.get(
                    self.SNAPSHOT_PATH, params={"tickers": ",".join(tickers)}
                )
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                if attempt < self.MAX_TRANSIENT_RETRIES:
                    logger.warning(
                        "Massive request failed (%s), retrying (%d/%d)",
                        exc, attempt + 1, self.MAX_TRANSIENT_RETRIES,
                    )
                    await asyncio.sleep(self.RETRY_BACKOFF_SECONDS * (attempt + 1))
                    continue
                logger.error("Massive request failed after retries: %s", exc)
                return {}

            if resp.status_code == 429:
                # Don't retry — the poll interval (15s on free tier) is
                # already chosen to stay under the 5-calls/minute cap, so a
                # 429 means something else is also calling; back off fully
                # to the next scheduled cycle rather than hammering harder.
                logger.warning("Massive rate limit hit (429) — skipping this poll cycle")
                return {}
            if resp.status_code == 403:
                logger.error(
                    "Massive returned 403 NOT_AUTHORIZED — your plan may not include this "
                    "data; falling back is not automatic, check your key/plan"
                )
                return {}
            try:
                resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                logger.error("Massive returned HTTP %s: %s", exc.response.status_code, exc)
                return {}

            data = resp.json()
            # A malformed/unknown ticker is simply absent from the response
            # array rather than erroring the whole request — this dict
            # comprehension naturally treats "requested 10, got 7 back" as
            # "3 tickers unchanged this cycle," matching get_prices' documented
            # contract in base.py.
            return {
                t["ticker"]: t["lastTrade"]["p"]
                for t in data.get("tickers", [])
                if t.get("lastTrade")
            }
        return {}

    async def is_valid_ticker(self, ticker: str) -> bool:
        assert self._client is not None, "start() must be called before is_valid_ticker()"
        try:
            resp = await self._client.get(self.SNAPSHOT_PATH, params={"tickers": ticker})
        except httpx.HTTPError as exc:
            logger.error("Massive is_valid_ticker check failed for %s: %s", ticker, exc)
            return False
        if resp.status_code != 200:
            return False
        return len(resp.json().get("tickers", [])) > 0
```

**Notes**:
- `lastTrade.p` is the field used as "current price." On the free Basic plan, `lastTrade` is
  stale/absent outside real-time entitlement — only `prevDay` (end-of-day) is populated, so a
  Basic-tier key effectively updates once per day, not every 15 seconds. This is a Massive plan
  limitation, not a bug in this client; call it out in the README next to `MASSIVE_API_KEY`.
- Auth uses the `Authorization: Bearer` header (not the `?apiKey=` query param) specifically to
  keep the key out of access logs and proxies (`MASSIVE_API.md` §1).
- `is_valid_ticker` making a real network call (vs. the simulator's O(1) dict lookup) is why the
  interface declares both methods `async` uniformly (§3).

---

## 7. Selecting the Implementation & Driving the Update Loop

```python
# backend/app/market/factory.py
import os

from .base import MarketDataSource
from .massive import MassiveMarketDataSource
from .simulator import SimulatorMarketDataSource


def build_market_data_source() -> MarketDataSource:
    """The entire selection logic PLAN.md §5 describes: if MASSIVE_API_KEY
    is set and non-empty, use Massive; otherwise use the simulator. Nothing
    else in the app should re-check this env var — call this once at
    startup and store the result on app.state (see §8)."""
    api_key = os.environ.get("MASSIVE_API_KEY", "").strip()
    if api_key:
        return MassiveMarketDataSource(api_key=api_key)
    return SimulatorMarketDataSource()
```

```python
# backend/app/market/loop.py
import asyncio
import logging
from typing import Awaitable, Callable

from .base import MarketDataSource
from .cache import PriceCache

logger = logging.getLogger(__name__)

SIMULATOR_TICK_SECONDS = 0.5   # matches PLAN.md §6 "~500ms"
MASSIVE_POLL_SECONDS = 15      # matches PLAN.md §6 free-tier cadence


async def run_update_loop(
    source: MarketDataSource,
    cache: PriceCache,
    get_watchlist_tickers: Callable[[], Awaitable[list[str]]],
    interval_seconds: float,
) -> None:
    """One background task per running app. Wrapped in try/except so that
    even an implementation bug that somehow raises out of get_prices (rather
    than returning {} per its contract) can't kill the loop — the loop is
    the sole writer to `cache`, so if it dies, the SSE stream silently goes
    stale forever. Defense in depth on top of §6's own error handling."""
    while True:
        try:
            tickers = await get_watchlist_tickers()
            if tickers:
                prices = await source.get_prices(tickers)
                for ticker, price in prices.items():
                    await cache.update(ticker, price)
        except Exception:
            logger.exception("market data update loop iteration failed")
        await asyncio.sleep(interval_seconds)
```

- **Simulator**: `interval_seconds=0.5`. `get_prices` is a cheap in-memory read.
- **Massive**: `interval_seconds=15` (free tier). `get_prices` makes one snapshot call for the
  whole watchlist regardless of how many tickers are watched, up to Massive's 250-ticker limit
  (never a concern at this project's scale).
- The SSE broadcast (§9) reads `cache.snapshot()` on its own ~500ms cadence, independent of this
  loop's interval — this is exactly what makes Massive's "most heartbeats resend the last known
  price unchanged" behavior (`PLAN.md` §6) fall out naturally, with no special-casing needed in the
  SSE layer.

---

## 8. FastAPI Startup & Shutdown Wiring

```python
# backend/app/main.py
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .db.watchlist import get_watchlist_tickers
from .market.cache import PriceCache
from .market.factory import build_market_data_source
from .market.loop import MASSIVE_POLL_SECONDS, SIMULATOR_TICK_SECONDS, run_update_loop
from .market.massive import MassiveMarketDataSource
from .routes import stream, watchlist  # portfolio, chat, health routers similarly included


@asynccontextmanager
async def lifespan(app: FastAPI):
    source = build_market_data_source()
    cache = PriceCache()
    await source.start()

    interval = (
        MASSIVE_POLL_SECONDS
        if isinstance(source, MassiveMarketDataSource)
        else SIMULATOR_TICK_SECONDS
    )
    update_task = asyncio.create_task(
        run_update_loop(source, cache, get_watchlist_tickers, interval)
    )

    # Stored on app.state so routes can reach both without a second global —
    # this is the single constructed MarketDataSource instance (§7).
    app.state.market_source = source
    app.state.price_cache = cache

    yield

    update_task.cancel()
    await source.stop()


app = FastAPI(lifespan=lifespan)
app.include_router(stream.router)
app.include_router(watchlist.router)
```

---

## 9. SSE Endpoint

Resolves `REVIEW.md` §B2: **one SSE event per broadcast tick, containing the full array of all
tracked tickers** — not one event per ticker. Simpler for the frontend (one `onmessage` handler,
one array to diff against local state) and matches "pushes an event for all tickers known to the
system at a regular cadence" (`PLAN.md` §6) most literally. No extra SSE library needed — a plain
async generator with `media_type="text/event-stream"` is sufficient.

```python
# backend/app/routes/stream.py
import asyncio
import json

from fastapi import APIRouter, Request
from starlette.responses import StreamingResponse

from ..market.base import PriceTick
from ..market.cache import PriceCache

router = APIRouter()

SSE_BROADCAST_SECONDS = 0.5


def _serialize_tick(tick: PriceTick) -> dict:
    return {
        "ticker": tick.ticker,
        "price": tick.price,
        "previous_price": tick.previous_price,
        "timestamp": tick.timestamp.isoformat(),
        "direction": tick.direction.value,
    }


async def _price_event_generator(request: Request, cache: PriceCache):
    while True:
        if await request.is_disconnected():
            break
        ticks = await cache.snapshot()
        payload = {"ticks": [_serialize_tick(t) for t in ticks]}
        yield f"event: prices\ndata: {json.dumps(payload)}\n\n"
        await asyncio.sleep(SSE_BROADCAST_SECONDS)


@router.get("/api/stream/prices")
async def stream_prices(request: Request):
    cache: PriceCache = request.app.state.price_cache
    return StreamingResponse(
        _price_event_generator(request, cache),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # disable proxy buffering if ever fronted by nginx
        },
    )
```

Each connected client (in practice, one browser tab in this single-user app, but the design
supports multiple) runs its own independent generator loop polling the shared cache — no pub/sub
broadcast machinery is needed since cache reads are cheap and `PriceCache.snapshot()` is safe for
concurrent readers.

Example wire payload (matches `MARKET_INTERFACE.md` §8):

```
event: prices
data: {"ticks": [{"ticker": "AAPL", "price": 190.42, "previous_price": 190.00, "timestamp": "2026-09-12T14:32:00.123456+00:00", "direction": "up"}, {"ticker": "GOOGL", "price": 175.10, "previous_price": 175.10, "timestamp": "2026-09-12T14:32:00.123456+00:00", "direction": "unchanged"}]}

```

`direction` is always present (never omitted) as one of `"up" | "down" | "unchanged"` — the
frontend never has to treat a missing field as a third state.

---

## 10. Integration Points: Watchlist & Trade Validation

Per `PLAN.md` §9 step 6 ("exactly one code path validates... whether it originates from the trade
bar or from chat"), both the REST endpoints and the LLM's auto-execution call the *same* service
functions — never duplicated logic. This section shows the market-data-relevant slice of each;
full trade/portfolio business logic (cash checks, position updates) belongs to a separate
portfolio design doc.

### 10.1 Watchlist — resolves `REVIEW.md` §A1/§A2

```python
# backend/app/services/watchlist_service.py
from fastapi import HTTPException

from ..db import watchlist as watchlist_db
from ..market.base import MarketDataSource


async def add_ticker(ticker: str, source: MarketDataSource) -> None:
    """The one code path for adding a ticker to the watchlist — called by
    POST /api/watchlist and by the LLM's watchlist_changes auto-execution.
    `source.is_valid_ticker` is what differs between data sources: a closed
    ~30-ticker table for the simulator (§5.1), a live API check for Massive
    (§6) — this function itself never branches on which is active."""
    ticker = ticker.strip().upper()
    if not await source.is_valid_ticker(ticker):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "unrecognized_ticker",
                "detail": f"'{ticker}' is not a recognized symbol for the active market data source.",
            },
        )
    await watchlist_db.add_ticker(ticker)


async def remove_ticker(ticker: str) -> None:
    ticker = ticker.strip().upper()
    removed = await watchlist_db.remove_ticker(ticker)
    if not removed:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "not_on_watchlist",
                "detail": f"'{ticker}' is not currently on the watchlist.",
            },
        )
```

```python
# backend/app/routes/watchlist.py
from fastapi import APIRouter, Request
from pydantic import BaseModel

from ..services import watchlist_service

router = APIRouter()


class AddTickerRequest(BaseModel):
    ticker: str


@router.post("/api/watchlist")
async def add_ticker(body: AddTickerRequest, request: Request):
    await watchlist_service.add_ticker(body.ticker, request.app.state.market_source)
    return {"ticker": body.ticker.strip().upper(), "status": "added"}


@router.delete("/api/watchlist/{ticker}")
async def remove_ticker(ticker: str):
    await watchlist_service.remove_ticker(ticker)
    return {"ticker": ticker.strip().upper(), "status": "removed"}
```

### 10.2 Trades — resolves `REVIEW.md` §B1

Trades are restricted to tickers currently present in the price cache (equivalently, on the
watchlist — `MARKET_INTERFACE.md` §7). A trade for an unwatched ticker is rejected before any
cash/position mutation, rather than implicitly adding it to the watchlist or fetching a price
out-of-band. If the LLM wants to trade something not yet watched, it emits a `watchlist_changes`
add *and* the trade in the same structured response — each validated independently.

```python
# backend/app/services/trade_service.py (excerpt — market-data slice only)
from fastapi import HTTPException

from ..market.cache import PriceCache


async def get_fill_price(ticker: str, cache: PriceCache) -> float:
    """Resolves the current fill price for a market order. The rest of
    trade execution (cash/share validation, position updates, trade log)
    is out of scope for this document."""
    tick = await cache.get(ticker.strip().upper())
    if tick is None:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "ticker_not_tracked",
                "detail": f"'{ticker}' is not on the watchlist — add it before trading.",
            },
        )
    return tick.price
```

---

## 11. Testing Strategy

Covers `PLAN.md` §12's "market data" unit test scope: simulator validity, GBM correctness, Massive
parsing, and interface conformance across both implementations.

### 11.1 Price cache — the subtle `previous_price` behavior

```python
# backend/tests/market/test_cache.py
import pytest

from app.market.cache import PriceCache


@pytest.mark.asyncio
async def test_previous_price_carries_forward_on_heartbeat():
    cache = PriceCache()
    await cache.update("AAPL", 190.00)
    tick2 = await cache.update("AAPL", 190.42)
    assert tick2.previous_price == 190.00
    assert tick2.direction.value == "up"

    tick3 = await cache.update("AAPL", 190.42)  # heartbeat, no real change
    assert tick3.previous_price == 190.00  # carried forward, not 190.42
    assert tick3.direction.value == "up"    # carried forward too
```

### 11.2 Simulator — determinism, sector correlation, ticker universe

```python
# backend/tests/market/test_simulator.py
import pytest

from app.market.simulator import SimulatorMarketDataSource, TICKER_UNIVERSE


@pytest.mark.asyncio
async def test_prices_stay_positive_and_bounded():
    sim = SimulatorMarketDataSource(seed=42)
    dt = 0.5 / (6.5 * 3600)
    for _ in range(500):
        sim._advance_all(dt)
    for ticker, params in TICKER_UNIVERSE.items():
        price = sim._prices[ticker]
        assert price > 0
        assert 0.5 * params.seed_price < price < 1.5 * params.seed_price


@pytest.mark.asyncio
async def test_ticker_universe_membership():
    # This is the regression test that directly closes REVIEW.md §A1: PYPL
    # must be a valid add per PLAN.md §9's example, ZZZZ must not exist.
    sim = SimulatorMarketDataSource()
    assert await sim.is_valid_ticker("PYPL") is True
    assert await sim.is_valid_ticker("ZZZZ") is False


@pytest.mark.asyncio
async def test_get_prices_omits_untracked_tickers():
    sim = SimulatorMarketDataSource()
    prices = await sim.get_prices(["AAPL", "ZZZZ"])
    assert "AAPL" in prices
    assert "ZZZZ" not in prices
```

Sector correlation (same-sector tickers' per-tick returns positively correlated over many ticks,
given a fixed seed) is a good statistical test to add — compute a Pearson correlation coefficient
across a simulated series and assert it's above a modest positive threshold. This is the one
behavior most likely to silently break (e.g. if the sector factor were accidentally redrawn per
ticker instead of shared).

### 11.3 Massive — mocked HTTP, error handling

```python
# backend/tests/market/test_massive.py
import httpx
import pytest
import respx

from app.market.massive import MassiveMarketDataSource


@pytest.mark.asyncio
@respx.mock
async def test_get_prices_parses_snapshot():
    respx.get(url__regex=r".*/v2/snapshot/.*").mock(
        return_value=httpx.Response(
            200,
            json={"tickers": [{"ticker": "AAPL", "lastTrade": {"p": 190.42}}]},
        )
    )
    source = MassiveMarketDataSource(api_key="test-key")
    await source.start()
    prices = await source.get_prices(["AAPL"])
    assert prices == {"AAPL": 190.42}
    await source.stop()


@pytest.mark.asyncio
@respx.mock
async def test_rate_limit_returns_empty_dict_not_raise():
    respx.get(url__regex=r".*/v2/snapshot/.*").mock(return_value=httpx.Response(429))
    source = MassiveMarketDataSource(api_key="test-key")
    await source.start()
    prices = await source.get_prices(["AAPL"])
    assert prices == {}  # degrades gracefully, never raises
    await source.stop()


@pytest.mark.asyncio
@respx.mock
async def test_missing_ticker_in_response_is_simply_omitted():
    respx.get(url__regex=r".*/v2/snapshot/.*").mock(
        return_value=httpx.Response(200, json={"tickers": []})
    )
    source = MassiveMarketDataSource(api_key="test-key")
    await source.start()
    prices = await source.get_prices(["ZZZZ_UNKNOWN"])
    assert prices == {}
    await source.stop()
```

(`respx` mocks `httpx` at the transport level — add it as a dev dependency: `uv add --dev respx`.)

### 11.4 Interface conformance across both implementations

```python
# backend/tests/market/test_interface_conformance.py
import httpx
import pytest
import respx

from app.market.massive import MassiveMarketDataSource
from app.market.simulator import SimulatorMarketDataSource


@pytest.fixture(params=["simulator", "massive"])
async def source(request):
    if request.param == "simulator":
        src = SimulatorMarketDataSource(seed=42)
        await src.start()
        yield src
        await src.stop()
    else:
        with respx.mock:
            respx.get(url__regex=r".*/v2/snapshot/.*").mock(
                return_value=httpx.Response(
                    200, json={"tickers": [{"ticker": "AAPL", "lastTrade": {"p": 190.42}}]}
                )
            )
            src = MassiveMarketDataSource(api_key="test-key")
            await src.start()
            yield src
            await src.stop()


@pytest.mark.asyncio
async def test_get_prices_omits_unknown_tickers(source):
    prices = await source.get_prices(["AAPL", "ZZZZ_NOT_REAL"])
    assert "AAPL" in prices
    assert "ZZZZ_NOT_REAL" not in prices
```

---

## 12. Dependencies

```bash
# From backend/, once the uv project exists (see REVIEW.md §C3):
uv add fastapi uvicorn httpx
uv add --dev pytest pytest-asyncio respx
```

No SSE helper library and no Massive/Polygon SDK — see §1 and `MASSIVE_API.md` §4 for the
rationale (plain `httpx` + a hand-rolled generator is sufficient for this project's one endpoint
shape).

---

## 13. Summary — What This Document Fixes vs. Prior Docs

| Gap in prior docs | Resolution in this document |
|---|---|
| `MARKET_INTERFACE.md`/`MASSIVE_API.md` described resilience in prose only | §6, §7 give the actual retry/backoff/graceful-degradation code (`get_prices` never raises; `run_update_loop` also wraps in try/except as defense in depth) |
| No FastAPI wiring existed anywhere | §8 (`lifespan`), §9 (SSE route) — concrete, runnable wiring from process start to HTTP response |
| Watchlist/trade validation described only as a principle ("one code path") | §10 gives the actual service functions and the routes that call them |
| No test code existed, only "testing considerations" prose | §11 gives runnable pytest examples for cache, simulator, Massive (mocked), and cross-implementation conformance |

Everything in `MARKET_INTERFACE.md`, `MARKET_SIMULATOR.md`, and `MASSIVE_API.md` remains valid as
background research and design rationale; this document is what an implementer should actually
build from.
