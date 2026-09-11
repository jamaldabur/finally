# PLAN.md Review

Fresh pass over `planning/PLAN.md` looking for ambiguities, cross-section inconsistencies, missing specification that would let two implementers build incompatible things, and simplification opportunities. Organized by severity, with section references back to PLAN.md.

---

## A. Inconsistencies (doc contradicts itself)

### A1. The watchlist ticker whitelist contradicts the LLM example (§6 vs §9)
§6 says: "Only tickers with a defined seed price/sector are supported. Watchlist additions... for an unrecognized ticker are rejected with an error." The only tickers given seed price/sector in §6 are the 10 default tickers (AAPL/GOOGL/MSFT/AMZN/NVDA/META, JPM/V, TSLA/NFLX) — which are also the entire default watchlist (§7). If that's really the full universe, **no ticker can ever be successfully added** — every add attempt is either already on the watchlist or unrecognized.

Yet §9's structured-output example shows the LLM adding `PYPL`, a ticker with no defined seed/sector anywhere in the doc. As written, that example call would always be rejected with an error, which seems unintentional.

**Needs a decision**: either (a) define a larger fixed universe of supported tickers (e.g. 30-50 symbols with seed price + sector) and pick the §9 example from it, or (b) change the §9 example to a ticker actually outside the seed 10 but pull it from that expanded list. Right now Backend and Frontend/LLM-prompt implementers have no shared source of truth for "which tickers are addable," and will likely build incompatible assumptions.

### A2. Does the ticker whitelist apply when using real market data (Massive)? (§6)
The rejection rule in §6 is stated under "Simulator (Default)," but §9's watchlist-validation function is described as one single code path regardless of data source. If `MASSIVE_API_KEY` is set, does the whitelist still cap the app at 10(ish) hardcoded tickers, or can users watch any real symbol Massive can quote? As written the restriction reads as global, which would make the Massive integration pointless (why integrate a real data API you can only ever point at 10 fixed tickers?). Worth an explicit sentence either way.

### A3. Docker persistence mechanism: named volume vs. bind mount (§4 vs §11)
§4 says: "`db/` at the top level is the runtime volume mount point... persists across container restarts via Docker volume," implying the local `./db` directory is bind-mounted.

§11's example command is: `docker run -v finally-data:/app/db ...` — this is a **named Docker volume** (`finally-data`), not a bind mount of the local `db/` directory. A named volume is an opaque Docker-managed store; a student would not see `finally.db` appear in their local `db/` folder with this command, which contradicts §4's framing (and the `db/.gitkeep` / "SQLite file lives here at runtime" language in the directory tree). Pick one — a bind mount (`-v ./db:/app/db`) better matches the "zero config, self-contained, file the student can see/back up" spirit described elsewhere — and make §4, §11, and the start scripts consistent.

### A4. `docker-compose.yml` role contradicts its own rationale (§3 vs §4)
§3's rationale table states "Single Docker container | Students run one command; no docker-compose for production, no service orchestration." §4 then lists `docker-compose.yml` at the project root as "Optional convenience wrapper" with no further qualification. If it's dev-only tooling, say so explicitly next to the table row so it doesn't read as walking back the "no docker-compose" decision; if it's meant for something else, say what.

### A5. "Canvas-based charting library preferred (Lightweight Charts or Recharts)" (§10)
Recharts is SVG-based, not canvas-based — the two named options don't both satisfy the stated constraint. Either drop the "canvas-based" qualifier, drop Recharts from the list, or rephrase (e.g. "a performant charting library — Lightweight Charts (canvas) preferred, Recharts acceptable for simpler charts").

### A6. Automatic browser launch: guaranteed vs. optional (§2 vs §11)
§2 "First Launch" states as fact: "A browser opens to `http://localhost:8000`." §11 describes the start script as "Optionally opens the browser." If it's actually optional/best-effort (e.g. `open`/`start` may not be available in all environments), §2 should be softened to match, otherwise the two sections describe different guaranteed behavior.

---

## B. Missing specification (would let two implementers diverge)

