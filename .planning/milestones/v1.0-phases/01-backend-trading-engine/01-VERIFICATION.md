---
phase: 01-backend-trading-engine
verified: 2026-09-16T00:00:00Z
status: passed
score: 15/15 must-haves verified
covered_files: [".planning/REQUIREMENTS.md", ".planning/phases/01-backend-trading-engine/01-01-PLAN.md", ".planning/phases/01-backend-trading-engine/01-01-SUMMARY.md", ".planning/phases/01-backend-trading-engine/01-02-PLAN.md", ".planning/phases/01-backend-trading-engine/01-02-SUMMARY.md", ".planning/phases/01-backend-trading-engine/01-03-PLAN.md", ".planning/phases/01-backend-trading-engine/01-03-SUMMARY.md", ".planning/phases/01-backend-trading-engine/01-04-PLAN.md", ".planning/phases/01-backend-trading-engine/01-04-SUMMARY.md", "backend/app/db/chat_messages.py", "backend/app/db/portfolio_snapshots.py", "backend/app/db/positions.py", "backend/app/db/trades.py", "backend/app/db/users_profile.py", "backend/app/db/watchlist.py", "backend/app/main.py", "backend/app/portfolio/__init__.py", "backend/app/portfolio/service.py", "backend/app/portfolio/snapshots.py", "backend/app/routes/portfolio.py", "backend/app/routes/watchlist.py"]
covered_digest: "v1:sha256:654636553550f83b25a3632ea88b671f7450fa3e192ee066af7e301f95806e9f"
behavior_unverified: 0
overrides_applied: 0
---

# Phase 1: Backend Trading Engine Verification Report

**Phase Goal:** A caller of the API can execute market trades against a persistent, validated portfolio and mutate the watchlist — the full trading engine works end-to-end, ready for a frontend to consume
**Verified:** 2026-09-16
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

