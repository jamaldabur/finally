"""Tests for app/llm/actions.py::execute_llm_actions() (03-01-PLAN.md Task 3,
tests 6-7).

Builds ChatResponseSchema instances directly rather than going through the
route, and drives them through execute_llm_actions() with a real
PriceCache, the simulator market source, and a real asyncio.Lock — same
convention as backend/tests/portfolio/test_service.py.
"""

from __future__ import annotations

import asyncio
import math

import pytest

from app.db import portfolio_snapshots as portfolio_snapshots_module
from app.db import positions as positions_module
from app.db import trades as trades_module
from app.db import users_profile as users_profile_module
from app.db import watchlist as watchlist_module
from app.llm.actions import execute_llm_actions
from app.llm.mock import build_mock_response
from app.llm.schema import ChatResponseSchema, LlmTradeItem, LlmWatchlistChange
from app.market.cache import PriceCache
from app.market.simulator import SimulatorMarketDataSource
from app.portfolio.service import execute_trade


async def _init_tables() -> None:
    await users_profile_module.init_db()
    await positions_module.init_db()
    await trades_module.init_db()
    await portfolio_snapshots_module.init_db()
    await watchlist_module.init_db()


@pytest.mark.asyncio
async def test_execute_llm_actions_annotates_bad_item_and_executes_good_one() -> None:
    """Test 6: one bad item (quantity=-1) and one good item yield two
    annotations in source order — error then executed — and only the good
    one produced a trade."""
    await _init_tables()
    cache = PriceCache()
    market_source = SimulatorMarketDataSource()
    lock = asyncio.Lock()
    await cache.update("CSCO", 100.0)

    response = ChatResponseSchema(
        message="ok",
        trades=[
            LlmTradeItem(ticker="CSCO", side="buy", quantity=-1),
            LlmTradeItem(ticker="CSCO", side="buy", quantity=5),
        ],
    )

    result = await execute_llm_actions(
        price_cache=cache,
        market_source=market_source,
        lock=lock,
        response=response,
    )

    assert len(result.trades) == 2
    assert result.trades[0].outcome == "error"
    assert result.trades[1].outcome == "executed"

    all_trades = await trades_module.get_trades()
    assert len(all_trades) == 1
    assert all_trades[0].quantity == 5


@pytest.mark.asyncio
async def test_execute_llm_actions_does_not_collapse_duplicate_items() -> None:
    """Test 7: two identical trade items yield two independent executed
    annotations, and the cash balance reflects both fills."""
    await _init_tables()
    cache = PriceCache()
    market_source = SimulatorMarketDataSource()
    lock = asyncio.Lock()
    await cache.update("CSCO", 100.0)

    response = ChatResponseSchema(
        message="ok",
        trades=[
            LlmTradeItem(ticker="CSCO", side="buy", quantity=5),
            LlmTradeItem(ticker="CSCO", side="buy", quantity=5),
        ],
    )

    result = await execute_llm_actions(
        price_cache=cache,
        market_source=market_source,
        lock=lock,
        response=response,
    )

    assert len(result.trades) == 2
    assert result.trades[0].outcome == "executed"
    assert result.trades[1].outcome == "executed"

    cash = await users_profile_module.get_cash_balance()
    assert cash == 9000.0


@pytest.mark.asyncio
async def test_execute_llm_actions_watchlist_add_and_remove_happy_path() -> None:
    """Adding a ticker not yet on the watchlist and removing one that is
    both report outcome == "executed", and the watchlist table reflects the
    changes (CR-01 / WR-03 happy-path coverage)."""
    await _init_tables()
    cache = PriceCache()
    market_source = SimulatorMarketDataSource()
    lock = asyncio.Lock()

    response = ChatResponseSchema(
        message="ok",
        watchlist_changes=[
            LlmWatchlistChange(ticker="PYPL", action="add"),
            LlmWatchlistChange(ticker="AAPL", action="remove"),
        ],
    )

    result = await execute_llm_actions(
        price_cache=cache,
        market_source=market_source,
        lock=lock,
        response=response,
    )

    assert len(result.watchlist_changes) == 2
    assert result.watchlist_changes[0].outcome == "executed"
    assert result.watchlist_changes[0].reason is None
    assert result.watchlist_changes[1].outcome == "executed"
    assert result.watchlist_changes[1].reason is None

    tickers = await watchlist_module.get_watchlist_tickers()
    assert "PYPL" in tickers
    assert "AAPL" not in tickers


