---
phase: 03-ai-chat-copilot
plan: 01
subsystem: ai-chat-backend
tags: [litellm, openrouter, structured-output, pydantic, fastapi, portfolio-validation]
requires:
  - phase: 01-portfolio-engine
    provides: "execute_trade(), add_watchlist_ticker()/remove_watchlist_ticker(), compute_portfolio_view(), PriceCache, portfolio_lock — the shared validated mutation path this plan routes LLM-proposed actions through"
provides:
  - "POST /api/chat — the whole agentic chat loop end-to-end (message -> LLM/mock -> structured parse -> validated execution -> annotated outcome)"
  - "app/llm/ package: schema.py (ChatResponseSchema), client.py (LiteLLM/OpenRouter call + is_mock_mode + defensive parse), mock.py (deterministic mock), actions.py (validate-then-execute-then-annotate loop)"
  - "execute_trade() hardened against invalid quantity/side for every caller, not just the HTTP route"
affects: [03-02-chat-persistence, 03-03-chat-frontend, 03-04-chat-ui-badges]
actuals:
  tokens: 106474
  tasks: 3
  commits: 5
tech-stack:
  added:
    - "litellm — LiteLLM abstraction over OpenRouter, structured output via response_format + client-side enable_json_schema_validation"
    - "pydantic — response_format schema models (ChatResponseSchema, LlmTradeItem, LlmWatchlistChange)"
    - "python-dotenv — loads project-root .env at backend startup so OPENROUTER_API_KEY reaches LiteLLM"
    - "Model: openrouter/openrouter/free (OpenRouter's Free Models Router) — switched from the originally planned openrouter/openai/gpt-oss-120b after that model returned HTTP 402 insufficient credits during live verification; see Deviations"
  patterns:
    - "Single validated mutation path: LLM-proposed trades/watchlist changes execute only through execute_trade() / add_watchlist_ticker() / remove_watchlist_ticker() — the exact functions the manual trade bar and watchlist routes call. No second chat-only persistence path exists."
    - "Permissive response_format schema + strict per-item gate: LlmTradeItem/LlmWatchlistChange use unconstrained str/float fields so one hallucinated item can't invalidate the whole LLM response; _validate_trade_item()/_validate_watchlist_item() in actions.py reject bad items individually before execute_trade() is ever called."
    - "Belt-and-suspenders validation: the same quantity/side guard now exists at both app/llm/actions.py (pre-call gate) and the top of execute_trade() itself (Task 3), so every caller — chat or otherwise — is protected."
    - "Single env-var reader: LLM_MOCK is read only inside app/llm/client.py::is_mock_mode(), evaluated fresh per call for concurrency safety."
key-files:
  created:
    - backend/app/llm/__init__.py
    - backend/app/llm/schema.py
    - backend/app/llm/client.py
    - backend/app/llm/mock.py
    - backend/app/llm/actions.py
    - backend/app/routes/chat.py
    - backend/tests/routes/test_chat.py
    - backend/tests/llm/__init__.py
    - backend/tests/llm/test_client.py
    - backend/tests/llm/test_actions.py
  modified:
    - backend/app/portfolio/service.py
    - backend/app/main.py
    - backend/pyproject.toml
    - backend/uv.lock
    - backend/tests/portfolio/test_service.py
    - .claude/skills/litellm-stream/SKILL.md
    - planning/PLAN.md
    - .claude/CLAUDE.md
    - .planning/PROJECT.md
key-decisions:
  - "Model switched from openrouter/openai/gpt-oss-120b to openrouter/openrouter/free after live verification hit a 402 insufficient-credits error on the original model (user-directed override, applied and re-verified before Task 3)"
  - "execute_trade()'s new quantity/side guard lives at the very top of the function, before ticker normalization and before is_valid_ticker() — so an invalid quantity is reported as an invalid quantity, not masked by a downstream unknown-ticker rejection"
