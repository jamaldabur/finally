---
phase: 03-ai-chat-copilot
plan: 02
subsystem: ai-chat-backend
tags: [sqlite, persistence, chat-history, prompt-bounding, litellm, mock-determinism]
requires:
  - phase: 03-ai-chat-copilot
    provides: "03-01: POST /api/chat end-to-end loop (LLM/mock -> structured parse -> execute_llm_actions -> ChatResponse), app/llm/client.py's build_messages()/get_chat_response(), app/llm/mock.py's build_mock_response()"
provides:
  - "insert_message()/get_messages() read/write helpers on app/db/chat_messages.py, ordered by rowid so same-request rows keep insertion order regardless of tied created_at timestamps"
  - "GET /api/chat — history hydration endpoint returning annotated trades/watchlist_changes per assistant message"
  - "POST /api/chat persists both turns of every exchange, after execute_llm_actions() returns, user-then-assistant"
  - "PROMPT_HISTORY_LIMIT=20 enforced inside build_messages() — the prompt can never grow unbounded regardless of session length"
  - "Regression-test lock on build_mock_response()'s determinism and [LLM_MOCK] labelling contract"
affects: [03-03-chat-frontend, 03-04-chat-ui-badges]
actuals:
  tokens: 6393
  tasks: 2
  commits: 4
tech-stack:
  added: []
  patterns:
    - "rowid-ordered history reads: ORDER BY rowid DESC LIMIT ? then reversed in Python, because two rows written inside one request can carry identical ISO created_at strings"
    - "Persist-after-execute, user-before-assistant: both insert_message() calls happen only after execute_llm_actions() returns, and in that order, so a concurrent GET /api/chat can never observe an orphaned user message"
    - "Actions-column degrade-not-500: _actions_from_json() wraps parse+validate in try/except(JSONDecodeError, ValidationError, TypeError, KeyError), returning ([], []) for any malformed row instead of failing the whole history endpoint"
key-files:
  created:
    - backend/tests/llm/test_mock.py
  modified:
    - backend/app/db/chat_messages.py
    - backend/app/routes/chat.py
    - backend/app/llm/client.py
    - backend/app/llm/mock.py
    - backend/tests/db/test_chat_messages.py
    - backend/tests/routes/test_chat.py
key-decisions:
  - "PROMPT_HISTORY_LIMIT = 20, GET /api/chat limit = 50 (03-RESEARCH.md A2, per plan's planner_assumptions) — two independent constants, trivially changed, decided here since PLAN.md specifies no pruning policy for chat_messages"
  - "History ordering keyed on SQLite rowid, not created_at — created_at strings from two rows written in one request can be identical, which would make user/assistant ordering arbitrary exactly where it matters most"
patterns-established:
  - "Thin persistence layer mirrors app/db/trades.py exactly: frozen dataclass, _insert_*_sync/_get_*_sync using `with _connect() as conn:`, then one-line async wrappers via asyncio.to_thread — chat_messages.py now matches this shape for its two new functions"
