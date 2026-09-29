---
phase: 06-test-coverage
reviewed: 2026-09-29T00:00:00Z
depth: standard
files_reviewed: 33
files_reviewed_list:
  - .dockerignore
  - backend/tests/portfolio/test_service.py
  - backend/tests/routes/test_watchlist.py
  - frontend/components/charts/chartTheme.test.ts
  - frontend/components/chat/ActionBadge.test.tsx
  - frontend/components/chat/ChatPanel.test.tsx
  - frontend/components/header/Header.test.tsx
  - frontend/components/positions/PositionsTable.test.tsx
  - frontend/components/ui/PriceCell.test.tsx
  - frontend/components/watchlist/WatchlistPanel.test.tsx
  - frontend/components/watchlist/WatchlistRow.test.tsx
  - frontend/lib/format.test.ts
  - frontend/lib/priceStore.test.tsx
  - frontend/package.json
  - frontend/test-support/eventSourceStub.ts
  - frontend/test-support/fetchStub.ts
  - frontend/test-support/renderWithProviders.tsx
  - frontend/vitest.config.mts
  - frontend/vitest.setup.ts
  - test/.dockerignore
  - test/.gitignore
  - test/docker-compose.test.yml
  - test/Dockerfile.playwright
  - test/package.json
  - test/playwright.config.ts
  - test/run-e2e.mjs
  - test/specs/01-fresh-start.spec.ts
  - test/specs/02-watchlist.spec.ts
  - test/specs/03-trading.spec.ts
  - test/specs/04-visualization.spec.ts
  - test/specs/05-chat.spec.ts
  - test/specs/06-sse-reconnect.spec.ts
  - test/specs/helpers.ts
findings:
  critical: 0
  warning: 3
  info: 1
  total: 4
status: issues_found
---

# Phase 06: Code Review Report

**Reviewed:** 2026-09-29T00:00:00Z
**Depth:** standard
**Files Reviewed:** 33
**Status:** issues_found

## Summary

