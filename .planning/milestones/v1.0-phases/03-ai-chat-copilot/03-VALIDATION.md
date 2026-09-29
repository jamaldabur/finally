---
phase: "3"
slug: "ai-chat-copilot"
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-09-17"
validated: "2026-09-21"
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

*All 8 plans executed (4 original + 4 gap-closure: 03-05 G-03-1/G-03-2, 03-06 G-03-3, 03-07 G-03-4, 03-08 G-03-5/G-03-6). Task IDs and statuses below reflect the actual committed test suite (214/214 backend tests passing; frontend typecheck/lint/build clean at time of validation). No new requirement IDs were introduced by the gap-closure plans — each closes a bug within an already-covered requirement (CHAT-01–06, UI-08), so the original per-requirement mapping below still holds; the gap-closure rows add regression depth, not new coverage surface.*

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| T2 (tracer) | 03-01 | 1 | CHAT-01 | — | `POST /api/chat` returns `{message, trades, watchlist_changes}` shape | route (TestClient) | `uv run pytest tests/routes/test_chat.py::test_post_chat_returns_structured_response -x` | ✅ | ✅ green |
| T2 (tracer) | 03-01 | 1 | CHAT-02 | — | Structured output requested via `response_format`; mock path bypasses network; defensive parse never raises | unit (LLM client, mocked) + one live-verified round trip | `uv run pytest tests/llm/test_client.py -x` | ✅ | ✅ green |
| T2 (tracer) | 03-01 | 1 | CHAT-03 | T-3-01 | LLM trade/watchlist change auto-executes through `execute_trade()` / `add_/remove_watchlist_ticker()` — no second execution path | integration (chat route + real service functions, isolated DB) | `uv run pytest tests/routes/test_chat.py::test_chat_trade_auto_executes -x` | ✅ | ✅ green |
| T2 (tracer) / 03-04 T1 | 03-01 / 03-04 | 1 / 3 | CHAT-04 | — | Each action annotated `executed`/`error`, separate from `message`; rendered as a per-action badge, verbatim reason, no raw-HTML injection | route + frontend static/automated_ui | `uv run pytest tests/routes/test_chat.py::test_chat_action_annotated_on_insufficient_cash -x` | ✅ | ✅ green |
| 03-02 T1 | 03-02 | 2 | CHAT-05 | — | `GET /api/chat` returns prior history, never an orphaned user message | route | `uv run pytest tests/routes/test_chat.py::test_get_chat_hydrates_history -x` | ✅ | ✅ green |
| T2 (tracer) / 03-02 T2 | 03-01 / 03-02 | 1 / 2 | CHAT-06 | — | `LLM_MOCK=true` skips network, deterministic, `[LLM_MOCK]`-prefixed | unit + route | `uv run pytest tests/llm/test_mock.py tests/routes/test_chat.py::test_chat_with_llm_mock -x` | ✅ | ✅ green |
| T3 | 03-01 | 1 | Pitfall 2 fix | T-3-02 | `execute_trade()` rejects `quantity<=0` / invalid `side` directly, not just at the HTTP layer | unit (service) | `uv run pytest tests/portfolio/test_service.py::test_execute_trade_rejects_invalid_quantity_and_side -x` | ✅ | ✅ green |
| 03-03 T1-2 / 03-04 T1-2 / 03-05 T1-2 / 03-07 T1-2 | 03-03 / 03-04 / 03-05 / 03-07 | 2 / 3 / 4 / 5 | UI-08 | T-03-15, T-03-16 | Chat panel hydrates history, renders inline success/error badges separate from bubble text; collapse rail rebuilt as one animating element with real contrast/hover/keyboard affordances (G-03-1/G-03-2); collapsed rail spans full column height with upright label (G-03-4) | frontend static grep + `automated_ui` + one deferred human click-through | `npm --prefix frontend run typecheck && lint && build` | ✅ | ✅ green (automated) — full click-through UAT deferred, see Manual-Only |
| 03-06 T1-2 | 03-06 | 3 | CHAT-02 (regression) | — | LLM client recovers a markdown-fenced-but-valid structured response, never renders raw/garbage model text as the assistant message; one-shot `FALLBACK_MODEL` failover on primary failure (G-03-3, a confirmed blocker) | unit (LLM client, mocked responses) | `uv run pytest tests/llm/test_client.py -x` | ✅ | ✅ green |
| 03-08 T1-2 | 03-08 | 4 | CHAT-03 (regression) | — | Every LLM-proposed trade/watchlist action normalized exactly once and reused for validation+execution+annotation (closes G-03-6, a confirmed live data-loss bug); sell-only negative-quantity sign recovery, negative buy still rejected (closes G-03-5) | unit (actions, schema) | `uv run pytest tests/llm/test_actions.py tests/llm/test_schema.py -x` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `backend/tests/routes/test_chat.py` — CHAT-01, CHAT-03, CHAT-04, CHAT-05, CHAT-06 (03-01/03-02)
- [x] `backend/tests/db/test_chat_messages.py` — `insert_message()`/`get_messages()` read/write + ordering/multibyte tests (03-02)
- [x] `backend/tests/llm/__init__.py`, `test_client.py`, `test_mock.py` — LiteLLM wrapper (mocked network) and `LLM_MOCK` deterministic branch (03-01/03-02)
- [x] `backend/tests/portfolio/test_service.py` — `execute_trade()` quantity/side validation regression test (03-01)
- [x] Framework install: none needed, as planned — pytest/pytest-asyncio already project-wide

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Status |
|----------|-------------|------------|--------|
| Real (non-mock) structured-output reliability via OpenRouter for this project's exact schema | CHAT-02 | Requires a live network call with a real `OPENROUTER_API_KEY`; behavior is provider-routing-dependent | ✅ **Done** — orchestrator ran the live round trip through the actual production code path (async `acompletion(..., response_format=ChatResponseSchema, stream=True)`) against `openrouter/openrouter/free` (the model in use after the 03-01 deviation); returned real structured JSON, parsed cleanly. Evidence recorded in 03-01-SUMMARY.md D2. |
| Full click-through UAT: buy/reject badges, panel collapse/expand (rebuilt in 03-05), full-height rail (fixed in 03-07), scroll-to-latest pill, AI-driven watchlist update reflecting without reload, reload restoring expanded state + full history with badges | UI-08 | Requires a human observing real browser interaction/animation — no frontend component test harness exists yet (Phase 6's TEST-04) | ✅ **Done** — round-3 end-of-phase UAT (`03-UAT.md`), test 1, passed |
| Live (non-mock) chat: fence-recovery/failover against the real OpenRouter router (G-03-3); sell-quantity sign recovery and watchlist add/remove fidelity against the real router (G-03-5/G-03-6) | CHAT-02, CHAT-03 | Requires a live `OPENROUTER_API_KEY` and observing several non-deterministic real completions | ✅ **Done** — round-3 end-of-phase UAT, tests 2-3, passed (initial reports traced to a stale backend process pre-dating the fixes, not a code defect — see `.planning/debug/sell-side-case-sensitivity.md`) |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** validated — 214/214 backend tests passing, frontend typecheck/lint/build clean, all 7 requirements (CHAT-01–06, UI-08, plus the Pitfall 2 execute_trade fix) have automated coverage. All manual-only items (full UI click-through, live-router sanity checks) have now completed end-of-phase UAT (round 3) with zero remaining open gaps.

---

## Validation Audit 2026-09-18

| Metric | Count |
|--------|-------|
| Requirements checked | 8 (CHAT-01–06, UI-08, Pitfall 2 fix) |
| Gaps found | 0 |
| Resolved | 0 (none needed — every SUMMARY.md already carried a populated `coverage:` block with passing verification) |
| Escalated to Manual-Only | 1 (UI-08 full click-through, deferred by design per `workflow.human_verify_mode: end-of-phase`) |
| Backend test suite | 170 passed, 0 failed (re-run by the validator, not just trusted from SUMMARYs) |
| Frontend | `typecheck`/`lint`/`build` all clean, `frontend/out/index.html` present |

---

## Validation Audit 2026-09-21

| Metric | Count |
|--------|-------|
| Requirements checked | 7 (CHAT-01–06, UI-08) — all previously COVERED, none newly introduced |
| Gaps found | 0 — the four gap-closure plans (03-05/03-06/03-07/03-08) fixed bugs within already-covered requirements; no new requirement surface to map |
| Resolved | 0 (no requirement-to-test gaps existed) |
| Manual-only items completed | 2 of 2 — full UI click-through (UI-08) and live-router sanity checks (CHAT-02/CHAT-03) both passed round-3 end-of-phase UAT; zero items remain deferred |
| Backend test suite | 214 passed, 0 failed (re-run directly, not trusted from SUMMARYs) |
| Frontend | `typecheck`/`lint` clean (re-run directly) |
