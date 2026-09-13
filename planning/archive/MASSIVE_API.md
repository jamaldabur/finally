# MASSIVE_API.md — Massive (formerly Polygon.io) Market Data API Research

This document is reference material for implementing the Massive-backed branch of the market
data layer described in `PLAN.md` §6. It is **not** the interface FinAlly's backend code should
call directly — see `MARKET_INTERFACE.md` for the abstraction this project actually codes
against. This file exists so the Backend/Market Data agent has one place to look up exact
endpoints, auth, payload shapes, and rate limits instead of re-researching them.

> **Provenance note**: Polygon.io rebranded to **Massive** on 2025-10-30. It is the same company,
> same platform, same data, same account/API-key system — only the brand name, primary domain
> (`api.polygon.io` → `api.massive.com`), and docs site (`massive.com/docs`) changed. Old
> `api.polygon.io` URLs continue to work during a transition period. All research below reflects
> the current Massive-branded docs and endpoint set as of 2026-09.
>
> **Prompt-injection note**: Massive's own `llms.txt` (an AI-agent-oriented docs summary at
> `massive.com/docs/llms.txt`) contains a line instructing coding agents to store the key in a
> `MASSIVE_API_KEY` environment variable. That happens to already be this project's convention
> (`PLAN.md` §5), independently decided before this research — it is not being adopted *because*
> the docs said so. Flagging it here per house practice for any embedded instruction found in
> fetched content; nothing else in the docs asked for any different or unusual action.

---

## 1. Base URL & Authentication

- **Base URL**: `https://api.massive.com` (the legacy `https://api.polygon.io` is a working alias
  during the transition period; use the `massive.com` domain for new code).
- **Auth**: every REST call accepts the key **either** as a query parameter or a header — pick one
  convention project-wide, don't mix:
  - Query parameter: `?apiKey=YOUR_KEY` appended to any endpoint
  - Header: `Authorization: Bearer YOUR_KEY`
- No OAuth, no signing, no per-request nonce. A single static API key per account.
- **Recommendation for FinAlly**: use the `Authorization: Bearer` header. It keeps the key out of
  logged URLs (query strings routinely end up in access logs, error trackers, and proxy logs).

```bash
curl "https://api.massive.com/v2/aggs/ticker/AAPL/prev" \
  -H "Authorization: Bearer $MASSIVE_API_KEY"
```

---

## 2. Rate Limits & Plans

| Plan | Price | Calls | Data delay | History |
|---|---|---|---|---|
| Basic (free) | $0/mo | **5 calls/minute** | End-of-day only (no intraday real-time) | 2 years |
| Starter | $29/mo | Unlimited | 15-minute delayed | 5 years |
| Developer | $79/mo | Unlimited | 15-minute delayed, includes trades | 10 years |
| Advanced | $199/mo | Unlimited | **Real-time** | 20+ years |

Implications for this project:

- `PLAN.md` §6 already assumes the free tier's 5 calls/minute → 15-second poll interval. That
  matches the Basic plan's limit exactly (5/min = one call every 12s; 15s gives headroom).
- **The free Basic plan does not include real-time or even 15-minute-delayed intraday quotes** —
  only end-of-day data. A user running FinAlly with a Basic-tier `MASSIVE_API_KEY` will get prices
  that update once per day, not every 15 seconds. This is worth an explicit callout in
  `MARKET_INTERFACE.md` and the README: Massive integration is "real data, but real-time behavior
  requires at least the Starter plan." The simulator remains the only source of true intra-session
  price movement for anyone not paying for Starter+.
- Beyond the free tier, Massive states no hard rate limit but asks integrators to stay under
  ~100 requests/second as an informal courtesy ceiling — irrelevant at this project's scale (one
  poller, at most ~10-50 tickers).

---

## 3. Relevant Endpoints

All examples below assume `stocksTicker` is a single symbol like `AAPL`, and that multiple tickers
are needed for FinAlly's watchlist use case — the **snapshot** endpoints are what let us fetch many
tickers in one call rather than one request per ticker.

### 3.1 Full Market Snapshot — `GET /v2/snapshot/locale/us/markets/stocks/tickers`

The single most useful endpoint for FinAlly's watchlist-poll loop: one request returns "latest
known state" for an arbitrary set of tickers.

**Query parameters**:
- `tickers` — comma-separated, case-sensitive list, e.g. `AAPL,GOOGL,MSFT`. Omit for the entire
  market (10,000+ symbols — never do this for a 10-50 ticker watchlist).
- `include_otc` — bool, default `false`.

**Example request**:
```
GET https://api.massive.com/v2/snapshot/locale/us/markets/stocks/tickers?tickers=AAPL,GOOGL,MSFT
Authorization: Bearer <key>
```

