"""Validated watchlist add/remove path (PLAN.md §6/§8).

`app.db.watchlist.add_ticker`/`remove_ticker` are pure storage — they don't
validate that a ticker is a recognized symbol or already present. This
module is where that validation happens, so both the REST routes and (later)
the LLM chat flow share it.
"""

from __future__ import annotations

from ..db import watchlist

DEFAULT_USER_ID = "default"


class WatchlistError(Exception):
    """Raised when a watchlist change fails validation. `.reason` is a
    human-readable string suitable for returning to the caller."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


async def add_watchlist_ticker(
    app_state, ticker: str, user_id: str = DEFAULT_USER_ID
) -> None:
    normalized = ticker.strip().upper()
    if not await app_state.market_source.is_valid_ticker(normalized):
        raise WatchlistError("unrecognized ticker")

    added = await watchlist.add_ticker(user_id, normalized)
    if not added:
        raise WatchlistError("already on watchlist")


async def remove_watchlist_ticker(
    app_state, ticker: str, user_id: str = DEFAULT_USER_ID
) -> None:
    normalized = ticker.strip().upper()
    removed = await watchlist.remove_ticker(user_id, normalized)
    if not removed:
        raise WatchlistError("not on watchlist")