patterns-established:
  - "Two-layer validation for untrusted LLM-sourced action items: schema stays permissive to preserve the model's message on partial malformation, per-item business-rule gates reject individually, and the shared service function gets its own defense-in-depth guard for every other (non-chat) caller"
requirements-completed: [CHAT-01, CHAT-02, CHAT-03, CHAT-04, CHAT-06]
coverage:
  - id: D1
    description: "POST /api/chat returns {message, trades, watchlist_changes} for every request, both action lists always present"
    requirement: CHAT-01
    verification:
      - kind: unit
        ref: "backend/tests/routes/test_chat.py#test_post_chat_returns_structured_response"
        status: pass
      - kind: unit
        ref: "backend/tests/routes/test_chat.py#test_post_chat_rejects_blank_message"
        status: pass
    human_judgment: false
  - id: D2
    description: "Real (non-mock) path requests structured output via LiteLLM response_format, client-side schema validation enabled, defensive parse never raises"
    requirement: CHAT-02
    verification:
      - kind: unit
        ref: "backend/tests/llm/test_client.py#test_parse_llm_response_never_raises_and_falls_back_to_message"
        status: pass
      - kind: unit
        ref: "backend/tests/llm/test_client.py#test_parse_llm_response_preserves_multibyte_characters"
        status: pass
      - kind: manual
        ref: "Orchestrator live round-trip via acompletion(..., response_format=ChatResponseSchema, stream=True) against openrouter/openrouter/free — returned real structured JSON, parsed cleanly (see Deviations)"
        status: pass
    human_judgment: true
    rationale: "The live-provider round trip (does OpenRouter actually honor response_format end-to-end for this project's schema) cannot be exercised by an automated unit test — it requires a real network call to a paid third-party API. Already executed and confirmed by the orchestrator per the tracer feedback gate; recorded here as evidence, not re-run by this agent."
  - id: D3
    description: "LLM-requested trades/watchlist changes auto-execute through execute_trade()/add_watchlist_ticker()/remove_watchlist_ticker() — no second code path"
    requirement: CHAT-03
    verification:
      - kind: unit
        ref: "backend/tests/routes/test_chat.py#test_chat_trade_auto_executes"
        status: pass
      - kind: unit
        ref: "backend/tests/routes/test_chat.py#test_chat_watchlist_change_auto_executes"
        status: pass
      - kind: unit
        ref: "backend/tests/portfolio/test_service.py#test_execute_trade_rejects_invalid_quantity_and_side"
        status: pass
      - kind: static
        ref: "grep -v '^\\s*#' backend/app/llm/actions.py | grep -cE 'execute_trade\\(|add_watchlist_ticker\\(|remove_watchlist_ticker\\(' -> 9; negative grep for set_cash_balance|upsert_position|insert_trade -> 0 matches"
        status: pass
    human_judgment: false
  - id: D4
    description: "Every action annotated executed/error with backend's verbatim reason, returned as structured data separate from message"
    requirement: CHAT-04
    verification:
      - kind: unit
        ref: "backend/tests/routes/test_chat.py#test_chat_action_annotated_on_insufficient_cash"
        status: pass
      - kind: unit
        ref: "backend/tests/llm/test_actions.py#test_execute_llm_actions_annotates_bad_item_and_executes_good_one"
        status: pass
      - kind: unit
        ref: "backend/tests/llm/test_actions.py#test_execute_llm_actions_does_not_collapse_duplicate_items"
        status: pass
    human_judgment: false
  - id: D5
    description: "LLM_MOCK=true produces deterministic responses with no network call, read from exactly one module"
    requirement: CHAT-06
    verification:
      - kind: unit
        ref: "backend/tests/routes/test_chat.py#test_chat_with_llm_mock"
        status: pass
      - kind: unit
        ref: "backend/tests/llm/test_client.py#test_is_mock_mode_reads_truthy_and_falsy_values"
        status: pass
    human_judgment: false
  - id: D6
    description: "execute_trade()'s quantity/side gap closed with regression tests — reject invalid quantity/side for every direct caller, no state change"
    verification:
      - kind: unit
        ref: "backend/tests/portfolio/test_service.py#test_execute_trade_rejects_invalid_quantity_and_side"
        status: pass
      - kind: static
        ref: "grep -v '^\\s*#' backend/app/portfolio/service.py | grep -c math.isfinite -> 1"
        status: pass
      - kind: unit
        ref: "cd backend && uv run pytest -q -> 151 passed"
        status: pass
    human_judgment: false
