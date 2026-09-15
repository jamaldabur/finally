"""FastAPI application entry point.

Wires the market data layer (planning/MARKET_DATA_DESIGN.md §8) into a real
running app: builds the active MarketDataSource, starts it, and drives it
into the shared PriceCache via a background update loop for the lifetime of
the process. `create_app()` is a factory (rather than a bare module-level
`app`) so tests can construct isolated instances with their own lifespan run.
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .db import init_db
from .db.portfolio_snapshots import insert_snapshot
from .db.watchlist import get_watchlist_tickers
from .market.cache import PriceCache
from .market.factory import build_market_data_source
from .market.loop import MASSIVE_POLL_SECONDS, SIMULATOR_TICK_SECONDS, run_update_loop
from .market.massive import MassiveMarketDataSource
from .portfolio.service import get_portfolio_state
from .routes import chat, health, portfolio, stream, watchlist

logger = logging.getLogger(__name__)

SNAPSHOT_INTERVAL_SECONDS = 30

# backend/app/main.py -> parents[2] is the repo root, so this defaults to
# <repo root>/static — where the Docker build copies the Next.js static
# export (PLAN.md §11). Override with FINALLY_STATIC_DIR if needed. Absent
# in local dev (no frontend build present), in which case no mount happens.
_DEFAULT_STATIC_DIR = Path(__file__).resolve().parents[2] / "static"
STATIC_DIR = Path(os.environ.get("FINALLY_STATIC_DIR", str(_DEFAULT_STATIC_DIR)))


async def _run_snapshot_loop(app: FastAPI, interval: float) -> None:
    """Records a portfolio_snapshots row every `interval` seconds (PLAN.md
    §7) — in addition to the immediate snapshot `execute_trade` records after
    every fill. Wrapped in try/except, same as run_update_loop, so a single
    bad iteration (e.g. a transient DB error) can't silently kill the loop
    for the rest of the process's lifetime."""
    while True:
        await asyncio.sleep(interval)
        try:
            state = await get_portfolio_state(app.state)
            await insert_snapshot("default", state["total_value"])
        except Exception:
            logger.exception("portfolio snapshot loop iteration failed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()

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
    # this is the single constructed MarketDataSource instance for the
    # process's lifetime (planning/MARKET_DATA_DESIGN.md §7).
    app.state.market_source = source
    app.state.price_cache = cache

    snapshot_task = asyncio.create_task(
        _run_snapshot_loop(app, SNAPSHOT_INTERVAL_SECONDS)
    )

    yield

    snapshot_task.cancel()
    update_task.cancel()
    await source.stop()


def create_app() -> FastAPI:
    app = FastAPI(title="FinAlly", lifespan=lifespan)
    app.include_router(health.router)
    app.include_router(stream.router)
    app.include_router(portfolio.router)
    app.include_router(watchlist.router)
    app.include_router(chat.router)

    # Mounted last, at "/", so it only serves paths the API routers above
    # didn't already claim (e.g. "/api/*"). Only present once the frontend
    # has been built into STATIC_DIR (PLAN.md §11's Docker image) — skipped
    # in local backend-only dev where that directory doesn't exist.
    if STATIC_DIR.is_dir():
        app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")

    return app


app = create_app()