### B1. Trading a ticker not on the watchlist (§8, §10, §6)
The price cache only holds prices for "tickers known to the system," described elsewhere as equivalent to the watchlist (§6, SSE section). `POST /api/portfolio/trade` takes `{ticker, quantity, side}` with no stated restriction to watchlist membership, and the Trade Bar (§10) doesn't say whether the ticker field is constrained to current watchlist entries. If a user (or the LLM) submits a trade for a ticker that isn't being watched, where does the fill price come from? Options: (a) trades are restricted to watchlist tickers only (reject otherwise), (b) an unwatched ticker is implicitly added to the watchlist as part of the trade, (c) price is fetched on-demand outside the cache. This needs an explicit rule — it affects backend validation, the trade bar UI, and the LLM's trade-execution behavior.

### B2. SSE event wire format is underspecified (§6, "SSE Streaming")
The doc says the server "pushes an event for all tickers known to the system at a regular cadence" and each event "contains ticker, price, previous price, timestamp, and change direction." It's not clear whether:
- this is **one SSE event per tick containing an array of all tickers**, or **one SSE event per ticker** (many events per tick), and
- what the literal field names/JSON shape are, and
- what values "change direction" takes (e.g. `"up" | "down" | "unchanged"`? or an omitted field when unchanged?).

Frontend and backend are built by different agents against this contract — an explicit example payload would prevent drift.

### B3. "Recent conversation history" has no bound (§9 step 2, §8 `GET /api/chat`)
Both the prompt-construction step and the hydration endpoint refer to "recent"/"recent conversation history" without a count or time window. Since `chat_messages` grows unboundedly (no pruning, matching the `portfolio_snapshots` policy), this needs an explicit cap (e.g. "last 20 messages") both to bound LLM context/cost per request and to bound what `GET /api/chat` returns on page load.

### B4. `GET /api/portfolio/history` has no range/limit (§7, §8)
`portfolio_snapshots` rows are explicitly never pruned and accumulate every 30s plus on every trade. `GET /api/portfolio/history` has no stated limit, offset, or time-range parameter, so a long-running session could return an ever-growing payload on every chart load. Worth at least a default limit or downsampling note, or an explicit "return everything, acceptable for demo scope" statement so implementers don't disagree.

### B5. LLM mock response behavior is unspecified but load-bearing for E2E tests (§5, §9, §12)
`LLM_MOCK=true` must "return deterministic mock responses," and one required E2E scenario is "AI chat (mocked): send a message, receive a response, trade execution appears inline" — meaning the mock must, for *some* known input, emit an actual `trades` action, not just message text. But nothing in §9 specifies the mock's decision logic (keyword matching on the user's message? fixed canned response regardless of input? a special test-only trigger phrase?). Since the Backend agent builds the mock and a different test-writing agent builds the E2E scenario, they need a shared contract for at least one deterministic "this input produces a trade action" case — otherwise the two are likely to disagree independently.

### B6. HTTP status/error-body convention for validation failures (§8, §9)
Nothing specifies the response shape/status code when a trade or watchlist action fails validation (insufficient cash, selling more than owned, duplicate watchlist add, removing a ticker not on the watchlist, unrecognized ticker). §8 only calls out 400 for the unrecognized-ticker watchlist case. Since the same validation function backs both the direct REST endpoints (§8) and the chat auto-execution annotation (§9 step 7, "executed" vs "error" + reason), a single documented error shape (status code + body field names) would keep the trade bar's error handling and the chat panel's inline badges consistent.

### B7. Position lifecycle at zero quantity (§7 `positions`)
When a sell reduces a position's `quantity` to 0, is the row deleted, or retained with `quantity=0`? This affects the positions table, the heatmap (a 0-weight rectangle?), and whether a `UNIQUE(user_id, ticker)` re-buy after a full exit is a fresh INSERT or an UPDATE. Also unstated: `avg_cost` recalculation method on partial sells — presumably unchanged (standard weighted-average-cost behavior, where only buys move `avg_cost`), but this should be said explicitly since it's the crux of the P&L math the unit tests (§12) are supposed to cover.

