---
status: testing
phase: 03-ai-chat-copilot
source: [03-VERIFICATION.md]
started: 2026-09-20T00:00:00Z
updated: 2026-09-20T00:00:00Z
---

## Current Test

number: 1
name: Full click-through of the chat panel (layout, empty state, send/receive, live portfolio update, reload persistence)
expected: |
  With LLM_MOCK=true on the backend and the frontend dev server running: (1) chat panel is the third column at the same width as the watchlist column; (2) empty state shows "Ask FinAlly anything" + body copy; (3) typing "how am I doing?" and pressing Enter disables the input, shows the three-dot thinking bubble, then renders the reply left-aligned with a blue border while the user's own message is right-aligned; (4) typing "buy 5 AAPL" updates the header cash balance and positions table without a reload; (5) reloading the page restores the full conversation with badges.
awaiting: user response

## Tests

### 1. Full click-through of the chat panel (layout, empty state, send/receive, live portfolio update, reload persistence)
expected: Each step behaves exactly as described — the composite of the 03-03-PLAN.md and 03-04-PLAN.md `<human-check>` walkthroughs, deferred to end-of-phase UAT per `workflow.human_verify_mode=end-of-phase` (same convention Phase 2 used with 0 issues).
result: [pending]

### 2. Action badges, collapse rail, scroll-to-latest pill, watchlist live-sync
expected: Send "buy 3 AAPL" → green executed badge with fill price. Send "buy 100000 AAPL" → red error badge with the backend's verbatim rejection sentence in mixed case. Send "add PYPL to my watchlist" → green badge + PYPL appears in the left watchlist panel without reload. Click Collapse → panel becomes a narrow "Chat" rail; click it again → expands. Scroll up during a new reply → "New messages ↓" pill appears and jumps to latest on click. Paste a long unbroken string → bubble wraps instead of widening the panel. Reload → panel returns to expanded with the full conversation and badges intact. The error badge's reason text is never rephrased, truncated, or case-transformed.
result: [pending]

### 3. Non-ASCII reason rendering and scroll smoothness (backstop truths)
expected: A verbatim backend `reason` string containing non-ASCII characters or quote marks renders in the error badge with no escaping artifacts or mojibake. Scroll behavior stays smooth (not jumpy) across a long real scrollback.
result: [pending]

### 4. Judgment-tier prohibitions: no outcome-narration, no out-of-band execution, no manipulative framing
expected: The assistant's `message` text never asserts or implies a trade/watchlist outcome, never executes an action not present in `trades[]`/`watchlist_changes[]`, and the system prompt/responses show no urgency/FOMO/loss-aversion/guaranteed-return framing. (Strong supporting code evidence already found by the verifier — SYSTEM_PROMPT's hard constraints, ActionBadge.tsx reading only `action.outcome`/`action.reason`, execute_llm_actions() only acting on parsed arrays — but these are judgment-tier prohibitions requiring explicit human sign-off, not an automated pass.)
result: [pending]

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0
blocked: 0

## Gaps
