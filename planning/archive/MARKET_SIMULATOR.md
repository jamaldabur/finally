# MARKET_SIMULATOR.md — Market Simulator Design

This document specifies the built-in market simulator described in `PLAN.md` §6, implementing the
`MarketDataSource` interface from `MARKET_INTERFACE.md` §2. It is the default data source (used
whenever `MASSIVE_API_KEY` is unset), and needs no network access or external dependencies.

This document also resolves `REVIEW.md` Review 1 §A1/§B11: the exact ticker universe, and where
GBM parameters live.

---

## 1. Ticker Universe

`REVIEW.md` Review 1 (§A1) identified that `PLAN.md`'s only tickers with defined seed data were
the 10 default watchlist tickers themselves — making every watchlist *addition* impossible, which
directly contradicted §9's own example of adding `PYPL`. This document defines a wider, fixed
universe so that scenario works, and so the simulator has real headroom for "add a ticker" demos.

The table below is the **complete, hardcoded set** of tickers the simulator can generate prices
for. `SimulatorMarketDataSource.is_valid_ticker()` (§4) checks membership in this table and
nothing else — an add request for anything not listed here is rejected per `PLAN.md` §8.

| Ticker | Company | Sector | Seed Price (USD) | Daily Drift (μ) | Daily Volatility (σ) |
|---|---|---|---:|---:|---:|
| AAPL | Apple | Tech | 190.00 | 0.0003 | 0.018 |
| GOOGL | Alphabet | Tech | 175.00 | 0.0003 | 0.020 |
| MSFT | Microsoft | Tech | 420.00 | 0.0003 | 0.017 |
| AMZN | Amazon | Tech | 185.00 | 0.0004 | 0.021 |
| NVDA | NVIDIA | Tech | 130.00 | 0.0006 | 0.032 |
| META | Meta Platforms | Tech | 560.00 | 0.0004 | 0.024 |
| ORCL | Oracle | Tech | 175.00 | 0.0002 | 0.019 |
| CRM | Salesforce | Tech | 300.00 | 0.0002 | 0.020 |
| AMD | Advanced Micro Devices | Tech | 165.00 | 0.0005 | 0.030 |
| CSCO | Cisco | Tech | 58.00 | 0.0001 | 0.015 |
| JPM | JPMorgan Chase | Finance | 215.00 | 0.0002 | 0.015 |
| V | Visa | Finance | 285.00 | 0.0002 | 0.014 |
| BAC | Bank of America | Finance | 42.00 | 0.0002 | 0.017 |
| GS | Goldman Sachs | Finance | 550.00 | 0.0002 | 0.018 |
| MA | Mastercard | Finance | 475.00 | 0.0002 | 0.014 |
| PYPL | PayPal | Finance | 78.00 | 0.0001 | 0.022 |
| TSLA | Tesla | Consumer | 250.00 | 0.0005 | 0.035 |
| NFLX | Netflix | Consumer | 700.00 | 0.0004 | 0.025 |
| DIS | Disney | Consumer | 105.00 | 0.0001 | 0.019 |
| NKE | Nike | Consumer | 78.00 | 0.0001 | 0.020 |
| SBUX | Starbucks | Consumer | 95.00 | 0.0001 | 0.018 |
| PEP | PepsiCo | Consumer | 168.00 | 0.0001 | 0.012 |
| KO | Coca-Cola | Consumer | 63.00 | 0.0001 | 0.011 |
| COST | Costco | Consumer | 900.00 | 0.0002 | 0.015 |
| JNJ | Johnson & Johnson | Healthcare | 155.00 | 0.0001 | 0.012 |
| PFE | Pfizer | Healthcare | 28.00 | 0.0000 | 0.017 |
| UNH | UnitedHealth | Healthcare | 500.00 | 0.0001 | 0.019 |
| LLY | Eli Lilly | Healthcare | 780.00 | 0.0005 | 0.021 |
| XOM | Exxon Mobil | Energy | 115.00 | 0.0001 | 0.016 |
| CVX | Chevron | Energy | 160.00 | 0.0001 | 0.016 |

