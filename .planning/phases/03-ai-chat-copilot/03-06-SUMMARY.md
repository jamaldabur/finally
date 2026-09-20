---
phase: 03-ai-chat-copilot
plan: 06
subsystem: llm-integration
tags: [litellm, openrouter, structured-output, gap-closure, tdd, error-handling]
requires:
  - phase: 03-ai-chat-copilot
    provides: "Plan 03-01's LLM client (parse_llm_response, get_chat_response, MODEL deviation to openrouter/openrouter/free) and Plan 03-02's chat route/history wiring"
provides:
  - "Code-fence recovery in parse_llm_response() so a correctly-formed model response wrapped in a markdown fence keeps its trades instead of silently dropping them"
  - "Two named, content-assertable fallback constants (PARSE_FALLBACK_MESSAGE, LLM_UNAVAILABLE_MESSAGE) that fully replace raw-model-text-as-message on any parse/validation failure"
  - "Non-streaming structured LLM call (_call_model_once) so provider/validation errors surface as real exceptions instead of returning silently with HTTP 200 and no log line"
  - "One-shot transient-error failover to FALLBACK_MODEL (openrouter/nvidia/nemotron-3-super-120b-a12b:free), with authentication/bad-request errors propagating untouched"
affects: [03-ai-chat-copilot]
actuals:
  tokens: 6341
  tasks: 2
  commits: 2
tech-stack:
  added: []
  patterns:
    - "Named, content-assertable fallback message constants instead of ad-hoc inline strings, so regression tests can assert exact content rather than truthiness"
    - "One-shot failover to a distinct model on a narrow, named transient-error tuple, never a bare except Exception, so real config bugs (auth, bad request) are never masked"
    - "Anchored, module-scope-compiled fence-stripping regex applied at most once per parse, never looped, to prevent unbounded stripping against untrusted text"
key-files:
  created: []
  modified:
    - backend/app/llm/client.py
    - backend/tests/llm/test_client.py
key-decisions:
  - "Deleted litellm.enable_json_schema_validation rather than re-enabling it after dropping stream=True — re-enabling it would raise before parse_llm_response()'s fence recovery ever runs, reintroducing the exact silently-dropped-trade failure this plan fixes (planner_assumptions #1)"
  - "FALLBACK_MODEL set to openrouter/nvidia/nemotron-3-super-120b-a12b:free, matching this repo's own agent-teams branch's independent choice for the identical free-router flakiness problem"
  - "Both tasks' implementation landed in a single feat commit (preceded by a single test commit covering both tasks' behaviors) rather than four separate TDD commits, since Task 2's rework depends on Task 1's constants and both edit the same module docstring region and the same two functions — consistent with planner_assumptions #4's own note that the tasks are sequential, not independently separable"
patterns-established:
  - "Content-asserting fallback-message oracle: tests assert `result.message == NAMED_CONSTANT`, not `assert result.message` truthiness — the weak oracle that let G-03-3 ship"
requirements-completed: [CHAT-01, CHAT-02, CHAT-03, CHAT-04, CHAT-06]
gap_ids: [G-03-3]
coverage:
  - id: D1
    description: "A fenced-but-correct model response keeps its trades and shows its real message, both through parse_llm_response() directly and end-to-end through get_chat_response()"
    requirement: CHAT-03
    verification:
      - kind: unit
        ref: "backend/tests/llm/test_client.py::test_parse_llm_response_recovers_fenced_valid_json_tagged"
        status: pass
      - kind: unit
        ref: "backend/tests/llm/test_client.py::test_parse_llm_response_recovers_untagged_fenced_json_with_whitespace"
        status: pass
      - kind: unit
        ref: "backend/tests/llm/test_client.py::test_get_chat_response_recovers_fenced_trades_end_to_end"
        status: pass
    human_judgment: false
  - id: D2
    description: "Every unparseable/unrecoverable input returns the exact PARSE_FALLBACK_MESSAGE constant, never raw model text, and never raises"
    requirement: CHAT-01,CHAT-02
    verification:
      - kind: unit
        ref: "backend/tests/llm/test_client.py::test_parse_llm_response_never_shows_raw_text_and_falls_back_to_constant[uat-garbage,plain-prose,wrong-schema-json,empty-string]"
        status: pass
      - kind: unit
        ref: "backend/tests/llm/test_client.py::test_parse_llm_response_never_raises"
        status: pass
      - kind: unit
        ref: "backend/tests/llm/test_client.py::test_parse_llm_response_preserves_multibyte_characters"
        status: pass
    human_judgment: false
  - id: D3
    description: "The structured call passes no truthy streaming flag and reads content from the response's message, coercing missing content to an empty string"
    verification:
      - kind: unit
        ref: "backend/tests/llm/test_client.py::test_call_llm_structured_passes_no_truthy_streaming_flag"
        status: pass
      - kind: unit
        ref: "backend/tests/llm/test_client.py::test_call_llm_structured_returns_empty_string_for_missing_content"
        status: pass
    human_judgment: false
  - id: D4
    description: "A transient provider error triggers exactly one failover to FALLBACK_MODEL with an identical message list; auth errors never fail over; both-fail returns LLM_UNAVAILABLE_MESSAGE with an error log; mock mode makes zero completion calls"
    requirement: CHAT-02,CHAT-06
    verification:
      - kind: unit
        ref: "backend/tests/llm/test_client.py::test_call_llm_structured_fails_over_once_on_transient_error"
        status: pass
      - kind: unit
        ref: "backend/tests/llm/test_client.py::test_call_llm_structured_never_exceeds_two_calls_when_both_fail"
        status: pass
      - kind: unit
        ref: "backend/tests/llm/test_client.py::test_call_llm_structured_does_not_fail_over_on_authentication_error"
        status: pass
      - kind: unit
        ref: "backend/tests/llm/test_client.py::test_get_chat_response_returns_unavailable_message_when_both_models_fail"
        status: pass
      - kind: unit
        ref: "backend/tests/llm/test_client.py::test_mock_mode_never_calls_completion_function"
        status: pass
    human_judgment: false
  - id: D5
    description: "Live human verification against the real (non-mock) OpenRouter path: repeated real chat turns never show raw JSON/fences/leaked instructions, an executed sell shows a green badge with a fill price, and every degraded turn has a corresponding log line"
    verification: []
    human_judgment: true
    rationale: "Task 2's <human-check> requires a live backend+frontend session with a real OPENROUTER_API_KEY and manual observation of several real (non-deterministic, router-selected) LLM replies plus the uvicorn log — not automatable by the executor. Deferred to end-of-phase UAT per workflow.human_verify_mode=end-of-phase, the same convention Plans 03-01/03-02's own <human-check> items used."