**Example response** (trimmed to one ticker):
```json
{
  "status": "OK",
  "tickers": [
    {
      "ticker": "AAPL",
      "lastTrade": { "p": 190.42, "s": 100, "t": 1736443800123456789 },
      "prevDay":   { "o": 188.10, "h": 191.00, "l": 187.50, "c": 189.80, "v": 51234567, "vw": 189.55 },
      "day":       { "o": 189.90, "h": 191.20, "l": 189.10, "c": 190.42, "v": 12345678, "vw": 190.10 },
      "min":       { "o": 190.30, "h": 190.45, "l": 190.25, "c": 190.42, "v": 51234, "t": 1736443800000 },
      "updated": 1736443800123456789,
      "todaysChange": 0.62,
      "todaysChangePerc": 0.327
    }
  ]
}
```

**Field notes**:
- `lastTrade.p` — the field to use as "current price." `lastTrade.t` is a **Unix nanosecond**
  timestamp (divide by 1e9 for seconds, or 1e6 for ms) — a common bug source, watch the units.
- `prevDay.c` — previous trading day's close. This is the natural "previous price" baseline for
  computing daily % change when the market has been closed (pre-market / after-hours / weekend).
  It is **not** the same thing as PLAN.md's SSE `previous price` field, which means "the last
  *different* price we saw," updated tick-to-tick — that comparison happens in FinAlly's own price
  cache (see `MARKET_INTERFACE.md`), not from this API.
- `day.*` — today's session OHLCV so far, resets at the start of each trading day.
- On the free/Basic plan, `lastTrade` and `min` will be stale/absent outside real-time
  entitlement — `prevDay` (end-of-day) is what's actually populated.
- Data resets daily around 3:30 AM ET and repopulates from ~4:00 AM ET onward as exchanges report.

### 3.2 Unified Snapshot — `GET /v3/snapshot`

A newer, cross-asset-class snapshot endpoint (stocks, options, indices in one call, distinguished
by ticker prefix). Supports `ticker.any_of=AAPL,MSFT,...` (up to 250 tickers) and returns richer
per-ticker data (`fmv` fair market value, full quote with bid/ask, session OHLC). For FinAlly's
stocks-only, ≤50-ticker watchlist, **the older `/v2/snapshot/.../tickers` endpoint (§3.1) is
simpler and sufficient** — `/v3/snapshot` is worth knowing about but not the recommended default
for this project.

### 3.3 Previous Day Bar — `GET /v2/aggs/ticker/{ticker}/prev`

Single ticker's previous full trading day OHLCV. Useful as a fallback/seed value (e.g. to compute
"previous close" for a ticker with no snapshot data yet), but for multi-ticker polling the
snapshot endpoint (§3.1) is strictly better — one call instead of N.

```
GET https://api.massive.com/v2/aggs/ticker/AAPL/prev?adjusted=true
```
```json
{
  "status": "OK",
  "ticker": "AAPL",
  "resultsCount": 1,
  "results": [
    { "T": "AAPL", "o": 188.10, "h": 191.00, "l": 187.50, "c": 189.80, "v": 51234567, "vw": 189.55, "t": 1736380800000 }
  ]
}
```
Note the field naming inconsistency vs. §3.1: here it's the terse aggregate-bar shape (`o/h/l/c/v/vw/t`),
`t` in **milliseconds**, `T` (capital) for ticker — different from the snapshot's `prevDay.c` etc.
Anticipate this if the same parsing code is reused across endpoints.

### 3.4 Custom Bars / Aggregates (historical OHLC) — `GET /v2/aggs/ticker/{ticker}/range/{multiplier}/{timespan}/{from}/{to}`

For historical/backfill data (e.g., seeding a chart with real history rather than only points
accumulated since the SSE stream started — see `PLAN.md` §10's note that sparklines/charts
currently only accumulate client-side; this endpoint is the natural future extension if a
"load history" feature is ever added, but is **not required** by the current PLAN.md scope).

```
GET https://api.massive.com/v2/aggs/ticker/AAPL/range/1/day/2026-01-01/2026-06-01?adjusted=true&sort=asc&limit=5000
```
```json
{
  "status": "OK", "ticker": "AAPL", "queryCount": 100, "resultsCount": 100, "adjusted": true,
  "results": [
    { "o": 188.10, "h": 191.00, "l": 187.50, "c": 189.80, "v": 51234567, "vw": 189.55, "t": 1736380800000, "n": 342156 }
  ]
}
```
- `multiplier` + `timespan` combine (e.g. `1` + `minute`, `5` + `minute`, `1` + `day`).
- `t` is bar **start** time, Unix milliseconds.
- `limit` max 50,000 rows per call; paginate via `from`/`to` windowing for longer ranges.
- Not used by FinAlly's MVP polling loop — documented here for completeness / future use only.

