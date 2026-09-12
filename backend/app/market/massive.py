"""Massive (formerly Polygon.io) market data client.

Optional data source, active whenever `MASSIVE_API_KEY` is set and non-empty
(PLAN.md §5/§6). Conforms to `MarketDataSource` and honors its resilience
contract: every failure mode (rate limit, entitlement gap, transient network
error, malformed response) is logged and returns an empty dict rather than
raising, so a bad poll cycle degrades to "no update this cycle," never a
crash. See planning/MASSIVE_API.md for the endpoint research this is based on.
"""

import asyncio
import logging

import httpx

from .base import MarketDataSource

logger = logging.getLogger(__name__)


class MassiveMarketDataSource(MarketDataSource):
    BASE_URL = "https://api.massive.com"
    SNAPSHOT_PATH = "/v2/snapshot/locale/us/markets/stocks/tickers"
    MAX_TRANSIENT_RETRIES = 2
    RETRY_BACKOFF_SECONDS = 1.0

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._client: httpx.AsyncClient | None = None

    async def start(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={"Authorization": f"Bearer {self._api_key}"},
            timeout=10.0,
        )

    async def stop(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def get_prices(self, tickers: list[str]) -> dict[str, float]:
        """One snapshot call for the whole watchlist. On any failure — rate
        limit, entitlement gap, transient network error, malformed response
        — logs and returns {} rather than raising. `run_update_loop` then
        simply skips this cycle, and `PriceCache` keeps serving the last
        known-good price."""
        assert self._client is not None, "start() must be called before get_prices()"
        if not tickers:
            return {}
        for attempt in range(self.MAX_TRANSIENT_RETRIES + 1):
            try:
                resp = await self._client.get(
                    self.SNAPSHOT_PATH, params={"tickers": ",".join(tickers)}
                )
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                if attempt < self.MAX_TRANSIENT_RETRIES:
                    logger.warning(
                        "Massive request failed (%s), retrying (%d/%d)",
                        exc,
                        attempt + 1,
                        self.MAX_TRANSIENT_RETRIES,
                    )
                    await asyncio.sleep(self.RETRY_BACKOFF_SECONDS * (attempt + 1))
                    continue
                logger.error("Massive request failed after retries: %s", exc)
                return {}

            if resp.status_code == 429:
                # Don't retry — the poll interval (15s on free tier) is
                # already chosen to stay under the 5-calls/minute cap, so a
                # 429 means something else is also calling; back off fully
                # to the next scheduled cycle rather than hammering harder.
                logger.warning("Massive rate limit hit (429) — skipping this poll cycle")
                return {}
            if resp.status_code == 403:
                logger.error(
                    "Massive returned 403 NOT_AUTHORIZED — your plan may not include this "
                    "data; falling back is not automatic, check your key/plan"
                )
                return {}
            try:
                resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                logger.error("Massive returned HTTP %s: %s", exc.response.status_code, exc)
                return {}

            try:
                data = resp.json()
            except ValueError:
                logger.error("Massive returned a non-JSON response body")
                return {}

            # A malformed/unknown ticker is simply absent from the response
            # array rather than erroring the whole request — this dict
            # comprehension naturally treats "requested 10, got 7 back" as
            # "3 tickers unchanged this cycle," matching get_prices'
            # documented contract in base.py.
            return {
                t["ticker"]: t["lastTrade"]["p"]
                for t in data.get("tickers", [])
                if t.get("lastTrade") and "p" in t["lastTrade"]
            }
        return {}

    async def is_valid_ticker(self, ticker: str) -> bool:
        assert self._client is not None, "start() must be called before is_valid_ticker()"
        try:
            resp = await self._client.get(self.SNAPSHOT_PATH, params={"tickers": ticker})
        except httpx.HTTPError as exc:
            logger.error("Massive is_valid_ticker check failed for %s: %s", ticker, exc)
            return False
        if resp.status_code != 200:
            return False
        try:
            data = resp.json()
        except ValueError:
            return False
        return len(data.get("tickers", [])) > 0
