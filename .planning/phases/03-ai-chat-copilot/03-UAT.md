---
status: complete
phase: 03-ai-chat-copilot
source: [03-VERIFICATION.md]
started: 2026-09-20T00:00:00Z
updated: 2026-09-20T00:20:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Full click-through of the chat panel (layout, empty state, send/receive, live portfolio update, reload persistence)
expected: Each step behaves exactly as described — the composite of the 03-03-PLAN.md and 03-04-PLAN.md `<human-check>` walkthroughs, deferred to end-of-phase UAT per `workflow.human_verify_mode=end-of-phase` (same convention Phase 2 used with 0 issues).
result: issue
reported: "the collapse of the AI assistant isn't working well"
severity: major

### 2. Action badges, collapse rail, scroll-to-latest pill, watchlist live-sync
expected: Send "buy 3 AAPL" → green executed badge with fill price. Send "buy 100000 AAPL" → red error badge with the backend's verbatim rejection sentence in mixed case. Send "add PYPL to my watchlist" → green badge + PYPL appears in the left watchlist panel without reload. Click Collapse → panel becomes a narrow "Chat" rail; click it again → expands. Scroll up during a new reply → "New messages ↓" pill appears and jumps to latest on click. Paste a long unbroken string → bubble wraps instead of widening the panel. Reload → panel returns to expanded with the full conversation and badges intact. The error badge's reason text is never rephrased, truncated, or case-transformed.
result: issue
reported: "collapse/expand feels broken and the collapsed rail is hard to notice/find; requesting a design change to the collapse control (add a clear expand/collapse affordance, e.g. a chevron icon, hover feedback, and a smoother transition)"
severity: major

### 3. Non-ASCII reason rendering and scroll smoothness (backstop truths)
expected: A verbatim backend `reason` string containing non-ASCII characters or quote marks renders in the error badge with no escaping artifacts or mojibake. Scroll behavior stays smooth (not jumpy) across a long real scrollback.
result: pass

### 4. Judgment-tier prohibitions: no outcome-narration, no out-of-band execution, no manipulative framing
expected: The assistant's `message` text never asserts or implies a trade/watchlist outcome, never executes an action not present in `trades[]`/`watchlist_changes[]`, and the system prompt/responses show no urgency/FOMO/loss-aversion/guaranteed-return framing. (Strong supporting code evidence already found by the verifier — SYSTEM_PROMPT's hard constraints, ActionBadge.tsx reading only `action.outcome`/`action.reason`, execute_llm_actions() only acting on parsed arrays — but these are judgment-tier prohibitions requiring explicit human sign-off, not an automated pass.)
result: issue
reported: "Told the AI assistant to sell 2 AAPL against the real (non-mock) LLM and got the message text: 'Invalid placeholder, avoid outputting non-JSON text when schema is required.' instead of a real response."
severity: major

## Summary

total: 4
passed: 1
issues: 3
pending: 0
skipped: 0
blocked: 0

## Gaps

- gap_id: G-03-1
  truth: "Each step behaves exactly as described — the composite of the 03-03-PLAN.md and 03-04-PLAN.md <human-check> walkthroughs"
  status: failed
  reason: "User reported: the collapse of the AI assistant isn't working well"
  severity: major
  test: 1
  artifacts: []
  missing: []

- gap_id: G-03-2
  truth: "Click Collapse → panel becomes a narrow \"Chat\" rail; click it again → expands"
  status: failed
  reason: "User reported: collapse/expand feels broken and the collapsed rail is hard to notice/find; requesting a design change to the collapse control (add a clear expand/collapse affordance, e.g. a chevron icon, hover feedback, and a smoother transition)"
  severity: major
  test: 2
  artifacts:
    - path: "frontend/components/chat/ChatPanel.tsx"
      issue: "Collapsed rail (lines 48-65) is a rotated 10px text label with no icon/chevron and no hover state, and the expanded->collapsed transition is an instant conditional-render swap with no CSS transition — likely why it reads as low-discoverability and abrupt/broken rather than an intentional, responsive toggle."
  missing:
    - "Add a visible directional affordance (chevron icon) to both the collapse trigger and the collapsed rail"
    - "Add hover state styling to both triggers"
    - "Consider a smooth width/opacity transition between expanded and collapsed states instead of an instant swap"

- gap_id: G-03-3
  truth: "The assistant's message text never asserts or implies a trade/watchlist outcome, never executes an action not present in trades[]/watchlist_changes[], and shows no manipulative framing"
  status: failed
  reason: "User reported: told the AI assistant to sell 2 AAPL against the real (non-mock) LLM and got the message text 'Invalid placeholder, avoid outputting non-JSON text when schema is required.' instead of a real response — HTTP 200, no server-side error logged, so the backend's own defensive-parse fallback worked as designed (no 500), but the underlying openrouter/openrouter/free auto-router returned literal non-JSON text (looks like a leaked schema-enforcement instruction string, not a real answer) that then surfaced verbatim as the assistant's message."
  severity: major
  test: 4
  artifacts:
    - path: "backend/app/llm/client.py"
      issue: "parse_llm_response()'s fallback (line ~146) uses the raw non-JSON content verbatim as the displayed message when schema validation fails. This is correct 'never 5xx' behavior but produces a confusing/broken-looking response to the user when the free-tier auto-router (MODEL=openrouter/openrouter/free) picks an underlying model that doesn't reliably honor response_format — a known risk flagged in 03-01-SUMMARY.md's model-change deviation but not yet mitigated with a retry/fallback model."
  missing:
    - "Decide whether to add a retry-with-fallback-model step (e.g. FALLBACK_MODEL on a parse failure, mirroring the pattern used on this repo's agent-teams branch) so a single bad free-router pick doesn't surface as a nonsense message"
    - "At minimum, replace the raw-content fallback message with a clearer generic failure message (matching the existing network/exception fallback: \"I'm having trouble reaching the assistant right now\") when parse_llm_response() falls back due to schema validation failure specifically, rather than showing the model's raw non-JSON output verbatim to the user"
