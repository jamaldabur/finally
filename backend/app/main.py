"""FastAPI application entry point.

Wires the market data layer (planning/MARKET_DATA_DESIGN.md §8) into a real
running app: builds the active MarketDataSource, starts it, and drives it
into the shared PriceCache via a background update loop for the lifetime of
the process. `create_app()` is a factory (rather than a bare module-level
`app`) so tests can construct isolated instances with their own lifespan run.
"""

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import chat_messages, portfolio_snapshots, positions, trades, users_profile
from .db.watchlist import get_watchlist_tickers, init_db
from .market.cache import PriceCache
from .market.factory import build_market_data_source
from .market.loop import MASSIVE_POLL_SECONDS, SIMULATOR_TICK_SECONDS, run_update_loop
from .market.massive import MassiveMarketDataSource
from .portfolio.snapshots import run_portfolio_snapshot_loop
from .routes import chat, health, portfolio, stream
from .routes import watchlist as watchlist_routes

# backend/app/main.py -> parents[0]=app, [1]=backend, [2]=repo root — loads
# the project-root .env (PLAN.md §5) so OPENROUTER_API_KEY reaches LiteLLM.
# No override=True: an already-exported variable or a test's
# monkeypatch.setenv must both win over the file (03-01-PLAN.md Task 2).
load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # All init_db() calls run before any asyncio.create_task(...) below —
    # a background task's first tick could otherwise hit "no such table"
    # (01-RESEARCH.md Pitfall 6).
    await init_db()
    await users_profile.init_db()
    await positions.init_db()
    await trades.init_db()
    await portfolio_snapshots.init_db()
    await chat_messages.init_db()

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
    snapshot_task = asyncio.create_task(run_portfolio_snapshot_loop(cache))

    # Stored on app.state so routes can reach both without a second global —
    # this is the single constructed MarketDataSource instance for the
    # process's lifetime (planning/MARKET_DATA_DESIGN.md §7).
    app.state.market_source = source
    app.state.price_cache = cache
    # Guards the read-modify-write of cash_balance + positions + the trades
    # insert in app/portfolio/service.py::execute_trade(), mirroring
    # PriceCache's own asyncio.Lock (the codebase's only other precedent for
    # guarding shared mutable state under concurrent async access).
    app.state.portfolio_lock = asyncio.Lock()
    # Stored so tests (and any future introspection) can assert the task was
    # actually cancelled on shutdown, not just fire-and-forget (01-RESEARCH.md
    # Pitfall 5 — an untracked task leaks across TestClient teardown and can
    # write into the next test's throwaway database).
    app.state.snapshot_task = snapshot_task

    yield

    update_task.cancel()
    snapshot_task.cancel()
    await source.stop()


def create_app() -> FastAPI:
    app = FastAPI(title="FinAlly", lifespan=lifespan)
    # Dev-only convenience: `next dev` (Plan 02-01) runs on :3000 while this
    # backend runs on :8000, and `output: 'export'` forecloses the usual
    # Next.js dev-proxy trick (02-RESEARCH.md Pitfall 1), so the frontend
    # talks to the backend cross-origin during local development. Scoped to
    # exactly one explicit origin, no credentials — PLAN.md §3 production
    # architecture is same-origin (FastAPI serves the static export), so this
    # middleware is inert there. Phase 5 should decide whether it ships in
    # the Docker image at all once frontend and backend are always
    # same-origin.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(stream.router)
    app.include_router(portfolio.router)
    app.include_router(watchlist_routes.router)
    app.include_router(chat.router)
    return app


app = create_app()