Roadmap Phase 1 Success Criteria (5), cross-checked against the 15 requirement IDs and the plan-level `must_haves.truths` from all four plans (01-01..01-04). Each row's evidence includes both a direct read of the shipped code and a live re-run of the specific test(s) that exercise the behavior (not just a citation of SUMMARY.md's claim).

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `POST /api/portfolio/trade` executes a buy — cash decreases, a position appears/grows with correct weighted-avg avg_cost, trade recorded in `trades` (PORT-01, DATA-01/02/03) | VERIFIED | `backend/app/portfolio/service.py::_apply_buy` (read, lines 210-252) computes `new_avg_cost` as share-weighted average, calls `upsert_position`/`set_cash_balance`/`insert_trade` in order inside `async with lock:`. Re-ran `uv run pytest tests/routes/test_portfolio.py tests/portfolio/test_service.py -q` — all buy-path tests pass (`test_buy_fills_at_cached_price_and_persists`, `test_second_buy_weights_avg_cost`, `test_buy_writes_one_trades_row_per_fill`, `test_buy_then_buy_weights_avg_cost`) |
| 2 | `POST /api/portfolio/trade` executes a sell — cash increases, position updates/clears, trade recorded (PORT-02) | VERIFIED | `_apply_sell` (lines 255-297) credits cash, preserves `avg_cost` on partial sell, calls `positions.delete_position()` when `abs(new_quantity) < QUANTITY_EPSILON`. Re-ran targeted tests: `test_sell_credits_cash_and_reduces_position`, `test_sell_all_closes_position`, `test_sell_fractional_remainder_keeps_row`, `test_sell_does_not_change_avg_cost` — all pass |
| 3 | A buy with insufficient cash or a sell exceeding owned shares is rejected with a clear error and no state change (PORT-03, PORT-04) | VERIFIED | Re-ran `uv run pytest tests/routes/test_portfolio.py -k "beyond_cash or sell_more_than_held or no_partial_write" -q` — 3/3 pass, asserting cash/position/trades-count are byte-identical after rejection. Rejection branches return before any write, still inside the lock (code read confirms `return TradeResult(status="error", ...)` precedes every `positions.upsert_position`/`set_cash_balance`/`insert_trade` call on both branches) |
| 4 | `GET /api/portfolio` returns current cash, positions with unrealized P&L, total value; `GET /api/portfolio/history` returns snapshots every 30s + immediately after each trade (PORT-05, PORT-06, DATA-04) | VERIFIED | `compute_portfolio_view()` (service.py:47-123) joins `users_profile`+`positions` with live `PriceCache`, computes `unrealized_pnl`/`pct_change` fresh on every call (never persisted — confirmed no such columns in `positions` schema), applies the locked mark-to-cost fallback for unpriced tickers. `execute_trade()` calls `insert_snapshot()` on the success path only, inside the lock (service.py:196-205). `run_portfolio_snapshot_loop` (snapshots.py) records-then-sleeps at `SNAPSHOT_INTERVAL_SECONDS = 30`, wrapped in `try/except Exception` + `logger.exception`, cancelled in `main.py` lifespan teardown. Re-ran `test_get_portfolio_returns_locked_shape`, `test_get_portfolio_reflects_a_trade`, `test_get_portfolio_history_returns_snapshots`, `test_trade_records_an_immediate_snapshot`, `test_rejected_trade_records_no_snapshot` — all pass |
| 5 | `POST /api/watchlist` adds a recognized ticker (400 on unrecognized) and `DELETE /api/watchlist/{ticker}` removes it, both persisted in SQLite across restarts (WLST-01/02/03, DATA-06) | VERIFIED | `app/routes/watchlist.py` normalizes via `_normalize()` before `is_valid_ticker()` gating and before persistence; `app/db/watchlist.py::add_watchlist_ticker`/`remove_watchlist_ticker` use parameterized `INSERT OR IGNORE`/`DELETE`. Re-ran `uv run pytest tests/routes/test_watchlist.py tests/db/test_watchlist.py -q` — 18/18 pass, including `test_watchlist_add_survives_app_restart` (rebuilds `create_app()` against the same monkeypatched SQLite path) |