duration: 25min
completed: 2026-09-20
status: complete
---

# Phase 03 Plan 06: Fence-Recovery and One-Shot LLM Failover Summary

**Closed G-03-3 by making the chat client's parse path recover markdown-fenced valid responses before giving up, replacing raw-model-text fallbacks with two named constants, dropping the streaming flag that silenced provider errors, and adding a bounded one-shot failover to a distinct fallback model.**

## Performance
- **Duration:** 25min
- **Started:** 2026-09-20T21:45:00Z
- **Completed:** 2026-09-20T22:10:00Z
- **Tasks:** 2 completed
- **Files modified:** 2

## Accomplishments
- `parse_llm_response()` now retries schema validation against a fence-stripped text before giving up, so a code-fenced but otherwise correct model response keeps its `message` and its `trades[]` intact — the highest-severity finding in the debug session (a real trade silently vanishing).
- Two named constants, `PARSE_FALLBACK_MESSAGE` and `LLM_UNAVAILABLE_MESSAGE`, are now the only two possible fallback texts ever shown to the user; the model's own raw text can never reach the assistant's `message` field under any parse or validation failure.
- The structured LLM call no longer passes `stream=True`. This was the load-bearing config cause of G-03-3: streaming routed provider/validation errors around LiteLLM's normal error-raising path, producing HTTP 200 with zero log lines for a genuinely broken turn.
- The dead `litellm.enable_json_schema_validation` toggle and its now-false docstring claim are removed, with the module docstring rewritten to state that schema validation is owned entirely by this module's own (strictly better, fence-recovering) `parse_llm_response()`.
- `_call_llm_structured()` now fails over exactly once to a distinct `FALLBACK_MODEL` on a narrow, named tuple of transient provider errors — never on authentication or bad-request errors, which propagate untouched so a real misconfiguration is never masked behind a second model call.
- The regression test oracle now asserts exact message *content* (`result.message == PARSE_FALLBACK_MESSAGE` / `== LLM_UNAVAILABLE_MESSAGE`) everywhere, replacing the truthiness-only assertion that let the original defect ship silently.

## Task Commits
1. **Task 1 & 2 (combined, test-first): add failing tests for fence recovery and one-shot failover** - `db1575d`
2. **Task 1 & 2 (combined, implementation): recover fenced JSON, drop streaming, fail over once (G-03-3)** - `4d0999c`

## Files Created/Modified
- `backend/app/llm/client.py` — Added `FALLBACK_MODEL`, `_TRANSIENT_ERRORS`, `PARSE_FALLBACK_MESSAGE`, `LLM_UNAVAILABLE_MESSAGE`, `_CODE_FENCE_RE`/`_strip_code_fence()`; restructured `parse_llm_response()` for fence recovery; split the structured call into `_call_model_once()` (non-streaming) + `_call_llm_structured()` (one-shot failover wrapper); removed the dead `litellm.enable_json_schema_validation` toggle and rewrote the module docstring
- `backend/tests/llm/test_client.py` — Added/strengthened tests: fenced-JSON recovery (tagged and untagged), content-asserting parse-failure oracle (UAT garbage, prose, wrong-schema JSON, empty string), end-to-end fenced-trade survival through `get_chat_response()`, no-streaming-flag assertion, missing-content coercion, transient-error one-shot failover with identical message list, two-call ceiling on double failure, no-failover-on-auth-error, `LLM_UNAVAILABLE_MESSAGE` on double failure with an error-level log, and zero completion calls under mock mode

