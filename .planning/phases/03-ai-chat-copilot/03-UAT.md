---
status: diagnosed
phase: 03-ai-chat-copilot
source: [03-VERIFICATION.md]
started: 2026-09-20T00:00:00Z
updated: 2026-09-20T00:30:00Z
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
severity: blocker

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
  root_cause: "Same root cause as G-03-2 — see that entry. This is the general first report of the same collapse-control design-contract defect; investigated together as one debug session to avoid duplicate work."
  artifacts:
    - path: "frontend/components/chat/ChatPanel.tsx"
      issue: "See G-03-2 for the full breakdown."
  missing:
    - "Resolved by the same fix as G-03-2."
  debug_session: ".planning/debug/chat-panel-collapse-toggle.md"

- gap_id: G-03-2
  truth: "Click Collapse → panel becomes a narrow \"Chat\" rail; click it again → expands"
  status: failed
  reason: "User reported: collapse/expand feels broken and the collapsed rail is hard to notice/find; requesting a design change to the collapse control (add a clear expand/collapse affordance, e.g. a chevron icon, hover feedback, and a smoother transition)"
  severity: major
  test: 2
  root_cause: >
    Purely a UX/design-quality gap, not a functional bug — every candidate functional cause
    (broken handlers, remount resetting state, Tailwind purge, z-index/overlap, render loops)
    was eliminated with direct evidence. Two distinct, measurable defects compound:
    (1) "hard to notice" — the collapsed rail's fill (#1a1a2e on #0d1117 = 1.109:1 contrast)
    and its only delimiter (1px border-l, 1.551:1) both fail the WCAG 1.4.11 3:1 floor for UI
    components, so the 48px rail itself is visually imperceptible — only the 12px rotated
    "Chat" text (5.5:1) reads at all; (2) "feels broken" — zero CSS transition exists anywhere
    on the collapse/expand toggle (confirmed via source grep and the compiled dev-server CSS
    bundle), so the 320px<->48px change is an instant two-subtree DOM swap with no
    interpolation, there is no hover state on the collapsed rail at all, and the expanded
    "Collapse" button has no padding (~50x16px hit box, under the WCAG 2.5.8 24x24 minimum)
    and no chrome, so it reads as a label rather than a control. Root origin: 03-UI-SPEC.md
    itself specifies exactly this design (no icon, `border-l` only, no hover, no transition
    called out) — this is a spec defect, not an executor error; 03-UI-SPEC.md is still
    `status: draft` with all Checker Sign-Off dimensions unchecked. A secondary, unrelated
    dead-code bug was also found: the unread-indicator dot's only reachable trigger is a false
    positive (pre-existing history is flagged as "unread" if the panel is collapsed before the
    mount-hydrate fetch resolves), since `ChatInput` (the only way `messages` grows) is
    unmounted while collapsed.
  artifacts:
    - path: "frontend/components/chat/ChatPanel.tsx"
      issue: "Lines 48-65 (collapsed rail: sub-3:1 contrast fill+border, no icon, no hover, no rounded-lg) and lines 72-78 (unpadded/chromeless Collapse button, ~50x16px hit target). Lines 32-46: unread-dot false-positive on pre-existing history."
    - path: ".planning/phases/03-ai-chat-copilot/03-UI-SPEC.md"
      issue: "Specifies the defective design directly (no icon library, border-l-only rail, no hover/transition called out) and its own Spacing table's 48px-rail touch-target claim doesn't hold for the collapse-direction control. status: draft, Approval: pending — should be reconciled alongside the code fix, not left contradicting it."
    - path: "frontend/app/page.tsx"
      issue: "p-6 row padding is why the collapsed rail floats as a sliver 24px inside the viewport edge rather than reading as a docked rail (contributing, not primary)."
  missing:
    - "Raise the collapsed rail's fill/border contrast to >=3:1 against #0d1117 (WCAG 1.4.11)"
    - "Add a directional affordance — a Unicode/inline-SVG chevron is compatible with the spec's 'no icon library' rule; do not import an icon-library component"
    - "Add a visible hover state to the collapsed rail (currently has none)"
    - "Give the expanded 'Collapse' button real padding/chrome so its hit target clears 24x24 (WCAG 2.5.8) and it reads as a control, not a label"
    - "Animate the width transition — requires restructuring from two disjoint conditional-render subtrees to one persistent element with a transitioning width class, since CSS cannot interpolate across an unmount/remount"
    - "Fix the unread-dot false positive (fold in cheaply alongside the above)"
    - "Update 03-UI-SPEC.md to match the corrected design so spec and code stay in contract"
  debug_session: ".planning/debug/chat-panel-collapse-toggle.md"

- gap_id: G-03-3
  truth: "The assistant's message text never asserts or implies a trade/watchlist outcome, never executes an action not present in trades[]/watchlist_changes[], and shows no manipulative framing"
  status: resolved
  resolved_by: "03-06"
  resolved_at: "2026-09-20"
  reason: "User reported: told the AI assistant to sell 2 AAPL against the real (non-mock) LLM and got the message text 'Invalid placeholder, avoid outputting non-JSON text when schema is required.' instead of a real response"
  severity: blocker
  test: 4
  root_cause: >
    Three confirmed, compounding causes, escalating this beyond the originally-suspected
    cosmetic issue into a functional defect that can silently drop real trades. (1) [primary,
    code] parse_llm_response() (backend/app/llm/client.py:153-162) treats every JSON-parse/
    schema-validation failure identically and renders `raw.strip()` verbatim as the displayed
    message — confirmed by direct testing with garbage text, plain prose, and valid-JSON-wrong-
    schema, all three rendered verbatim. (2) [load-bearing, config] `litellm.enable_json_schema_validation
    = True` (client.py:33) is DEAD CODE on this call path: `_call_llm_structured()` passes
    `stream=True` (client.py:143), and LiteLLM's streaming branch returns before
    `post_call_processing()` — the only consumer of that flag anywhere in the package — so
    schema validation silently never runs, confirmed by a differential test (stream=False
    raises JSONSchemaValidationError on the exact reported string; stream=True does not raise
    at all). This is also why NO error was logged for this request: `get_chat_response()`'s
    `except Exception` fallback (which already returns the correct generic message) was never
    reached, because nothing raised. (3) [environment] MODEL=openrouter/openrouter/free (the
    03-01 deviation) has zero retry/fallback (confirmed via repo-wide grep) despite documented
    flakiness; this repo's own agent-teams branch pairs the identical model with a
    FALLBACK_MODEL, a one-shot failover, code-fence stripping, and a constant fallback message
    — none of which were carried over. SEVERITY UPGRADE: reproduced end-to-end that a
    CORRECTLY-formed model response wrapped in a markdown code fence (a documented free-router
    behavior, confirmed present in agent-teams' _strip_code_fence existing specifically for
    this) hits the identical branch — the raw fenced JSON blob is shown as the message AND
    `trades` parses to `[]`, silently dropping a real, valid trade request. This is a genuine
    violation of the phase's core value (agentic execute step), not a display bug.
    Amplifier: routes/chat.py:166 persists the bad message unconditionally and
    build_messages() replays it into every future prompt's history, so a single bad response
    poisons subsequent turns too. The one existing test for this path
    (tests/llm/test_client.py:13-21, test_parse_llm_response_never_raises_and_falls_back_to_message)
    asserts only `assert result.message` (truthy) and would pass even showing `{"message": 42}`
    verbatim to the user — a weak-oracle gap, not a missing test.
  artifacts:
    - path: "backend/app/llm/client.py"
      issue: "Lines 153-162 (verbatim-raw fallback, no distinction between garbage/prose/wrong-schema-JSON); line 33 vs 143 (enable_json_schema_validation is inert under stream=True); line 35 (MODEL with no fallback/retry); module docstring lines 11-15 make a now-false claim about the client-side validation backstop being active."
    - path: "backend/tests/llm/test_client.py"
      issue: "Line 13-21's oracle asserts only message truthiness, not content — passes while encoding the bug as acceptable."
    - path: "backend/app/routes/chat.py"
      issue: "Line 166 persists the malformed message unconditionally, and build_messages() replays it into future prompt history, compounding the failure across turns."
  missing:
    - "Stop displaying raw model text on any parse/validation failure — return a constant generic fallback message instead (reuse the existing network-exception fallback text or a dedicated one)"
    - "Before giving up, strip markdown code fences and retry model_validate_json (port agent-teams' _strip_code_fence) — this is what prevents the silent trade-drop, the higher-value fix"
    - "Add a FALLBACK_MODEL + one-shot failover mirroring agent-teams, so one bad free-router pick isn't terminal for the turn"
    - "Resolve the dead enable_json_schema_validation flag honestly: either drop stream=True (nothing is actually streamed to the browser — POST /api/chat returns one complete body per PLAN.md §9 step 4 — so streaming buys nothing here, and removing it re-activates both the validation backstop and correct error logging) or delete the flag and correct the docstring's claim"
    - "Strengthen test_parse_llm_response_never_raises_and_falls_back_to_message to assert message content (and that a code-fenced valid response's trades survive), so this class of regression can't pass silently again"
  debug_session: ".planning/debug/llm-raw-garbage-as-message.md"
