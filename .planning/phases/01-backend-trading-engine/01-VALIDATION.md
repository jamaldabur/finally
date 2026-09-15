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
| TBD | TBD | 0 | DATA-01 | — | users_profile schema created + seeded $10,000 | unit | `uv run pytest tests/db/test_users_profile.py -x` | ❌ Wave 0 | ⬜ pending |
| TBD | TBD | 0 | DATA-02 | — | positions schema, UNIQUE(user_id, ticker) enforced | unit | `uv run pytest tests/db/test_positions.py -x` | ❌ Wave 0 | ⬜ pending |
| TBD | TBD | 0 | DATA-03 | — | trades schema, append-only insert works | unit | `uv run pytest tests/db/test_trades.py -x` | ❌ Wave 0 | ⬜ pending |
| TBD | TBD | 0 | DATA-04 | — | Snapshot recorded every 30s + immediately after trade | unit + integration | `uv run pytest tests/db/test_portfolio_snapshots.py tests/portfolio/test_service.py -x` | ❌ Wave 0 | ⬜ pending |
| TBD | TBD | 0 | DATA-05 | — | chat_messages schema created (unused this phase) | unit | `uv run pytest tests/db/test_chat_messages.py -x` | ❌ Wave 0 | ⬜ pending |
| TBD | TBD | 0 | DATA-06 | — | add/remove watchlist ticker persists | unit | `uv run pytest tests/db/test_watchlist.py -x` | ✓ (extend) | ⬜ pending |
| TBD | TBD | 0 | PORT-01/02 | — | Buy/sell fills at cached price, updates cash+positions | unit | `uv run pytest tests/portfolio/test_service.py -x` | ❌ Wave 0 | ⬜ pending |
| TBD | TBD | 0 | PORT-03 | — | Buy rejected, insufficient cash | unit | `uv run pytest tests/portfolio/test_service.py -k insufficient_cash -x` | ❌ Wave 0 | ⬜ pending |
| TBD | TBD | 0 | PORT-04 | — | Sell rejected, insufficient shares | unit | `uv run pytest tests/portfolio/test_service.py -k insufficient_shares -x` | ❌ Wave 0 | ⬜ pending |
| TBD | TBD | 0 | PORT-05 | — | `GET /api/portfolio` shape + values | integration (route) | `uv run pytest tests/routes/test_portfolio.py -x` | ❌ Wave 0 | ⬜ pending |
| TBD | TBD | 0 | PORT-06 | — | `GET /api/portfolio/history` returns snapshots | integration (route) | `uv run pytest tests/routes/test_portfolio.py -k history -x` | ❌ Wave 0 | ⬜ pending |
| TBD | TBD | 0 | WLST-01 | — | `POST /api/watchlist` add, 400 on unrecognized ticker | integration (route) | `uv run pytest tests/routes/test_watchlist.py -x` | ❌ Wave 0 | ⬜ pending |
| TBD | TBD | 0 | WLST-02 | — | `DELETE /api/watchlist/{ticker}` remove | integration (route) | `uv run pytest tests/routes/test_watchlist.py -k delete -x` | ❌ Wave 0 | ⬜ pending |
| TBD | TBD | 0 | WLST-03 | — | `GET /api/watchlist` with latest prices | integration (route) | `uv run pytest tests/routes/test_watchlist.py -k get -x` | ❌ Wave 0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky — Task/Plan/Wave columns are filled in once PLAN.md assigns concrete task IDs.*

---

## Wave 0 Requirements

- [ ] `backend/tests/conftest.py` — shared `isolated_db` fixture (currently duplicated per-file across existing tests; centralize now given 5+ new table modules)
- [ ] `backend/tests/db/test_users_profile.py`, `test_positions.py`, `test_trades.py`, `test_portfolio_snapshots.py`, `test_chat_messages.py` — one per new table
- [ ] `backend/tests/portfolio/test_service.py` — trade execution logic, avg-cost math, insufficient-cash/shares edge cases
- [ ] `backend/tests/routes/test_portfolio.py` — new route module
- [ ] `backend/tests/routes/test_watchlist.py` — new route module (distinct from the existing `tests/db/test_watchlist.py`, which tests the db layer only)
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