## Decisions Made
- Deleted the dead `litellm.enable_json_schema_validation` toggle rather than reactivating it once streaming was dropped — reactivating it would raise before `parse_llm_response()`'s fence recovery ever runs, silently reintroducing the exact trade-dropping failure this plan closes (planner_assumptions #1, the one place the two UAT-offered options genuinely conflicted).
- `FALLBACK_MODEL = "openrouter/nvidia/nemotron-3-super-120b-a12b:free"`, matching this repo's own `agent-teams` branch's independent choice for the same free-router-flakiness problem — a paid model was not viable given the account's lack of purchased credits (the original Plan 03-01 402 deviation).
- Combined both tasks' test-first work into one test commit and both tasks' implementation into one feat commit, rather than four separate TDD commits, because Task 2's non-streaming/failover rework depends on Task 1's `LLM_UNAVAILABLE_MESSAGE` constant and both tasks edit the identical module docstring region and the same two functions (`_call_llm_structured`/`parse_llm_response`) — consistent with the plan's own planner_assumptions #4 noting the tasks are sequential and not independently separable. RED was confirmed (all new/strengthened assertions failed against the pre-plan `client.py`) before the implementation commit made them pass.

## Deviations from Plan

**1. [Process note, not a Rule 1-4 deviation] Two negative-grep verify commands (`! grep -qE "while |for .* in range\("`) initially matched the prose word "while" inside two docstring sentences, not any actual loop construct.**
- **Found during:** Final verification pass after Task 2 implementation.
- **Issue:** The literal substring `"while "` appeared in two explanatory comments ("...never ran while the structured call streamed..." and "...trades vanish silently while the user is told..."), tripping the plan's loop-detection grep even though no loop existed anywhere in the file.
- **Fix:** Reworded both sentences to avoid the literal substring while preserving identical meaning (e.g., "...never ran, because the structured call itself streamed..." and "...trades vanish silently, and the user is told...").
- **Files modified:** `backend/app/llm/client.py`
- **Verification:** `grep -nE "while |for .* in range\(" backend/app/llm/client.py` now exits 1 (no match); full test suite re-run, 191/191 passed.
- **Commit:** Folded into `4d0999c` (pre-commit fix, no separate commit needed).

**Total deviations:** 1 auto-fixed (Rule 1 — cosmetic grep-tripping wording, not a functional bug, but corrected before commit to satisfy the plan's own hard verification gate). **Impact:** None on behavior; purely a documentation-wording fix required to pass an automated verification command.

## Issues Encountered
None beyond the grep-wording note above. All automated `<verify>` commands from both tasks pass, including the negative greps guarding against reverting the Plan 03-01 model deviation, reintroducing streaming, reintroducing the dead validation toggle, adding an unbounded retry loop, or adding a library-level retry multiplier.

## User Setup Required
None — no external service configuration required. (Task 2's `<human-check>` requires a human with a live `OPENROUTER_API_KEY` to manually verify several real, non-deterministic chat replies plus the uvicorn log; this is deferred to end-of-phase UAT per `workflow.human_verify_mode=end-of-phase`, matching how Plans 03-01/03-02's own `<human-check>` items were handled. See coverage item D5.)

## Next Phase Readiness
This closes UAT gap G-03-3 (blocker — the most severe of the three Phase 03 UAT gaps: a real, correctly-requested trade could be silently dropped by the LLM path). Sibling gap-closure plan 03-05 (frontend collapse-control fix for G-03-1/G-03-2) touches entirely unrelated files (`frontend/components/chat/ChatPanel.tsx`, `frontend/app/page.tsx`, `03-UI-SPEC.md`) and requires no coordination with this plan. Once both close, Phase 03's UAT should be re-run end-to-end (test 4's live-LLM chat scenario is the direct regression check for this plan; tests 1-2 are the direct regression check for 03-05) before the phase is considered fully verified.

---
*Phase: 03-ai-chat-copilot*
*Completed: 2026-09-20*

## Self-Check: PASSED

- FOUND: backend/app/llm/client.py
- FOUND: backend/tests/llm/test_client.py
- FOUND: .planning/phases/03-ai-chat-copilot/03-06-SUMMARY.md
- FOUND commit: db1575d (test)
- FOUND commit: 4d0999c (feat)
- FOUND commit: a09e940 (docs/summary)
