/**
 * Hand-rolled `EventSource` test double (Phase 6, TEST-04, D-04).
 *
 * jsdom 30 has no native `EventSource` implementation at all (verified in
 * 06-RESEARCH.md Pitfall 2 — a direct runtime probe found
 * `typeof window.EventSource === "undefined"`), so any test that mounts a
 * component depending on `frontend/lib/priceStore.tsx` needs a global
 * substitute before that component renders.
 *
 * The real backend contract (`backend/app/routes/stream.py`) emits a
 * *named* SSE event, `event: prices`, never the default unnamed `message`
 * event — `priceStore.tsx` subscribes via
 * `es.addEventListener("prices", ...)`, not `es.onmessage`. This stub's
 * `emit()` helper mirrors that: it only delivers to listeners registered
 * for the exact event type passed in (and to `onmessage` when that type is
 * literally `"message"`, matching how a real browser routes events), so a
 * test that mistakenly fires the default message event fails loudly by
 * simply not reaching the handler under test, rather than silently
 * appearing to work.
 *
 * Mirrors the backend's own stub-class convention (`StubSource`,
 * `_FakeRequest` — see `.planning/codebase/TESTING.md`): a small, readable
 * class purpose-built for this app's exact contract, not a general-purpose
 * mocking library.
 */

type Listener = (event: MessageEvent) => void;

export class StubEventSource {
  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSED = 2;

  static instances: StubEventSource[] = [];

  static reset(): void {
    StubEventSource.instances = [];
  }

  static latest(): StubEventSource {
    const instance = StubEventSource.instances[StubEventSource.instances.length - 1];
    if (!instance) {
      throw new Error(
        "StubEventSource.latest() called but no EventSource was constructed — did the test render a component wrapped in PriceStoreProvider?",
      );
    }
    return instance;
  }

  readonly url: string;
  readyState: number = StubEventSource.CONNECTING;
  closed = false;

  onopen: ((event: Event) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;

  private readonly listeners = new Map<string, Listener[]>();

  constructor(url: string) {
    this.url = url;
    StubEventSource.instances.push(this);
  }

  addEventListener(type: string, handler: Listener): void {
    const existing = this.listeners.get(type) ?? [];
    existing.push(handler);
    this.listeners.set(type, existing);
  }

  removeEventListener(type: string, handler: Listener): void {
    const existing = this.listeners.get(type);
    if (!existing) return;
    this.listeners.set(
      type,
      existing.filter((registered) => registered !== handler),
    );
  }

  close(): void {
    this.readyState = StubEventSource.CLOSED;
    this.closed = true;
  }

  /** Test helper: simulate the browser successfully opening the connection. */
  open(): void {
    this.readyState = StubEventSource.OPEN;
    this.onopen?.(new Event("open"));
  }

  /**
   * Test helper: deliver a named SSE event, matching
   * `backend/app/routes/stream.py`'s real wire format
   * (`event: prices\ndata: {...}`). Only listeners registered for this
   * exact `type` receive it; `onmessage` only fires when `type` is the
   * default `"message"`, mirroring real browser `EventSource` routing.
   */
  emit(type: string, data: unknown): void {
    const event = new MessageEvent(type, { data: JSON.stringify(data) });
    for (const handler of this.listeners.get(type) ?? []) handler(event);
    if (type === "message") this.onmessage?.(event);
  }

  /** Test helper: shorthand for the app's actual named `prices` event. */
  emitPrices(ticks: unknown[]): void {
    this.emit("prices", { ticks });
  }

  /** Test helper: simulate a connection error (the browser auto-retries). */
  fail(): void {
    this.readyState = StubEventSource.CONNECTING;
    this.onerror?.(new Event("error"));
  }
}
