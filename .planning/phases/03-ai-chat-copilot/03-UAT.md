---
status: diagnosed
phase: 03-ai-chat-copilot
source: [03-VERIFICATION.md]
started: 2026-09-21T00:00:00Z
updated: 2026-09-21T00:30:00Z
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
  root_cause: >
    Two causes — the rotated text is NOT the primary defect. (1) PRIMARY: ChatPanel.tsx's
    collapsed-state wrapper carries `h-full`, which resolves against page.tsx's row container
    (specified height `auto`, since `flex-1` sets flex-basis not height) — this degrades the
    wrapper to CONTENT height and, critically, DISABLES `align-items: stretch`, the mechanism
    that gives every sibling column its full height. Measured live in the actual production
    build (headless Chromium against `frontend/out`): the collapsed rail is a 48x59px CHIP, not
    a full-height rail — `main` stretches to 841px, the rail does not. Verified by two live
    mutations: forcing `height:auto` makes the rail jump to 841px; forcing `align-self:stretch`
    on top of `height:100%` does NOT fix it (stretch is genuinely disabled by the definite
    height, not merely unrequested). Predates 03-05 — `h-full` has been present since Plan
    03-03 (commit cea030e), carried through unchanged; the prior debug session
    (chat-panel-collapse-toggle.md) assumed the rail was "full-column-height" but never verified
    it in a real browser (no browser tool was connected then) — that assumption was wrong.
    (2) SECONDARY, real but smaller: the vertical rotated "Chat" label CSS applies correctly
    (confirmed: compiled bundle has the rule, computed styles show writing-mode: vertical-rl,
    glyph advance widths are identical rotated vs horizontal — no font-rendering bug) — it's
    simply an unnecessary reading-orientation mismatch against the upright chevron above it,
    made to look "broken"/cramped specifically because of the 59px chip height from cause (1)
    (the rotated "t" grazes the bottom border in the tiny chip). "Chat" fits horizontally in the
    46px inner rail width at 12px/500 (25.05px) or 10px/600 uppercase (26.09px) — no width
    change needed, no new 03-UI-SPEC.md Spacing exception needed.
  artifacts:
    - path: "frontend/components/chat/ChatPanel.tsx"
      issue: "Line 73: h-full on the collapsed-state wrapper (primary — collapses the rail to content height and disables stretch). Line 96: [writing-mode:vertical-rl] rotated label (secondary — correct CSS, wrong choice for this control, exacerbated by cause 1). Line 88: rail button has no padding, so its height is an exact content fit."
    - path: "frontend/app/page.tsx"
      issue: "Line 23: the row flex container's specified height is auto (flex-1 only sets flex-basis) — this is the containing block h-full resolves against and fails to stretch from."
    - path: ".planning/phases/03-ai-chat-copilot/03-UI-SPEC.md"
      issue: "Copywriting Contract and Layout & Interaction Contract (Dock placement) both prescribe the rotated label and never state the rail must be full-column height — this ambiguity is part of why the height defect went unnoticed by the checker."
  missing:
    - "Delete h-full from ChatPanel.tsx's collapsed-state wrapper (keep h-full on the inner button/section, which then resolve correctly once the wrapper itself is stretched) — this is the load-bearing fix"
    - "Change the collapsed-rail label from rotated ([writing-mode:vertical-rl]) to horizontal text — no width change needed, 'Chat' fits the existing 46px inner width"
    - "Amend 03-UI-SPEC.md: Copywriting Contract's rail-label row (rotated -> horizontal), Dock placement (state explicitly that the rail is full-column height), new Amendments entry — Spacing Scale needs no change"
    - "Note (adjacent, NOT part of this gap, do not conflate): with a long hydrated conversation the expanded panel also has no internal scroll boundary and the whole page scrolls instead — same 'no definite height in the ancestor chain' family, but a separate fix (a definite-height chain from html/body down); removing h-full here does not fix it. Not in this gap's scope; flag for a future phase or a separate gap if it recurs in testing."
  debug_session: ".planning/debug/collapsed-rail-vertical-label.md"

