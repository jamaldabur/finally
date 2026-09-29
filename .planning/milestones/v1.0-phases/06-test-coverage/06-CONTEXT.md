# Phase 6: Test Coverage - Context

**Gathered:** 2026-09-27
**Status:** Ready for planning

<domain>
## Phase Boundary

The full trading loop — backend logic, frontend behavior, and the Docker-deployed app — is verified by automated tests. In scope: backend pytest coverage for trade execution/P&L edge cases (TEST-01), LLM structured-output parsing including malformed responses (TEST-02), and API route contracts (TEST-03); frontend unit tests for price-flash animation, watchlist CRUD, portfolio calculations, and chat rendering (TEST-04); a Playwright E2E suite in `test/` with its own `docker-compose.test.yml`, run with `LLM_MOCK=true` (TEST-05).

Out of scope for this phase: any change to backend business logic, frontend UI, or the LLM integration itself — this phase only adds test coverage for what Phases 1–5 already built; CI pipeline automation (not called for by REQUIREMENTS.md or PLAN.md — see D-12); cloud deployment (PLAN.md §11 stretch goal).

</domain>

<decisions>
## Implementation Decisions

The user deferred all gray-area choices to Claude ("whatever you want") — the same pattern as Phase 2 and Phase 5. The decisions below are Claude's calls, grounded in what actually exists in the codebase today (not assumed), made to be consistent with `planning/PLAN.md`. Downstream agents should treat them as locked unless they hit a concrete blocker.

### Backend coverage strategy
- **D-01:** Treat TEST-01/02/03 as an **audit-and-close-gaps** task, not a from-scratch suite. The backend already has 228 passing pytest tests across `backend/tests/{market,db,llm,portfolio,routes}/` and `test_main.py`, built incrementally during Phases 1–3 — including `insufficient cash/shares` edge cases (`tests/portfolio/test_service.py`, `tests/routes/test_chat.py`) and malformed-LLM-response handling (`tests/llm/test_client.py`, `tests/llm/test_schema.py`). — **Reversibility:** reversible — auditing first and finding no gaps costs nothing extra; the alternative (writing a parallel suite regardless of overlap) would waste effort re-testing already-proven behavior. — **Rationale:** REQUIREMENTS.md's TEST-01/02/03 wording maps closely to what's already tested; the planner's job is to diff the roadmap's exact success-criteria language against existing test names/assertions and produce a gap list, not to assume zero coverage exists.
- **D-02:** Any genuinely net-new backend test work this phase produces should follow the codebase's existing conventions exactly (see `code_context` below) — section-comment-organized Arrange-Act-Assert, `monkeypatch`/`tmp_path` for DB isolation, `respx` for HTTP mocking, stub classes over new mocking-library dependencies — rather than introducing a different testing style for "the Phase 6 tests."

### Frontend test framework
- **D-03:** Use **Vitest + React Testing Library**, not Jest. — **Reversibility:** costly — switching test runners later means rewriting every test file's assertion/mock API surface, though the RTL test bodies themselves would mostly survive. — **Rationale:** the frontend has zero test infrastructure today (no test script in `frontend/package.json`); Vitest is the natural fit for a Next.js App Router + TypeScript + ESM project (no Babel/`ts-jest` transform config needed, faster watch mode), and PROJECT.md's own Key Decisions log already named "Vitest/React Testing Library" as the deferred-to-Phase-6 choice.
- **D-04:** Mock the SSE price stream with a **hand-rolled `EventSource` stub class** (matching the backend's existing `StubSource`/`_FakeRequest` stub-class convention documented in `.planning/codebase/TESTING.md`), not a new mocking-library dependency (e.g. `mock-socket`). — **Reversibility:** reversible. — **Rationale:** jsdom has no native `EventSource`; a small stub that exposes `onmessage`/`onerror`/`onopen` and a way to fire synthetic events is sufficient for testing flash-trigger logic (`price !== previous_price`) and the connection-status state machine (D-06 from `02-CONTEXT.md`) without pulling in a library for a ~20-line need.
- **D-05:** Mock `fetch` calls (portfolio, watchlist, chat endpoints) per-test with `vi.fn()`/`vi.spyOn()` rather than a global HTTP-mocking library (e.g. MSW) — keeps parity with the backend's "prefer stub classes over heavy mocking frameworks" instinct and avoids a dependency for a single-origin, small-surface API.

### E2E fresh-start & fixtures
- **D-06:** `test/docker-compose.test.yml`'s app service mounts a **throwaway, per-run volume** for `db/` (an anonymous or explicitly-named test volume removed via `docker compose down -v` after the suite), never the developer's real `db/` bind mount. — **Reversibility:** reversible. — **Rationale:** PLAN.md's E2E "Fresh start" scenario (default watchlist, $10k balance, streaming prices) requires a genuinely empty, freshly-seeded SQLite file every run; reusing the dev DB would both violate that scenario and risk corrupting the user's actual simulated portfolio data.
- **D-07:** Mocked chat trade/watchlist E2E scenarios drive the chat input with strings matching `backend/app/llm/mock.py`'s existing regex contract — `_TRADE_PATTERN` (`\b(buy|sell)\s+(\d+(?:\.\d+)?)\s+([A-Za-z]{1,5})\b`, e.g. "buy 10 AAPL") and `_WATCHLIST_PATTERN` (`\b(add|remove)\s+([A-Za-z]{1,5})\b`, e.g. "add PYPL") — rather than inventing new trigger phrases. — **Rationale:** `mock.py`'s own docstring states this determinism contract exists specifically so "Phase 6's E2E suite" has "a real action to assert against"; it's already locked by `backend/tests/llm/test_mock.py` and must not be duplicated or reinvented.
- **D-08:** The Playwright container in `docker-compose.test.yml` waits on the app container's `GET /api/health` (the same endpoint the Dockerfile's own `HEALTHCHECK` — D-11 from `05-CONTEXT.md` — already targets) before running specs, rather than a fixed sleep. — **Reversibility:** reversible.

