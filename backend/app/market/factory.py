"""Selects the active MarketDataSource implementation at startup."""

import os

from .base import MarketDataSource
from .massive import MassiveMarketDataSource
from .simulator import SimulatorMarketDataSource


def build_market_data_source() -> MarketDataSource:
    """The entire selection logic PLAN.md §5 describes: if MASSIVE_API_KEY
    is set and non-empty, use Massive; otherwise use the simulator. Nothing
    else in the app should re-check this env var — call this once at
    startup and store the result on app.state."""
    api_key = os.environ.get("MASSIVE_API_KEY", "").strip()
    if api_key:
        return MassiveMarketDataSource(api_key=api_key)
    return SimulatorMarketDataSource()
