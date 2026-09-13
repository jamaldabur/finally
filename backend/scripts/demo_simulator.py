"""Rich terminal demo of the market data simulator.

Ticks `SimulatorMarketDataSource` in real time through the exact same
`run_update_loop` / `PriceCache` path the real FastAPI app uses (see
planning/MARKET_DATA_DESIGN.md §7), then renders it as a live-updating
table — a terminal-native preview of what the SSE stream pushes to the
frontend, not a separate reimplementation of the simulator's behavior.

Usage (from backend/):
    uv run --group demo python scripts/demo_simulator.py
    uv run --group demo python scripts/demo_simulator.py --all
    uv run --group demo python scripts/demo_simulator.py --tickers AAPL NVDA TSLA
    uv run --group demo python scripts/demo_simulator.py --seed 42 --fps 4

Ctrl+C to stop.
"""

from __future__ import annotations

import argparse
import asyncio

from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.text import Text

from app.market.base import ChangeDirection, PriceTick
from app.market.cache import PriceCache
from app.market.loop import SIMULATOR_TICK_SECONDS, run_update_loop
from app.market.simulator import DEFAULT_WATCHLIST, TICKER_UNIVERSE, SimulatorMarketDataSource

DIRECTION_STYLE = {
    ChangeDirection.UP: "bold green",
    ChangeDirection.DOWN: "bold red",
    ChangeDirection.UNCHANGED: "dim",
}
DIRECTION_ARROW = {
    # Plain ASCII, not Unicode arrows: Windows' legacy console codepage
    # (cp1252) can't encode U+25B2/U+25BC/U+00B7, which crashes Rich's
    # legacy-Windows render path with a UnicodeEncodeError. ASCII is the
    # only choice guaranteed to render on every terminal this gets run in.
    ChangeDirection.UP: "^",
    ChangeDirection.DOWN: "v",
    ChangeDirection.UNCHANGED: "-",
}


def build_table(ticks: list[PriceTick], tickers: list[str], event_count: int) -> Table:
    table = Table(
        title=f"FinAlly Market Simulator - Live  (events fired: {event_count})",
        expand=True,
    )
    table.add_column("Ticker", style="bold")
    table.add_column("Sector")
    table.add_column("Price", justify="right")
    table.add_column("Chg", justify="right")
    table.add_column("Chg %", justify="right")

    by_ticker = {tick.ticker: tick for tick in ticks}
    for ticker in tickers:
        sector = TICKER_UNIVERSE[ticker].sector
        tick = by_ticker.get(ticker)
        if tick is None:
            table.add_row(ticker, sector, "-", "-", "-")
            continue
        style = DIRECTION_STYLE[tick.direction]
        arrow = DIRECTION_ARROW[tick.direction]
        delta = tick.price - tick.previous_price
        pct = (delta / tick.previous_price * 100) if tick.previous_price else 0.0
        table.add_row(
            ticker,
            sector,
            f"${tick.price:,.2f}",
            Text(f"{arrow} {delta:+.2f}", style=style),
            Text(f"{pct:+.2f}%", style=style),
        )
    return table


async def run_demo(tickers: list[str], seed: int | None, fps: float) -> None:
    source = SimulatorMarketDataSource(seed=seed)
    cache = PriceCache()
    await source.start()

    # A crude "event just fired" counter for the title bar, purely for demo
    # flavor — it inspects the same private state the simulator itself owns,
    # which is fine here since this script is not production code.
    event_count = 0
    last_prices = dict(source._prices)

    async def get_watchlist() -> list[str]:
        return tickers

    update_task = asyncio.create_task(
        run_update_loop(source, cache, get_watchlist, SIMULATOR_TICK_SECONDS)
    )

    console = Console()
    try:
        with Live(console=console, refresh_per_second=fps, screen=False) as live:
            while True:
                await asyncio.sleep(1 / fps)
                current_prices = source._prices
                for ticker, price in current_prices.items():
                    prior = last_prices.get(ticker, price)
                    if prior and abs(price / prior - 1) > 0.015:
                        event_count += 1
                last_prices = dict(current_prices)

                ticks = await cache.snapshot()
                live.update(build_table(ticks, tickers, event_count))
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        update_task.cancel()
        await source.stop()
        console.print("\n[dim]Simulator stopped.[/dim]")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--tickers",
        nargs="+",
        metavar="TICKER",
        help=f"Tickers to display (default: the {len(DEFAULT_WATCHLIST)}-ticker default watchlist).",
    )
    group.add_argument(
        "--all",
        action="store_true",
        help=f"Show the entire {len(TICKER_UNIVERSE)}-ticker universe instead of the default watchlist.",
    )
    parser.add_argument("--seed", type=int, default=None, help="Fix the RNG seed for a reproducible run.")
    parser.add_argument("--fps", type=float, default=2.0, help="Terminal refresh rate in Hz (default: 2).")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.all:
        tickers = list(TICKER_UNIVERSE.keys())
    else:
        tickers = args.tickers or DEFAULT_WATCHLIST

    unknown = [t for t in tickers if t not in TICKER_UNIVERSE]
    if unknown:
        raise SystemExit(f"Unknown ticker(s): {', '.join(unknown)}")

    try:
        asyncio.run(run_demo(tickers, args.seed, args.fps))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