requirements-completed: [CHAT-05, CHAT-01, CHAT-06]
coverage:
  - id: D1
    description: "GET /api/chat returns prior conversation history — every stored user and assistant message, with each assistant message's annotated trades and watchlist changes"
    requirement: CHAT-05
    verification:
      - kind: unit
        ref: "backend/tests/routes/test_chat.py#test_get_chat_on_empty_database_returns_empty_history"
        status: pass
      - kind: unit
        ref: "backend/tests/routes/test_chat.py#test_get_chat_hydrates_history"
        status: pass
      - kind: unit
        ref: "backend/tests/routes/test_chat.py#test_get_chat_carries_executed_trade_outcome"
        status: pass
    human_judgment: false
  - id: D2
    description: "POST /api/chat persists user then assistant message only after execute_llm_actions() has returned, so GET /api/chat can never return an orphaned user message"
    requirement: CHAT-05
    verification:
      - kind: unit
        ref: "backend/tests/routes/test_chat.py#test_get_chat_never_returns_orphan_user_message"
        status: pass
      - kind: static
        ref: "grep -v '^\\s*#' backend/app/routes/chat.py | grep -c 'insert_message(' -> 2"
        status: pass
    human_judgment: false
  - id: D3
    description: "Multi-byte content (emoji, CJK) round-trips through chat_messages with identical code points; history rows order by rowid, not created_at, under tied timestamps"
    requirement: CHAT-01
    verification:
      - kind: unit
        ref: "backend/tests/db/test_chat_messages.py#test_insert_message_preserves_multibyte_characters"
        status: pass
      - kind: unit
        ref: "backend/tests/db/test_chat_messages.py#test_get_messages_orders_by_rowid_not_created_at"
        status: pass
      - kind: unit
        ref: "backend/tests/db/test_chat_messages.py#test_get_messages_limit_returns_most_recent_oldest_first"
        status: pass
    human_judgment: false
  - id: D4
    description: "A NULL/empty/unparseable actions value degrades to empty trades/watchlist_changes for that one message instead of a 500"
    verification:
      - kind: unit
        ref: "backend/tests/routes/test_chat.py#test_get_chat_degrades_unparseable_actions_to_empty_lists"
        status: pass
    human_judgment: false
  - id: D5
    description: "build_messages() caps history at PROMPT_HISTORY_LIMIT (20) regardless of how many rows exist, and real history (not an empty list) reaches the model"
    verification:
      - kind: unit
        ref: "backend/tests/routes/test_chat.py#test_build_messages_caps_history_at_prompt_history_limit"
        status: pass
      - kind: unit
        ref: "backend/tests/routes/test_chat.py#test_chat_history_reaches_second_prompt"
        status: pass
      - kind: static
        ref: "grep -v '^\\s*#' backend/app/llm/client.py | grep -c PROMPT_HISTORY_LIMIT -> 2; grep -v '^\\s*#' backend/app/routes/chat.py | grep -c 'get_messages(' -> 2"
        status: pass
    human_judgment: false
  - id: D6
    description: "LLM_MOCK output is provably deterministic, visibly labelled [LLM_MOCK], and covers buy/sell/add/remove parsing"
    requirement: CHAT-06
    verification:
      - kind: unit
        ref: "backend/tests/llm/test_mock.py#test_build_mock_response_is_deterministic"
        status: pass
      - kind: unit
        ref: "backend/tests/llm/test_mock.py#test_build_mock_response_always_prefixed"
        status: pass
      - kind: unit
        ref: "backend/tests/llm/test_mock.py#test_build_mock_response_requires_watchlist_keyword"
        status: pass
      - kind: static
        ref: "grep -qE '^\\s*(import|from)\\s+(random|time|datetime|os)\\b' backend/app/llm/mock.py -> no match"
        status: pass
    human_judgment: false
duration: ~35min
completed: 2026-09-18
status: complete
---

# Phase 03 Plan 02: Chat Persistence & Prompt Bounding Summary

**`chat_messages` gains a full read/write layer ordered by SQLite `rowid` (not the tie-prone `created_at` string), `GET /api/chat` hydrates the panel with annotated actions, and `build_messages()` now caps the LLM prompt at 20 recent messages regardless of session length.**

## Performance
- **Duration:** ~35min
- **Started:** 2026-09-18
- **Completed:** 2026-09-18
- **Tasks:** 2/2 completed
- **Files modified:** 7 (1 created, 6 modified)

## Accomplishments
- `chat_messages.py` gained `ChatMessage`, `insert_message()`, `get_messages()` — mirroring `trades.py`'s exact shape (frozen dataclass, sync helpers, one-line async wrappers via `asyncio.to_thread`).
- History is ordered by `rowid DESC LIMIT ?` then reversed in Python, not by `created_at`, because two rows written inside one request can carry identical ISO timestamps — verified by a test that inserts three same-timestamp rows directly and confirms they still come back in insertion order.
- `POST /api/chat` now persists both turns of every exchange — user then assistant — only after `execute_llm_actions()` returns, guaranteeing a concurrent `GET /api/chat` can never observe a user message without its assistant reply.
- `GET /api/chat` added: hydrates the full history with each assistant message's annotated `trades`/`watchlist_changes`, degrading a malformed `actions` value to empty lists (`T-03-07`) rather than a 500.
- `PROMPT_HISTORY_LIMIT = 20` applied inside `build_messages()` so no call site can bypass it; `POST /api/chat` now reads real history via `get_messages()` instead of the tracer's hardcoded empty list.
- `build_mock_response()`'s determinism, `[LLM_MOCK]` labelling, and buy/sell/add/remove matcher coverage locked with 8 new regression tests in a new `tests/llm/test_mock.py` file.
- Full backend suite: 170 passed, 0 failures, 0 regressions — up from 151 at the end of 03-01, plus 19 new tests this plan (9 in Task 1: 4 in `test_chat_messages.py` + 5 in `test_chat.py`; 10 in Task 2: 8 in the new `test_mock.py` + 2 in `test_chat.py`).

## Task Commits
1. **Task 1 RED: failing tests for chat_messages persistence and GET /api/chat** - `e7c7f84`
2. **Task 1 GREEN: persist chat turns and serve history from GET /api/chat** - `66205fb`
3. **Task 2 RED: mock determinism tests + failing prompt-history-cap tests** - `16c6704`
4. **Task 2 GREEN: bound the LLM prompt to 20 recent messages and wire real history** - `d99e24f`

No REFACTOR commits were needed for either task — the GREEN implementations followed the established `trades.py`/`watchlist.py` patterns directly with no cleanup pass required.