@pytest.mark.asyncio
async def test_execute_llm_actions_watchlist_bad_item_annotated_error() -> None:
    """An invalid action string is rejected by _validate_watchlist_item()
    before ever touching the watchlist table."""
    await _init_tables()
    cache = PriceCache()
    market_source = SimulatorMarketDataSource()
    lock = asyncio.Lock()

    response = ChatResponseSchema(
        message="ok",
        watchlist_changes=[
            LlmWatchlistChange(ticker="PYPL", action="hold"),
        ],
    )

    result = await execute_llm_actions(
        price_cache=cache,
        market_source=market_source,
        lock=lock,
        response=response,
    )

    assert len(result.watchlist_changes) == 1
    assert result.watchlist_changes[0].outcome == "error"
    assert result.watchlist_changes[0].reason is not None

    tickers = await watchlist_module.get_watchlist_tickers()
    assert "PYPL" not in tickers


@pytest.mark.asyncio
async def test_execute_llm_actions_watchlist_unknown_ticker_rejected() -> None:
    """A ticker outside SimulatorMarketDataSource.TICKER_UNIVERSE is
    rejected with an error annotation and never reaches the watchlist
    table."""
    await _init_tables()
    cache = PriceCache()
    market_source = SimulatorMarketDataSource()
    lock = asyncio.Lock()

    response = ChatResponseSchema(
        message="ok",
        watchlist_changes=[
            LlmWatchlistChange(ticker="ZZZZ", action="add"),
        ],
    )

    result = await execute_llm_actions(
        price_cache=cache,
        market_source=market_source,
        lock=lock,
        response=response,
    )

    assert len(result.watchlist_changes) == 1
    assert result.watchlist_changes[0].outcome == "error"
    assert "Unknown ticker" in result.watchlist_changes[0].reason

    tickers = await watchlist_module.get_watchlist_tickers()
    assert "ZZZZ" not in tickers


@pytest.mark.asyncio
async def test_execute_llm_actions_watchlist_duplicate_items_not_collapsed() -> None:
    """Two identical watchlist add requests in the same response yield two
    independent annotations: the first actually inserts (executed), the
    second is a true no-op (error), matching CR-01's fixed contract."""
    await _init_tables()
    cache = PriceCache()
    market_source = SimulatorMarketDataSource()
    lock = asyncio.Lock()

    response = ChatResponseSchema(
        message="ok",
        watchlist_changes=[
            LlmWatchlistChange(ticker="PYPL", action="add"),
            LlmWatchlistChange(ticker="PYPL", action="add"),
        ],
    )

    result = await execute_llm_actions(
        price_cache=cache,
        market_source=market_source,
        lock=lock,
        response=response,
    )

    assert len(result.watchlist_changes) == 2
    assert result.watchlist_changes[0].outcome == "executed"
    assert result.watchlist_changes[1].outcome == "error"
    assert result.watchlist_changes[1].reason == "PYPL is already on the watchlist"


@pytest.mark.asyncio
async def test_execute_llm_actions_watchlist_noop_add_reports_error() -> None:
    """CR-01 regression: adding a ticker already on the watchlist must not
    be reported as "executed" — nothing was actually inserted."""
    await _init_tables()
    cache = PriceCache()
    market_source = SimulatorMarketDataSource()
    lock = asyncio.Lock()

    response = ChatResponseSchema(
        message="ok",
        watchlist_changes=[
            LlmWatchlistChange(ticker="AAPL", action="add"),  # already seeded
        ],
    )

    result = await execute_llm_actions(
        price_cache=cache,
        market_source=market_source,
        lock=lock,
        response=response,
    )

    assert len(result.watchlist_changes) == 1
    assert result.watchlist_changes[0].outcome == "error"
    assert result.watchlist_changes[0].reason == "AAPL is already on the watchlist"


@pytest.mark.asyncio
async def test_execute_llm_actions_watchlist_noop_remove_reports_error() -> None:
    """CR-01 regression: removing a ticker that isn't on the watchlist must
    not be reported as "executed" — nothing was actually deleted."""
    await _init_tables()
    cache = PriceCache()
    market_source = SimulatorMarketDataSource()
    lock = asyncio.Lock()

    response = ChatResponseSchema(
        message="ok",
        watchlist_changes=[
            LlmWatchlistChange(ticker="PYPL", action="remove"),  # never added
        ],
    )

    result = await execute_llm_actions(
        price_cache=cache,
        market_source=market_source,
        lock=lock,
        response=response,
    )

    assert len(result.watchlist_changes) == 1
    assert result.watchlist_changes[0].outcome == "error"
    assert result.watchlist_changes[0].reason == "PYPL is not on the watchlist"