### CI / local-only scope
- **D-09:** No CI pipeline (e.g. GitHub Actions test workflow) is created in this phase. — **Reversibility:** reversible — adding one later is additive, no existing test needs to change. — **Rationale:** neither PLAN.md nor REQUIREMENTS.md's TEST-01 through TEST-05 mention CI; the roadmap's success criteria are phrased as "the suite passes," which is satisfied by local runnability. `.github/workflows/` currently contains only Claude Code's own automation (`claude.yml`, `claude-code-review.yml`), not a project test pipeline — adding one would be a new capability beyond this phase's scope, not an implementation detail of it.

### Claude's Discretion
Per the user's "whatever you want" response, all four gray areas above (backend audit-vs-rewrite strategy, frontend framework/mocking choices, E2E fixture/fresh-start semantics, CI scope) were left to Claude's judgment. Anything not explicitly pinned down here (e.g. exact Vitest config file structure, specific Playwright spec file organization beyond PLAN.md §12's listed scenarios, precise assertion wording) remains open for the researcher/planner to decide.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Product spec
- `planning/PLAN.md` §12 — Testing Strategy: backend/frontend unit test scope, E2E infrastructure (`test/docker-compose.test.yml`), key E2E scenarios, `LLM_MOCK=true` determinism requirement

### Requirements
- `.planning/REQUIREMENTS.md` — TEST-01 through TEST-05 (traceability table maps all five to Phase 6, currently Pending)

### Existing backend test suite (the audit baseline for D-01)
- `backend/tests/portfolio/test_service.py`, `backend/tests/routes/test_chat.py` — existing insufficient-cash/shares edge case coverage
- `backend/tests/llm/test_client.py`, `backend/tests/llm/test_schema.py` — existing malformed-LLM-response coverage
- `backend/tests/routes/test_portfolio.py`, `test_watchlist.py`, `test_chat.py` — existing API route contract tests
- `.planning/codebase/TESTING.md` — documents established backend testing conventions (stub classes, `monkeypatch`/`tmp_path` isolation, `respx`, Arrange-Act-Assert with section comments) — **NOTE: dated 2026-09-15, predates most of the 228 current tests; treat its conventions as still-current but its file inventory and coverage estimates as stale**

### E2E determinism contract (D-07)
- `backend/app/llm/mock.py` — `_TRADE_PATTERN`, `_WATCHLIST_PATTERN`, and the module docstring's explicit statement that this exists for Phase 6's E2E suite
- `backend/tests/llm/test_mock.py` — locks `build_mock_response()`'s determinism contract

### Prior phase decisions this phase must not duplicate/contradict
- `.planning/phases/02-core-trading-ui/02-CONTEXT.md` D-06 — connection-status dot state machine (green/yellow/red), relevant to frontend SSE tests
- `.planning/phases/05-docker-packaging-deployment/05-CONTEXT.md` D-11 — `GET /api/health` HEALTHCHECK target, relevant to E2E readiness-wait (D-08)
- `.planning/phases/05-docker-packaging-deployment/05-CONTEXT.md` D-10 — no top-level `docker-compose.yml` exists; `test/docker-compose.test.yml` is a separate, already-scoped file this decision doesn't affect

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/tests/conftest.py` and the per-module `monkeypatch`/`tmp_path` isolation pattern — any new backend test follows this, no new fixture infrastructure needed.
- `backend/app/llm/mock.py`'s `_TRADE_PATTERN`/`_WATCHLIST_PATTERN` — ready-made, already-tested E2E trigger phrases (D-07).
- `backend/app/routes/health.py`'s `GET /api/health` — already used by the Dockerfile `HEALTHCHECK`; reusable as the E2E readiness-wait target (D-08).

### Established Patterns
- Backend: pytest-asyncio `asyncio_mode = "auto"`, stub classes (`StubSource`, `_FakeRequest`, `StubRng`) preferred over mocking libraries beyond `respx` for HTTP, `pytest.approx()` for float comparisons, deterministic seeds for the simulator.
- Frontend (from Phase 2–4 STATE.md decisions): `EventSource`-based SSE consumed via a shared context/provider; price-flash logic compares against a per-cell `useRef` of the last-rendered price, never the SSE tick's `previous_price` field directly — any frontend test of flash behavior must exercise this same comparison, not assert on `previous_price`.

### Integration Points
- `frontend/package.json` has no `test` script yet — Phase 6 adds Vitest config, a test script, and the first test files from a clean slate.
- `test/` currently contains only stray, untracked `node_modules`/`test-results` (no `package.json`, nothing git-tracked) — safe to treat as an empty starting point; nothing here is prior-phase work to preserve.
- `.github/workflows/claude.yml` / `claude-code-review.yml` exist but are Claude Code's own automation, not a project test pipeline — irrelevant to D-09.

</code_context>

<specifics>
## Specific Ideas

No specific requirements beyond what's captured in Implementation Decisions above — the user deferred all Phase 6 gray areas to Claude's judgment, consistent with Phase 2 and Phase 5's precedent.

</specifics>

<deferred>
## Deferred Ideas

None — no scope-creep suggestions came up during this discussion; the user deferred implementation choices rather than proposing new capabilities.

</deferred>

---

*Phase: 06-test-coverage*
*Context gathered: 2026-09-27*
