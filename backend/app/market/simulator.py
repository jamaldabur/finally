"""Built-in market data simulator.

Default data source (used whenever `MASSIVE_API_KEY` is unset). Generates
prices using geometric Brownian motion with per-ticker drift/volatility,
correlated per-sector moves, and occasional random "events" for drama
(PLAN.md §6). Needs no network access or external dependencies.
"""

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


# The complete, hardcoded set of tickers the simulator can generate prices
# for. `is_valid_ticker()` checks membership in this table and nothing else
# — an add request for anything not listed here is rejected (PLAN.md §8).
# Default seed watchlist (PLAN.md §7) is the first 10 entries in PLAN.md's
# original order; everything else is addable but not pre-watched.
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

# First 10 tickers of TICKER_UNIVERSE in PLAN.md §7's original order.
DEFAULT_WATCHLIST: list[str] = [
    "AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "NFLX",
]


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
            self._task = None

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


def _gbm_step(
    price: float, mu: float, sigma: float, dt: float, z: float, sector_factor: float = 0.0
) -> float:
    exponent = (mu - 0.5 * sigma**2) * dt + sigma * math.sqrt(dt) * z + sector_factor
    return price * math.exp(exponent)


def _maybe_apply_event(price: float, rng: random.Random) -> float:
    if rng.random() < EVENT_PROBABILITY_PER_TICK:
        magnitude = rng.uniform(*EVENT_MAGNITUDE_RANGE)
        direction = rng.choice([-1, 1])
        return price * (1 + direction * magnitude)
    return price