**Score:** 5/5 roadmap success criteria verified; 15/15 requirement IDs (DATA-01..06, PORT-01..06, WLST-01..03) have passing, behavior-exercising automated tests (0 present-but-unexercised)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/db/users_profile.py` | DATA-01 schema + seed | VERIFIED | Table, idempotent $10,000 seed, `get_cash_balance`/`set_cash_balance`, wired into lifespan before any `create_task` |
| `backend/app/db/positions.py` | DATA-02 schema | VERIFIED | `UNIQUE(user_id, ticker)` upsert via `ON CONFLICT DO UPDATE`, `delete_position()` added in Plan 02 |
| `backend/app/db/trades.py` | DATA-03 append-only log | VERIFIED | No update/delete function exists; `insert_trade`/`get_trades` ordered by `executed_at` |
| `backend/app/db/portfolio_snapshots.py` | DATA-04 schema | VERIFIED | Append-only, `insert_snapshot`/`get_snapshots` ordered by `recorded_at` |
| `backend/app/db/chat_messages.py` | DATA-05 schema-only | VERIFIED | Exact 6-column schema (`id, user_id, role, content, actions, created_at`), `actions` nullable, no speculative read/write helpers (Phase 3's concern) |
| `backend/app/db/watchlist.py` | DATA-06 mutation | VERIFIED | `add_watchlist_ticker`/`remove_watchlist_ticker`/`get_watchlist_entries` extend the pre-existing read-only module without moving `DB_PATH`/`_connect` |
| `backend/app/portfolio/service.py` | Single validated trade path | VERIFIED | `execute_trade()` — one function, both sides, structured `TradeResult`, never raises `HTTPException` (`grep -c HTTPException` = 0), lock-guarded critical section |
| `backend/app/routes/portfolio.py` | `POST/GET /api/portfolio*` | VERIFIED | All three endpoints present, matching the locked contract in each plan |
| `backend/app/routes/watchlist.py` | `GET/POST/DELETE /api/watchlist` | VERIFIED | All three endpoints present, single shared `_normalize()` helper |
| `backend/app/portfolio/snapshots.py` | 30s background recorder | VERIFIED | `run_portfolio_snapshot_loop`, structured like `run_update_loop`, lifespan-managed and cancelled on shutdown |
| `backend/app/main.py` | Lifespan wiring | VERIFIED | All 6 `init_db()` calls precede both `asyncio.create_task()` calls (line-number-verified); `portfolio_lock`, `snapshot_task` on `app.state`; both routers registered |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `app/main.py` lifespan | `users_profile/positions/trades/portfolio_snapshots/chat_messages.init_db()` | Direct awaits before `create_task` | WIRED | Confirmed by direct read: all 5 `init_db()` awaits (plus watchlist's) precede `update_task = asyncio.create_task(...)` at line 47 |
| `app/portfolio/service.py::execute_trade()` | `PriceCache.get()` | Fill-price source | WIRED | `tick = await price_cache.get(ticker)`; `grep -c 'get_prices'` in service.py returns 0 — never re-fetches from `market_source` |
| `app/routes/portfolio.py::post_trade` | `execute_trade()` → `HTTPException(400)` | Error translation | WIRED | `if result.status == "error": raise HTTPException(status_code=400, detail=result.reason)` |
| `app/routes/watchlist.py::post_watchlist` | `market_source.is_valid_ticker()` | Validity gate before persistence | WIRED | Confirmed: normalize → `is_valid_ticker` check → `add_watchlist_ticker` call, in that order |
| `execute_trade()` (locked section) | `compute_portfolio_view()` + `insert_snapshot()` | Snapshot-on-trade | WIRED | Nested call inside the held lock, gated on `result.status == "executed"`; `compute_portfolio_view()` documented and verified lock-free (no `async with lock` inside it) |
| `run_update_loop` | newly-added watchlist ticker | No-restart pricing | WIRED | `run_update_loop` re-reads `get_watchlist_tickers()` every cycle (pre-existing Phase 0 code, unchanged) |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full backend suite is current and green | `cd backend && uv run pytest -q` | `138 passed, 2 warnings in 14.98s` | PASS |
| Concurrent trades serialized by lock (no double-spend) | `uv run pytest tests/portfolio/test_service.py -k "concurrent or insufficient" -q` | `3 passed, 7 deselected` | PASS |
| State-preserving rejections (buy/sell) | `uv run pytest tests/routes/test_portfolio.py -k "beyond_cash or sell_more_than_held or no_partial_write" -q` | `3 passed, 18 deselected` | PASS |
| Watchlist persistence across app rebuild | `uv run pytest tests/routes/test_watchlist.py tests/db/test_watchlist.py -q` | `18 passed` | PASS |
| No debt markers in phase-modified files | `grep -nE "TBD\|FIXME\|XXX\|TODO\|HACK\|PLACEHOLDER\|not implemented" backend/app/db/*.py backend/app/portfolio/*.py backend/app/routes/{portfolio,watchlist}.py backend/app/main.py` | no matches | PASS |
| Git commit hashes cited in SUMMARYs exist | `git log --oneline -20` | all cited hashes (`24b04d5`, `3ad1359`, `4b3131b`, `afb9203`, `b9ea857`, ... `4fcd1eb`) present | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| DATA-01 | 01-01 | users_profile persistence, $10k seed | SATISFIED | `test_users_profile.py`, code read |
| DATA-02 | 01-01 | positions persistence | SATISFIED | `test_positions.py`, code read |
| DATA-03 | 01-01 | append-only trades log | SATISFIED | `test_trades.py`, code read |
| DATA-04 | 01-04 | snapshots every 30s + on-trade | SATISFIED | `test_portfolio_snapshots.py`, `test_snapshots.py`, on-trade tests re-run |
| DATA-05 | 01-03 | chat_messages schema | SATISFIED | `test_chat_messages.py`, code read |
| DATA-06 | 01-03 | watchlist mutation persisted | SATISFIED | `test_watchlist.py` re-run, restart-survival test |
| PORT-01 | 01-01 | market buy | SATISFIED | route + service tests re-run |
| PORT-02 | 01-02 | market sell | SATISFIED | route + service tests re-run |
| PORT-03 | 01-01/02 | buy insufficient cash rejected | SATISFIED | re-run, zero-state-change asserted |
| PORT-04 | 01-02 | sell insufficient shares rejected | SATISFIED | re-run, epsilon-tolerant sell-all also covered |
| PORT-05 | 01-04 | GET /api/portfolio | SATISFIED | re-run, code read confirms locked shape |
| PORT-06 | 01-04 | GET /api/portfolio/history | SATISFIED | re-run |
| WLST-01 | 01-03 | POST /api/watchlist add + 400 | SATISFIED | re-run |
| WLST-02 | 01-03 | DELETE /api/watchlist/{ticker} | SATISFIED | re-run |
| WLST-03 | 01-03 | GET /api/watchlist with prices | SATISFIED | re-run |

No orphaned requirements: `.planning/REQUIREMENTS.md`'s Phase 1 traceability table lists exactly these 15 IDs, all "Complete", and all 15 appear in at least one plan's `requirements:` frontmatter field (01-01: DATA-01/02/03, PORT-01/03; 01-02: PORT-02/03/04; 01-03: DATA-05/06, WLST-01/02/03; 01-04: DATA-04, PORT-05/06).

### Anti-Patterns Found

None blocking. No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` markers in any file this phase created or modified. No stub returns, no empty handlers, no hardcoded empty data flowing to a response.

Advisory findings already surfaced and documented in `01-REVIEW.md` (standard-depth code review, 0 critical / 5 warning / 5 info, explicitly non-blocking per that report's own status and per this workflow's required-reading note):
- WR-01/WR-02: `execute_trade()`'s own validation of `side`/`quantity` relies on the HTTP-layer Pydantic guards rather than validating internally — masked today because the only caller is the Pydantic-validated route, but relevant before Phase 3 calls `execute_trade()` directly with LLM-sourced arguments. Not a Phase 1 truth failure: PORT-03/04 as declared (rejected via HTTP) are correctly enforced today.
- WR-03: The 30-second background snapshot recorder does not hold `portfolio_lock`, so in a narrow window a snapshot could record an inconsistent `total_value` if it lands between two sequential writes inside a concurrent trade's locked section. No declared must-have or roadmap success criterion requires the periodic recorder itself to be lock-protected (only that trades and rejections are atomic, and both are independently tested and verified above). Confirmed present in the current code (`snapshots.py` calls `run_portfolio_snapshot_loop(cache)` with no lock parameter, `main.py:50`).
- WR-04/WR-05: SQLite connections not explicitly closed; background tasks cancelled but not awaited at shutdown. Both are resource-hygiene concerns, not functional failures against this phase's must-haves.

These are forward-looking hardening items appropriately scoped to review/backlog, not blockers to this phase's stated goal.

### Human Verification Required

None. Phase 1 is backend-only (API-caller-to-database); every declared truth has a corresponding automated test, and all were re-run live during this verification rather than trusted from SUMMARY.md claims.

### Gaps Summary

No gaps. All 5 roadmap success criteria and all 15 requirement IDs are verified against the actual codebase (not just SUMMARY.md claims) via direct code reads plus live re-execution of targeted pytest subsets and the full 138-test suite. The phase's stated purpose — a complete, persistent, validated backend trading engine ready for Phase 2's frontend to consume — is achieved.

---

_Verified: 2026-09-16_
_Verifier: Claude (gsd-verifier)_
