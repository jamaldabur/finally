---
status: complete
phase: 03-ai-chat-copilot
source: [03-VERIFICATION.md]
started: 2026-09-21T19:30:00Z
updated: 2026-09-21T20:05:00Z
---

## Current Test

[testing complete]

## Tests

### 1. UI-08 collapse-control + full-height-rail walkthrough
expected: Matches 03-05-PLAN.md Task 2's and 03-07-PLAN.md Task 2's human-checks exactly — the direct regression check for G-03-1/G-03-2 and the newly-landed G-03-4 (rail height + label orientation).
result: pass

### 2. Live (non-mock) LLM chat sanity check for G-03-3
expected: Matches 03-06-PLAN.md Task 2's human-check exactly. Send "sell 2 AAPL" several times against the real OPENROUTER_API_KEY path (the free router picks a different backing model per call) and confirm every reply is either coherent prose or one of the two fixed fallback sentences, never raw JSON/a code fence/leaked instruction text; confirm an executed trade shows a green badge with a fill price and moves the header cash/positions table; check the uvicorn log and confirm any fallback reply has a corresponding warning/error log line.
result: issue
reported: "trying to buy 1 GOOGL i get {\"action\": \"BUY\", \"symbol\": \"GOOGL\", \"quantity\": 1, \"price\": 89.12, \"estimated_cost\": 89.12, \"cash_after\": 9252.56, \"status\": \"REQUESTED\"} — raw JSON rendered as the chat message, not coherent prose, not a badge, wrong schema shape entirely (action/symbol/price/cash_after/status — none of these are our LlmTradeItem/ChatResponse fields)"
severity: blocker

### 3. Live (non-mock) LLM sign-convention and watchlist-integrity sanity check for G-03-5/G-03-6
expected: Matches 03-08-PLAN.md Task 2's human-check exactly. With LLM_MOCK unset and a real OPENROUTER_API_KEY, send "sell 2 AAPL" at least six times (holding a position of that size), and confirm every turn either executes with a green badge/positive quantity/fill price and moves the header cash and positions table, or fails for an honest reason (assistant decline or one of the two fixed fallback sentences) — never a red "Invalid quantity" badge with a negative number. Then ask the assistant to add a ticker not currently on the watchlist and confirm it appears (count before/after); repeat with a removal. Check the uvicorn log for a warning/error line on any fallback turn.
result: issue
reported: "trying to sell 2 AAPL i get \"Requesting sale of 2 AAPL shares at the current price of $221.21. Estimated proceeds: $442.42. ✕ SELL 2 AAPL — Invalid side: 'SELL'\" — the model returned side as uppercase 'SELL' and it was rejected outright instead of being normalized to lowercase"
severity: major

### 4. Judgment-tier prohibitions across all eight plans
expected: |
  (a, carried) the assistant's message text never asserts/implies an outcome, never executes an
  action outside the parsed arrays, and the system prompt carries no urgency/FOMO/pressure
  framing;
  (b, carried) the collapsed rail's contrast fix does not make the rail brighter than the
  surrounding panels to the point of competing for attention;
  (c, carried) the fallback model call never receives augmented/re-prompted context derived from
  the failed primary response, and no log line ever contains the raw model body or an environment
  variable value;
  (d, new in 03-07) the rail label's readability fix does not shrink the type below the 12px Label
  role or drop the word entirely;
  (e, new in 03-08) no code path anywhere infers trade direction from a quantity's sign — side is
  the only field that conveys direction, and the sell recovery changes magnitude only.
result: pass

## Summary

total: 4
passed: 2
issues: 2
pending: 0
skipped: 0
blocked: 0

## Gaps

- gap_id: G-03-7
  truth: "Matches 03-06-PLAN.md Task 2's human-check exactly — the LLM reply is coherent prose or a fixed fallback sentence, never raw JSON, when the assistant proposes a trade"
  status: resolved
  resolved_by: "diagnosis (no code change) — .planning/debug/sell-side-case-sensitivity.md"
  resolved_at: "2026-09-21"
  reason: "User reported: trying to buy 1 GOOGL produced a raw JSON blob as the chat message text — {\"action\": \"BUY\", \"symbol\": \"GOOGL\", \"quantity\": 1, \"price\": 89.12, \"estimated_cost\": 89.12, \"cash_after\": 9252.56, \"status\": \"REQUESTED\"} — a completely different shape from our LlmTradeItem/ChatResponse schema"
  severity: blocker
  test: 2
  root_cause: "Same stale-runtime event as G-03-8 (23 seconds apart in chat_messages, same uvicorn process). The backend serving the request was started 2026-09-20 20:49:50, ~45 hours before this UAT round, without --reload, and predates commit 4d0999c (03-06's fix, landed 80 min after that process started) which made parse_llm_response() incapable of ever assigning raw model text to `message` — it returns PARSE_FALLBACK_MESSAGE instead. At HEAD the code is correct; no fix plan needed."
  artifacts: []
  missing:
    - "Restart the backend (this session did so) and retest — not a code fix"
  debug_session: ".planning/debug/sell-side-case-sensitivity.md"

- gap_id: G-03-8
  truth: "Matches 03-08-PLAN.md Task 2's human-check exactly — a sell request executes cleanly against the real router, never rejected on a normalization technicality"
  status: resolved
  resolved_by: "diagnosis (no code change) — .planning/debug/sell-side-case-sensitivity.md"
  resolved_at: "2026-09-21"
  reason: "User reported: trying to sell 2 AAPL produced a red error badge — \"Requesting sale of 2 AAPL shares at the current price of $221.21. Estimated proceeds: $442.42. ✕ SELL 2 AAPL — Invalid side: 'SELL'\" — the model returned side as uppercase 'SELL', which was rejected outright instead of case-normalized"
  severity: major
  test: 3
  root_cause: "Stale backend process (PID 11468), running since 2026-09-20 20:49:50 without --reload, ~45 hours old — predates commit b2187b2 (WR-02 fix: normalize case before validating trade side/watchlist action) and 03-08's a06d51d. Empirically confirmed: at HEAD, LlmTradeItem(side='SELL'/' SELL '/'Sell') all normalize to 'sell' and validate cleanly via actions.py:102 (side = item.side.strip().lower()) — the exact mirror of the action-field handling; the suspected validator/normalizer asymmetry does not exist. The pre-b2187b2 validator reproduces the reported string byte-for-byte when run against side='SELL'. No source defect; no fix plan needed."
  artifacts:
    - path: "backend/app/llm/actions.py"
      issue: "None — verified correct at HEAD (side normalization at line 102 mirrors action normalization)"
  missing:
    - "Restart the backend (this session did so) and retest — not a code fix. The free router serves a different backing model per call, so test 3 still needs several repetitions per its original expected steps."
  debug_session: ".planning/debug/sell-side-case-sensitivity.md"
