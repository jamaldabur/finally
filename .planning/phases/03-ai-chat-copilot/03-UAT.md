---
status: testing
phase: 03-ai-chat-copilot
source: [03-VERIFICATION.md]
started: 2026-09-21T19:30:00Z
updated: 2026-09-21T19:30:00Z
---

## Current Test

number: 1
name: UI-08 collapse-control + full-height-rail walkthrough
expected: |
  With the app running (LLM_MOCK=true is fine), collapse the chat panel and confirm:
  (1) HEIGHT — the rail runs the full height of the body area, top-aligned with the watchlist
  panel and bottom-aligned with the positions panel beside it, not a small chip in the top-right
  corner.
  (2) LABEL — the word "Chat" reads left-to-right, upright, under the left-pointing chevron, not
  rotated.
  (3) The rail reads as a distinct docked element (visible outline against #0d1117) and responds
  to hover; click to expand and confirm the width animates smoothly rather than snapping; click
  "Collapse" in the panel header (chevron + button) and confirm the reverse animation; tab to each
  control and press Enter to confirm keyboard operation; reload and confirm the panel returns
  expanded; collapse immediately after a reload, before history finishes loading, and confirm no
  unread dot appears.
awaiting: user response

## Tests

### 1. UI-08 collapse-control + full-height-rail walkthrough
expected: Matches 03-05-PLAN.md Task 2's and 03-07-PLAN.md Task 2's human-checks exactly — the direct regression check for G-03-1/G-03-2 and the newly-landed G-03-4 (rail height + label orientation).
result: [pending]

### 2. Live (non-mock) LLM chat sanity check for G-03-3
expected: Matches 03-06-PLAN.md Task 2's human-check exactly. Send "sell 2 AAPL" several times against the real OPENROUTER_API_KEY path (the free router picks a different backing model per call) and confirm every reply is either coherent prose or one of the two fixed fallback sentences, never raw JSON/a code fence/leaked instruction text; confirm an executed trade shows a green badge with a fill price and moves the header cash/positions table; check the uvicorn log and confirm any fallback reply has a corresponding warning/error log line.
result: [pending]

### 3. Live (non-mock) LLM sign-convention and watchlist-integrity sanity check for G-03-5/G-03-6
expected: Matches 03-08-PLAN.md Task 2's human-check exactly. With LLM_MOCK unset and a real OPENROUTER_API_KEY, send "sell 2 AAPL" at least six times (holding a position of that size), and confirm every turn either executes with a green badge/positive quantity/fill price and moves the header cash and positions table, or fails for an honest reason (assistant decline or one of the two fixed fallback sentences) — never a red "Invalid quantity" badge with a negative number. Then ask the assistant to add a ticker not currently on the watchlist and confirm it appears (count before/after); repeat with a removal. Check the uvicorn log for a warning/error line on any fallback turn.
result: [pending]

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
result: [pending]

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0
blocked: 0

## Gaps
