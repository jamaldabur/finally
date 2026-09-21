---
status: testing
phase: 03-ai-chat-copilot
source: [03-VERIFICATION.md]
started: 2026-09-21T00:00:00Z
updated: 2026-09-21T00:00:00Z
---

## Current Test

number: 1
name: UI-08 collapse-control walkthrough (regression check for G-03-1/G-03-2)
expected: |
  Matches 03-05-PLAN.md Task 2's human-check exactly: the collapsed rail is now clearly visible (higher-contrast edge), shows a chevron affordance, has a hover state, the "Collapse" button has a real hit target and its own chevron, the width transition animates smoothly in both directions, keyboard operation works (aria-expanded on both controls), reload always returns to expanded, and the unread dot never lights up on pre-existing history collapsed before hydrate resolves.
awaiting: user response

## Tests

### 1. UI-08 collapse-control walkthrough (regression check for G-03-1/G-03-2)
expected: Matches 03-05-PLAN.md Task 2's human-check exactly — the collapsed rail is now clearly visible (higher-contrast edge), shows a chevron affordance, has a hover state, the "Collapse" button has a real hit target and its own chevron, the width transition animates smoothly in both directions, keyboard operation works (aria-expanded on both controls), reload always returns to expanded, and the unread dot never lights up on pre-existing history collapsed before hydrate resolves.
result: [pending]

### 2. Live (non-mock) LLM chat sanity check (regression check for G-03-3, the blocker)
expected: Send "sell 2 AAPL" several times against the real OPENROUTER_API_KEY path (the free router picks a different backing model per call) and confirm every reply is either coherent prose or one of the two fixed fallback sentences — never raw JSON, a code fence, or leaked instruction text. An executed trade shows a green badge with a fill price and moves the header cash/positions table. If a fallback reply ever appears, the uvicorn log shows a corresponding warning/error line (not silence).
result: [pending]

### 3. Judgment-tier prohibitions across all six plans
expected: (a) the assistant's message text never asserts/implies an outcome, never executes an action outside the parsed trades[]/watchlist_changes[] arrays, and the system prompt carries no urgency/FOMO/pressure framing; (b) the collapsed rail's contrast fix does not make the rail brighter than the surrounding panels to the point of competing for attention; (c) the fallback model call never receives augmented/re-prompted context derived from the failed primary response, and no log line ever contains the raw model body or an environment variable value. (Strong supporting code evidence already found by the verifier for all three — this needs your confirmation, not just mine.)
result: [pending]

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps
