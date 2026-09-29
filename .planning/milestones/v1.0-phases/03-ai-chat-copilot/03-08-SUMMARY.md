---
phase: 03-ai-chat-copilot
plan: 08
subsystem: llm-integration
tags: [litellm, openrouter, structured-output, gap-closure, tdd, normalization, security]

requires:
  - phase: 03-ai-chat-copilot
    provides: "Plan 03-01's execute_llm_actions()/actions.py validate-then-execute-then-annotate loop, ChatResponseSchema, SYSTEM_PROMPT, and Plan 03-06's non-streaming call/one-shot failover"
provides:
  - "A normalize-once-and-reuse loop in execute_llm_actions(): _normalize_trade_item() / _normalize_watchlist_item() each run exactly once per item, and validation, dispatch, execution and annotation all read that one normalized result"
  - "A sell-only sign recovery: a negative sell quantity executes at its absolute magnitude; a negative buy stays rejected (never blanket abs())"
  - "An explicit add/remove watchlist dispatch with a non-raising error branch for any other value — no destructive fallthrough reachable if validation is bypassed"
  - "JSON Schema field descriptions on LlmTradeItem.quantity/side (no constraint) plus a matching SYSTEM_PROMPT hard constraint, telling the model the sign convention"
affects: [03-ai-chat-copilot]

actuals:
  tokens: 7430
  tasks: 2
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Normalize-once-and-reuse: a pure, synchronous module-level helper derives every normalized field from an untrusted item exactly one time per loop iteration; validation, execution and annotation all read that single result — no second, partial re-derivation is permitted anywhere downstream"
    - "Sign recovery conditioned on a corroborating field, never blanket: abs() is applied only when a companion field (side='sell') already states the same direction unambiguously; the ambiguous case (a negative buy) stays rejected rather than silently reinterpreted"
    - "Explicit dispatch with a non-raising catch-all: an if/elif naming every valid branch, with a final else that annotates an error and continues rather than falling through to a destructive default"
    - "Schema descriptions over schema constraints for untrusted-model-facing hints: a Field(description=...) is a costless signal the provider may ignore; a Field(gt=...)/enum is a gate that discards an entire good response the instant one item is malformed"

key-files:
  created:
    - backend/tests/llm/test_schema.py
  modified:
    - backend/app/llm/actions.py
    - backend/app/llm/schema.py
    - backend/app/llm/client.py
    - backend/tests/llm/test_actions.py

key-decisions:
  - "Annotations (error and executed, trade and watchlist) now report the normalized values, not the raw model item — a small, deliberate behaviour change. Echoing the raw value while having validated/executed a different one was the exact defect this plan removes, so the badge now describes exactly what the system understood and did (planner_assumptions #1)"
  - "LlmWatchlistChange intentionally received no Field(description=...) this round — its padded-action failure is closed structurally by the single-normalization fix in actions.py, so a schema hint there would reduce nothing still reachable (planner_assumptions #2)"
  - "backend/app/portfolio/service.py and backend/app/llm/mock.py were read but deliberately left unmodified: execute_trade()'s own quantity guard is the last line of defense for direct, non-chat callers, and the mock's regex patterns are a determinism contract for Phase 6's E2E suite"

patterns-established:
  - "Normalize-once-and-reuse for any future field added to an LLM-sourced item: derive it exactly once into a local, and have every downstream reader — validator, executor, annotator — use that one derived value, never re-derive independently"

requirements-completed: [CHAT-01, CHAT-02, CHAT-03, CHAT-04, CHAT-06]
gap_ids: [G-03-5, G-03-6]

coverage:
  - id: D1
    description: "A validated value and an executed value are provably the same value for both trades and watchlist changes — _normalize_trade_item()/_normalize_watchlist_item() each run exactly once per loop iteration, and no validator or executor re-derives independently"
    requirement: CHAT-03
    verification:
      - kind: unit
        ref: "backend/tests/llm/test_actions.py::test_execute_llm_actions_padded_side_executes"
        status: pass
      - kind: unit
        ref: "backend/tests/llm/test_actions.py::test_execute_llm_actions_padded_add_action_adds_and_removes_nothing"
        status: pass
      - kind: unit
        ref: "backend/tests/llm/test_actions.py::test_execute_llm_actions_padded_remove_action_removes"
        status: pass
      - kind: other
        ref: "grep -cE \"^def _normalize_trade_item\\(\" / \"= _normalize_trade_item\\(\" / \"^def _normalize_watchlist_item\\(\" / \"= _normalize_watchlist_item\\(\" backend/app/llm/actions.py — all >=1"
        status: pass
    human_judgment: false
  - id: D2
    description: "A padded ' add' on a ticker already on the watchlist reports an error and leaves that ticker in place — the literal reproduction of the confirmed data-loss incident (a requested add silently performing a remove and reporting success)"
    requirement: CHAT-04
    verification:
      - kind: unit
        ref: "backend/tests/llm/test_actions.py::test_execute_llm_actions_padded_add_on_watched_ticker_does_not_delete_it"
        status: pass
      - kind: other
        ref: "grep -vE \"^\\s*#\" backend/app/llm/actions.py | grep -cE 'elif action == \"remove\"' — explicit dispatch, no implicit-else fallthrough into the destructive branch"
        status: pass
    human_judgment: false
  - id: D3
    description: "A sell whose quantity arrives negative executes at its absolute magnitude; a negative buy still errors and mutates nothing; zero, negative zero, NaN and infinity are rejected for both sides"
    requirement: CHAT-03
    verification:
      - kind: unit
        ref: "backend/tests/llm/test_actions.py::test_execute_llm_actions_recovers_negative_sell_quantity"
        status: pass
      - kind: unit
        ref: "backend/tests/llm/test_actions.py::test_execute_llm_actions_still_rejects_negative_buy_quantity"
        status: pass
      - kind: unit
        ref: "backend/tests/llm/test_actions.py::test_execute_llm_actions_rejects_zero_and_non_finite_quantities (10 parametrizations)"
        status: pass
    human_judgment: false
  - id: D4
    description: "execute_trade()'s own non-positive-quantity guard and the mock's regex patterns are unchanged, protecting every direct non-chat caller and Phase 6's E2E determinism contract"
    requirement: CHAT-06
    verification:
      - kind: unit
        ref: "backend/tests/portfolio/test_service.py (11 tests, run as its own step) and backend/tests/llm/test_mock.py (8 tests)"
        status: pass
      - kind: other
        ref: "grep -c 'quantity <= 0' backend/app/portfolio/service.py ; grep -c '_TRADE_PATTERN' backend/app/llm/mock.py"
        status: pass
    human_judgment: false
  - id: D5
    description: "The regression gap that let both defects ship is closed: tests construct schema items directly and the suite records why the mock path could never reach either input"
    requirement: CHAT-06
    verification:
      - kind: unit
        ref: "backend/tests/llm/test_actions.py::test_mock_response_cannot_emit_a_negative_quantity"
        status: pass
    human_judgment: false
  - id: D6
    description: "The emitted JSON Schema carries descriptions on the trade item's quantity and side and no bound/enumeration, a malformed item still parses, and SYSTEM_PROMPT carries the matching sign-convention rule"
    requirement: CHAT-02
    verification:
      - kind: unit
        ref: "backend/tests/llm/test_schema.py (6 tests: descriptions present, no constraint, malformed item parses, watchlist schema unchanged, prompt rule present, model constant unchanged)"
        status: pass
    human_judgment: false
  - id: D7
    description: "Live, non-mock verification: with a real OPENROUTER_API_KEY, repeated 'sell 2 AAPL' chat turns never show a red 'Invalid quantity' badge with a negative number, and an AI-driven watchlist add/remove is confirmed by counting the watchlist before and after (not by badge color alone)"
    verification: []
    human_judgment: true
    rationale: "Requires a live OPENROUTER_API_KEY against the non-stationary free auto-router and manual browser interaction across multiple chat turns — cannot be established by an automated check. Deferred per workflow.human_verify_mode=end-of-phase to the phase's end-of-phase UAT batch, same convention Phase 2 used."

duration: 45min
completed: 2026-09-21
status: complete
---

# Phase 03 Plan 08: Normalize LLM Action Outcomes Summary

**Collapsed `execute_llm_actions()`'s two independent field-derivation paths (validator vs. executor) into one normalize-once-and-reuse loop, closing a confirmed live data-loss bug where a padded watchlist "add" silently deleted a ticker and reported success, plus recovering a redundant negative-sign sell quantity that was previously discarded outright.**

## Performance
- **Duration:** ~45min
- **Started:** 2026-09-21T15:30:00Z (approx, first Read)
- **Completed:** 2026-09-21T16:20:00Z (approx, final commit)
- **Tasks:** 2 completed
- **Files modified:** 3 source files, 2 test files (1 new)

## Accomplishments
- `_normalize_trade_item()` and `_normalize_watchlist_item()` now derive the ticker/side/quantity or ticker/action exactly once per item; every validator, `execute_trade()` call, watchlist mutation, and annotation reads that single normalized result — no field is ever re-derived a second, divergent way.
- Closed the confirmed data-loss defect: a watchlist action of `" add"` (leading whitespace) on an already-watched ticker previously passed validation as `"add"`, failed a raw equality check in the executor, and fell through to the REMOVE call while reporting a green "executed" badge. Now it is annotated as an error with the existing already-on-the-watchlist reason, and the ticker stays put.
- Recovered the reported gap: a sell whose quantity arrives negative (e.g. `side="sell", quantity=-2`) now executes at its absolute magnitude instead of being discarded as an invalid quantity — while a negative buy is still rejected outright, since recovering it would require inferring trade direction from an ambiguous sign in a system that auto-executes trades with no confirmation dialog.
- Added a preventive layer: `LlmTradeItem.quantity`/`.side` now carry JSON Schema `description` text (no numeric/enum constraint) and `SYSTEM_PROMPT` carries a matching hard-constraint bullet, both stating the sign convention to the backing model — reducing (not eliminating) how often the bad item is produced in the first place.
- 25 tests in `test_actions.py` (8 new) and 6 new tests in `test_schema.py` all pass; the full backend suite (214 tests) passes with zero regressions.

## Task Commits
1. **Task 1 RED: add regression tests for validator/executor divergence** - `951fd95` (test)
2. **Task 1 GREEN: normalize each LLM action once and reuse it** - `a06d51d` (feat)
3. **Task 2 RED: add contract tests for schema descriptions and prompt rule** - `f1178e0` (test)
4. **Task 2 GREEN: tell the model the sign convention in schema and prompt** - `8f60cb7` (feat)

## Files Created/Modified
- `backend/app/llm/actions.py` - Added `_normalize_trade_item()`/`_normalize_watchlist_item()`; rewrote both `execute_llm_actions()` loops to normalize once and reuse; explicit add/remove dispatch with non-raising error branch; extended module docstring
- `backend/app/llm/schema.py` - Added `Field(description=...)` (no constraint) to `LlmTradeItem.quantity`/`.side`; extended module docstring on description-vs-constraint rationale
- `backend/app/llm/client.py` - Added one hard-constraint bullet to `SYSTEM_PROMPT` on the quantity sign convention; updated the comment above it
- `backend/tests/llm/test_actions.py` - Added 8 named regression tests (negative sell recovery, negative buy still rejected, zero/NaN/infinity rejected for both sides, padded side executes, padded add adds/doesn't delete a watched ticker, padded remove removes, mock path structurally cannot emit either input)
- `backend/tests/llm/test_schema.py` - New file: 6 contract tests against the generated JSON Schema (descriptions present, no constraint, malformed item still parses, watchlist schema unchanged, prompt rule present, model constant unchanged)

## Decisions Made
- Annotations now report normalized values rather than echoing the raw model item — the coherent choice once validation and execution both read the single normalized result; existing tests already asserted outcomes and backend-verbatim reason strings, so nothing regressed.
- `LlmWatchlistChange` deliberately received no field description this round; its failure is closed structurally, so a description there would be motion without effect.
- No change to `backend/app/portfolio/service.py` or `backend/app/llm/mock.py` — both were read-only context per the plan, preserving the last line of defense for direct callers and the E2E determinism contract respectively.

## Deviations from Plan

None — plan executed exactly as written. One self-corrected test-authoring bug (not a deviation from the plan's design): the first draft of `test_execute_llm_actions_rejects_zero_and_non_finite_quantities` asserted zero trade rows globally, but the "sell" parametrization's own setup buy legitimately writes one row; fixed by comparing against a captured baseline before the assertion under test runs, per Rule 1 (bug in the test I was actively writing, fixed inline before it was ever committed as RED).

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness

All automated verification for this plan passes (214/214 backend tests, all plan-specified greps). One item remains for the phase's end-of-phase UAT batch, per `workflow.human_verify_mode=end-of-phase` (the same convention Phase 2 used): Task 2's `<human-check>` — live, non-mock chat verification with a real `OPENROUTER_API_KEY`, sending "sell 2 AAPL" at least six times and confirming no red "Invalid quantity" badge with a negative number ever appears, plus an AI-driven watchlist add/remove confirmed by counting entries before and after (not by badge color alone). This is the only outstanding item; no code changes are blocked on it.

This is one of two round-2 UAT gap-closure plans in Phase 3: G-03-5 and G-03-6 are closed by this plan. Plan `03-07-PLAN.md` (G-03-4, the collapsed chat rail) exists on disk but has not yet been executed — no `03-07-SUMMARY.md` exists. `03-07` does not depend on this plan's files (disjoint file scope: frontend `ChatPanel`/rail vs. this plan's backend `app/llm/*`), so its execution is unblocked and is the only remaining plan in Phase 3.

---
*Phase: 03-ai-chat-copilot*
*Completed: 2026-09-21*
