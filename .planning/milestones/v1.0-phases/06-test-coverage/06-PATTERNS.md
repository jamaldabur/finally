# Phase 6: Test Coverage - Pattern Map

**Mapped:** 2026-09-27
**Files analyzed:** 10 (1 backend gap-closure test, 5+ new frontend test/config files, 4 new E2E infra/spec files)
**Analogs found:** 10 / 10

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `backend/tests/routes/test_watchlist.py` (add 1 test) | test | request-response | same file, `test_get_watchlist_returns_seeded_tickers` etc. | exact (extend existing file) |
| `frontend/vitest.config.ts` | config | — | `node_modules/next/dist/docs/.../vitest.md` official example | exact (framework doc, no local analog exists) |
| `frontend/vitest.setup.ts` | config | — | official Next.js Vitest guide + D-04 stub wiring | exact |
| `frontend/lib/test-support/eventSourceStub.ts` | utility (test double) | event-driven | `backend/tests/market/` `StubSource` convention (per `.planning/codebase/TESTING.md`) | role-match (cross-language convention, same pattern) |
| `frontend/components/ui/PriceCell.test.tsx` | test (component) | request-response/event-driven | `frontend/components/ui/PriceCell.tsx` (component under test) | exact |
| `frontend/lib/priceStore.test.tsx` | test (hook/provider) | event-driven | `frontend/lib/priceStore.tsx` (provider under test) | exact |
| `frontend/components/watchlist/WatchlistPanel.test.tsx` | test (component) | CRUD | `frontend/components/watchlist/WatchlistPanel.tsx` + `frontend/lib/api.ts` | exact |
| `frontend/lib/portfolioStore.test.tsx` | test (store) | CRUD | `frontend/lib/portfolioStore.tsx` + `frontend/lib/api.ts` (`fetchPortfolio`) | exact |
| `frontend/components/chat/ActionBadge.test.tsx` | test (component) | request-response | `frontend/components/chat/ActionBadge.tsx` + `frontend/lib/api.ts` (`postChatMessage`) | exact |
| `test/docker-compose.test.yml` | config | event-driven (container orchestration) | `Dockerfile` (root) HEALTHCHECK block | role-match (only existing container-lifecycle artifact) |
| `test/playwright.config.ts` + `test/package.json` | config | — | none in-repo (stray untracked `@playwright/test` install only) | no analog — use RESEARCH.md Code Examples |
| `test/specs/fresh-start.spec.ts` (and other specs) | test (E2E) | request-response / streaming | RESEARCH.md Code Examples "Playwright spec skeleton" + `backend/app/llm/mock.py` trigger contract | no analog — use RESEARCH.md Code Examples |

## Pattern Assignments

### `backend/tests/routes/test_watchlist.py` (test, request-response) — ADD ONE TEST