# --- 03-08 gap-closure regression tests (G-03-5, G-03-6) ---------------------
#
# These tests construct LlmTradeItem/LlmWatchlistChange objects directly
# rather than routing through build_mock_response(), because _TRADE_PATTERN
# matches only unsigned digits and _WATCHLIST_PATTERN captures a bare word —
# the mock path is structurally incapable of producing either a signed
# quantity or a padded side/action. See
# test_mock_response_cannot_emit_a_negative_quantity below, which pins that
# fact in the suite.


@pytest.mark.asyncio
async def test_execute_llm_actions_recovers_negative_sell_quantity() -> None:
    """G-03-5: a sell item whose quantity arrives negative executes at its
    absolute magnitude — the direction was already stated correctly in
    `side`, so the redundant sign must not discard the item."""
    await _init_tables()
    cache = PriceCache()
    market_source = SimulatorMarketDataSource()
    lock = asyncio.Lock()
    await cache.update("CSCO", 100.0)

    await execute_trade(
        price_cache=cache,
        market_source=market_source,
        lock=lock,
        ticker="CSCO",
        side="buy",
        quantity=5,
    )

    response = ChatResponseSchema(
        message="ok",
        trades=[LlmTradeItem(ticker="CSCO", side="sell", quantity=-2)],
    )
    result = await execute_llm_actions(
        price_cache=cache,
        market_source=market_source,
        lock=lock,
        response=response,
    )

    assert len(result.trades) == 1
    trade = result.trades[0]
    assert trade.outcome == "executed"
    assert trade.quantity == 2
    assert trade.price is not None

    position = await positions_module.get_position("CSCO")
    assert position is not None
    assert position.quantity == 3


@pytest.mark.asyncio
async def test_execute_llm_actions_still_rejects_negative_buy_quantity() -> None:
    """G-03-5 missing item 1: a negative buy stays rejected — recovering it
    would mean inferring trade direction from a sign, which this project
    never does. No trade row is written and cash is unchanged."""
    await _init_tables()
    cache = PriceCache()
    market_source = SimulatorMarketDataSource()
    lock = asyncio.Lock()
    await cache.update("CSCO", 100.0)

    response = ChatResponseSchema(
        message="ok",
        trades=[LlmTradeItem(ticker="CSCO", side="buy", quantity=-1)],
    )
    result = await execute_llm_actions(
        price_cache=cache,
        market_source=market_source,
        lock=lock,
        response=response,
    )

    assert len(result.trades) == 1
    assert result.trades[0].outcome == "error"

    all_trades = await trades_module.get_trades()
    assert len(all_trades) == 0
    cash = await users_profile_module.get_cash_balance()
    assert cash == 10000.0


@pytest.mark.asyncio
@pytest.mark.parametrize("side", ["buy", "sell"])
@pytest.mark.parametrize("quantity", [0.0, -0.0, math.nan, math.inf, -math.inf])
async def test_execute_llm_actions_rejects_zero_and_non_finite_quantities(
    side: str, quantity: float
) -> None:
    """Zero, negative zero, NaN and infinity are all still rejected for
    both sides, before execute_trade() is ever called — none of them is a
    finite strictly-negative sell quantity, so the recovery path never
    applies to any of them."""
    await _init_tables()
    cache = PriceCache()
    market_source = SimulatorMarketDataSource()
    lock = asyncio.Lock()
    await cache.update("CSCO", 100.0)
    if side == "sell":
        # Establish a held position so this case cannot fail for the
        # unrelated reason of insufficient shares — the setup buy itself
        # writes one trade row, so the assertion below compares against
        # that baseline rather than assuming zero rows overall.
        await execute_trade(
            price_cache=cache,
            market_source=market_source,
            lock=lock,
            ticker="CSCO",
            side="buy",
            quantity=5,
        )
    trades_before = len(await trades_module.get_trades())

    response = ChatResponseSchema(
        message="ok",
        trades=[LlmTradeItem(ticker="CSCO", side=side, quantity=quantity)],
    )
    result = await execute_llm_actions(
        price_cache=cache,
        market_source=market_source,
        lock=lock,
        response=response,
    )

    assert len(result.trades) == 1
    assert result.trades[0].outcome == "error"

    all_trades = await trades_module.get_trades()
    assert len(all_trades) == trades_before


@pytest.mark.asyncio
async def test_execute_llm_actions_padded_side_executes() -> None:
    """A trade item whose side carries surrounding whitespace and mixed
    case executes correctly. Before the single-normalization fix, this
    input passed validation (which stripped and lowered) and was then
    rejected by execute_trade() (which received the raw, padded side)."""
    await _init_tables()
    cache = PriceCache()
    market_source = SimulatorMarketDataSource()
    lock = asyncio.Lock()
    await cache.update("CSCO", 100.0)

    response = ChatResponseSchema(
        message="ok",
        trades=[LlmTradeItem(ticker="CSCO", side=" BUY ", quantity=5)],
    )
    result = await execute_llm_actions(
        price_cache=cache,
        market_source=market_source,
        lock=lock,
        response=response,
    )

    assert len(result.trades) == 1
    assert result.trades[0].outcome == "executed"
    assert result.trades[0].side == "buy"