Every file in scope is a test, test-support/harness module, or test-infrastructure
config for Phase 06 (test-coverage); no application source was touched, consistent
with the phase's scope boundary. The suite is unusually disciplined for a first
pass — unit tests are driven through real provider trees rather than mocks,
several files document an explicit "non-vacuity check" (temporarily breaking the
implementation and confirming the test catches it, then restoring), and the E2E
Docker harness (`test/docker-compose.test.yml`, `test/Dockerfile.playwright`,
`test/run-e2e.mjs`) is already hardened against the specific risks this review
was asked to check: no published host ports, a throwaway named volume (never the
developer's own `db/` bind mount or the production `finally-data` volume name),
no `env_file` pulling the host's `.env`/`OPENROUTER_API_KEY` into the ephemeral
container, and `MASSIVE_API_KEY` forced empty so the suite never depends on a
real market-data provider. `backend/app/market/factory.py` was spot-checked to
confirm the empty-string convention actually selects the simulator, and the root
`Dockerfile` was spot-checked to confirm the `HEALTHCHECK` the compose file's
`condition: service_healthy` depends on actually exists.

No blocker-level defects were found. Four findings remain: one backend test with
a wall-clock race assumption that could flake under load, one E2E helper with a
selector that couples test correctness to unrelated Tailwind utility classes,
one latent (currently dormant) mutation-during-iteration hazard in the hand-rolled
`EventSource` stub, and one dead field in the `fetch` stub's return value.

## Warnings

### WR-01: Watchlist route test's "uncached ticker" assertion relies on winning a wall-clock race against the background update loop

**File:** `backend/tests/routes/test_watchlist.py:66-78`
**Issue:** `test_get_watchlist_uncached_ticker_has_null_price` adds `ORCL` via
`POST /api/watchlist` and immediately asserts, via a synchronous `GET
/api/watchlist`, that its price/previous_price/direction/timestamp are all
`None`. The test's own comment explains why this is expected to work: the
background `run_update_loop` (started in `app/main.py`'s lifespan for every
`TestClient`) only fetches `DEFAULT_WATCHLIST` tickers on its already-in-flight
first iteration, and won't pick up `ORCL` until its *next* ~0.5s tick — "long
after this synchronous test has already asserted and returned." That's a timing
assumption, not a synchronization guarantee: the test never stops, mocks, or
monkeypatches the background loop, so if the POST+GET round trip is slow enough
(loaded CI runner, debugger attached, GC pause) for the loop's next tick to land
first, the assertion silently flips from "proves the null-price contract" to a
flaky failure — or, in the opposite direction, could mask a real regression
that makes the loop fetch tickers faster than intended, since a coincidental win
of the race would still pass. The same pattern (documented, unenforced race
avoidance) also appears in `test_get_watchlist_joins_cached_prices`'s comment,
but that test seeds the price directly and doesn't depend on the loop's timing
for its own assertions — only this one actually depends on the race outcome.
**Fix:** Make the non-interference deterministic instead of timing-based, e.g.
monkeypatch the loop to a no-op for this test, or inject a large tick interval
so the test doesn't need to race it:
```python
@pytest.fixture
def client_without_update_loop(monkeypatch):
    monkeypatch.delenv("MASSIVE_API_KEY", raising=False)
    monkeypatch.setattr("app.market.loop.SIMULATOR_TICK_SECONDS", 3600)
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
```
or assert the invariant a different way that doesn't depend on the loop not
having run yet (e.g., have the route/service expose whether a ticker has ever
been priced, rather than inferring it from timing).

### WR-02: E2E chat-bubble locator is coupled to unrelated Tailwind utility classes

**File:** `test/specs/helpers.ts:184-191`
**Issue:** `mockChatBubbles()` (used by `sendChat()`, which is the synchronization
barrier for every chat-driven E2E spec — `02-watchlist.spec.ts`,
`05-chat.spec.ts`) identifies assistant chat bubbles with
`page.locator(".border-l-2.border-accent-blue", { hasText: /^\[LLM_MOCK\]/ })`.
`border-l-2` and `border-accent-blue` are purely cosmetic Tailwind utility
classes with no semantic meaning. A future, purely visual restyle of the chat
bubble (e.g., switching the accent border to a different utility, or dropping
the left-border treatment entirely) would silently break every spec that calls
`sendChat()`, with a failure mode ("locator found 0 bubbles, timed out") that
gives no indication the underlying chat functionality is actually fine — it
looks like a functional regression when it's a pure style change. This is the
one CSS-class-dependent locator in an otherwise semantic-selector-first test
suite (every other locator in this file and the specs uses ARIA roles,
accessible names, or exact text).
**Fix:** Identify the bubble by something the component's contract actually
owns — a `data-testid`, an `aria-label`, or a semantic wrapper role — rather
than styling classes:
```tsx
// ChatMessageList.tsx (illustrative)
<div data-role="assistant-bubble" className="border-l-2 border-accent-blue">
```
```ts
// helpers.ts
function mockChatBubbles(page: Page): Locator {
  return page.locator('[data-role="assistant-bubble"]', {
    hasText: /^\[LLM_MOCK\]/,
  });
}
```

### WR-03: `StubEventSource.emit()` iterates a live reference to the listener array

**File:** `frontend/test-support/eventSourceStub.ts:98-102`
**Issue:**
```ts
emit(type: string, data: unknown): void {
  const event = new MessageEvent(type, { data: JSON.stringify(data) });
  for (const handler of this.listeners.get(type) ?? []) handler(event);
  if (type === "message") this.onmessage?.(event);
}
```
`this.listeners.get(type)` returns the actual backing array stored in the map,
not a copy. If any handler invoked during this loop calls
`removeEventListener` for the same event `type` (a legitimate thing for a
component's cleanup/re-subscribe logic to do reactively), the array is mutated
mid-iteration and a `for...of` loop over a shrinking array can skip the handler
that shifted into the just-vacated index. This is currently dormant because
every component in this codebase registers exactly one `"prices"` listener
per `EventSource` (confirmed in `frontend/lib/priceStore.tsx`), but it is a
latent correctness trap for the harness itself: a future test or component
that adds a second `"prices"` listener, or that removes-and-re-adds a listener
from within its own handler, would get inconsistent event delivery with no
indication the stub — not the code under test — is at fault.
**Fix:** Snapshot the listener list before dispatching:
```ts
emit(type: string, data: unknown): void {
  const event = new MessageEvent(type, { data: JSON.stringify(data) });
  for (const handler of [...(this.listeners.get(type) ?? [])]) handler(event);
  if (type === "message") this.onmessage?.(event);
}
```

## Info

### IN-01: `stubFetch()`'s `unexpected` return value is dead code

**File:** `frontend/test-support/fetchStub.ts:83-87, 121-123, 149-155`
**Issue:** `stubFetch()` builds and returns an `unexpected: RecordedCall[]`
array, populated whenever a test hits an unrouted `"<METHOD> <path>"` key. No
test file in scope (or anywhere under `frontend/`) reads `.unexpected` —
confirmed via search, zero matches. The unrouted-call case is already enforced
a different way: the stubbed `fetch` throws synchronously for that call
(`throw new Error(\`Unrouted fetch call: ${key}\`)`), which is what actually
fails a test that hits it. The `unexpected` array is therefore maintained on
every request for a consumer that doesn't exist, adding surface area to the
harness's public return type without corresponding value.
**Fix:** Either drop the field to shrink the harness's API surface:
```ts
return { calls, callsTo(key: string) { ... } };
```
or, if the intent was to let a test assert "no unrouted calls happened" without
the whole test aborting on the first one (e.g., a softer diagnostic mode), add
at least one test that exercises that path so the field has a proven purpose.

---

_Reviewed: 2026-09-29T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