## Files Created/Modified
- `backend/app/db/chat_messages.py` - Added `ChatMessage` dataclass, `_insert_message_sync`/`_get_messages_sync`, `insert_message()`/`get_messages()`
- `backend/app/routes/chat.py` - Added `ChatMessageResponse`/`ChatHistoryResponse`, `_actions_to_json()`/`_actions_from_json()`, `GET /api/chat`; wired persistence and real history reads into `POST /api/chat`
- `backend/app/llm/client.py` - Added `PROMPT_HISTORY_LIMIT = 20`, applied inside `build_messages()`
- `backend/app/llm/mock.py` - Docstring locks the determinism contract explicitly (no functional change — behavior already correct from 03-01)
- `backend/tests/db/test_chat_messages.py` - 4 new tests (insert/read round trip, rowid ordering, limit, multibyte content)
- `backend/tests/routes/test_chat.py` - 7 new tests (empty history, hydration, executed-trade annotation, malformed-actions degradation, orphan guard, prompt cap, cross-request history reach)
- `backend/tests/llm/test_mock.py` - New file, 8 regression tests for `build_mock_response()`

## Decisions Made
- **`PROMPT_HISTORY_LIMIT = 20`, `GET /api/chat` limit = 50** — both single constants per the plan's `planner_assumptions`; no pruning policy exists in PLAN.md for `chat_messages`, so this plan decides it explicitly rather than leaving it implicit.
- **`rowid` over `created_at` for ordering** — `created_at` strings from two rows written in one request (the user turn and its assistant reply) can be identical; `rowid` is monotonic per insert and needs no schema change.
- **History cap enforced inside `build_messages()`, not at the call site** — `app/routes/chat.py` cannot forget or bypass the cap; the constant and its enforcement live in one place.

## Deviations from Plan

None — plan executed exactly as written.

One note worth flagging explicitly rather than silently: Task 2's `build_mock_response()` behavior (buy/sell parsing, watchlist add/remove requiring the literal word "watchlist", the `[LLM_MOCK]` prefix on every branch) was already fully correct from 03-01 — verified by hand before writing `tests/llm/test_mock.py`, and all 8 tests passed immediately with no RED phase for that file (workflow.tdd_mode is `false` project-wide, so this is not a gate violation; it is documented here as the honest state rather than staging an artificial failure). The genuinely new behavior in Task 2 — `PROMPT_HISTORY_LIMIT` and wiring real history into the POST handler — did go through a real RED (import/assertion failures) → GREEN cycle, committed as `16c6704` → `d99e24f`.

## TDD Gate Compliance

Both tasks carry `tdd="true"`. `workflow.tdd_mode` is `false` project-wide (per `.planning/config.json`), so the orchestrator-level RED-commit gate was not enforced, but the RED→GREEN discipline was followed for both tasks' genuinely-new behavior:

- **Task 1** (`chat_messages.py` read/write + `GET /api/chat`): full RED (`e7c7f84`, 9 new tests failing with `AttributeError`/`405`/`KeyError` — all directly tied to the missing implementation, no fixture/import collection errors) → full GREEN (`66205fb`, all 18 tests in scope passing, 160 total passing with no regressions).
- **Task 2** (`PROMPT_HISTORY_LIMIT` + history wiring): the two genuinely-new-behavior tests went through real RED (`16c6704` — `ImportError` on `PROMPT_HISTORY_LIMIT` inside the test body for one, an `assert False` on empty history for the other, both isolated to their own test functions, not collection-time failures) → GREEN (`d99e24f`, all passing). The 8 `test_mock.py` tests characterize pre-existing correct behavior from 03-01 and passed on first run — flagged above as an intentional, documented departure from strict RED-GREEN for that one file, not a violation of the gate's intent (there is no unimplemented behavior being masked).

No missing RED commits, no INVALID_RED states, no unexpected GREEN on the tests that did carry a RED phase.

## Issues Encountered
None. All acceptance criteria and `<verify>` commands from the plan pass; full backend suite (170 tests) is green.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness

Plan 03-03 (frontend chat UI, dispatched independently in this wave) can now build against a stable `GET /api/chat` contract:
- `ChatHistoryResponse.messages[]` — each item carries `id`, `role`, `content`, `trades`, `watchlist_changes`, `created_at`, matching `POST /api/chat`'s `ChatResponse` shape for the action lists so the frontend can reuse one badge-rendering component for both the live response and hydrated history.
- A page refresh now restores the full conversation — the single most visible "does this feel broken" risk PLAN.md flags for a chat assistant is closed.
- The prompt is bounded at 20 messages regardless of session length — Phase 6's E2E suite (`LLM_MOCK=true`) can run long conversational scenarios without per-request cost growing unbounded.

## Self-Check: PASSED

---
*Phase: 03-ai-chat-copilot*
*Completed: 2026-09-18*
