/**
 * Global Vitest setup (Phase 6, TEST-04): jest-dom matchers, React Testing
 * Library cleanup, and per-test installation of the `EventSource` and
 * `ResizeObserver` test doubles jsdom does not provide natively.
 *
 * Vitest does not enable RTL's automatic-cleanup-via-globals mode, so a
 * missing `cleanup()` here would leak DOM nodes between tests. `cleanup()`
 * runs before the global un-stub calls in `afterEach` so provider effects
 * (e.g. `PriceStoreProvider`'s unmount cleanup, which calls `es.close()`)
 * still see the stubbed `EventSource` while they tear down.
 */

import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, beforeEach, vi } from "vitest";
import { StubEventSource } from "./test-support/eventSourceStub";

// Recharts' `ResponsiveContainer` (used by the watchlist sparkline)
// constructs a `ResizeObserver`, which jsdom does not implement. A no-op
// stand-in is enough for component mounts that merely render a chart
// without asserting on resize behavior.
class StubResizeObserver {
  observe(): void {}
  unobserve(): void {}
  disconnect(): void {}
}

beforeEach(() => {
  StubEventSource.reset();
  vi.stubGlobal("EventSource", StubEventSource);
  vi.stubGlobal("ResizeObserver", StubResizeObserver);
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});