duration: ~24min (Task 2 tracer: ~13min in a prior session; deviation + Task 3 this session: ~11min)
completed: 2026-09-18
status: complete
---

# Phase 03 Plan 01: AI Chat Copilot Tracer & Trade-Path Hardening Summary

**End-to-end `POST /api/chat` loop (mock or `openrouter/openrouter/free` via LiteLLM structured output) auto-executing LLM-proposed trades through the shared `execute_trade()` path, with that function now hardened against invalid quantity/side for every caller.**

## Performance
- **Duration:** ~24min total across two sessions (Task 2 tracer previously; deviation + Task 3 this session)
- **Completed:** 2026-09-18
- **Tasks:** 3/3 completed (Task 1 checkpoint approved with no code; Task 2 tracer; Task 3 hardening)
- **Files modified:** 15 (10 created, 9 modified across both sessions' commits, excluding `uv.lock` noise)

## Accomplishments
- Proved the full agentic chat loop end-to-end: user message → LLM (mock or real) → validated structured output → real trade execution via `execute_trade()` → annotated outcome returned to the client — the architectural risk of Phase 3, concentrated into one slice, now proven working.
- Closed the `execute_trade()` quantity/side validation gap flagged since Phase 1 code review (01-REVIEW.md WR-01/WR-02, STATE.md blocker): the function now rejects a non-finite/non-positive quantity or a side outside `{buy, sell}` for every caller, not just the HTTP route's Pydantic layer — critical because the chat flow calls it directly.
- Switched the LLM model to `openrouter/openrouter/free` after the originally planned model failed live verification with a 402 (insufficient credits), re-verifying the full structured-output round trip on the new model before continuing.
- Full backend suite: 151 passed, 0 failures, 0 regressions.

## Task Commits
1. **Task 2: End-to-end chat trade tracer** - `8d6c74b` (prior session)
2. **Deviation: switch LLM model** - `6d442d2`
3. **Task 3 RED: failing test for execute_trade() guard** - `3862f88`
4. **Task 3 GREEN: implement execute_trade() guard** - `d42d0eb`
5. **Task 3: regression tests for LLM action validation/parse fallback** - `14a8cc9`

## Files Created/Modified
- `backend/app/llm/schema.py` - `ChatResponseSchema`/`LlmTradeItem`/`LlmWatchlistChange` — permissive response_format models
- `backend/app/llm/client.py` - LiteLLM/OpenRouter call, `is_mock_mode()`, `SYSTEM_PROMPT`, `build_messages()`, `parse_llm_response()`, `get_chat_response()`; `MODEL` now `openrouter/openrouter/free`
- `backend/app/llm/mock.py` - Deterministic `build_mock_response()` for `LLM_MOCK=true`
- `backend/app/llm/actions.py` - `_validate_trade_item()`/`_validate_watchlist_item()` gates plus `execute_llm_actions()` validate-then-execute-then-annotate loop
- `backend/app/routes/chat.py` - `POST /api/chat` route, request/response Pydantic models
- `backend/app/portfolio/service.py` - `execute_trade()` gains a leading quantity/side validation guard (Task 3)
- `backend/app/main.py` - `load_dotenv()` at startup, `include_router(chat.router)`
- `backend/tests/routes/test_chat.py` - 6 route-level tests for the full chat round trip
- `backend/tests/portfolio/test_service.py` - `test_execute_trade_rejects_invalid_quantity_and_side` (Task 3)
- `backend/tests/llm/test_client.py`, `backend/tests/llm/test_actions.py` - regression coverage for parse fallback, mock-mode gating, and per-item action validation (Task 3)
- `.claude/skills/litellm-stream/SKILL.md`, `planning/PLAN.md`, `.claude/CLAUDE.md`, `.planning/PROJECT.md` - model-name references updated to `openrouter/openrouter/free`

## Decisions Made
- **Model switch (Rule 4, pre-approved by user):** `openrouter/openai/gpt-oss-120b` → `openrouter/openrouter/free`. See Deviations below for full detail.
- **Guard placement in `execute_trade()`:** the validation guard runs as the very first statements, before ticker normalization and before `is_valid_ticker()`, so a bad quantity is reported as a bad quantity rather than masked by an unrelated unknown-ticker error. Mirrors the plan's explicit acceptance criterion.
- **Bool exclusion added to the quantity guard:** `isinstance(quantity, bool)` is explicitly rejected even though `bool` is an `int` subclass in Python — a defensive addition beyond the plan's literal wording, consistent with Rule 2 (missing critical input validation), since a stray boolean quantity is exactly the kind of hallucinated LLM output this guard exists to catch.

## Deviations from Plan

### Auto-fixed Issues

**None** — Task 3 was implemented exactly as specified; no bugs or missing functionality were discovered outside the plan's explicit scope.

### Pre-approved Architectural Change (Rule 4 — user-directed, already approved before this dispatch)

**1. [Rule 4 - Architectural] Switched LLM model from `openrouter/openai/gpt-oss-120b` to `openrouter/openrouter/free`**
- **Found during:** Tracer feedback gate (orchestrator's live verification of Task 2, after this plan's Task 2 was already committed at `8d6c74b`)
- **Issue:** The `POST /api/chat` handler itself worked correctly (200, correct 3-key shape, no `[LLM_MOCK]` prefix), but the underlying OpenRouter call failed with HTTP 402 insufficient credits on `openrouter/openai/gpt-oss-120b`.
- **Fix:** User explicitly directed switching to `openrouter/openrouter/free` (OpenRouter's "Free Models Router" — an auto-router across free underlying models). The correct LiteLLM model string requires OpenRouter's own model slug `openrouter/free` nested inside LiteLLM's `openrouter/` provider prefix — i.e. the doubled form `openrouter/openrouter/free`. A plain `openrouter/free` (single prefix) 404s at OpenRouter's own API ("No endpoints available for openrouter/free"). This exact doubled-prefix pattern is already used successfully on this repo's own `agent-teams` branch (`backend/app/llm/client.py`: `MODEL = "openrouter/openrouter/free"`).
- **Verification performed:** The orchestrator ran a live round trip through the *actual production code path* — the async `acompletion(model=MODEL, messages=..., response_format=ChatResponseSchema, stream=True)` call, accumulating `delta.content` across the streamed chunks, then `ChatResponseSchema.model_validate_json()` on the result. This succeeded with real output: `{"message":"Buying 5 shares of AAPL.","trades":[{"quantity":5,"side":"buy","ticker":"AAPL"}],"watchlist_changes":[]}`, parsed cleanly with no fallback triggered.
- **Caveat (observed, not fixed — no new code needed):** During a separate raw (non-streaming) test of the new model, the auto-router occasionally routed to an underlying "reasoning" model that put its answer in `reasoning_content` instead of `content`, leaving `content` empty. This was not reproduced on the actual streaming production path used by `_call_llm_structured()`, but is a real risk of choosing a free auto-router over a fixed model. No new code is needed to handle it: `parse_llm_response()`'s existing empty/malformed-content fallback (already covered by `test_parse_llm_response_never_raises_and_falls_back_to_message`) already degrades this exact failure mode to a message-only response rather than a 5xx. This is a known, accepted operational characteristic of the free-router choice, not a bug.
- **Files modified:** `backend/app/llm/client.py` (the only functional change — `MODEL` constant), plus four documentation references updated to match: `.claude/skills/litellm-stream/SKILL.md`, `planning/PLAN.md` §9, `.claude/CLAUDE.md`, `.planning/PROJECT.md`.
- **Verification:** Full backend suite re-run after the change — 145 passed, 0 failures (no test asserts on the literal `MODEL` string). Later, after Task 3's additions, the full suite stands at 151 passed.
- **Commit:** `6d442d2`

### Plan text superseded by this deviation (not re-litigated, not re-verified — already satisfied)

Per explicit continuation instructions, the plan's literal `<verify>` grep for the old model string (`grep -v "^\s*#" backend/app/llm/client.py | grep -c "openrouter/openai/gpt-oss-120b"`) and the `<human-check>` wording naming the old model are both superseded by the deviation above. The underlying intent — a live call proving `response_format` structured output actually works end-to-end — was verified against the new model per the paragraph above and is not re-verified by this agent. Likewise the plan's `<artifacts>` entry for `client.py` naming the old model string is superseded; the module now contains `openrouter/openrouter/free` instead, confirmed by `grep -c "openrouter/openrouter/free" backend/app/llm/client.py` → 1.

### Observed, Not Fixed (Out of Scope)

**1. `LLM_MOCK` literal-substring grep over-count.** The plan's acceptance criterion states `backend/app/llm/client.py` is the only file under `backend/app/` reading the `LLM_MOCK` env var, verified by `grep -rlE "LLM_MOCK" backend/app | wc -l` expecting exactly 1. Running this today returns 2 source files (`client.py` and `mock.py`), because `mock.py` contains the literal `[LLM_MOCK]` prefix text on its mock messages (an explicit plan requirement, "the mock's message text must be prefixed with `[LLM_MOCK]`") and its module docstring — neither of which reads the environment variable. `os.environ.get("LLM_MOCK", ...)` appears only once, in `client.py::is_mock_mode()`, confirmed by direct inspection. This is a pre-existing characteristic of Task 2's already-committed code (`8d6c74b`), not something Task 3 touched or introduced, and is out of this task's file scope (`backend/app/portfolio/service.py`, three test files). Flagged here for visibility rather than fixed.

**Total deviations:** 1 (pre-approved architectural change, fully documented and verified). **Impact:** None negative — the model switch was necessary to make the real (non-mock) path functional at all given the original model's account-level credit exhaustion, and was verified working end-to-end through the exact production code path before Task 3 began.

## Issues Encountered
None beyond the deviation above. All Task 3 acceptance criteria and verify commands pass; full backend suite (151 tests) is green with no regressions.

## User Setup Required
None - no external service configuration required beyond the pre-existing `OPENROUTER_API_KEY` in the project-root `.env` (already required by PLAN.md §5/§9).

## Next Phase Readiness

Plans 03-02 (chat persistence) and 03-03 (chat frontend) both depend on this plan and are ready to dispatch:
- `app/llm/actions.py`'s `AnnotatedTrade`/`AnnotatedWatchlistChange` field shapes (`outcome`, `reason`, `price`) are locked and stable for 03-02 to persist into `chat_messages.actions` and for 03-04's badge components to render.
- `GET /api/chat` (history hydration) is not yet implemented — 03-02's scope.
- `execute_trade()` is now safe for any direct (non-HTTP) caller, closing the last outstanding blocker from Phase 1 code review.

**Known follow-up, explicitly deferred (not silently lost):** the model-name propagation in this plan's deviation intentionally did NOT touch `.planning/phases/03-ai-chat-copilot/03-RESEARCH.md`, `03-VALIDATION.md`, `03-PATTERNS.md`, `COVERAGE.md`, `.planning/ROADMAP.md`, `.planning/REQUIREMENTS.md` (still names `openrouter/openai/gpt-oss-120b` in its CHAT-02 description), `.planning/codebase/*.md`, or `README.md` — those are historical/research artifacts out of scope for this dispatch per explicit continuation instructions. The orchestrator should decide separately whether/when to refresh those references to `openrouter/openrouter/free` for consistency.

## Self-Check: PASSED

---
*Phase: 03-ai-chat-copilot*
*Completed: 2026-09-18*
