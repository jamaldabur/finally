"""Unified market data interface.

Common contract implemented by both `SimulatorMarketDataSource` and
`MassiveMarketDataSource` (see PLAN.md §6, planning/MARKET_DATA_DESIGN.md §3).
Everything above this layer — the price cache, SSE streaming, watchlist
validation, trade execution — codes only against `MarketDataSource` and must
never branch on which concrete implementation is active.
"""

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
    and driven by a single background task (`run_update_loop`) that feeds the
    shared `PriceCache`. No other code should hold a reference to more than
    one `MarketDataSource` instance at a time.
    """

    @abstractmethod
    async def start(self) -> None:
        """Called once at app startup. Simulator: spawns its internal tick
        loop. Massive: constructs the shared httpx.AsyncClient — Massive
        performs no polling itself; `run_update_loop` drives its cadence
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
        for ordinary failure modes (rate limits, transient network errors)."""

    @abstractmethod
    async def is_valid_ticker(self, ticker: str) -> bool:
        """Whether `ticker` can be added to the watchlist under this data
        source. What 'valid' means differs by implementation, by design:
        the simulator checks a closed table, Massive checks the live API."""
