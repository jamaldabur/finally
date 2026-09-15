import { describe, expect, it, beforeEach, afterEach, vi } from "vitest";
import { act, render, screen } from "@testing-library/react";
import { MarketDataProvider, useMarketData } from "@/lib/marketData";
import type { PriceStreamEvent } from "@/lib/types";

class FakeEventSource {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSED = 2;

  readyState = FakeEventSource.CONNECTING;
  onopen: (() => void) | null = null;
  onerror: (() => void) | null = null;
  private listeners: Record<string, ((event: MessageEvent<string>) => void)[]> = {};
  static instances: FakeEventSource[] = [];

  constructor(public url: string) {
    FakeEventSource.instances.push(this);
  }

  addEventListener(type: string, listener: (event: MessageEvent<string>) => void) {
    (this.listeners[type] ??= []).push(listener);
  }

  removeEventListener(type: string, listener: (event: MessageEvent<string>) => void) {
    this.listeners[type] = (this.listeners[type] ?? []).filter((l) => l !== listener);
  }

  open() {
    this.readyState = FakeEventSource.OPEN;
    this.onopen?.();
  }

  // Mirrors the backend's real wire format: a named "prices" SSE event.
  emit(payload: PriceStreamEvent) {
    const event = { data: JSON.stringify(payload) } as MessageEvent<string>;
    for (const listener of this.listeners["prices"] ?? []) listener(event);
  }

  close() {
    this.readyState = FakeEventSource.CLOSED;
  }
}

function Probe() {
  const { prices, history, status } = useMarketData();
  return (
    <div>
      <div data-testid="status">{status}</div>
      <div data-testid="price">{prices.AAPL?.price ?? "none"}</div>
      <div data-testid="history-length">{(history.AAPL ?? []).length}</div>
    </div>
  );
}

describe("MarketDataProvider", () => {
  beforeEach(() => {
    FakeEventSource.instances = [];
    // @ts-expect-error - stubbing the global for the test
    global.EventSource = FakeEventSource;
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("reports connected once the stream opens", () => {
    render(
      <MarketDataProvider>
        <Probe />
      </MarketDataProvider>
    );
    const es = FakeEventSource.instances[0];
    act(() => es.open());
    expect(screen.getByTestId("status")).toHaveTextContent("connected");
  });

  it("accumulates a history point for a genuine price change", () => {
    render(
      <MarketDataProvider>
        <Probe />
      </MarketDataProvider>
    );
    const es = FakeEventSource.instances[0];
    act(() => es.open());

    act(() =>
      es.emit({ ticks: [{ ticker: "AAPL", price: 190, previous_price: 190, timestamp: "t1", direction: "unchanged" }] })
    );
    expect(screen.getByTestId("history-length")).toHaveTextContent("1");

    act(() =>
      es.emit({ ticks: [{ ticker: "AAPL", price: 191, previous_price: 190, timestamp: "t2", direction: "up" }] })
    );
    expect(screen.getByTestId("price")).toHaveTextContent("191");
    expect(screen.getByTestId("history-length")).toHaveTextContent("2");
  });

  it("does not grow history on a repeated unchanged heartbeat", () => {
    render(
      <MarketDataProvider>
        <Probe />
      </MarketDataProvider>
    );
    const es = FakeEventSource.instances[0];
    act(() => es.open());

    act(() =>
      es.emit({ ticks: [{ ticker: "AAPL", price: 190, previous_price: 190, timestamp: "t1", direction: "unchanged" }] })
    );
    act(() =>
      es.emit({ ticks: [{ ticker: "AAPL", price: 190, previous_price: 190, timestamp: "t2", direction: "unchanged" }] })
    );
    act(() =>
      es.emit({ ticks: [{ ticker: "AAPL", price: 190, previous_price: 190, timestamp: "t3", direction: "unchanged" }] })
    );

    expect(screen.getByTestId("history-length")).toHaveTextContent("1");
    expect(screen.getByTestId("price")).toHaveTextContent("190");
  });
});