**Analog:** same file (extend, don't create new)

**Fixture pattern already in file** (lines 13-25):
```python
@pytest.fixture
def client(monkeypatch):
    """A TestClient wrapping a fresh app instance, with MASSIVE_API_KEY unset
    so the simulator (and its TICKER_UNIVERSE) is the active market data
    source. ..."""
    monkeypatch.delenv("MASSIVE_API_KEY", raising=False)
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
```

**Test-body pattern to copy** (matches existing `test_get_watchlist_returns_seeded_tickers`, lines 32-41 — plain Arrange-Act-Assert, no section comments needed for a one-liner):
```python
def test_post_watchlist_empty_ticker_is_422(client: TestClient) -> None:
    resp = client.post("/api/watchlist", json={"ticker": ""})

    assert resp.status_code == 422
```

**Why this gap exists:** `backend/app/routes/watchlist.py:27-29` declares `ticker: str = Field(min_length=1)` on `WatchlistAddRequest`, but no test in the file exercises the empty-string 422 path (RESEARCH.md D-01 audit finding, TEST-03's only real gap).

**Convention notes (D-02):** No new fixtures, no new mocking library. Use the existing `client` fixture verbatim; place the new test alongside the other `POST /api/watchlist` tests in this same file (do not create a new file — this is gap-closure, not a new suite).

---

### `frontend/vitest.config.ts` (config)

**No local analog** — this is a from-scratch bootstrap (RESEARCH.md Wave 0 gap). Use the official Next.js guide example verbatim, already verified against this project's exact installed Next.js/React versions:

```typescript
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import tsconfigPaths from "vite-tsconfig-paths";

export default defineConfig({
  plugins: [tsconfigPaths(), react()],
  test: {
    environment: "jsdom",
    setupFiles: ["./vitest.setup.ts"],
  },
});
```

Source: `node_modules/next/dist/docs/01-app/02-guides/testing/vitest.md` (bundled with this project's Next.js 16.3.5 install — see RESEARCH.md "Code Examples").

---

### `frontend/lib/test-support/eventSourceStub.ts` (utility/test-double, event-driven)

**Analog (convention, not code):** backend's `StubSource`/`_FakeRequest` stub-class convention documented in `.planning/codebase/TESTING.md` — "prefer stub classes over mocking libraries." No native TS equivalent exists yet; RESEARCH.md's Pattern 1 is the copy-ready implementation, derived directly from the real SSE wire contract:

**Critical real contract to match** (`frontend/lib/priceStore.tsx:84`):
```typescript
es.addEventListener("prices", (event: MessageEvent<string>) => {
  const payload = JSON.parse(event.data) as PricesEvent;
  ...
```
The event name is `"prices"`, NOT the default `"message"` — the stub's `emit()` helper must let tests fire a named event, or `priceStore.tsx`'s handler will never be reached.

**Stub to copy verbatim (from RESEARCH.md Pattern 1):**
```typescript
class StubEventSource {
  static instances: StubEventSource[] = [];
  onopen: (() => void) | null = null;
  onerror: (() => void) | null = null;
  readyState = 0;
  private listeners = new Map<string, ((e: MessageEvent) => void)[]>();

  constructor(public url: string) {
    StubEventSource.instances.push(this);
  }

  addEventListener(type: string, handler: (e: MessageEvent) => void) {
    const list = this.listeners.get(type) ?? [];
    list.push(handler);
    this.listeners.set(type, list);
  }

  emit(type: string, data: unknown) {
    this.readyState = 1;
    const event = { data: JSON.stringify(data) } as MessageEvent;
    for (const handler of this.listeners.get(type) ?? []) handler(event);
  }

  triggerError() {
    this.readyState = 0;
    this.onerror?.();
  }

  close() {
    this.readyState = 2;
  }
}
// wiring: vi.stubGlobal("EventSource", StubEventSource);
```

---

### `frontend/components/ui/PriceCell.test.tsx` (test, request-response/event-driven)

**Analog:** `frontend/components/ui/PriceCell.tsx` (the component itself, 50 lines, read in full — see full source above)

**Core pattern to test (component's own logic, lines 32-43):**
```typescript
useEffect(() => {
  if (price === null) return;
  if (lastPrice.current !== null && price !== lastPrice.current) {
    setFlashClass(direction === "up" ? "bg-green-500/30" : "bg-red-500/30");
    const timer = setTimeout(() => setFlashClass(""), 500);
    lastPrice.current = price;
    return () => clearTimeout(timer);
  }
  lastPrice.current = price;
}, [price, direction]);
```

**Anti-pattern (must avoid in the test, per RESEARCH.md):** do NOT assert against a tick's `previous_price` field — it stays permanently stale on unchanged heartbeats. Instead, `render()` the component, then `rerender()` with a different `price` prop (two distinct renders), and assert the flash class appears then clears after the timeout (use `vi.useFakeTimers()` + `act()` to advance past 500ms).

---

### `frontend/lib/priceStore.test.tsx` (test, event-driven)

**Analog:** `frontend/lib/priceStore.tsx` (provider under test, full source read above)

**Imports pattern to copy:**
```typescript
import { render, screen, act } from "@testing-library/react";
import { vi } from "vitest";
import { PriceStoreProvider, usePriceStore } from "@/lib/priceStore";
```

**Core pattern under test — connection status state machine** (`priceStore.tsx:131-144`):
```typescript
es.onopen = () => { setStatus("connected"); clearGraceTimer(); };
es.onerror = () => {
  setStatus("reconnecting");
  clearGraceTimer();
  graceTimer.current = setTimeout(() => {
    if (es.readyState !== EventSource.OPEN) setStatus("disconnected");
  }, DISCONNECT_GRACE_MS);
};
```
Test setup: `vi.stubGlobal("EventSource", StubEventSource)` before mount, grab `StubEventSource.instances[0]`, call `.emit("prices", { ticks: [...] })` to simulate a tick, `.triggerError()` + `vi.advanceTimersByTime(5000)` to test the disconnect grace window (D-06 from Phase 2 context, referenced in RESEARCH.md).

---

### `frontend/components/watchlist/WatchlistPanel.test.tsx` (test, CRUD)

**Analog:** `frontend/lib/api.ts` (`fetchWatchlist`, lines 45-53) + `frontend/components/watchlist/WatchlistPanel.tsx`

**Fetch-mock pattern to copy** (RESEARCH.md Pattern 2, adapted for watchlist shape):
```typescript
import { vi } from "vitest";

function mockFetchOnce(body: unknown, ok = true, status = 200) {
  vi.spyOn(global, "fetch").mockResolvedValueOnce({
    ok, status, json: async () => body,
  } as Response);
}
```

**Wire shape to mock** — matches `WatchlistEntryResponse` in `backend/app/routes/watchlist.py:31-37`, consumed via `frontend/lib/api.ts:45-53`'s `fetchWatchlist()`:
```typescript
mockFetchOnce({ watchlist: [
  { ticker: "AAPL", price: 190.0, previous_price: 188.5, direction: "up", timestamp: "2026-09-27T00:00:00Z" },
] });
```

**Error-shape handling to mirror** (`frontend/lib/api.ts:55-60`, needed for add/remove failure-path tests):
```typescript
type ApiErrorDetail = string | { msg: string; loc?: (string | number)[] }[];
```

---

### `frontend/lib/portfolioStore.test.tsx` (test, CRUD)

**Analog:** `frontend/lib/api.ts` (`fetchPortfolio`, lines 20-26) + RESEARCH.md's exact `PortfolioResponse` fixture

**Fixture to copy verbatim (RESEARCH.md Pattern 2):**
```typescript
import type { PortfolioResponse } from "@/lib/types";

const portfolio: PortfolioResponse = {
  cash_balance: 9000,
  positions: [
    {
      ticker: "CSCO", quantity: 10, avg_cost: 100, current_price: 120,
      market_value: 1200, unrealized_pnl: 200, pct_change: 20,
    },
  ],
  positions_value: 1200,
  total_value: 10200,
  total_unrealized_pnl: 200,
};

mockFetchOnce(portfolio);
```
Use to assert portfolio display/P&L calculations render correctly (TEST-04).

---

### `frontend/components/chat/ActionBadge.test.tsx` (test, request-response)

**Analog:** `frontend/lib/api.ts` (`postChatMessage`, lines 99-117) + `frontend/components/chat/ActionBadge.tsx`

**Key contract to mock** (`api.ts:93-98` comment): `POST /api/chat` returns 200 even when a proposed trade/watchlist action failed — action-level success/error is read from the response body's `trades[]`/`watchlist_changes[]` `reason`/outcome fields, not from `!res.ok`. Tests must mock a 200 response containing both an `executed` and an `error`-outcome action to exercise `ActionBadge`'s per-outcome rendering (labeled success vs error per PLAN.md §9/§10).

```typescript
mockFetchOnce({
  message: "Done.",
  trades: [{ ticker: "AAPL", side: "buy", quantity: 1, outcome: "executed" }],
  watchlist_changes: [{ ticker: "ZZZZ", action: "add", outcome: "error", reason: "Unknown ticker" }],
});
```
(Adjust field names to match the actual `ChatResponse` type in `frontend/lib/types.ts` if they differ — read that file at implementation time.)

---

### `test/docker-compose.test.yml` (config, container orchestration)

**Analog:** root `Dockerfile`'s `HEALTHCHECK` block (lines 54-55):
```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"
```
This HEALTHCHECK is reused via Compose's `depends_on: condition: service_healthy` (D-08) — no new health-check logic should be written.

**Full pattern to copy (RESEARCH.md Pattern 3):**
```yaml
services:
  app:
    build:
      context: ../..
      dockerfile: Dockerfile
    environment:
      LLM_MOCK: "true"
    volumes:
      - e2e-db:/app/db

  playwright:
    image: mcr.microsoft.com/playwright:v1.63.0-noble
    init: true
    ipc: host
    working_dir: /work
    volumes:
      - .:/work
    environment:
      BASE_URL: http://app:8000
    depends_on:
      app:
        condition: service_healthy
    command: npx playwright test

volumes:
  e2e-db:
```
Note: name the volume `e2e-db` (or similarly distinct), never `finally-data` (production volume name per PLAN.md §11) — D-06 explicitly requires a throwaway, never-shared volume.

---

### `test/specs/*.spec.ts` (test, E2E)

**No in-repo analog.** Use RESEARCH.md's Playwright spec skeleton and the `mock.py` trigger contract:

**Fresh-start skeleton:**
```typescript
import { test, expect } from "@playwright/test";

test("fresh start shows default watchlist, $10k cash, and live prices", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText(/10,000/)).toBeVisible();
  const watchlistRows = page.locator("[data-testid=watchlist-row]");
  await expect(watchlistRows).toHaveCount(10);
  await expect(page.locator("[data-testid=price-cell]").first()).not.toHaveText("—", { timeout: 5000 });
});
```

**Mocked chat trade/watchlist trigger phrases — MUST match `backend/app/llm/mock.py`'s real regex contract exactly:**
- Trade: `"buy 5 CSCO"` or `"sell 3 AAPL"` (matches `_TRADE_PATTERN`)
- Watchlist: `"add PYPL to my watchlist"` or `"remove META from the watchlist"` — the bare phrase `"add PYPL"` alone does NOT work; `build_mock_response()` requires the literal substring `"watchlist"` (case-insensitive) anywhere in the message before it even checks `_WATCHLIST_PATTERN` (`backend/app/llm/mock.py:45-49`, locked by `backend/tests/llm/test_mock.py:81-87`'s `test_build_mock_response_requires_watchlist_keyword`).

**SSE reconnection scenario:** prefer `page.context().setOffline(true/false)` (browser-side network toggle) over stopping/restarting the `app` container — exercises the same real `EventSource` `onerror`/`onopen` code path without container-lifecycle coupling from inside a spec.

## Shared Patterns

### Backend: stub-class-over-mocking-library convention (D-02)
**Source:** `.planning/codebase/TESTING.md` (backend `StubSource`/`_FakeRequest` convention)
**Apply to:** the one new backend test — no new fixtures or mocking libraries, reuse `client` fixture as-is.

### Frontend: single fetch chokepoint (D-05)
**Source:** `frontend/lib/api.ts` — every API call funnels through this one module.
**Apply to:** all frontend component/store tests — mock `global.fetch` per test via `vi.spyOn`, never mock a component's internal fetch call directly, and always shape mock bodies against `frontend/lib/types.ts`'s real types.

### Frontend: named SSE event, not default `message` (critical, cross-cutting)
**Source:** `backend/app/routes/stream.py` (`event: prices`) / `frontend/lib/priceStore.tsx:84` (`addEventListener("prices", ...)`)
**Apply to:** `eventSourceStub.ts`, `priceStore.test.tsx`, and any component test that renders through `PriceStoreProvider` — always fire `.emit("prices", ...)`, never rely on a default `onmessage`.

### Frontend: flash-trigger comparison is render-history-based, not tick-based
**Source:** `frontend/components/ui/PriceCell.tsx:30-43`
**Apply to:** `PriceCell.test.tsx` and any other flash-animation test — drive two distinct renders with different `price` props; never assert on `tick.previous_price`.

### E2E: reuse existing Docker HEALTHCHECK, no custom wait script
**Source:** root `Dockerfile` lines 54-55
**Apply to:** `test/docker-compose.test.yml`'s `playwright` service `depends_on` block.

### E2E: mock.py trigger-phrase contract is the single source of truth
**Source:** `backend/app/llm/mock.py`, locked by `backend/tests/llm/test_mock.py`
**Apply to:** all chat-related E2E specs — trade phrases need `"<verb> <qty> <TICKER>"`; watchlist phrases need an add/remove verb + ticker AND the literal word "watchlist".

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `test/playwright.config.ts` | config | — | No Playwright config exists anywhere in-repo yet (only a stray untracked `node_modules` install); use RESEARCH.md's Docker/Playwright version-pinning guidance (`v1.63.0-noble` matching `@playwright/test@1.63.0`) |
| `test/package.json` | config | — | `test/` currently has no committed `package.json` at all; create fresh, pin `@playwright/test@1.63.0` |
| `frontend/vitest.config.ts` / `vitest.setup.ts` | config | — | Zero test infra exists in `frontend/` today; follow the official Next.js Vitest guide bundled in `node_modules/next/dist/docs/` exactly (already project-specific, not a generic online guide) |

## Metadata

**Analog search scope:** `backend/tests/{portfolio,llm,routes,db,market}/`, `backend/app/routes/watchlist.py`, `frontend/lib/{priceStore,api,types,portfolioStore}.ts(x)`, `frontend/components/{ui/PriceCell,watchlist/WatchlistPanel,chat/ActionBadge}.tsx`, root `Dockerfile`, `.planning/codebase/TESTING.md`
**Files scanned:** 9 read directly this session (plus RESEARCH.md's own prior direct reads of the same set, cross-referenced)
**Pattern extraction date:** 2026-09-27
**Tracked-source note:** All analog paths above are ordinary git-tracked source files in `backend/` and `frontend/` (or the root `Dockerfile`) — no `.gsd/capabilities/` mirror paths or other gitignored install/runtime mirrors were used as analogs.
