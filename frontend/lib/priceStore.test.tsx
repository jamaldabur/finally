/**
 * SSE store tests (Phase 6, TEST-04): the named `prices` event, the ignored
 * default `message` event, first-price recording, price-history
 * de-duplication, and the connection-status state machine (Phase 2 D-06)
 * including its 5-second disconnect grace window.
 *
 * A test-local `Probe` renders plain text lines so every assertion is a
 * `screen.getByText` query, never a direct read of internal store state.
 */

import { render, screen, act } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { PriceStoreProvider, usePriceStore } from "@/lib/priceStore";
import { StubEventSource } from "@/test-support/eventSourceStub";
import type { PriceTick } from "@/lib/types";

function Probe({ ticker }: { ticker: string }) {
  const { status, prices, firstPrices, priceHistory } = usePriceStore();
  const currentTick = prices.get(ticker);
  const first = firstPrices.get(ticker);
  const history = priceHistory.get(ticker) ?? [];
  return (
    <>
      <div>{`status:${status}`}</div>
      <div>{`price:${currentTick ? currentTick.price : "none"}`}</div>
      <div>{`first:${first !== undefined ? first : "none"}`}</div>
      <div>{`history:${history.length}`}</div>
    </>
  );
}

function tick(
  ticker: string,
  price: number,
  direction: PriceTick["direction"] = "up",
): PriceTick {
  return {
    ticker,
    price,
    previous_price: price - 1,
    timestamp: new Date().toISOString(),
    direction,
  };
}

function renderProbe(ticker = "AAPL") {
  return render(
    <PriceStoreProvider>
      <Probe ticker={ticker} />
    </PriceStoreProvider>,
  );
}

describe("PriceStoreProvider / usePriceStore", () => {
  it("opens exactly one EventSource with a URL ending in /api/stream/prices", () => {
    renderProbe();
    expect(StubEventSource.instances).toHaveLength(1);
    expect(StubEventSource.latest().url.endsWith("/api/stream/prices")).toBe(
      true,
    );
  });

  it("starts in the reconnecting status before anything happens", () => {
    renderProbe();
    expect(screen.getByText("status:reconnecting")).toBeInTheDocument();
  });

  it("becomes connected when the connection opens", () => {
    renderProbe();
    act(() => {
      StubEventSource.latest().open();
    });
    expect(screen.getByText("status:connected")).toBeInTheDocument();
  });

  it("applies a tick from the named prices event and becomes connected", () => {
    renderProbe();
    act(() => {
      StubEventSource.latest().emitPrices([tick("AAPL", 190)]);
    });
    expect(screen.getByText("price:190")).toBeInTheDocument();
    expect(screen.getByText("status:connected")).toBeInTheDocument();
  });

  it("ignores an unnamed message event carrying the same payload", () => {
    renderProbe();
    act(() => {
      StubEventSource.latest().emitPrices([tick("AAPL", 190)]);
    });
    act(() => {
      StubEventSource.latest().emit("message", {
        ticks: [tick("AAPL", 999)],
      });
    });
    expect(screen.getByText("price:190")).toBeInTheDocument();
  });

  it("keeps the first recorded price after a second, different tick", () => {
    renderProbe();
    act(() => {
      StubEventSource.latest().emitPrices([tick("AAPL", 190)]);
    });
    act(() => {
      StubEventSource.latest().emitPrices([tick("AAPL", 195)]);
    });
    expect(screen.getByText("first:190")).toBeInTheDocument();
    expect(screen.getByText("price:195")).toBeInTheDocument();
  });

  it("history stays length 1 for a repeated price and grows to 2 on a real change", () => {
    renderProbe();
    act(() => {
      StubEventSource.latest().emitPrices([tick("AAPL", 190)]);
    });
    expect(screen.getByText("history:1")).toBeInTheDocument();

    act(() => {
      StubEventSource.latest().emitPrices([tick("AAPL", 190)]);
    });
    expect(screen.getByText("history:1")).toBeInTheDocument();

    act(() => {
      StubEventSource.latest().emitPrices([tick("AAPL", 191)]);
    });
    expect(screen.getByText("history:2")).toBeInTheDocument();
  });

  it("reports disconnected only after the 5s grace window since the last error", () => {
    vi.useFakeTimers();
    renderProbe();
    act(() => {
      StubEventSource.latest().fail();
    });

    act(() => {
      vi.advanceTimersByTime(4999);
    });
    expect(screen.getByText("status:reconnecting")).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(1);
    });
    expect(screen.getByText("status:disconnected")).toBeInTheDocument();
  });

  it("stays connected past the original grace deadline when it reopens within the window", () => {
    vi.useFakeTimers();
    renderProbe();
    act(() => {
      StubEventSource.latest().fail();
    });
    act(() => {
      vi.advanceTimersByTime(3000);
    });
    act(() => {
      StubEventSource.latest().open();
    });
    act(() => {
      vi.advanceTimersByTime(3000); // total 6000ms since the original fail()
    });
    expect(screen.getByText("status:connected")).toBeInTheDocument();
  });

  it("re-arms a single grace timer across an error burst instead of stacking one per error", () => {
    vi.useFakeTimers();
    renderProbe();
    act(() => {
      StubEventSource.latest().fail(); // t=0, would fire disconnected at t=5000 if not re-armed
    });
    act(() => {
      vi.advanceTimersByTime(3000); // t=3000
    });
    act(() => {
      StubEventSource.latest().fail(); // re-arms: fires at t=3000+5000=8000
    });

    act(() => {
      vi.advanceTimersByTime(2000); // t=5000 total — the original (cleared) timer must not fire
    });
    expect(screen.getByText("status:reconnecting")).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(3000); // t=8000 — the re-armed timer fires now
    });
    expect(screen.getByText("status:disconnected")).toBeInTheDocument();
  });

  it("recovers to connected on a tick during the reconnecting window and never later disconnects", () => {
    vi.useFakeTimers();
    renderProbe();
    act(() => {
      StubEventSource.latest().fail();
    });
    act(() => {
      vi.advanceTimersByTime(2000);
    });
    act(() => {
      StubEventSource.latest().emitPrices([tick("AAPL", 190)]);
    });
    expect(screen.getByText("status:connected")).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(4000); // well past the original 5000ms deadline
    });
    expect(screen.getByText("status:connected")).toBeInTheDocument();
  });

  it("closes the stubbed EventSource on unmount", () => {
    const { unmount } = renderProbe();
    const instance = StubEventSource.latest();
    unmount();
    expect(instance.closed).toBe(true);
  });

  it("throws when used outside PriceStoreProvider", () => {
    vi.spyOn(console, "error").mockImplementation(() => {});

    function BadProbe() {
      usePriceStore();
      return null;
    }

    expect(() => render(<BadProbe />)).toThrow(
      "usePriceStore must be used within PriceStoreProvider",
    );
  });
});
