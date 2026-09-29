# Phase 6: Test Coverage - Research

**Researched:** 2026-09-27
**Domain:** Backend test-coverage audit (pytest), frontend unit testing (Vitest/RTL bootstrap), browser E2E testing (Playwright + Docker Compose)
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Backend coverage strategy**
- **D-01:** Treat TEST-01/02/03 as an **audit-and-close-gaps** task, not a from-scratch suite. The backend already has 228 passing pytest tests across `backend/tests/{market,db,llm,portfolio,routes}/` and `test_main.py`, built incrementally during Phases 1–3 — including `insufficient cash/shares` edge cases (`tests/portfolio/test_service.py`, `tests/routes/test_chat.py`) and malformed-LLM-response handling (`tests/llm/test_client.py`, `tests/llm/test_schema.py`). The planner's job is to diff the roadmap's exact success-criteria language against existing test names/assertions and produce a gap list, not to assume zero coverage exists.
- **D-02:** Any genuinely net-new backend test work this phase produces should follow the codebase's existing conventions exactly — section-comment-organized Arrange-Act-Assert, `monkeypatch`/`tmp_path` for DB isolation, `respx` for HTTP mocking, stub classes over new mocking-library dependencies.

**Frontend test framework**
- **D-03:** Use **Vitest + React Testing Library**, not Jest.
- **D-04:** Mock the SSE price stream with a **hand-rolled `EventSource` stub class** (matching the backend's `StubSource`/`_FakeRequest` stub-class convention), not a new mocking-library dependency (e.g. `mock-socket`).
- **D-05:** Mock `fetch` calls (portfolio, watchlist, chat endpoints) per-test with `vi.fn()`/`vi.spyOn()` rather than a global HTTP-mocking library (e.g. MSW).

**E2E fresh-start & fixtures**
- **D-06:** `test/docker-compose.test.yml`'s app service mounts a **throwaway, per-run volume** for `db/`, never the developer's real `db/` bind mount.
- **D-07:** Mocked chat trade/watchlist E2E scenarios drive the chat input with strings matching `backend/app/llm/mock.py`'s existing regex contract — `_TRADE_PATTERN` and `_WATCHLIST_PATTERN` — rather than inventing new trigger phrases.
- **D-08:** The Playwright container in `docker-compose.test.yml` waits on the app container's `GET /api/health` before running specs, rather than a fixed sleep.

**CI / local-only scope**
- **D-09:** No CI pipeline (e.g. GitHub Actions test workflow) is created in this phase.

### Claude's Discretion

Per the user's "whatever you want" response, all four gray areas above (backend audit-vs-rewrite strategy, frontend framework/mocking choices, E2E fixture/fresh-start semantics, CI scope) were left to Claude's judgment. Anything not explicitly pinned down (exact Vitest config file structure, specific Playwright spec file organization beyond PLAN.md §12's listed scenarios, precise assertion wording) remains open for the planner to decide.

### Deferred Ideas (OUT OF SCOPE)

None — no scope-creep suggestions came up during discussion; the user deferred implementation choices rather than proposing new capabilities. Any change to backend business logic, frontend UI, or the LLM integration itself is out of scope for this phase; CI pipeline automation and cloud deployment are also out of scope (see D-09 and PLAN.md §11).

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TEST-01 | Backend unit tests cover trade execution logic, P&L calculations, and edge cases (insufficient cash/shares) | Audited against actual test bodies in `backend/tests/portfolio/test_service.py` and `backend/tests/routes/test_portfolio.py` — see "Backend Coverage Audit" below. Finding: **already fully covered**, no gap. |
| TEST-02 | Backend unit tests cover LLM structured-output parsing, including malformed responses | Audited against `backend/tests/llm/test_client.py` and `test_schema.py` — see "Backend Coverage Audit" below. Finding: **already fully covered, and unusually thorough** (fenced-JSON recovery, non-ASCII, model failover, auth vs. rate-limit distinction), no gap. |
| TEST-03 | Backend unit tests cover API route status codes and response shapes for portfolio/watchlist/chat endpoints | Audited against `test_portfolio.py`, `test_watchlist.py`, `test_chat.py` — see "Backend Coverage Audit" below. Finding: **one concrete gap** — no test exercises `POST /api/watchlist`'s Pydantic `min_length=1` validation (empty-string ticker → 422). |
| TEST-04 | Frontend unit tests cover price flash animation triggering, watchlist CRUD, portfolio display calculations, and chat rendering/loading state | Vitest + RTL setup verified against the project's actual Next.js 16 / React 19 versions (official Next.js docs, bundled locally in `node_modules/next/dist/docs/`). Component-level contracts read directly from `PriceCell.tsx`, `priceStore.tsx`, `portfolioStore.tsx`, `WatchlistPanel.tsx`, `chatStore.tsx`, `ActionBadge.tsx`. See "Architecture Patterns" and "Code Examples". |
| TEST-05 | Playwright E2E suite (in `test/`, own `docker-compose.test.yml`, `LLM_MOCK=true`) covers fresh start, watchlist add/remove, buy, sell, visualization rendering, mocked chat trade execution, and SSE reconnection | Playwright-in-Docker pattern verified against official Playwright docs (image tag convention, required flags) and the project's existing `Dockerfile` HEALTHCHECK (D-08 reuse target). Mock-trigger phrase contract re-verified directly against `backend/app/llm/mock.py` source and its test — see "Common Pitfalls" for a correction to D-07's own example phrase. |

</phase_requirements>

## Summary

This phase has two very different halves. The **backend half (TEST-01/02/03) is nearly a non-event**: reading the actual test bodies (not just file names) in `backend/tests/portfolio/test_service.py`, `backend/tests/routes/test_portfolio.py`, `backend/tests/llm/test_client.py`, `backend/tests/llm/test_schema.py`, `backend/tests/routes/test_watchlist.py`, and `backend/tests/routes/test_chat.py` confirms the 228-test suite already exercises every scenario TEST-01/02/03 name in their literal wording — weighted-average cost, insufficient cash/shares (both at the service layer and the HTTP layer), unrealized P&L (gain and loss), unpriced-position mark-to-cost, quantity/side validation, malformed/fenced/non-JSON LLM responses, model failover and auth-vs-rate-limit handling, and full status-code/response-shape coverage for portfolio/watchlist/chat routes including 400/422 paths. The one genuine, source-verified gap found is narrow: `POST /api/watchlist`'s `Field(min_length=1)` constraint on `ticker` has no test asserting the resulting 422. The planner should scope TEST-01/02/03 as "add ~1 test, verify the rest already passes" rather than any new suite.

The **frontend and E2E halves (TEST-04/05) are real build-out work** from a genuinely empty starting point (no test script in `frontend/package.json`, no tracked files in `test/`). The official Next.js docs bundled in this exact `node_modules/next` install (`node_modules/next/dist/docs/01-app/02-guides/testing/vitest.md`) give the canonical Vitest setup for this Next.js version, and registry checks confirm `@testing-library/react` (latest 16.3.3) natively supports React 19 (`peerDependencies: react: "^18.0.0 || ^19.0.0"`) — no shims needed. jsdom (the recommended Vitest test environment) was directly verified in this session to have **no** `EventSource` implementation (`typeof window.EventSource === "undefined"` on jsdom 30.1.1), which confirms D-04's hand-rolled stub decision is not optional polish — it is required for any SSE-touching test to run at all. For E2E, official Playwright docs give the exact Docker image tag convention (`mcr.microsoft.com/playwright:v<version>-noble` matching the installed `@playwright/test` version) and required container flags (`--init`, `--ipc=host`); the existing `Dockerfile`'s `HEALTHCHECK` target (`GET /api/health`) is directly reusable as the Compose `depends_on: condition: service_healthy` gate per D-08, avoiding a second health-check implementation.

One correction to CONTEXT.md's own account of D-07 is important enough to flag here: `backend/app/llm/mock.py`'s watchlist trigger is **not** just `_WATCHLIST_PATTERN` alone — it first requires the literal substring `"watchlist"` (case-insensitive) anywhere in the message, and only then applies the add/remove regex. A message like `"add PYPL"` alone (CONTEXT.md's own example) produces **no** watchlist change under the real code (locked by `tests/llm/test_mock.py::test_build_mock_response_requires_watchlist_keyword`) — the E2E chat input for a watchlist scenario must read something like `"add PYPL to my watchlist"`.

**Primary recommendation:** Scope Phase 6 as roughly 90% frontend/E2E build-out and 10% backend gap-closure. Bootstrap Vitest per the official Next.js guide (jsdom environment, `vite-tsconfig-paths` for the project's `@/` import alias), write a ~20-line `EventSource` stub matching the backend's stub-class convention, mock `fetch` per-test via `vi.spyOn(global, "fetch")` against the exact wire shapes in `frontend/lib/types.ts`, and build the Playwright E2E suite as a two-service Compose file (app + test runner) gated on the existing `/api/health` HEALTHCHECK, using `"add PYPL to my watchlist"` / `"buy 5 CSCO"`-style phrases that match `mock.py`'s real trigger contract.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Backend unit test audit/gap-closure (TEST-01/02/03) | API / Backend | — | Tests exercise `app/portfolio/service.py`, `app/llm/client.py`, `app/routes/*` directly; no new architectural surface, purely a coverage audit of existing backend code |
| Frontend unit tests (TEST-04) | Browser / Client | — | Vitest + RTL run against React components (`PriceCell`, `WatchlistPanel`, `ActionBadge`, stores) in a simulated DOM (jsdom); no server involved |
| SSE/EventSource test doubles | Browser / Client | — | `EventSource` is a browser API; jsdom lacks it entirely (verified this session) so the stub lives in test-support code, not the app or API layer |
| E2E test orchestration (TEST-05) | CDN / Static (test infra) | API / Backend, Browser / Client | Playwright drives a real browser against the full Docker-built app (static frontend + FastAPI) — the only test tier that spans all layers in one run |
| E2E fixture/DB lifecycle (throwaway volume, D-06) | Database / Storage | — | A per-run Docker volume for `db/finally.db` is a storage-tier concern, isolated from the app's own runtime logic |
| Mocked-LLM E2E trigger contract (D-07) | API / Backend | Browser / Client | The regex contract lives in `app/llm/mock.py` (backend); the E2E test (browser tier) must conform to it, not invent its own phrasing |

## Standard Stack

### Core (Frontend Unit Testing — TEST-04)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|---------------|
| `vitest` | 5.0.2 | Test runner, assertions, watch mode, coverage | Native ESM/Vite integration — no Babel/`ts-jest` transform layer needed for a Next.js App Router + TypeScript project; this is the exact tool the official Next.js Vitest guide recommends for this Next.js major version `[CITED: node_modules/next/dist/docs/01-app/02-guides/testing/vitest.md]` |
| `@vitejs/plugin-react` | 6.1.1 | JSX/Fast Refresh transform for Vite/Vitest | Required by the official guide's `vitest.config` for any React component test `[CITED: node_modules/next/dist/docs/01-app/02-guides/testing/vitest.md]` |
| `jsdom` | 30.1.1 | Simulated browser DOM environment for Vitest | The official guide's `test.environment: 'jsdom'` setting; confirmed via direct runtime check this session that it has no `EventSource` (see Pitfalls) `[CITED: node_modules/next/dist/docs/01-app/02-guides/testing/vitest.md]`, `[VERIFIED: jsdom 30.1.1 runtime check, this session]` |
| `@testing-library/react` | 16.3.3 | Component rendering + query API for tests | Peer deps confirmed to support React 19 natively (`react: "^18.0.0 \|\| ^19.0.0"`) — no compatibility shim needed for this project's React 19.3.0 `[VERIFIED: npm registry `npm view @testing-library/react peerDependencies`, this session]` |
| `@testing-library/dom` | 10.4.2 | Underlying DOM query engine RTL depends on | Required peer of `@testing-library/react` (`^10.0.0`) per the official guide's install list `[CITED: node_modules/next/dist/docs/01-app/02-guides/testing/vitest.md]` |
| `vite-tsconfig-paths` | 6.1.1 | Resolves the project's `@/*` TypeScript path alias inside Vitest | The codebase imports via `@/lib/api`, `@/lib/types`, etc. (confirmed in `WatchlistPanel.tsx`, `ActionBadge.tsx`); Vitest does not read `tsconfig.json` path mappings without this plugin — the official guide lists it explicitly for the TypeScript case `[CITED: node_modules/next/dist/docs/01-app/02-guides/testing/vitest.md]`, `[VERIFIED: frontend/components/watchlist/WatchlistPanel.tsx:25 imports `@/lib/api`]` |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `@testing-library/jest-dom` | 7.0.1 | Extra DOM assertion matchers (`toBeInTheDocument()`, etc.) | Optional but conventional with RTL; not a mocking library, so it doesn't conflict with D-02/D-05's "no new mocking dependency" instinct — add a `vitest.setup.ts` importing it if the planner wants nicer assertions |
| `@playwright/test` | 1.63.0 | E2E test runner + browser automation (TEST-05) | Already present as stray, untracked install under `test/node_modules/@playwright/test` `[VERIFIED: C:\Users\jamal\projects\finally\test\node_modules\@playwright\test present, this session — no committed package.json]`; the phase should commit a real `test/package.json` pinning this version |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Hand-rolled `EventSource` stub (D-04) | `mock-socket`, `eventsourcemock` (npm) | A library adds a dependency for a ~20-line need and doesn't match the backend's own established stub-class convention (`StubSource`, `_FakeRequest`) — rejected per D-04, not researched further |
| Per-test `vi.fn()`/`vi.spyOn()` fetch mocking (D-05) | MSW (Mock Service Worker) | MSW is the modern default for larger apps with many endpoints and shared handlers, but this app's entire API surface funnels through one module (`frontend/lib/api.ts`) — spying on `global.fetch` per test is simpler and matches D-02's backend-mirroring "prefer stubs over frameworks" instinct |
| Vitest | Jest | Rejected in CONTEXT.md D-03 — Jest would need `ts-jest`/Babel config for this ESM/App-Router project; not researched further here |

**Installation:**
```bash
cd frontend
npm install -D vitest @vitejs/plugin-react jsdom @testing-library/react @testing-library/dom @testing-library/jest-dom vite-tsconfig-paths

cd ../test
npm init -y
npm install -D @playwright/test
npx playwright install --with-deps chromium   # browser binaries for local runs outside Docker
```

**Version verification:** All frontend test-tooling versions above were checked live against the npm registry this session (`npm view <pkg> version`) on 2026-09-27 — see per-row citations. Backend test dependencies (`pytest`, `pytest-asyncio`, `respx`) are already pinned in `backend/pyproject.toml` and need no new installation for this phase.

## Package Legitimacy Audit

| Package | Registry | Age signal | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-------------|-----------|-------------|---------|-------------|
| `vitest` | npm | Latest version published 2026-09-25 | 120.5M/wk | github.com/vitest-dev/vitest | SUS (`too-new`) | **Approved — heuristic false positive.** "Too-new" fired on the latest *release date*, not package age; 120M weekly downloads and an official, long-established repo make this a routine active-maintenance release, not a slopsquat risk. No `checkpoint:human-verify` needed. |
| `@vitejs/plugin-react` | npm | Published 2026-08-28 | 105.3M/wk | github.com/vitejs/vite-plugin-react | OK | Approved |
| `jsdom` | npm | Latest version published 2026-09-22 | 116.9M/wk | github.com/jsdom/jsdom | SUS (`too-new`) | **Approved — heuristic false positive**, same reasoning as `vitest`. |
| `@testing-library/react` | npm | Published 2026-08-27 | 68.7M/wk | github.com/testing-library/react-testing-library | OK | Approved |
| `@testing-library/dom` | npm | Latest version published 2026-09-13 | 84.5M/wk | github.com/testing-library/dom-testing-library | SUS (`too-new`) | **Approved — heuristic false positive**, same reasoning. |
| `@testing-library/jest-dom` | npm | Published 2026-08-09 | 74.3M/wk | github.com/testing-library/jest-dom | OK | Approved |
| `vite-tsconfig-paths` | npm | Published 2026-02-11 | 34.3M/wk | github.com/aleclarson/vite-tsconfig-paths | OK | Approved |
| `@playwright/test` | npm | Latest version published 2026-09-04 | 72.1M/wk | github.com/microsoft/playwright | SUS (`too-new`) | **Approved — heuristic false positive**, same reasoning; also already present in `test/node_modules` from a prior untracked install. |

**Packages removed due to `[SLOP]` verdict:** none.
**Packages flagged as suspicious `[SUS]`:** `vitest`, `jsdom`, `@testing-library/dom`, `@playwright/test` — all four fired the legitimacy checker's `too-new` signal purely because their *most recent version* was published recently (all within the last ~3 weeks of research date), which is normal cadence for actively-maintained, 60M+/week-download, officially-repo'd packages, not a hallmark of a new/hallucinated package. Cross-checked each against its GitHub source repo and download volume before approving; no `checkpoint:human-verify` gate is recommended for these four specifically, but the planner may still add one if a stricter posture is preferred — the underlying `package-legitimacy check` seam has no age-of-package (vs. age-of-latest-version) distinction today.

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────── Backend pytest (unaffected tier) ───────────────────────────┐
│  backend/tests/{portfolio,llm,routes,db,market}/*.py  --pytest-->  app/*  (existing)     │
│  Gap-closure only: +1 test for POST /api/watchlist empty-ticker 422                      │
└────────────────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────── Frontend Vitest unit tests (new, TEST-04) ───────────────────┐
│  frontend/**/*.test.tsx                                                                  │
│    │                                                                                      │
│    ├─> render(<Component/>) via @testing-library/react, jsdom environment                │
│    │      - PriceCell.test.tsx     : simulate prop change -> assert flash class + fade    │
│    │      - WatchlistPanel.test.tsx: mock fetch("/api/watchlist") -> assert rows render   │
│    │      - portfolioStore.test.tsx: mock fetch("/api/portfolio") -> assert P&L math      │
│    │      - ChatPanel/ActionBadge.test.tsx: mock fetch("/api/chat") -> assert badges      │
│    │                                                                                      │
│    ├─> priceStore tests use a hand-rolled EventSource stub (jsdom has none) to fire       │
│    │      synthetic "prices" named events and assert connection-status transitions        │
│    │                                                                                      │
│    └─> fetch is mocked per-test via vi.spyOn(global, "fetch") against frontend/lib/       │
│           types.ts wire shapes (no MSW, no network)                                       │
└────────────────────────────────────────────────────────────────────────────────────────┘

┌───────────────────────── Playwright E2E (new, TEST-05, Docker) ────────────────────────┐
│  docker compose -f test/docker-compose.test.yml up --build --abort-on-container-exit     │
│    │                                                                                      │
│    ├─> "app" service: built from repo-root Dockerfile, LLM_MOCK=true, throwaway volume   │
│    │      for db/ (D-06), HEALTHCHECK already targets GET /api/health (Dockerfile)        │
│    │                                                                                      │
│    ├─> "playwright" service: depends_on app with condition: service_healthy (D-08),      │
│    │      image mcr.microsoft.com/playwright:v1.63.0-noble, runs `npx playwright test`   │
│    │      against http://app:8000 (Compose internal DNS)                                  │
│    │                                                                                      │
│    └─> Specs drive a real Chromium against the built app: fresh start, watchlist          │
│           add/remove, buy/sell, heatmap/P&L chart rendering, chat trade via "buy 5        │
│           CSCO"/"add PYPL to my watchlist" (real mock.py trigger contract), SSE           │
│           reconnect (kill/restart the app service mid-test or throttle network)           │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure

```
frontend/
├── vitest.config.ts             # jsdom env, @vitejs/plugin-react, vite-tsconfig-paths
├── vitest.setup.ts              # imports @testing-library/jest-dom matchers (optional)
├── test/                        # colocated test-support helpers (NOT the top-level E2E dir)
│   └── eventSourceStub.ts       # hand-rolled EventSource stub class (D-04)
├── components/**/*.test.tsx     # colocated next to the component under test
└── lib/**/*.test.ts             # colocated next to each store/module

test/                             # top-level E2E dir (PLAN.md §12, distinct from frontend/test/)
├── docker-compose.test.yml
├── package.json                 # pins @playwright/test, "test" script
├── playwright.config.ts         # baseURL http://app:8000, projects: [chromium]
└── specs/
    ├── fresh-start.spec.ts
    ├── watchlist.spec.ts
    ├── trading.spec.ts
    ├── visualization.spec.ts
    ├── chat.spec.ts
    └── sse-reconnect.spec.ts
```

> Note the naming collision risk: the official Next.js Vitest convention colocates unit tests inside `frontend/` (or a `frontend/__tests__/`), while PLAN.md's `test/` is the **separate, top-level E2E directory**. Keep these two `test`-named locations distinct — do not colocate Playwright specs under `frontend/test/`.

### Pattern 1: Hand-Rolled EventSource Stub (D-04)

**What:** A minimal class exposing `onopen`/`onmessage`/`onerror`, an `addEventListener` that supports the app's **named** `"prices"` event (not the default `message` event), and a way for the test to fire synthetic events.
**When to use:** Any test of `priceStore.tsx` or any component that (indirectly) depends on the SSE connection.
**Why it must exist:** jsdom has no native `EventSource` — confirmed by direct runtime check this session (see Pitfalls). Every test touching `priceStore.tsx` will throw `ReferenceError: EventSource is not defined` without this stub or an equivalent global assignment.

```typescript
// Source: derived from backend's StubSource convention
// (.planning/codebase/TESTING.md) + the app's actual SSE contract
// [VERIFIED: backend/app/routes/stream.py:38-42 — event name and payload shape]
//   yield f"event: prices\ndata: {json.dumps(payload)}\n\n"
//   payload = {"ticks": [_serialize_tick(t) for t in ticks]}
class StubEventSource {
  static instances: StubEventSource[] = [];
  onopen: (() => void) | null = null;
  onerror: (() => void) | null = null;
  readyState = 0; // EventSource.CONNECTING
  private listeners = new Map<string, ((e: MessageEvent) => void)[]>();

  constructor(public url: string) {
    StubEventSource.instances.push(this);
  }

  addEventListener(type: string, handler: (e: MessageEvent) => void) {
    const list = this.listeners.get(type) ?? [];
    list.push(handler);
    this.listeners.set(type, list);
  }

  // Test helper: fire a named "prices" event with a given ticks payload,
  // matching backend/app/routes/stream.py's PricesEvent shape exactly.
  emit(type: string, data: unknown) {
    this.readyState = 1; // EventSource.OPEN
    const event = { data: JSON.stringify(data) } as MessageEvent;
    for (const handler of this.listeners.get(type) ?? []) handler(event);
  }

  triggerError() {
    this.readyState = 0;
    this.onerror?.();
  }

  close() {
    this.readyState = 2; // EventSource.CLOSED
  }
}

// In vitest.setup.ts or per-test: vi.stubGlobal("EventSource", StubEventSource);
```

### Pattern 2: Per-Test `fetch` Mocking Against Real Wire Shapes (D-05)

**What:** `vi.spyOn(global, "fetch")` returning a `Response`-like object built from the exact TypeScript types in `frontend/lib/types.ts` — never an ad-hoc shape.
**When to use:** Any component/store test that calls through `frontend/lib/api.ts` (`fetchPortfolio`, `fetchWatchlist`, `postTrade`, `fetchChatHistory`, `postChatMessage`).

```typescript
// Source: shape verified against frontend/lib/types.ts (PortfolioResponse)
// and frontend/lib/api.ts's fetchPortfolio() (this session, Read tool)
import { vi } from "vitest";
import type { PortfolioResponse } from "@/lib/types";

function mockFetchOnce(body: unknown, ok = true, status = 200) {
  vi.spyOn(global, "fetch").mockResolvedValueOnce({
    ok,
    status,
    json: async () => body,
  } as Response);
}

const portfolio: PortfolioResponse = {
  cash_balance: 9000,
  positions: [
    {
      ticker: "CSCO",
      quantity: 10,
      avg_cost: 100,
      current_price: 120,
      market_value: 1200,
      unrealized_pnl: 200,
      pct_change: 20,
    },
  ],
  positions_value: 1200,
  total_value: 10200,
  total_unrealized_pnl: 200,
};

mockFetchOnce(portfolio);
```

### Pattern 3: Docker Compose Two-Service E2E Harness (D-06/D-08)

**What:** Two Compose services — `app` (the real built image) and a Playwright test-runner — with the runner gated on the app's health check via `depends_on: condition: service_healthy`.
**When to use:** `test/docker-compose.test.yml`, per D-06/D-08.

```yaml
# Source: pattern per official Playwright Docker docs
# (playwright.dev/docs/docker, fetched this session) + this repo's own
# Dockerfile HEALTHCHECK (D-08 reuse target, verified this session:
# repo-root Dockerfile's `HEALTHCHECK ... CMD python -c "...urlopen('http://localhost:8000/api/health')"`)
services:
  app:
    build:
      context: ../..          # repo root (Dockerfile's expected build context)
      dockerfile: Dockerfile
    environment:
      LLM_MOCK: "true"
    volumes:
      - e2e-db:/app/db        # throwaway, per-run volume (D-06) — never the dev db/ bind mount
    # HEALTHCHECK is already baked into the image (Dockerfile) — no override needed here.

  playwright:
    image: mcr.microsoft.com/playwright:v1.63.0-noble   # pin to installed @playwright/test version
    init: true
    ipc: host
    working_dir: /work
    volumes:
      - .:/work
    environment:
      BASE_URL: http://app:8000
    depends_on:
      app:
        condition: service_healthy   # waits on the app's own HEALTHCHECK, not a fixed sleep (D-08)
    command: npx playwright test

volumes:
  e2e-db:
```

### Anti-Patterns to Avoid

- **Asserting on the SSE tick's `previous_price` field for flash logic:** `PriceCache.update()` keeps the old `previous_price` on an unchanged heartbeat, so `tick.price !== tick.previous_price` stays true forever after the first real move. `PriceCell.tsx` deliberately compares against its own `useRef` of the last-rendered price instead — any frontend test of flash behavior must drive the component through **two distinct renders with different `price` props**, not assert on the tick shape directly `[VERIFIED: frontend/components/ui/PriceCell.tsx:30-43]`.
- **Using the default `onmessage`/`"message"` event in the EventSource stub:** the backend emits a **named** event, `event: prices` `[VERIFIED: backend/app/routes/stream.py:38 — yield f"event: prices\ndata: ..."]`; a stub or test that fires a default unnamed message event will silently never reach `priceStore.tsx`'s handler, which is registered via `es.addEventListener("prices", ...)` `[VERIFIED: frontend/lib/priceStore.tsx:84]`.
- **Reusing the dev `db/` bind mount for E2E:** would corrupt the user's real simulated portfolio and violate the "fresh start" scenario's requirement of a genuinely empty, freshly-seeded database (D-06).
- **Inventing new LLM-mock trigger phrases for E2E chat scenarios:** must match `mock.py`'s actual contract exactly, including the watchlist-keyword requirement (see Pitfall 1 below) — not just the two documented regexes in isolation.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|--------------|-----|
| DOM rendering + querying in tests | A custom render/query harness | `@testing-library/react` + `@testing-library/dom` | Mature, React 19-compatible, and already the ecosystem default paired with Vitest per the official Next.js guide |
| Simulated browser DOM for Vitest | A custom `document`/`window` shim | `jsdom` (via Vitest's `environment: 'jsdom'` config) | Standard, well-tested DOM implementation; only known gap relevant here is `EventSource` (deliberately stubbed per D-04) |
| Health-check-based container readiness wait | A custom polling/sleep script in the Compose file or a wrapper shell script | Compose's native `depends_on: condition: service_healthy`, reading the app's existing `Dockerfile` `HEALTHCHECK` | The app image already declares a real, verified health probe (D-11 from Phase 5) — Compose's built-in condition consumes it directly; re-implementing a wait loop would duplicate logic that already exists and is already tested in production shape |
| Browser automation across Chromium/Firefox/WebKit | A custom Puppeteer/CDP wrapper | `@playwright/test` | Official, actively maintained, and this repo already has a stray untracked install of it under `test/node_modules` — the phase should formalize that existing choice with a real `package.json`, not replace it |

**Key insight:** Every "don't hand-roll" item above already has an existing artifact in this repo pointing at the standard solution (the backend's own stub-class convention for test doubles, the Dockerfile's HEALTHCHECK, the stray Playwright install) — this phase is assembling and formalizing pieces already present, not introducing new tooling philosophy.

## Common Pitfalls

### Pitfall 1: D-07's own example trigger phrase does not actually work

**What goes wrong:** Writing an E2E watchlist-change chat scenario using the phrase `"add PYPL"` (as CONTEXT.md's own D-07 text illustrates) produces `watchlist_changes: []` — no action, no badge, test fails.
**Why it happens:** `build_mock_response()` in `backend/app/llm/mock.py` only checks `_WATCHLIST_PATTERN` (`\b(add|remove)\s+([A-Za-z]{1,5})\b`) **after** first confirming the literal substring `"watchlist"` appears anywhere in the message (case-insensitive) `[VERIFIED: backend/app/llm/mock.py:45-49]`:
  ```python
  if "watchlist" in stripped.lower():
      watchlist_match = _WATCHLIST_PATTERN.search(stripped)
  ```
  This is independently locked as a regression test: `[VERIFIED: backend/tests/llm/test_mock.py:81-87]`
  ```python
  def test_build_mock_response_requires_watchlist_keyword() -> None:
      """... an add/remove verb alone, without the word "watchlist",
      yields no watchlist change ..."""
      result = build_mock_response("add PYPL")
      assert result.watchlist_changes == []
  ```
**How to avoid:** Use a phrase containing both an add/remove verb + ticker **and** the literal word "watchlist", e.g. `"add PYPL to my watchlist"` or `"remove META from the watchlist"` (the exact phrasing used in `backend/tests/llm/test_mock.py`'s own passing cases).
**Warning signs:** An E2E chat spec that asserts a watchlist badge appears, but the phrase sent doesn't contain "watchlist" — will fail deterministically, not flakily, so it should surface immediately in first-run CI/local execution.

### Pitfall 2: jsdom has no `EventSource` — confirmed by direct check, not assumption

**What goes wrong:** Any test that renders a component depending on `priceStore.tsx` (directly or via context) throws `ReferenceError: EventSource is not defined` under Vitest's default jsdom environment.
**Why it happens:** jsdom implements most DOM/web-platform APIs but not `EventSource`. This was verified directly this session rather than assumed from community reports: `jsdom@30.1.1` was installed in an isolated scratch directory and probed —
  ```
  typeof window.EventSource = undefined
  typeof window.WebSocket = function
  ```
  `[VERIFIED: jsdom 30.1.1 runtime check performed this session — JSDOM('<!doctype html>...', {url:'http://localhost'}).window.EventSource is undefined]`
  jsdom's own published "unimplemented parts of the web platform" list does not explicitly name `EventSource`, so this fact could **not** be responsibly claimed from that documentation's absence — the direct runtime probe above is what makes this a verified, not assumed, finding.
**How to avoid:** Install the D-04 stub class (see Pattern 1) via `vi.stubGlobal("EventSource", StubEventSource)` in a `vitest.setup.ts` or per-test-file `beforeEach`, before any component under test mounts.
**Warning signs:** `ReferenceError: EventSource is not defined` in Vitest output is the exact, unambiguous signal — it will not present as a subtler test failure.

### Pitfall 3: async Server Components are not unit-testable under Vitest (Next.js's own caveat)

**What goes wrong:** Attempting to `render()` an `async` Server Component directly in a Vitest test either fails or produces a misleading pass.
**Why it happens:** The official Next.js Vitest guide states this explicitly: *"Since `async` Server Components are new to the React ecosystem, Vitest currently does not support them. While you can still run unit tests for synchronous Server and Client Components, we recommend using E2E tests for `async` components."* `[CITED: node_modules/next/dist/docs/01-app/02-guides/testing/vitest.md]`
**How to avoid:** This project's `app/page.tsx` and interactive components (`WatchlistPanel`, `ChatPanel`, etc.) are all Client Components (`"use client"` directive confirmed by direct read of `priceStore.tsx`, `portfolioStore.tsx`, `WatchlistPanel.tsx`, `chatStore.tsx` — every one opens with `"use client";`), so this caveat is not expected to block TEST-04 in practice, but the planner should not assume any *new* Server Component introduced later is unit-testable this way — route it to the Playwright E2E suite instead.
**Warning signs:** A test that "passes" against an async Server Component but renders nothing meaningful, or a Vitest error specifically citing unsupported async component rendering.

### Pitfall 4: `test/` (top-level E2E dir) name collides conceptually with frontend unit-test conventions

**What goes wrong:** A planner or executor could colocate Playwright specs under `frontend/test/` (a plausible Vitest colocation folder name) instead of the project's actual top-level `test/` directory that PLAN.md §12 designates for E2E + `docker-compose.test.yml`.
**Why it happens:** Both "unit test colocation folder" and "top-level E2E folder" are conventionally named `test`/`tests` in different ecosystems, and this project genuinely has both concepts in play simultaneously for the first time in Phase 6.
**How to avoid:** Keep the top-level `test/` directory (already gitignored in its current stray-artifact state; `[VERIFIED: git status test/ --porcelain --ignored, this session, returned "!! test/"]`) exclusively for the E2E Compose harness + specs, per PLAN.md's directory structure (§4). Frontend unit tests should colocate next to their components/modules (the pattern the official Next.js guide's own example uses) or live under a `frontend/__tests__/` folder if the planner prefers non-colocation — either way, distinct from the top-level `test/`.
**Warning signs:** `npm run test` at the frontend level accidentally picking up (or a CI script accidentally skipping) files under a misnamed nested `test/` folder.

### Pitfall 5: Playwright Docker image version must match `@playwright/test`'s installed version exactly

**What goes wrong:** A version mismatch between the `@playwright/test` npm package and the `mcr.microsoft.com/playwright` Docker image tag causes Playwright to fail locating the correct browser binaries inside the container.
**Why it happens:** Playwright ships browser binaries pinned to each release; the official docs state this directly: *"When running tests remotely, ensure the Playwright version in your tests matches the version running in the Docker container"* `[CITED: playwright.dev/docs/docker, fetched this session]`.
**How to avoid:** Pin the Compose file's `playwright` service image to `mcr.microsoft.com/playwright:v1.63.0-noble` (matching the currently-latest `@playwright/test@1.63.0` `[VERIFIED: npm registry `npm view @playwright/test version`, this session]`) and pin `test/package.json`'s `@playwright/test` devDependency to that exact same version — re-verify both stay in lockstep if either is bumped later.
**Warning signs:** Browser-launch errors inside the container referencing a missing executable path, despite `npx playwright test` working fine on the host machine.

## Code Examples

### Vitest config for this exact Next.js/React version

```typescript
// Source: node_modules/next/dist/docs/01-app/02-guides/testing/vitest.md
// (official Next.js guide, bundled with this project's installed Next.js 16.3.5)
// vitest.config.ts
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import tsconfigPaths from "vite-tsconfig-paths";

export default defineConfig({
  plugins: [tsconfigPaths(), react()],
  test: {
    environment: "jsdom",
    setupFiles: ["./vitest.setup.ts"], // registers EventSource stub + jest-dom matchers
  },
});
```

### Backend gap-closure test (TEST-03's one real gap)

```python
# Follows this file's own established client fixture + Arrange-Act-Assert
# convention (backend/tests/routes/test_watchlist.py), closing the one gap
# found: WatchlistAddRequest's Field(min_length=1) constraint
# [VERIFIED: backend/app/routes/watchlist.py:27-29]
#   class WatchlistAddRequest(BaseModel):
#       ticker: str = Field(min_length=1)
def test_post_watchlist_empty_ticker_is_422(client: TestClient) -> None:
    resp = client.post("/api/watchlist", json={"ticker": ""})

    assert resp.status_code == 422
```

### Playwright spec skeleton (fresh start scenario)

```typescript
// Source: PLAN.md §12 "Fresh start" scenario + this session's confirmed
// backend seed data (10-ticker DEFAULT_WATCHLIST, $10k cash — see
// backend/db seed logic already tested in backend/tests/db/test_watchlist.py)
import { test, expect } from "@playwright/test";

test("fresh start shows default watchlist, $10k cash, and live prices", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText(/10,000/)).toBeVisible();
  const watchlistRows = page.locator("[data-testid=watchlist-row]");
  await expect(watchlistRows).toHaveCount(10);
  // SSE tick should update at least one price cell within a few seconds.
  await expect(page.locator("[data-testid=price-cell]").first()).not.toHaveText("—", {
    timeout: 5000,
  });
});
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|-------------------|---------------|--------|
| Jest + `ts-jest`/Babel for Next.js unit testing | Vitest (native Vite/ESM integration) | Reflected in Next.js's own current official testing guide for this Next.js major version `[CITED: node_modules/next/dist/docs/01-app/02-guides/testing/vitest.md]` | No transform-config maintenance burden; faster watch-mode iteration; this is why D-03 chose Vitest over Jest |

**Deprecated/outdated:** None specific to this phase's stack — all recommended packages are current, actively maintained majors as of this research date.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|----------------|
| A1 | `@testing-library/jest-dom` is a low-risk "Supporting" addition consistent with D-02/D-05's spirit (not a new mocking framework) | Standard Stack (Supporting) | Low — if the planner disagrees, RTL's built-in DOM API (`element.textContent`, etc.) works without it; purely a convenience/readability choice, easily dropped |
| A2 | The four `[SUS]` "too-new" verdicts from `package-legitimacy check` are heuristic false positives rather than genuine slopsquat risk | Package Legitimacy Audit | Low — cross-checked each against download volume (60M+/week) and official GitHub source repo before approving; if the planner wants a stricter posture, adding a lightweight `checkpoint:human-verify` before `npm install` costs little |
| A3 | Colocated test files (next to components) is the right frontend organization choice, vs. a single `__tests__/` folder | Architecture Patterns (Recommended Project Structure) | Low — this is explicitly left to planner/executor discretion per CONTEXT.md's "anything not pinned down" clause; either layout works with the same `vitest.config.ts` |

**If this table is empty:** N/A — three low-risk assumptions logged above; none touch a compliance, retention, or security requirement.

## Open Questions

1. **Should `data-testid` attributes be added to components for Playwright locators, or should specs rely on accessible-role/text queries only?**
   - What we know: The frontend components read so far (`WatchlistRow`, `PriceCell`, `ActionBadge`) don't currently carry `data-testid` attributes; PLAN.md doesn't mandate a query strategy.
   - What's unclear: Whether adding `data-testid`s counts as "changing frontend UI" (explicitly out of scope per CONTEXT.md's domain boundary) or is acceptable test-support scaffolding.
   - Recommendation: Treat minimal, non-visual `data-testid` additions as test infrastructure (not a UI change) since they don't alter rendered output or business logic — but the planner should make this call explicitly rather than leave it implicit, and if avoided, Playwright specs should use `getByRole`/`getByText` queries against the actual rendered strings already documented in `ActionBadge.tsx`/`WatchlistRow.tsx`.

2. **How should the E2E suite assert SSE reconnection (PLAN.md §12's "disconnect and verify reconnection" scenario) inside Docker Compose?**
   - What we know: `priceStore.tsx`'s connection-status state machine (green/yellow/red, Phase 2 D-06) is driven by native `EventSource` `onerror`/`onopen` events, which fire automatically on real network interruption — a real browser's `EventSource` retries on its own, per PLAN.md §6.
   - What's unclear: The cleanest way to simulate an interruption from *outside* the browser in a Compose harness — options include Playwright's own network-throttling/offline emulation (`page.context().setOffline(true)`, browser-side, no container restart needed) vs. actually stopping/restarting the `app` container mid-test (heavier, more realistic, but couples the spec to Compose lifecycle commands).
   - Recommendation: Prefer Playwright's built-in `context.setOffline(true/false)` toggle for this scenario — it directly exercises the same `EventSource` `onerror`/`onopen` code path without needing container-level orchestration from inside a spec file, keeping the test fast and hermetic.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|--------------|-----------|---------|----------|
| Node.js | Vitest, Playwright, frontend build | Yes | v22.13.0 | — |
| npm | Package installs | Yes | 11.0.0 | — |
| Docker | E2E Compose harness (TEST-05) | Yes | 29.7.2 | — |
| Docker Compose | E2E Compose harness (TEST-05) | Yes | v5.4.0 | — |
| Python / uv | Backend pytest (TEST-01/02/03) | Yes | Python 3.13.1 (host), uv 0.10.9; backend targets `>=3.12` and the Docker image uses `python:3.12-slim` | — |

**Missing dependencies with no fallback:** none — all tooling required for this phase is present in the environment.
**Missing dependencies with fallback:** none.

## Validation Architecture

> This phase is unusual: TEST-04/05's own deliverable *is* the test framework this section would normally audit against. The gaps below are therefore this phase's actual Wave 1 scope, not separate infrastructure debt.

### Test Framework

| Property | Value |
|----------|-------|
| Backend framework | pytest 8.0+ / pytest-asyncio 0.24+ (already configured, `backend/pyproject.toml`) |
| Backend config file | `backend/pyproject.toml` `[tool.pytest.ini_options]` |
| Backend quick run | `cd backend && uv run pytest` |
| Backend full suite | `cd backend && uv run pytest -v` (228 existing tests + gap-closure additions) |
| Frontend framework | Vitest 5.0.2 (not yet configured — this phase's deliverable) |
| Frontend config file | `frontend/vitest.config.ts` (to be created) |
| Frontend quick run | `cd frontend && npm run test -- --run <file>` |
| Frontend full suite | `cd frontend && npm run test -- --run` |
| E2E framework | Playwright 1.63.0 (not yet configured — this phase's deliverable) |
| E2E config file | `test/playwright.config.ts` (to be created) |
| E2E run command | `docker compose -f test/docker-compose.test.yml up --build --abort-on-container-exit` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|---------------------|--------------|
| TEST-01 | Trade execution / P&L / insufficient cash-shares | unit | `pytest tests/portfolio/test_service.py -x` | Yes (audit only) |
| TEST-02 | LLM structured-output parsing incl. malformed responses | unit | `pytest tests/llm/test_client.py tests/llm/test_schema.py -x` | Yes (audit only) |
| TEST-03 | API route status codes/response shapes | unit | `pytest tests/routes/ -x` | Yes, ❌ one gap: empty-ticker 422 test (Wave 0/1) |
| TEST-04 | Price flash, watchlist CRUD, portfolio calc, chat rendering | unit | `npm run test -- --run` | ❌ Wave 0 — no test infra exists yet |
| TEST-05 | Fresh start, watchlist, buy/sell, viz, mocked chat, SSE reconnect | e2e | `docker compose -f test/docker-compose.test.yml up --abort-on-container-exit` | ❌ Wave 0 — no test infra exists yet |

### Sampling Rate

- **Per task commit:** backend — `pytest -x` on the touched module; frontend — `npm run test -- --run <touched file>`
- **Per wave merge:** backend full suite (`uv run pytest`); frontend full suite (`npm run test -- --run`)
- **Phase gate:** Full backend suite green + full frontend suite green + full Playwright E2E suite green (via Compose) before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `frontend/vitest.config.ts` + `frontend/vitest.setup.ts` — Vitest bootstrap, covers TEST-04's entire test-runner prerequisite
- [ ] `frontend/lib/test-support/eventSourceStub.ts` (or equivalent) — shared EventSource stub, covers any SSE-dependent TEST-04 test
- [ ] `frontend/package.json` `"test"` script — currently absent entirely
- [ ] `test/package.json` + `test/playwright.config.ts` — E2E bootstrap, covers TEST-05's entire test-runner prerequisite
- [ ] `test/docker-compose.test.yml` — E2E container orchestration, covers TEST-05's infra requirement
- [ ] `backend/tests/routes/test_watchlist.py::test_post_watchlist_empty_ticker_is_422` (or similarly named) — the one identified backend gap for TEST-03

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|----------------|---------|--------------------|
| V2 Authentication | No | App has no authentication (single hardcoded `user_id="default"`, out of scope per REQUIREMENTS.md) — no new surface from this phase |
| V3 Session Management | No | No sessions exist in this app |
| V4 Access Control | No | No access-control boundaries exist to test |
| V5 Input Validation | Yes (audit only) | Pydantic (`Field(min_length=1)`, `Field(gt=0)`, `Query(ge=1, le=MAX_SNAPSHOT_LIMIT)`) already enforces input validation on every route; this phase's only V5-relevant work is closing the one identified test gap (empty-ticker 422), not adding new validation |
| V6 Cryptography | No | No cryptographic operations in scope |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|------------------------|
| Test-only `LLM_MOCK=true` accidentally leaking into a non-test build | Information Disclosure (of intent, not data) | E2E `docker-compose.test.yml` sets `LLM_MOCK=true` only for its own throwaway `app` service, entirely separate from the production `Dockerfile`/`docker run` invocation documented in PLAN.md §11 — no shared `.env` file between the two |
| Committing real `OPENROUTER_API_KEY` secrets into `test/docker-compose.test.yml` or CI-adjacent test fixtures | Information Disclosure | Not needed at all — E2E runs exclusively under `LLM_MOCK=true`, so no real API key should ever appear in any Phase 6 artifact; if a planner-authored task references `.env`, flag it as a review concern |
| Throwaway E2E Docker volume being confused with the production volume name | Tampering (of real user data) | Use a distinct, obviously-scoped volume name (e.g. `e2e-db`, not `finally-data`) in `test/docker-compose.test.yml`, per D-06 |

## Sources

### Primary (HIGH confidence)
- `node_modules/next/dist/docs/01-app/02-guides/testing/vitest.md` — official Next.js Vitest setup guide, bundled with this project's exact installed Next.js 16.3.5, read directly this session
- `npm view <package> version` / `npm view @testing-library/react peerDependencies` — direct npm registry queries, this session, for vitest, @vitejs/plugin-react, jsdom, @testing-library/react, @testing-library/dom, @testing-library/jest-dom, vite-tsconfig-paths, @playwright/test
- `gsd_run query package-legitimacy check --ecosystem npm ...` — direct legitimacy-seam query, this session, for all 8 frontend/E2E packages
- Direct jsdom 30.1.1 runtime probe (installed in an isolated scratch directory, this session) confirming `EventSource` is `undefined` while `WebSocket` is implemented
- Direct `Read` of backend source: `backend/app/llm/mock.py`, `backend/app/routes/{watchlist,portfolio,chat,stream}.py`, `backend/tests/{portfolio/test_service,llm/test_client,llm/test_schema,llm/test_mock,routes/test_portfolio,routes/test_watchlist,routes/test_chat}.py`
- Direct `Read` of frontend source: `frontend/lib/{priceStore,portfolioStore,chatStore,api,types}.tsx|ts`, `frontend/components/{ui/PriceCell,watchlist/WatchlistPanel,chat/ActionBadge}.tsx`, `frontend/package.json`

### Secondary (MEDIUM confidence)
- `https://playwright.dev/docs/docker` — official Playwright Docker guide (image tag convention, `--init`/`--ipc=host` flags), fetched this session via WebFetch
- WebSearch results on Docker Compose `depends_on: condition: service_healthy` pattern for Playwright — cross-referenced with the official docs above rather than relied on alone

### Tertiary (LOW confidence)
- General WebSearch results describing jsdom's lack of `EventSource` support (superseded by the direct runtime verification above, which is the claim actually cited in this document)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every version verified live against the npm registry this session, and the setup pattern is the current official Next.js guide for this exact installed Next.js version
- Architecture: HIGH — all component/store contracts (SSE event name, flash-trigger logic, single-API-module pattern) read directly from source this session, not inferred
- Pitfalls: HIGH — the two most load-bearing pitfalls (jsdom's missing `EventSource`, the mock.py watchlist-keyword gate) were each independently verified via direct execution/source-read this session, not assumed from training data or secondary sources

**Research date:** 2026-09-27
**Valid until:** 2026-10-27 (30 days — this is a fast-moving npm ecosystem corner, but all packages are stable majors; re-verify versions if planning is delayed past this window)