- gap_id: G-03-5
  truth: "An executed trade shows a green badge with a fill price and moves the header cash/positions table when the user asks the assistant to sell shares they hold"
  status: failed
  reason: "User reported: telling the chat 'sell 2 AAPL' produced a red error badge '✕ sell -2 AAPL — Invalid quantity: -2.0' — the LLM encoded the sell direction as a negative quantity instead of quantity=2/side=sell, and the backend rejected it outright instead of normalizing it"
  severity: major
  test: 2
  root_cause: >
    Confirmed empirically (not just by code read): _validate_trade_item(LlmTradeItem("AAPL",
    "sell", -2.0)) returns exactly 'Invalid quantity: -2.0', reproducing the reported badge text
    verbatim. This is a SYSTEMIC contract gap, not a one-off model confusion: the JSON schema
    actually sent to the provider via response_format has NO description and NO minimum/
    exclusiveMinimum on quantity, and NO enum on side — nothing anywhere (schema, system
    prompt) steers a model away from signed-quantity encoding. Live-probed 27 real calls against
    MODEL=openrouter/openrouter/free (the free auto-router): 8 distinct backing models observed;
    negative-quantity sells reproduced twice, both times from the SAME backing model
    (dots-studio/dots-3-note-preview:free, 2/2 occurrences) — deterministic per backing model,
    random only in which model the router serves that call (~1-in-5 trade-emitting responses in
    this sample). A/B test: adding one explicit prompt rule ("quantity is ALWAYS positive") made
    that same offending model return positive quantities in both follow-up calls — but prompt-
    only is not suficient alone since the router is non-stationary by construction and
    03-RESEARCH.md already documents this class of unreliability as expected. Also confirmed:
    build_mock_response()'s _TRADE_PATTERN only matches unsigned digits, so LLM_MOCK=true (every
    automated test) is structurally incapable of ever producing this input — no test gate existed
    for this class. execute_trade() has its own independent quantity<=0 guard (added in 03-01
    Task 3 specifically to protect non-chat callers) which must NOT be relaxed — confirmed a
    negative BUY quantity would otherwise pass the cost>cash check (negative cost never exceeds
    positive cash) and INCREASE cash, re-opening a Phase-1-era blocker.
  artifacts:
    - path: "backend/app/llm/actions.py"
      issue: "Lines 70-71: quantity<=0 rejected with no normalization. Lines 109-110/144-145: this gap's fix must normalize once per item and reuse that single value for both validation and execution (see G-03-6, a related but distinct defect found in the same code during this investigation)."
    - path: "backend/app/llm/schema.py"
      issue: "LlmTradeItem fields carry no Field(description=...) — the emitted JSON Schema is semantically empty for the model to work from. Add descriptions, NOT gt=0 (would violate the module's own documented one-bad-item-shouldn't-discard-the-response rationale)."
    - path: "backend/app/llm/client.py"
      issue: "SYSTEM_PROMPT (lines ~127-148) has no line about quantity sign convention. A/B-tested: adding one does measurably help, but is not sufficient alone given router non-stationarity."
    - path: "backend/app/llm/mock.py"
      issue: "_TRADE_PATTERN (lines 23-25) only matches unsigned digits — LLM_MOCK=true can never exercise this path, which is why no existing test caught it. New tests must construct LlmTradeItem directly."
  missing:
    - "Normalize quantity ONLY when the sign is redundant with side: if side=='sell' and quantity<0, use abs(quantity). Do NOT blanket-abs() — side=='buy' with a negative quantity is genuinely ambiguous (could mean 'sell' under a pure signed convention) and must stay rejected, or a real buy could silently execute in the opposite direction with no confirmation dialog. Verified this rule keeps existing negative-buy tests (test_actions.py:49, test_service.py:311) green."
    - "Add Field(description=...) to LlmTradeItem.quantity and .side (description only, no gt=0) plus one matching SYSTEM_PROMPT line — measurably reduces occurrence but is not sufficient alone"
    - "Do NOT touch execute_trade()'s own quantity<=0 guard — it must stay as the last line of defense for direct/non-chat callers"
    - "Add regression tests constructing LlmTradeItem directly (the mock path structurally cannot reach this): ('sell', -2.0) -> executed at 2.0; ('buy', -1) -> still error; boundary values 0, -0.0, NaN, inf"
  debug_session: ".planning/debug/llm-negative-sell-quantity.md"

- gap_id: G-03-6
  truth: "A watchlist change the assistant requests is applied faithfully — an 'add' adds the ticker, a 'remove' removes it, and the reported outcome matches what actually happened"
  status: failed
  reason: "Discovered incidentally by the G-03-5 debug agent while investigating the negative-quantity bug, not directly user-reported — but confirmed live and is more severe than G-03-5 (silent data loss reported as success), so filed as its own gap rather than left undocumented."
  severity: blocker
  test: 2
  root_cause: >
    _validate_trade_item()/_validate_watchlist_item() validate against item.side.strip().lower()
    / change.action.strip().lower(), but execute_llm_actions() separately re-derives with only
    .lower() (no .strip()) at actions.py:110 and :145 — the validator checks one value, the
    executor branches on a DIFFERENT value. For watchlist changes this is not just inconsistent,
    it is actively destructive: confirmed live — an LLM response with action=" add" (a leading
    space, exactly the kind of padding already observed from real models in this same
    investigation, e.g. side='SELL' uppercase from nex-agi/nex-n2.5-mini:free) passes validation
    (normalized to "add"), but execute_llm_actions()'s own re-derivation of `" add".lower()` is
    " add" (unstripped) which does not equal the literal string "add", so the code falls into
    its else-branch and calls remove_watchlist_ticker() instead of add_watchlist_ticker() —
    DELETING a ticker the user asked to ADD, while reporting outcome="executed" (a green success
    badge). Reproduced live: watchlist had AAPL among 10 tickers; LLM requested "add AAPL" with
    a leading space in the action field; AAPL was DELETED from the watchlist and the user was
    told it succeeded.
  artifacts:
    - path: "backend/app/llm/actions.py"
      issue: "Lines 109-110 and 144-145: executor re-derives side/action with only .lower(), not .strip().lower() like the validator uses — a whitespace-padded value from the LLM silently flips a watchlist add into a remove while reporting success."
  missing:
    - "Normalize ticker/side/action exactly once per loop iteration into local variables, and use those SAME normalized values for both validation and execution — structurally prevents this whole class of validator/executor divergence from recurring, not just this one instance"
    - "Add a regression test: an LLM response with a whitespace-padded 'add' action on a ticker not currently on the watchlist must add it (outcome=executed) and must NOT remove anything; same for a padded 'remove'"
  debug_session: ".planning/debug/llm-negative-sell-quantity.md"
