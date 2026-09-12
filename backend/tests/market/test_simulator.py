import math
import statistics

import pytest

from app.market.simulator import (
    DEFAULT_WATCHLIST,
    EVENT_MAGNITUDE_RANGE,
    EVENT_PROBABILITY_PER_TICK,
    TICKER_UNIVERSE,
    SimulatorMarketDataSource,
    _gbm_step,
    _maybe_apply_event,
)

DT = 0.5 / (6.5 * 3600)


# --- GBM math correctness -----------------------------------------------


def test_gbm_step_matches_closed_form_with_zero_shock():
    price, mu, sigma = 100.0, 0.0003, 0.02
    result = _gbm_step(price, mu, sigma, DT, z=0.0, sector_factor=0.0)
    expected = price * math.exp((mu - 0.5 * sigma**2) * DT)
    assert result == pytest.approx(expected)


def test_gbm_step_positive_z_increases_price_more_than_negative_z():
    price, mu, sigma = 100.0, 0.0003, 0.02
    up = _gbm_step(price, mu, sigma, DT, z=1.0)
    down = _gbm_step(price, mu, sigma, DT, z=-1.0)
    assert up > price
    assert down < price
    assert up > down


def test_gbm_step_sector_factor_shifts_price_multiplicatively():
    price, mu, sigma = 100.0, 0.0, 0.0
    baseline = _gbm_step(price, mu, sigma, DT, z=0.0, sector_factor=0.0)
    shifted = _gbm_step(price, mu, sigma, DT, z=0.0, sector_factor=0.01)
    assert shifted == pytest.approx(baseline * math.exp(0.01))


def test_gbm_step_never_produces_negative_price():
    # Even an extreme negative shock can't flip sign — GBM is multiplicative.
    result = _gbm_step(100.0, 0.0, 0.02, DT, z=-50.0, sector_factor=-1.0)
    assert result > 0


# --- Random events ---------------------------------------------------------


def test_maybe_apply_event_skips_when_roll_is_above_probability():
    class StubRng:
        def random(self):
            return EVENT_PROBABILITY_PER_TICK + 0.001  # never triggers

    price = _maybe_apply_event(100.0, StubRng())
    assert price == 100.0


def test_maybe_apply_event_applies_bounded_jump_when_triggered():
    class StubRng:
        def random(self):
            return 0.0  # always below the probability threshold

        def uniform(self, lo, hi):
            return hi  # max magnitude, deterministic

        def choice(self, seq):
            return seq[0]  # -1

    price = _maybe_apply_event(100.0, StubRng())
    lo, hi = EVENT_MAGNITUDE_RANGE
    assert price == pytest.approx(100.0 * (1 - hi))


# --- Ticker universe --------------------------------------------------------


@pytest.mark.asyncio
async def test_ticker_universe_membership():
    # Directly closes REVIEW.md §A1: PYPL must be a valid add per PLAN.md
    # §9's example, ZZZZ must not exist.
    sim = SimulatorMarketDataSource()
    assert await sim.is_valid_ticker("PYPL") is True
    assert await sim.is_valid_ticker("ZZZZ") is False


def test_ticker_universe_has_seed_price_sector_and_params_for_every_entry():
    assert len(TICKER_UNIVERSE) >= 30
    for ticker, params in TICKER_UNIVERSE.items():
        assert ticker.isupper()
        assert params.seed_price > 0
        assert params.sector
        assert params.sigma > 0


def test_default_watchlist_is_subset_of_universe_and_matches_plan():
    assert DEFAULT_WATCHLIST == [
        "AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "NFLX",
    ]
    assert all(ticker in TICKER_UNIVERSE for ticker in DEFAULT_WATCHLIST)


# --- get_prices contract -----------------------------------------------------


@pytest.mark.asyncio
async def test_get_prices_omits_untracked_tickers():
    sim = SimulatorMarketDataSource()
    prices = await sim.get_prices(["AAPL", "ZZZZ"])
    assert "AAPL" in prices
    assert "ZZZZ" not in prices


@pytest.mark.asyncio
async def test_get_prices_returns_seed_prices_before_any_tick():
    sim = SimulatorMarketDataSource()
    prices = await sim.get_prices(["AAPL", "GOOGL"])
    assert prices == {"AAPL": 190.00, "GOOGL": 175.00}


@pytest.mark.asyncio
async def test_get_prices_empty_request_returns_empty_dict():
    sim = SimulatorMarketDataSource()
    assert await sim.get_prices([]) == {}


# --- Simulation dynamics ------------------------------------------------------


@pytest.mark.asyncio
async def test_prices_stay_positive_and_bounded_over_many_ticks():
    sim = SimulatorMarketDataSource(seed=42)
    for _ in range(500):
        sim._advance_all(DT)
    for ticker, params in TICKER_UNIVERSE.items():
        price = sim._prices[ticker]
        assert price > 0
        assert 0.5 * params.seed_price < price < 1.5 * params.seed_price


@pytest.mark.asyncio
async def test_advance_all_is_deterministic_given_a_seed():
    sim_a = SimulatorMarketDataSource(seed=7)
    sim_b = SimulatorMarketDataSource(seed=7)
    for _ in range(50):
        sim_a._advance_all(DT)
        sim_b._advance_all(DT)
    assert sim_a._prices == sim_b._prices


@pytest.mark.asyncio
async def test_different_seeds_diverge():
    sim_a = SimulatorMarketDataSource(seed=1)
    sim_b = SimulatorMarketDataSource(seed=2)
    for _ in range(50):
        sim_a._advance_all(DT)
        sim_b._advance_all(DT)
    assert sim_a._prices != sim_b._prices


@pytest.mark.asyncio
async def test_same_sector_tickers_are_positively_correlated():
    """This is the behavior most likely to silently break (e.g. if the
    sector factor were accidentally redrawn per-ticker instead of shared) —
    verify via Pearson correlation over a simulated return series."""
    sim = SimulatorMarketDataSource(seed=123)
    returns: dict[str, list[float]] = {t: [] for t in ("AAPL", "GOOGL", "PFE")}
    previous = dict(sim._prices)
    for _ in range(2000):
        sim._advance_all(DT)
        for ticker in returns:
            returns[ticker].append(sim._prices[ticker] / previous[ticker] - 1)
        previous = dict(sim._prices)

    same_sector_corr = _pearson(returns["AAPL"], returns["GOOGL"])  # both Tech
    cross_sector_corr = _pearson(returns["AAPL"], returns["PFE"])  # Tech vs Healthcare

    assert same_sector_corr > 0.1
    assert same_sector_corr > cross_sector_corr


@pytest.mark.asyncio
async def test_start_spawns_background_task_and_stop_cancels_it():
    sim = SimulatorMarketDataSource(seed=1)
    await sim.start()
    assert sim._task is not None
    assert not sim._task.done()
    await sim.stop()
    assert sim._task is None


def _pearson(xs: list[float], ys: list[float]) -> float:
    mean_x, mean_y = statistics.mean(xs), statistics.mean(ys)
    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    var_x = sum((x - mean_x) ** 2 for x in xs)
    var_y = sum((y - mean_y) ** 2 for y in ys)
    if var_x == 0 or var_y == 0:
        return 0.0
    return cov / math.sqrt(var_x * var_y)
