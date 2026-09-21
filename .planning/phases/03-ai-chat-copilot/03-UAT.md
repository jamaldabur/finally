---
status: complete
phase: 03-ai-chat-copilot
source: [03-VERIFICATION.md]
started: 2026-09-21T00:00:00Z
updated: 2026-09-21T00:15:00Z
---

## Current Test

[testing complete]

## Tests

### 1. UI-08 collapse-control walkthrough (regression check for G-03-1/G-03-2)
expected: Matches 03-05-PLAN.md Task 2's human-check exactly — the collapsed rail is now clearly visible (higher-contrast edge), shows a chevron affordance, has a hover state, the "Collapse" button has a real hit target and its own chevron, the width transition animates smoothly in both directions, keyboard operation works (aria-expanded on both controls), reload always returns to expanded, and the unread dot never lights up on pre-existing history collapsed before hydrate resolves.
result: issue
reported: "the collapse button when collapsed isn't nice (the vertical 'Chat' label is broken, make it horizontal)"
severity: minor

### 2. Live (non-mock) LLM chat sanity check (regression check for G-03-3, the blocker)
expected: Send "sell 2 AAPL" several times against the real OPENROUTER_API_KEY path (the free router picks a different backing model per call) and confirm every reply is either coherent prose or one of the two fixed fallback sentences — never raw JSON, a code fence, or leaked instruction text. An executed trade shows a green badge with a fill price and moves the header cash/positions table. If a fallback reply ever appears, the uvicorn log shows a corresponding warning/error line (not silence).
result: issue
reported: "telling the chat 'sell 2 AAPL' produced a red error badge: '✕ sell -2 AAPL — Invalid quantity: -2.0' — the LLM encoded the sell direction as a negative quantity instead of quantity=2/side=sell, and the backend rejected it outright instead of normalizing it"
severity: major

### 3. Judgment-tier prohibitions across all six plans
expected: (a) the assistant's message text never asserts/implies an outcome, never executes an action outside the parsed trades[]/watchlist_changes[] arrays, and the system prompt carries no urgency/FOMO/pressure framing; (b) the collapsed rail's contrast fix does not make the rail brighter than the surrounding panels to the point of competing for attention; (c) the fallback model call never receives augmented/re-prompted context derived from the failed primary response, and no log line ever contains the raw model body or an environment variable value. (Strong supporting code evidence already found by the verifier for all three — this needs your confirmation, not just mine.)
result: pass

## Summary

total: 3
passed: 1
issues: 2
pending: 0
skipped: 0
blocked: 0

## Gaps

- gap_id: G-03-4
  truth: "Matches 03-05-PLAN.md Task 2's human-check exactly — the collapsed rail is clearly visible with a chevron affordance"
  status: failed
  reason: "User reported: the collapse button when collapsed isn't nice (the vertical 'Chat' label is broken, make it horizontal)"
  severity: minor
  test: 1
  artifacts:
    - path: "frontend/components/chat/ChatPanel.tsx"
      issue: "The collapsed rail's label uses [writing-mode:vertical-rl] (rotated vertical text) per 03-UI-SPEC.md's design; user finds this visually broken/hard to read and wants a horizontal label instead."
  missing:
    - "Change the collapsed-rail label from rotated vertical text to horizontal text (likely requires widening the rail slightly, or stacking short horizontal lines, since w-12/48px is narrow for horizontal text) — needs a concrete design decision, not just a CSS tweak, since it may conflict with the 48px rail width 03-UI-SPEC.md and WCAG hit-target reasoning already established in G-03-2's fix"

- gap_id: G-03-5
  truth: "An executed trade shows a green badge with a fill price and moves the header cash/positions table when the user asks the assistant to sell shares they hold"
  status: failed
  reason: "User reported: telling the chat 'sell 2 AAPL' produced a red error badge '✕ sell -2 AAPL — Invalid quantity: -2.0' — the LLM encoded the sell direction as a negative quantity instead of quantity=2/side=sell, and the backend rejected it outright instead of normalizing it"
  severity: major
  test: 2
  artifacts:
    - path: "backend/app/llm/actions.py"
      issue: "_validate_trade_item() (line 66-71) requires item.quantity > 0 strictly and rejects any non-positive value with 'Invalid quantity: {value}' — a negative quantity from a 'sell' request is rejected rather than normalized to its absolute value."
    - path: "backend/app/llm/client.py"
      issue: "SYSTEM_PROMPT gives no explicit instruction that quantity must always be a positive number and side alone conveys direction — nothing steers the model away from a signed-quantity representation."
    - path: "backend/app/llm/schema.py"
      issue: "LlmTradeItem.quantity is a plain float with no Field(gt=0) constraint (deliberate per its own docstring, to avoid discarding the whole response on one bad item) — so a negative value reaches _validate_trade_item() unchanged rather than being caught earlier."
  missing:
    - "Decide and implement a fix: either (a) normalize quantity to abs(quantity) before validating/executing when side is buy/sell (defensive, robust to any model phrasing), and/or (b) add explicit system-prompt guidance that quantity must always be positive, or (c) both — needs diagnosis to confirm which underlying model this reproduces against and whether it's a one-off (the free auto-router's per-call model variance) or a consistent pattern"
