---
phase: "3"
slug: "ai-chat-copilot"
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-09-17"
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.0+ with pytest-asyncio 0.24+ (`asyncio_mode = "auto"`) |
| **Config file** | `backend/pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `cd backend && uv run pytest tests/routes/test_chat.py tests/db/test_chat_messages.py tests/llm -x` |
| **Full suite command** | `cd backend && uv run pytest` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run the targeted `uv run pytest <new test file> -x`
- **After every plan wave:** Run `cd backend && uv run pytest`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

*Plans not yet created — task IDs are TBD until the planner runs. Requirement → test mapping below is what the planner must satisfy.*

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | CHAT-01 | — | `POST /api/chat` returns `{message, trades, watchlist_changes}` shape | route (TestClient) | `uv run pytest tests/routes/test_chat.py::test_post_chat_returns_structured_response -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | CHAT-02 | — | Structured output requested via `response_format`; mock path bypasses network | unit (LLM client, mocked) | `uv run pytest tests/llm/test_client.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | CHAT-03 | T-3-01 | LLM trade/watchlist change auto-executes through `execute_trade()` / `add_/remove_watchlist_ticker()` — no second execution path | integration (chat route + real service functions, isolated DB) | `uv run pytest tests/routes/test_chat.py::test_chat_trade_auto_executes -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | CHAT-04 | — | Each action annotated `executed`/`error`, separate from `message` | route | `uv run pytest tests/routes/test_chat.py::test_chat_action_annotated_on_insufficient_cash -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | CHAT-05 | — | `GET /api/chat` returns prior history | route | `uv run pytest tests/routes/test_chat.py::test_get_chat_hydrates_history -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | CHAT-06 | — | `LLM_MOCK=true` skips network, deterministic | unit + route | `uv run pytest tests/llm/test_mock.py tests/routes/test_chat.py::test_chat_with_llm_mock -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | Pitfall 2 fix | T-3-02 | `execute_trade()` rejects `quantity<=0` / invalid `side` directly, not just at the HTTP layer | unit (service) | `uv run pytest tests/portfolio/test_service.py::test_execute_trade_rejects_invalid_quantity_and_side -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | UI-08 | — | Chat panel hydrates history + renders inline success/error badges | manual/UAT (frontend test harness is Phase 6's TEST-04, not yet established) | manual UAT this phase | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/routes/test_chat.py` — stubs for CHAT-01, CHAT-03, CHAT-04, CHAT-05, CHAT-06
- [ ] `backend/tests/db/test_chat_messages.py` — extend existing schema-only file with read/write tests for `insert_message()`/`get_messages()`
- [ ] `backend/tests/llm/__init__.py`, `test_client.py`, `test_mock.py` — new package for the LiteLLM wrapper (mocked network) and `LLM_MOCK` deterministic branch
- [ ] `backend/tests/portfolio/test_service.py` — extend existing file with the `execute_trade()` quantity/side validation regression test
- [ ] Framework install: none — pytest/pytest-asyncio already configured project-wide; only `tests/llm/__init__.py` needs creating

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Chat panel hydrates history on mount and renders inline success/error badges separate from bubble text | UI-08 | Frontend component test harness (React Testing Library, TEST-04) is Phase 6's requirement, not yet established | Load app, send a chat message that triggers a trade, refresh page, confirm history persists and the trade renders as a separate badge from the message bubble |
| Real (non-mock) structured-output reliability of `openai/gpt-oss-120b` via OpenRouter for this project's exact schema | CHAT-02 | Cannot be tested without a live network call to OpenRouter using the real `OPENROUTER_API_KEY`; behavior is provider-routing-dependent and time-varying per RESEARCH.md Pitfall 1 | Once `OPENROUTER_API_KEY` is confirmed present and `LLM_MOCK=false`, send one real chat message and confirm the response parses into the structured schema without falling back to the message-only degradation path |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