@pytest.mark.asyncio
async def test_execute_llm_actions_padded_add_action_adds_and_removes_nothing() -> None:
    """A watchlist change whose action carries a leading space and names an
    add, for a ticker not currently on the watchlist, adds it — nothing is
    removed and the watchlist grows by exactly one."""
    await _init_tables()
    cache = PriceCache()
    market_source = SimulatorMarketDataSource()
    lock = asyncio.Lock()

    before = await watchlist_module.get_watchlist_tickers()
    assert "PYPL" not in before

    response = ChatResponseSchema(
        message="ok",
        watchlist_changes=[LlmWatchlistChange(ticker="PYPL", action=" add")],
    )
    result = await execute_llm_actions(
        price_cache=cache,
        market_source=market_source,
        lock=lock,
        response=response,
    )

    assert len(result.watchlist_changes) == 1
    assert result.watchlist_changes[0].outcome == "executed"

    after = await watchlist_module.get_watchlist_tickers()
    assert "PYPL" in after
    assert len(after) == len(before) + 1


@pytest.mark.asyncio
async def test_execute_llm_actions_padded_add_on_watched_ticker_does_not_delete_it() -> None:
    """The literal reproduction of the confirmed data-loss incident: a
    padded add (" add") for a ticker already on the watchlist must be
    annotated as an error with the existing already-on-the-watchlist
    reason, and that ticker must still be on the watchlist afterwards —
    never silently deleted by falling into the remove branch."""
    await _init_tables()
    cache = PriceCache()
    market_source = SimulatorMarketDataSource()
    lock = asyncio.Lock()

    before = await watchlist_module.get_watchlist_tickers()
    assert "AAPL" in before

    response = ChatResponseSchema(
        message="ok",
        watchlist_changes=[LlmWatchlistChange(ticker="AAPL", action=" add")],
    )
    result = await execute_llm_actions(
        price_cache=cache,
        market_source=market_source,
        lock=lock,
        response=response,
    )

    assert len(result.watchlist_changes) == 1
    assert result.watchlist_changes[0].outcome == "error"
    assert result.watchlist_changes[0].reason == "AAPL is already on the watchlist"

    after = await watchlist_module.get_watchlist_tickers()
    assert "AAPL" in after
    assert len(after) == len(before)


@pytest.mark.asyncio
async def test_execute_llm_actions_padded_remove_action_removes() -> None:
    """A watchlist change whose action carries surrounding whitespace and
    names a remove, for a ticker that is on the watchlist, removes exactly
    that one ticker."""
    await _init_tables()
    cache = PriceCache()
    market_source = SimulatorMarketDataSource()
    lock = asyncio.Lock()

    before = await watchlist_module.get_watchlist_tickers()
    assert "AAPL" in before

    response = ChatResponseSchema(
        message="ok",
        watchlist_changes=[LlmWatchlistChange(ticker="AAPL", action=" remove ")],
    )
    result = await execute_llm_actions(
        price_cache=cache,
        market_source=market_source,
        lock=lock,
        response=response,
    )

    assert len(result.watchlist_changes) == 1
    assert result.watchlist_changes[0].outcome == "executed"

    after = await watchlist_module.get_watchlist_tickers()
    assert "AAPL" not in after
    assert len(after) == len(before) - 1


def test_mock_response_cannot_emit_a_negative_quantity() -> None:
    """Pins in the suite why LLM_MOCK=true — the path every automated test
    and the whole E2E suite runs under — could never have caught either
    G-03-5 or G-03-6. _TRADE_PATTERN (app/llm/mock.py) matches only unsigned
    digits (`\\d+(?:\\.\\d+)?`), so a signed quantity like "-2" can never be
    captured: "sell -2 AAPL" produces no trade at all rather than a
    negative one. _WATCHLIST_PATTERN captures a bare `[A-Za-z]{1,5}` word
    with `\\b(add|remove)\\s+`, so its match can never carry surrounding
    whitespace the way a real backing model's JSON field can. Both gaps
    are therefore only reachable via directly-constructed schema items,
    which is what every other test in this block does."""
    negative_sell = build_mock_response("sell -2 AAPL")
    assert negative_sell.trades == []

    padded_add = build_mock_response("please add AAPL to my watchlist")
    assert len(padded_add.watchlist_changes) == 1
    assert padded_add.watchlist_changes[0].action == "add"