### B8. `OPENROUTER_API_KEY` is marked "Required" but the app has key features that don't need it (§5)
Watchlist, prices, and portfolio/trading work with no LLM involved, and `LLM_MOCK=true` bypasses OpenRouter entirely. Should the app fail to start if the key is absent and `LLM_MOCK` is false, or only fail lazily when `/api/chat` is actually called? "Required" as currently worded suggests a hard startup dependency that the rest of the spec doesn't otherwise justify.

### B9. Main chart's data source on ticker switch (§2 vs §10)
§2 states sparklines are "accumulated on the frontend from the SSE stream since page load (sparklines fill in progressively)" — implying no backend history endpoint feeds them. §10's "Main chart area" doesn't restate this, so it's implicit rather than confirmed that the big chart draws from the same in-browser SSE buffer (and therefore also starts sparse on first load / right after selecting a ticker that hasn't accumulated many ticks yet). Worth one explicit sentence so no implementer builds a `/api/prices/history/{ticker}` endpoint that the rest of the spec doesn't otherwise mention, and so the empty-chart-on-load behavior is understood as intentional, not a bug.

### B10. `watchlist_changes.action` enum not fully stated (§9)
The example only shows `"action": "add"`. §8's DELETE endpoint implies removal is also a valid LLM-driven action ("Manage the watchlist" via chat, §2), but the schema section never explicitly enumerates `"add" | "remove"`. Small gap, easy fix.

### B11. GBM parameters' configuration mechanism (§6)
"Configurable drift and volatility per ticker" doesn't say *where* — hardcoded per-ticker constants in the simulator module, a config file, or env vars? Given "Simulator... no external dependencies" is a stated virtue, a hardcoded per-ticker table is probably intended, but it's worth pinning down so the ticker-universe question (A1) and this land in the same place.

---

## C. Simplification opportunities

1. **Resolve A1/A2 together with one concrete list.** Add a short explicit table of the full supported-ticker universe (symbol, seed price, sector) to §6 or §7 — even if it's larger than the default 10 — so both the simulator seed data and any watchlist-add validation (manual, and the §9 LLM example) reference the same list. This single addition would close A1, A2, and B11 at once.

2. **Pick bind-mount over named volume** for the SQLite file (resolves A3) — it's more in keeping with "self-contained, zero config" and lets a student inspect/back up `finally.db` directly, which the rest of the doc's framing (`db/.gitkeep`, "SQLite file lives here at runtime") already assumes.

3. **Define one error-response shape once** (e.g. `{"error": "insufficient_cash", "detail": "..."}` with 400) and reference it from both §8 (trade/watchlist endpoints) and §9 (chat action annotation), rather than leaving each call site to invent its own. Removes B6 and keeps the "one validation function, two entry points" design (§9 step 6) honest all the way to the wire format.

4. **Give the SSE payload a two-line JSON example** (resolves B2) — this is cheap to add and is the single highest-leverage clarification for keeping the Frontend and Backend agents' contracts aligned, since SSE is the most continuously-active integration surface in the app.

5. **State the chat-history window as a number** (resolves B3) in one place (e.g. "the last 20 messages, oldest first") and have both §8's `GET /api/chat` and §9 step 2 reference that same number, rather than each independently deciding what "recent" means.

---

## Summary

Most of the plan is internally solid and unusually precise for a spec of this size (the SSE flash-vs-heartbeat distinction, the heatmap color-saturation cap, and the single-validation-path design for trades/watchlist are all good examples of ambiguity pre-empted correctly). The issues found cluster around two areas that were specified in one section but not carried through consistently to the sections that depend on them:

- **The ticker universe** (A1, A2, B11) — the simulator's whitelist rule and the LLM's example action directly contradict each other, and this is the one finding likely to actually break a demo (an agent following §9 literally will build an LLM that tries to add PYPL and always gets an error back).
- **Docker persistence** (A3, A4) — the volume-mount example contradicts the directory-structure narrative, which matters because start/stop scripts, the Dockerfile, and the "data persists across restarts" promise all depend on picking one mechanism.

Everything else is either a missing bound/format on an otherwise-clear feature (B2–B10) or a small wording contradiction (A5, A6) that's quick to fix. None of the frontend visual/UX sections (§2, §10 layout) or the testing strategy's scenario list (§12) have structural problems — the gaps there are in the *supporting* mock/data contracts (B5) rather than the test list itself.
