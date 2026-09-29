---
phase: 06-test-coverage
plan: 01
subsystem: testing
tags: [pytest, backend, watchlist, portfolio, trade-execution, audit]
requires: []
provides:
  - "Route-contract coverage for POST /api/watchlist's empty-ticker 422 boundary and its adjacent whitespace-only 400 boundary"
  - "Service-level coverage for selling below average cost, including the resulting unrealized P&L view"
  - "A TEST-01/TEST-02/TEST-03 audit matrix mapping every named behavior to a passing test"
affects: [06-test-coverage]
actuals:
  tokens: 9500
  tasks: 2
  commits: 2
tech-stack:
  added: []
  patterns:
    - "Audit-and-close-gaps: diffed roadmap requirement wording against actual existing test bodies (not just file/test names) before writing anything new"
key-files:
  created: []
  modified:
    - backend/tests/routes/test_watchlist.py
    - backend/tests/portfolio/test_service.py
key-decisions:
  - "Confirmed D-01's audit-first strategy: only two genuine gaps existed across all of TEST-01/02/03 (empty-ticker 422, sell-at-a-loss), not a from-scratch suite"
  - "P-14 (from PLAN.md frontmatter): added the sell-at-a-loss test as the one missing TEST-01 edge case named explicitly by root PLAN.md section 12"
patterns-established: []
requirements-completed: [TEST-01, TEST-02, TEST-03]
coverage:
  - id: D1
    description: "POST /api/watchlist empty-ticker request is rejected with 422 (Field(min_length=1)), watchlist unchanged"
    requirement: "TEST-03"
    verification:
      - kind: unit
        ref: "backend/tests/routes/test_watchlist.py::test_post_watchlist_empty_ticker_is_422"
        status: pass
    human_judgment: false
  - id: D2
    description: "POST /api/watchlist whitespace-only ticker is rejected with 400 Unknown ticker, watchlist unchanged"
    requirement: "TEST-03"
    verification:
      - kind: unit
        ref: "backend/tests/routes/test_watchlist.py::test_post_watchlist_whitespace_ticker_is_400"
        status: pass
    human_judgment: false
  - id: D3
    description: "Selling below average cost credits cash at market price, leaves avg_cost unchanged on the remaining position, and the portfolio view reports the resulting unrealized loss"
    requirement: "TEST-01"
    verification:
      - kind: unit
        ref: "backend/tests/portfolio/test_service.py::test_sell_at_a_loss_credits_market_price_and_keeps_avg_cost"
        status: pass
    human_judgment: false
  - id: D4
    description: "Full backend suite (231 tests) proves every TEST-01/02/03 named behavior via an existing or newly-added passing test — see audit matrix below"
    requirement: "TEST-01, TEST-02, TEST-03"
    verification:
      - kind: unit
        ref: "cd backend && uv run pytest -q --tb=short (231 passed)"
        status: pass
    human_judgment: false
duration: 20min
completed: 2026-09-27
status: complete
---

# Phase 06 Plan 01: Backend Test Coverage Audit and Gap-Closure Summary

**Closed the two genuine TEST-01/03 gaps (empty-ticker 422, selling below average cost) the RESEARCH.md audit found, and confirmed every other TEST-01/02/03 behavior already has a named passing test — backend suite is green at 231.**

## Performance
- **Duration:** 20min
- **Started:** 2026-09-27T20:36:27Z
- **Completed:** 2026-09-27T20:47:44Z
- **Tasks:** 2 completed
- **Files modified:** 2

## Accomplishments
- Closed the one TEST-03 route-contract gap: `POST /api/watchlist` with an empty ticker now has a passing test proving the 422 from `Field(min_length=1)`, plus a locked adjacent boundary (whitespace-only ticker → 400 "Unknown ticker: ").
- Closed the one TEST-01 portfolio edge case with no prior test: selling below average cost, proven to the cent (fill price, cash balance both returned and persisted, avg_cost unchanged, unrealized P&L view).
- Produced a full audit matrix (below) mapping every TEST-01/02/03 named behavior to an exact `file::test_name`, confirming D-01's audit-first strategy found no further gaps.
- Full backend suite: 231 passed, 0 failed/error/skipped/xfailed (228 pre-existing + 3 new).

