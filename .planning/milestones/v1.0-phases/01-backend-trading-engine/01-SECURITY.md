---
phase: "1"
slug: "backend-trading-engine"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-09-16"
---

# Phase 1 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| HTTP client → `POST /api/portfolio/trade` | Untrusted JSON body (ticker, side, quantity) | Trade request |
| HTTP client → `POST /api/watchlist` | Untrusted JSON body (ticker) | Watchlist mutation |
| HTTP client → `DELETE /api/watchlist/{ticker}` | Untrusted URL path segment | Watchlist mutation |
| Route/service → SQLite (`db/finally.db`) | Caller-influenced values reach persistent storage | ticker, quantity, price |
| Service → `PriceCache` (in-process) | Trusted: written only by `run_update_loop`, read-only from services | fill price |
| Two concurrent HTTP requests → shared `cash_balance`/`positions` | Overlapping read-modify-write of mutable state | cash, position rows |
| Background snapshot task → SQLite | Unattended writer runs for the process lifetime, outside any request | portfolio total_value |

---

## Threat Register

*Threat IDs are scoped per-plan (each plan's own `<threat_model>` STRIDE register in its PLAN.md); the same ID text (e.g. T-01-01) names a different concrete threat in each plan. The Plan column disambiguates.*

| Plan | Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|------|-----------|----------|-----------|----------|-------------|------------|--------|
| 01-01 | T-01-01 | Tampering | `app/db/{users_profile,positions,trades}.py` SQL | high | mitigate | `?` placeholders everywhere — verified `grep -c 'f"'` returns 0 across all 6 db modules | closed |
| 01-01 | T-01-02 | Tampering | `execute_trade()` critical section | high | mitigate | `async with lock:` wraps the full read-modify-write — verified present in `service.py` | closed |
| 01-01 | T-01-03 | Tampering/Repudiation | `POST /api/portfolio/trade` request body | medium | mitigate | Pydantic `quantity: float = Field(gt=0)`, `side: Literal["buy","sell"]` reject invalid input at 422 — verified in `routes/portfolio.py` | closed |
| 01-01 | T-01-04 | Tampering | Ticker reaching `positions`/`trades` | high | mitigate | `.strip().upper()` then `is_valid_ticker()` gate before any write — verified in `service.py` | closed |
| 01-01 | T-01-05 | Tampering (integrity) | quantity/price float path | medium | mitigate | `float`/`REAL` throughout, `QUANTITY_EPSILON`, no `int()` cast — verified `grep -c 'int('` returns 0 in `service.py` | closed |
| 01-01 | T-01-SC | Tampering | Dependency supply chain | low | accept | No packages installed this phase; `pydantic` `[SUS]` heuristic false positive verified in-repo (already locked transitively via fastapi) | closed (accepted) |
| 01-02 | T-01-01 | Tampering | `DELETE FROM positions` in `positions.py` | high | mitigate | `?` placeholders on `delete_position()` — covered by the same f-string=0 verification | closed |
| 01-02 | T-01-02 | Tampering | Concurrent trades double-spend/oversell | high | mitigate | Both rejection checks and both write paths inside the single `async with lock:` block; `test_concurrent_trades_are_serialized_by_the_lock` is the executable proof (passing) | closed |
| 01-02 | T-01-03 | Tampering/Repudiation | Negative/zero sell quantity | medium | mitigate | Same `Field(gt=0)` on `TradeRequest` covers both sides | closed |
| 01-02 | T-01-04 | Tampering | Unrecognized ticker on sell path | high | mitigate | Same single `is_valid_ticker()` gate covers buy and sell | closed |
| 01-02 | T-01-05 | Tampering (integrity) | Float residue leaving phantom position | medium | mitigate | `abs(new_quantity) < QUANTITY_EPSILON` deletes the row; epsilon added to held side only, never subtracted from requested | closed |
| 01-02 | T-01-07 | Repudiation | Rejected trades not recorded | low | accept | `trades` is an append-only log of fills only; PLAN.md §7 defines no attempt-outcome column; no audit requirement at single-user demo scale | closed (accepted) |
| 01-02 | T-01-SC | Tampering | Dependency supply chain | low | accept | No packages installed this plan | closed (accepted) |
| 01-03 | T-01-01 | Tampering | `INSERT OR IGNORE`/`DELETE` in `watchlist.py` | high | mitigate | `?` placeholders on both statements — covered by the f-string=0 verification | closed |
| 01-03 | T-01-03 | Tampering | `POST /api/watchlist` request body | medium | mitigate | `Field(min_length=1)` rejects empty ticker at 422 — verified in `routes/watchlist.py` | closed |
| 01-03 | T-01-04 | Tampering | Unrecognized ticker entering watchlist → market source | high | mitigate | `_normalize()` then `is_valid_ticker()` gates every add — verified in `routes/watchlist.py` | closed |
| 01-03 | T-01-08 | Tampering | Unicode/whitespace ticker variants bypassing `UNIQUE(user_id, ticker)` | medium | mitigate | Single shared `_normalize()` applied on all 3 endpoints — verified `grep -c '_normalize('` returns 4 (definition + 3 call sites) | closed |
| 01-03 | T-01-09 | Denial of Service | Unbounded watchlist growth enlarging poll cadence | low | accept | Adds capped by `TICKER_UNIVERSE` (30 symbols); single-user demo scale per `.planning/codebase/CONCERNS.md` | closed (accepted) |
| 01-03 | T-01-SC | Tampering | Dependency supply chain | low | accept | No packages installed this plan | closed (accepted) |
| 01-04 | T-01-01 | Tampering | SQL in `portfolio_snapshots.py` | high | mitigate | `?` placeholders; no caller-supplied query parameters on either read endpoint — covered by the f-string=0 verification | closed |
| 01-04 | T-01-02 | Tampering | Snapshot value recorded during concurrent trade | high | mitigate | Snapshot-on-trade insert happens inside the same `async with lock:` block as the cash/position writes | closed |
| 01-04 | T-01-05 | Tampering (integrity) | Derived P&L drifting from true position | medium | mitigate | `unrealized_pnl`/`pct_change` computed fresh on every read, never persisted — verified `grep -icE 'unrealized_pnl\|pct_change'` returns 0 in `db/positions.py` | closed |
| 01-04 | T-01-10 | Denial of Service | Deadlock from `compute_portfolio_view()` re-acquiring non-reentrant lock | high | mitigate | `compute_portfolio_view()` specified and verified lock-free (docstring confirms; a real buy-through-trade test exercises the nested call without hanging) | closed |
| 01-04 | T-01-11 | Denial of Service | Snapshot task dying silently, ending history series | medium | mitigate | Loop body wrapped in `try/except Exception` + `logger.exception` — verified present in `snapshots.py`; `test_snapshot_loop_survives_an_iteration_error` passes | closed |
| 01-04 | T-01-06 | Denial of Service | Unbounded `portfolio_snapshots` growth | low | accept | PLAN.md §7 explicitly accepts unbounded growth for single-user demo scale; pruning out of scope by design | closed (accepted) |
| 01-04 | T-01-SC | Tampering | Dependency supply chain | low | accept | No packages installed this plan | closed (accepted) |

*Status: open · closed · closed (accepted)*
*Severity: critical > high > medium > low — only open threats at or above `workflow.security_block_on` (high) count toward `threats_open`*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-01 | 01-01 T-01-SC, 01-02 T-01-SC, 01-03 T-01-SC, 01-04 T-01-SC | Dependency supply chain — no packages installed across any Phase 1 plan; `pydantic` `[SUS]` heuristic false positive already verified in `01-01-PLAN.md`'s register (locked transitively via fastapi, importable) | PLAN.md authors (per-plan, at plan time) | 2026-09-16 |
| AR-02 | 01-02 T-01-07 | Rejected trade attempts are not recorded anywhere — `trades` is a fills-only log by design; no audit requirement at single-user demo scale with fake money | 01-02-PLAN.md author | 2026-09-16 |
| AR-03 | 01-03 T-01-09 | Unbounded watchlist growth — capped by `TICKER_UNIVERSE` (30 symbols); single-user demo scale | 01-03-PLAN.md author | 2026-09-16 |
| AR-04 | 01-04 T-01-06 | Unbounded `portfolio_snapshots` growth — explicitly accepted in root `planning/PLAN.md` §7 for this single-user demo | 01-04-PLAN.md author + root PLAN.md §7 | 2026-09-16 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-09-16 | 24 | 24 | 0 | orchestrator (`/gsd-execute-phase 1`, `/gsd-secure-phase 1`), L1/ASVS-1 grep-depth verification against implementation files — no auditor subagent spawn needed (threats_open: 0 on first pass, register authored at plan time, asvs_level == 1) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-09-16