Default seed watchlist (`PLAN.md` §7) is unchanged — the first 10 rows in `PLAN.md`'s original
order (AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META, JPM, V, NFLX). Everything else in the table above
is available to add but not pre-watched, which is exactly the "add PYPL" scenario `PLAN.md` §9
demonstrates.

This table is the single source of truth for GBM parameters (resolving §B11 — "where do drift and
volatility live": as a hardcoded Python constant, not a config file or env var, matching the
simulator's "no external dependencies" design goal) and for sector groupings used in the
correlated-move logic (§3).

---

## 2. Price Model: Geometric Brownian Motion

Each ticker's price evolves under discrete-time GBM:

```
S(t+1) = S(t) * exp[ (μ - σ²/2) * dt + σ * sqrt(dt) * Z + sector_factor ]
```

Where:
- `S(t)` — current price
- `μ` (`drift`), `σ` (`volatility`) — from the per-ticker table in §1, expressed as **daily** rates
- `dt` — the simulation step size **as a fraction of a trading day**. At a 500ms tick and treating
  a trading day as 6.5 hours (23,400 seconds), `dt = 0.5 / 23400 ≈ 2.14e-5`. Using a realistic `dt`
  (rather than treating each 500ms tick as "one day") is what keeps per-tick moves visually subtle
  (fractions of a percent) rather than wildly unrealistic.
- `Z` — a standard normal random draw, independent per ticker per tick
- `sector_factor` — a small shared shock added to every ticker in the same sector this tick (§3);
  zero on ticks where no correlated event fires

This is the standard discrete GBM update (the `-σ²/2` term is the Itô correction so that the
*expected* price path matches the stated drift despite the log-normal step).

```python
import math
import random

def gbm_step(price: float, mu: float, sigma: float, dt: float, z: float, sector_factor: float = 0.0) -> float:
    exponent = (mu - 0.5 * sigma**2) * dt + sigma * math.sqrt(dt) * z + sector_factor
    return price * math.exp(exponent)
```

---

## 3. Correlated Sector Moves

Per `PLAN.md` §6: "each ticker belongs to a hardcoded sector bucket... a shared per-sector random
factor is added on top of each ticker's individual GBM step, so tickers in the same sector tend to
move together."

Implementation: once per tick, draw **one** shared normal sample per sector, scaled down relative
to individual ticker volatility (so sector co-movement is a visible tilt, not a dominant force that
makes all tech tickers move in lockstep):

```python
SECTOR_FACTOR_SCALE = 0.35  # fraction of an "average" ticker's per-tick sigma

def sector_factors(sectors: set[str], dt: float, rng: random.Random) -> dict[str, float]:
    return {
        sector: SECTOR_FACTOR_SCALE * 0.02 * math.sqrt(dt) * rng.gauss(0, 1)
        for sector in sectors
    }
```

Each ticker's per-tick call then passes `sector_factor=sector_factors[ticker_sector]` into
`gbm_step`. Because the same drawn value is reused for every ticker in a sector on a given tick,
AAPL/GOOGL/MSFT/etc. will tend to tick up or down together, while still each carrying their own
independent `Z` on top.

---

## 4. Random Events (Sudden Moves)

Per `PLAN.md` §6: "Occasional random 'events' — sudden 2-5% moves on a ticker for drama."

```python
EVENT_PROBABILITY_PER_TICK = 0.002   # ~1 event per ticker every ~4-5 minutes at 500ms ticks
EVENT_MAGNITUDE_RANGE = (0.02, 0.05)  # 2-5%

def maybe_apply_event(price: float, rng: random.Random) -> float:
    if rng.random() < EVENT_PROBABILITY_PER_TICK:
        magnitude = rng.uniform(*EVENT_MAGNITUDE_RANGE)
        direction = rng.choice([-1, 1])
        return price * (1 + direction * magnitude)
    return price
```

Events are applied as an independent multiplicative jump *after* the GBM step, once per ticker per
tick, and are not sector-correlated (a single-ticker "event" — earnings surprise, news headline —
is the intended flavor, distinct from the sector drift in §3).

---

## 5. Implementation

```python
# backend/app/market/simulator.py
import asyncio
import random
from dataclasses import dataclass

from .base import MarketDataSource

TRADING_DAY_SECONDS = 6.5 * 3600
TICK_SECONDS = 0.5

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

SECTOR_FACTOR_SCALE = 0.35
EVENT_PROBABILITY_PER_TICK = 0.002
EVENT_MAGNITUDE_RANGE = (0.02, 0.05)


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
            sector: SECTOR_FACTOR_SCALE * 0.02 * (dt ** 0.5) * self._rng.gauss(0, 1)
            for sector in sectors
        }
        for ticker, params in TICKER_UNIVERSE.items():
            z = self._rng.gauss(0, 1)
            new_price = _gbm_step(
                self._prices[ticker], params.mu, params.sigma, dt, z, factors[params.sector]
            )
            new_price = _maybe_apply_event(new_price, self._rng)
            self._prices[ticker] = round(new_price, 2)

    async def get_prices(self, tickers: list[str]) -> dict[str, float]:
        return {t: self._prices[t] for t in tickers if t in self._prices}

    async def is_valid_ticker(self, ticker: str) -> bool:
        return ticker in TICKER_UNIVERSE


def _gbm_step(price, mu, sigma, dt, z, sector_factor=0.0):
    import math
    exponent = (mu - 0.5 * sigma**2) * dt + sigma * math.sqrt(dt) * z + sector_factor
    return price * math.exp(exponent)


def _maybe_apply_event(price, rng):
    if rng.random() < EVENT_PROBABILITY_PER_TICK:
        magnitude = rng.uniform(*EVENT_MAGNITUDE_RANGE)
        direction = rng.choice([-1, 1])
        return price * (1 + direction * magnitude)
    return price
```

Notes on this implementation:

- **No locking needed on `_prices`**: a single asyncio task mutates it (`_tick_forever`), and reads
  (`get_prices`) happen on the same event loop thread between awaits — standard single-threaded
  asyncio safety, no `asyncio.Lock` required here (unlike `PriceCache` in `MARKET_INTERFACE.md`
  §3, which is written defensively since multiple call sites could in principle await it
  concurrently).
- **`round(new_price, 2)`** keeps prices at cent precision, matching how real quotes display; doing
  this once per tick (not per-read) means all consumers see the same rounded value, avoiding
  float-precision flicker in the frontend.
- **`seed` parameter**: exposed for deterministic unit tests (`PLAN.md` §12 — "GBM math is
  correct") — construct with a fixed seed and assert the resulting price sequence matches a
  precomputed expected sequence, or at least stays within statistically expected bounds.
- Prices can never go negative in GBM (it's multiplicative), so no floor/clamping logic is needed.

---

## 6. Testing Considerations (for `PLAN.md` §12)

- **Determinism**: construct `SimulatorMarketDataSource(seed=42)`, call `_advance_all` a fixed
  number of times, assert prices stay positive and within a plausible range (e.g. seed price ±50%
  over a short simulated span) — full bit-exact reproduction isn't necessary, just sanity bounds,
  since the exact sequence depends on `random.Random`'s internal algorithm rather than being a
  contract worth pinning.
- **Sector correlation**: with a fixed seed, verify that same-sector tickers' per-tick returns are
  positively correlated over many ticks (e.g. compute a Pearson correlation coefficient across a
  simulated series and assert it's above some modest positive threshold) — this is the one
  behavior that's easy to silently break (e.g. by accidentally drawing an independent `Z` for the
  sector factor instead of reusing the one shared draw).
- **Ticker universe membership**: `is_valid_ticker("PYPL")` → `True`; `is_valid_ticker("ZZZZ")` →
  `False`. This is the regression test that directly closes the Review 1 §A1 contradiction — it
  should be written against the exact ticker used in `PLAN.md` §9's example.
- **Interface conformance**: a shared test suite (parametrized over both
  `SimulatorMarketDataSource` and a mocked `MassiveMarketDataSource`) asserting both satisfy
  `MarketDataSource`'s contract — same method signatures, same "missing ticker is omitted, not
  errored" behavior from `get_prices`.