## Task Commits
1. **Task 1: Empty/whitespace ticker rejection on POST /api/watchlist** - `324d564` (test)
2. **Task 2: Sell-at-a-loss + TEST-01/02/03 audit** - `28a4b3a` (test)

## Files Created/Modified
- `backend/tests/routes/test_watchlist.py` - added `test_post_watchlist_empty_ticker_is_422` and `test_post_watchlist_whitespace_ticker_is_400`
- `backend/tests/portfolio/test_service.py` - added `test_sell_at_a_loss_credits_market_price_and_keeps_avg_cost`

## Audit Matrix

### TEST-01 — Trade execution, P&L, insufficient cash/shares

| Behavior | Proving test |
|---|---|
| Weighted-average cost on a second buy | `backend/tests/portfolio/test_service.py::test_buy_then_buy_weights_avg_cost` |
| Sell at a gain leaves avg cost unchanged | `backend/tests/portfolio/test_service.py::test_sell_does_not_change_avg_cost` |
| Sell at a loss (this plan's new coverage) | `backend/tests/portfolio/test_service.py::test_sell_at_a_loss_credits_market_price_and_keeps_avg_cost` |
| Insufficient cash rejected with no state change (service level) | `backend/tests/portfolio/test_service.py::test_buy_insufficient_cash_returns_error_result` |
| Insufficient cash rejected (route level) | `backend/tests/routes/test_portfolio.py::test_buy_beyond_cash_is_rejected` |
| Insufficient shares rejected with no state change (service level) | `backend/tests/portfolio/test_service.py::test_sell_insufficient_shares_returns_error_result` |
| Sell more than held / sell with no position rejected (route level) | `backend/tests/routes/test_portfolio.py::test_sell_more_than_held_is_rejected`, `backend/tests/routes/test_portfolio.py::test_sell_with_no_position_is_rejected` |
| Unrealized P&L on a gain | `backend/tests/portfolio/test_service.py::test_portfolio_view_computes_unrealized_pnl` |
| Unrealized P&L on a loss | `backend/tests/portfolio/test_service.py::test_portfolio_view_handles_loss` |
| Unpriced position marked to cost | `backend/tests/portfolio/test_service.py::test_portfolio_view_marks_unpriced_position_to_cost` |
| Concurrent trades serialized by the lock | `backend/tests/portfolio/test_service.py::test_concurrent_trades_are_serialized_by_the_lock` |

### TEST-02 — LLM structured-output parsing, including malformed responses

| Behavior | Proving test |
|---|---|
| Fenced JSON recovered (tagged) | `backend/tests/llm/test_client.py::test_parse_llm_response_recovers_fenced_valid_json_tagged` |
| Fenced JSON recovered (untagged, with whitespace) | `backend/tests/llm/test_client.py::test_parse_llm_response_recovers_untagged_fenced_json_with_whitespace` |
| Non-JSON model text falls back to a constant, never raises | `backend/tests/llm/test_client.py::test_parse_llm_response_never_shows_raw_text_and_falls_back_to_constant`, `backend/tests/llm/test_client.py::test_parse_llm_response_never_raises` |
| Multibyte text preserved | `backend/tests/llm/test_client.py::test_parse_llm_response_preserves_multibyte_characters` |
| Malformed trade item still parses into the response schema | `backend/tests/llm/test_schema.py::test_malformed_trade_item_still_parses_into_chat_response_schema` |
| Transient failure fails over once, never exceeds two calls | `backend/tests/llm/test_client.py::test_call_llm_structured_fails_over_once_on_transient_error`, `backend/tests/llm/test_client.py::test_call_llm_structured_never_exceeds_two_calls_when_both_fail` |
| Authentication error does not fail over | `backend/tests/llm/test_client.py::test_call_llm_structured_does_not_fail_over_on_authentication_error` |
| Mock mode never calls the completion function | `backend/tests/llm/test_client.py::test_mock_mode_never_calls_completion_function` |

### TEST-03 — API route status codes and response shapes (portfolio/watchlist/chat)

| Behavior | Proving test |
|---|---|
| Portfolio GET shape | `backend/tests/routes/test_portfolio.py::test_get_portfolio_returns_locked_shape` |
| Trade 200 path (buy/sell) | `backend/tests/routes/test_portfolio.py::test_buy_fills_at_cached_price_and_persists`, `backend/tests/routes/test_portfolio.py::test_sell_credits_cash_and_reduces_position` |
| Trade 400 path | `backend/tests/routes/test_portfolio.py::test_buy_unpriced_ticker_is_rejected`, `backend/tests/routes/test_portfolio.py::test_sell_more_than_held_is_rejected` |
| Trade 422 path | `backend/tests/routes/test_portfolio.py::test_buy_zero_or_negative_quantity_is_422` |
| History limit 422 bounds (zero/negative/over-max) | `backend/tests/routes/test_portfolio.py::test_get_portfolio_history_zero_limit_is_422`, `backend/tests/routes/test_portfolio.py::test_get_portfolio_history_negative_limit_is_422`, `backend/tests/routes/test_portfolio.py::test_get_portfolio_history_over_max_limit_is_422` |
| Watchlist GET | `backend/tests/routes/test_watchlist.py::test_get_watchlist_returns_seeded_tickers` |
| Watchlist POST | `backend/tests/routes/test_watchlist.py::test_post_watchlist_adds_recognized_ticker` |
| Watchlist DELETE | `backend/tests/routes/test_watchlist.py::test_delete_watchlist_removes_ticker` |
| Watchlist 400 unknown ticker | `backend/tests/routes/test_watchlist.py::test_post_watchlist_rejects_unknown_ticker` |
| Watchlist 422 empty ticker / 400 whitespace ticker (this plan's new coverage) | `backend/tests/routes/test_watchlist.py::test_post_watchlist_empty_ticker_is_422`, `backend/tests/routes/test_watchlist.py::test_post_watchlist_whitespace_ticker_is_400` |
| Chat 200 shape | `backend/tests/routes/test_chat.py::test_post_chat_returns_structured_response` |
| Chat blank-message 422 | `backend/tests/routes/test_chat.py::test_post_chat_rejects_blank_message` |
| Chat history hydration | `backend/tests/routes/test_chat.py::test_get_chat_hydrates_history` |

## Decisions Made
- Confirmed D-01 (audit-and-close-gaps, not a from-scratch suite): re-ran the audit against actual test bodies and found exactly the two gaps RESEARCH.md/PLAN.md's P-14 named — no additional gaps surfaced.
- No file under `backend/app/` was touched — every verification gate (`git diff --name-only 726046a -- backend/app`) confirmed `BACKEND_APP_UNTOUCHED` after both tasks.

## Deviations from Plan
None - plan executed exactly as written. Both new tests passed on first run; no fix-attempt cycles were needed.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Roadmap success criteria 1-3 (TEST-01/02/03) are now backed by named passing tests, closing the two real gaps and confirming the rest via audit.
- Frontend (TEST-04) and E2E (TEST-05) test infrastructure remain to be built in subsequent Phase 6 plans — no blockers from this plan.

---
*Phase: 06-test-coverage*
*Completed: 2026-09-27*

## Self-Check: PASSED

- FOUND: backend/tests/routes/test_watchlist.py
- FOUND: backend/tests/portfolio/test_service.py
- FOUND: .planning/phases/06-test-coverage/06-01-SUMMARY.md
- FOUND commit: 324d564
- FOUND commit: 28a4b3a