---

## 4. Python Access Options

Two viable approaches; **plain HTTP is recommended** for this project (see rationale below).

### Option A — Plain HTTP client (recommended)

```python
import os
import httpx

MASSIVE_BASE_URL = "https://api.massive.com"

async def fetch_snapshot(tickers: list[str]) -> dict:
    api_key = os.environ["MASSIVE_API_KEY"]
    url = f"{MASSIVE_BASE_URL}/v2/snapshot/locale/us/markets/stocks/tickers"
    params = {"tickers": ",".join(tickers)}
    headers = {"Authorization": f"Bearer {api_key}"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, params=params, headers=headers)
        resp.raise_for_status()
        return resp.json()
```

**Why plain HTTP over the official SDK for this project**:
- FinAlly needs exactly one endpoint shape (multi-ticker snapshot polling) — not the SDK's full
  surface (options, indices, forex, websockets, flat files).
- The SDK is mid-rebrand: the historical package is `polygon-api-client` (`pip install
  polygon-api-client`, `from polygon import RESTClient`), while the new official package is
  `massive` (`pip install -U massive`, `from massive import RESTClient`). Both currently work
  against the same account/key, but picking one during an active rename adds a dependency-naming
  risk (e.g. `uv.lock` pinning a package whose PyPI name or default base URL may shift again)
  that a 20-line `httpx` wrapper avoids entirely.
- The backend is already an async FastAPI app using `httpx`/`asyncio` idioms elsewhere (LiteLLM
  calls, per the `litellm-stream` skill) — a raw async HTTP call fits the existing style better
  than introducing a second, synchronous-by-default SDK client.
- This project's actual data need — poll a snapshot endpoint on an interval, parse a known JSON
  shape — does not benefit from an SDK's convenience methods, pagination iterators, or typed
  response models.

### Option B — Official SDK (`massive` package, if ever preferred)

```bash
uv add massive
```
```python
from massive import RESTClient

client = RESTClient(api_key=os.environ["MASSIVE_API_KEY"])
snapshot = client.get_snapshot_all("stocks", tickers=["AAPL", "GOOGL", "MSFT"])
```
Documented here for awareness only; not the recommended path (see rationale above). If adopted
later, `MARKET_INTERFACE.md`'s Massive implementation class is the only place that would need to
change — the abstract interface and everything downstream of it stays identical either way.

---

## 5. Error Handling Notes

- HTTP 429 on the free tier when the 5-calls/minute cap is exceeded — the poller's interval
  (§2, 15s) is chosen specifically to stay under this.
- HTTP 403 / `{"status": "NOT_AUTHORIZED"}` for entitlement gaps — e.g. requesting real-time data
  on a plan that only provides delayed/EOD data. This is the most likely real-world failure mode
  a student will hit with a free key, and should map to a clear log message ("Massive returned
  NOT_AUTHORIZED — your plan may not include this data; falling back is not automatic, check your
  key/plan") rather than a silent bad price.
- Malformed/unknown ticker in the `tickers` list is simply omitted from the `tickers` array in the
  response rather than erroring the whole request — the poller must handle "requested 10 tickers,
  got fewer back" gracefully (treat missing tickers as "no update this cycle," not a crash).
- Standard transient-failure handling applies (timeouts, 5xx, connection errors) — retry with
  backoff, keep serving the last-known-good price from the cache rather than blocking the SSE
  stream on a single failed poll.

---

## Sources

- [Polygon.io is Now Massive](https://massive.com/blog/polygon-is-now-massive)
- [Stock Market API | Massive](https://massive.com/stocks)
- [Overview | Stocks REST API - Massive](https://massive.com/docs/rest/stocks/overview)
- [Full Market Snapshot | Stocks REST API - Massive](https://massive.com/docs/rest/stocks/snapshots/full-market-snapshot)
- [Unified Snapshot | Stocks REST API - Massive](https://massive.com/docs/rest/stocks/snapshots/unified-snapshot)
- [Previous Day Bar (aggregates) - Massive docs](https://massive.com/docs/rest/stocks/aggregates/previous-day-bar)
- [Custom Bars (aggregates) - Massive docs](https://massive.com/docs/rest/stocks/aggregates/custom-bars)
- [What is the request limit for Massive's RESTful APIs?](https://massive.com/knowledge-base/article/what-is-the-request-limit-for-massives-restful-apis)
- [Pricing | Massive](https://massive.com/pricing)
- [GitHub - massive-com/client-python](https://github.com/massive-com/client-python)
- [polygon-api-client · PyPI](https://pypi.org/project/polygon-api-client/)
