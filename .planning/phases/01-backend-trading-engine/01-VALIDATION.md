---
phase: "1"
slug: "backend-trading-engine"
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-09-16"
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.0+ with pytest-asyncio 0.24+ (`asyncio_mode = "auto"`) |
| **Config file** | `backend/pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `cd backend && uv run pytest tests/db tests/portfolio tests/routes -q` |
| **Full suite command** | `cd backend && uv run pytest` |
| **Estimated runtime** | ~10-20 seconds |

---

## Sampling Rate

- **After every task commit:** Run the relevant quick-run subset (e.g. `uv run pytest tests/portfolio -q` after a trade-execution task)
- **After every plan wave:** `cd backend && uv run pytest` (full suite)
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 20 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-01-T1 | 01-01 | 1 | (Wave 0 scaffold) | T-01-01 | Every test runs against a throwaway SQLite file; the real `db/finally.db` is never touched | unit | `uv run pytest -q` | ❌ → created by this task | ⬜ pending |
| 01-01-T3 | 01-01 | 1 | DATA-01 | T-01-01 | users_profile schema created + seeded $10,000 | unit | `uv run pytest tests/db/test_users_profile.py -x` | ❌ → created by this task | ⬜ pending |
| 01-01-T3 | 01-01 | 1 | DATA-02 | T-01-01 | positions schema, UNIQUE(user_id, ticker) enforced | unit | `uv run pytest tests/db/test_positions.py -x` | ❌ → created by this task | ⬜ pending |
| 01-01-T3 | 01-01 | 1 | DATA-03 | T-01-01 | trades schema, append-only insert works | unit | `uv run pytest tests/db/test_trades.py -x` | ❌ → created by this task | ⬜ pending |
| 01-01-T2 | 01-01 | 1 | PORT-01 | T-01-02, T-01-04, T-01-05 | Buy fills at cached price inside the portfolio lock; unknown/unpriced ticker rejected before any write | integration (route) | `uv run pytest tests/routes/test_portfolio.py -x` | ❌ → created by this task | ⬜ pending |
| 01-01-T2 | 01-01 | 1 | PORT-03 | T-01-02 | Buy beyond cash rejected with zero state change | integration (route) | `uv run pytest tests/routes/test_portfolio.py -k beyond_cash -x` | ❌ → created by this task | ⬜ pending |
| 01-02-T1 | 01-02 | 2 | PORT-02 | T-01-01, T-01-05 | Sell credits cash, leaves avg_cost unchanged, deletes a fully closed position | integration (route) | `uv run pytest tests/routes/test_portfolio.py -k sell -x` | ✓ (extend) | ⬜ pending |
| 01-02-T2 | 01-02 | 2 | PORT-03 | T-01-02 | Buy rejected, insufficient cash, no partial write | unit | `uv run pytest tests/portfolio/test_service.py -k insufficient_cash -x` | ❌ → created by 01-02-T3 | ⬜ pending |
| 01-02-T2 | 01-02 | 2 | PORT-04 | T-01-02, T-01-05 | Sell rejected, insufficient shares, epsilon-tolerant so sell-all still succeeds | unit | `uv run pytest tests/portfolio/test_service.py -k insufficient_shares -x` | ❌ → created by 01-02-T3 | ⬜ pending |
| 01-02-T3 | 01-02 | 2 | PORT-01/02 | T-01-02 | Concurrent trades serialized by the portfolio lock; no double-spend | unit | `uv run pytest tests/portfolio/test_service.py -x` | ❌ → created by this task | ⬜ pending |
| 01-03-T1 | 01-03 | 2 | DATA-06 | T-01-01 | add/remove watchlist ticker persists via parameterized SQL | unit | `uv run pytest tests/db/test_watchlist.py -x` | ✓ (extend) | ⬜ pending |
| 01-03-T2 | 01-03 | 2 | WLST-01 | T-01-04, T-01-08 | `POST /api/watchlist` normalizes case then gates on `is_valid_ticker()`; 400 on unrecognized, no write | integration (route) | `uv run pytest tests/routes/test_watchlist.py -x` | ❌ → created by this task | ⬜ pending |
| 01-03-T2 | 01-03 | 2 | WLST-02 | T-01-01, T-01-08 | `DELETE /api/watchlist/{ticker}` removes, idempotent, path param never interpolated into SQL | integration (route) | `uv run pytest tests/routes/test_watchlist.py -k delete -x` | ❌ → created by this task | ⬜ pending |
| 01-03-T2 | 01-03 | 2 | WLST-03 | — | `GET /api/watchlist` with latest prices | integration (route) | `uv run pytest tests/routes/test_watchlist.py -k get -x` | ❌ → created by this task | ⬜ pending |
| 01-03-T3 | 01-03 | 2 | DATA-05 | T-01-01 | chat_messages schema created (unused this phase) | unit | `uv run pytest tests/db/test_chat_messages.py -x` | ❌ → created by this task | ⬜ pending |
| 01-04-T1 | 01-04 | 3 | DATA-04 | T-01-01 | portfolio_snapshots schema, append-only insert, ordered read | unit | `uv run pytest tests/db/test_portfolio_snapshots.py -x` | ❌ → created by this task | ⬜ pending |
| 01-04-T3 | 01-04 | 3 | DATA-04 | T-01-02, T-01-11 | Snapshot recorded every 30s and immediately after each successful trade; recorder survives an iteration error and is cancelled on shutdown | unit + integration | `uv run pytest tests/portfolio/test_snapshots.py tests/routes/test_portfolio.py -x` | ❌ → created by this task | ⬜ pending |
| 01-04-T2 | 01-04 | 3 | PORT-05 | T-01-05, T-01-10 | `GET /api/portfolio` shape + values; P&L computed on read, never persisted; no lock re-entry | integration (route) | `uv run pytest tests/routes/test_portfolio.py -x` | ✓ (extend) | ⬜ pending |
| 01-04-T2 | 01-04 | 3 | PORT-06 | — | `GET /api/portfolio/history` returns snapshots | integration (route) | `uv run pytest tests/routes/test_portfolio.py -k history -x` | ✓ (extend) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky. Commands run from `backend/`. Threat Ref values index the `<threat_model>` STRIDE registers in the corresponding PLAN.md.*

---

## Wave 0 Requirements

Each gap is now owned by a concrete task. No Wave 0 item is unassigned.

- [ ] `backend/tests/conftest.py` — shared `isolated_db` fixture → **01-01 Task 1**
- [ ] `backend/tests/db/test_users_profile.py`, `test_positions.py`, `test_trades.py` → **01-01 Task 3**
- [ ] `backend/tests/db/test_chat_messages.py` → **01-03 Task 3**
- [ ] `backend/tests/db/test_portfolio_snapshots.py` → **01-04 Task 1**
- [ ] `backend/tests/portfolio/test_service.py` — trade execution logic, avg-cost math, insufficient-cash/shares edge cases, lock serialization → **01-02 Task 3** (extended by 01-04 Task 2)
- [ ] `backend/tests/portfolio/test_snapshots.py` — periodic recorder behaviour → **01-04 Task 3**
- [ ] `backend/tests/routes/test_portfolio.py` — new route module → **01-01 Task 2** (extended by 01-02 and 01-04)
- [ ] `backend/tests/routes/test_watchlist.py` — new route module (distinct from the existing `tests/db/test_watchlist.py`, which tests the db layer only) → **01-03 Task 2**
- [ ] Framework install: none — pytest/pytest-asyncio already present

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 20s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
