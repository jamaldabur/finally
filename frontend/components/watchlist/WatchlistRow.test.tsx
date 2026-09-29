/**
 * WatchlistRow tests (Phase 6, TEST-04), driven through the real provider
 * tree via `renderWithProviders`. Covers the pre-tick price/em-dash state,
 * the session-change percentage (computed since the first tick observed
 * this session, per D-05/D-09), the sparkline's trend label, and click/Enter
 * ticker selection via the shared `ChartSelectionProvider`.
 *
 * Non-vacuity check performed for this task: temporarily changed
 * `WatchlistRow.tsx`'s change-colour comparison from `changePct >= 0` to
 * `changePct > 0`. Result: the "first tick shows +0.00% in text-green-400"
 * case failed (0% now rendered muted instead of green). Restored the
 * original `>= 0` comparison; all tests passed again. File confirmed
 * byte-identical to `726046a`.
 */

import { act, fireEvent, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { WatchlistRow } from "@/components/watchlist/WatchlistRow";
import { useChartSelection } from "@/lib/chartSelection";
import { renderWithProviders } from "@/test-support/renderWithProviders";
import { stubFetch } from "@/test-support/fetchStub";
import { StubEventSource } from "@/test-support/eventSourceStub";
import type { WatchlistEntry, PriceTick } from "@/lib/types";

function entry(
  overrides: Partial<WatchlistEntry> & Pick<WatchlistEntry, "ticker">,
): WatchlistEntry {
  return {
    price: null,
    previous_price: null,
    direction: null,
    timestamp: null,
    ...overrides,
  };
}

function tickFor(ticker: string, price: number): PriceTick {
  return {
    ticker,
    price,
    previous_price: price - 1,
    timestamp: new Date().toISOString(),
    direction: "up",
  };
}

function SelectionProbe() {
  const { selectedTicker } = useChartSelection();
  return <div>{`selected:${selectedTicker ?? "none"}`}</div>;
}

describe("WatchlistRow", () => {
  it("shows the API-seeded price and an em-dash change before any tick", () => {
    stubFetch();
    renderWithProviders(
      <WatchlistRow entry={entry({ ticker: "AAPL", price: 190 })} />,
    );

    expect(screen.getByText("190.00")).toBeInTheDocument();
    const changeCell = screen.getByText("—");
    expect(changeCell).toHaveClass("text-terminal-text-muted");
  });

  it("shows +0.00% in green on the first tick", () => {
    stubFetch();
    renderWithProviders(
      <WatchlistRow entry={entry({ ticker: "AAPL", price: 190 })} />,
    );

    act(() => {
      StubEventSource.latest().emitPrices([tickFor("AAPL", 100)]);
    });

    const changeCell = screen.getByText("+0.00%");
    expect(changeCell).toHaveClass("text-green-400");
  });

  it("shows a positive change in green once the price rises above the first tick", () => {
    stubFetch();
    renderWithProviders(
      <WatchlistRow entry={entry({ ticker: "AAPL", price: 190 })} />,
    );

    act(() => {
      StubEventSource.latest().emitPrices([tickFor("AAPL", 100)]);
    });
    act(() => {
      StubEventSource.latest().emitPrices([tickFor("AAPL", 105)]);
    });

    const changeCell = screen.getByText("+5.00%");
    expect(changeCell).toHaveClass("text-green-400");
  });

  it("shows a negative change in red once the price falls below the first tick", () => {
    stubFetch();
    renderWithProviders(
      <WatchlistRow entry={entry({ ticker: "AAPL", price: 190 })} />,
    );

    act(() => {
      StubEventSource.latest().emitPrices([tickFor("AAPL", 100)]);
    });
    act(() => {
      StubEventSource.latest().emitPrices([tickFor("AAPL", 95)]);
    });

    const changeCell = screen.getByText("-5.00%");
    expect(changeCell).toHaveClass("text-red-400");
  });

  it("rounds float noise away — first tick 3 then 3.3 displays +10.00%, never the raw 9.999999999999996", () => {
    stubFetch();
    renderWithProviders(
      <WatchlistRow entry={entry({ ticker: "AAPL", price: 190 })} />,
    );

    act(() => {
      StubEventSource.latest().emitPrices([tickFor("AAPL", 3)]);
    });
    act(() => {
      StubEventSource.latest().emitPrices([tickFor("AAPL", 3.3)]);
    });

    expect(screen.getByText("+10.00%")).toBeInTheDocument();
  });

  it("shows an em-dash price when the entry has no seeded price and no tick has arrived", () => {
    stubFetch();
    renderWithProviders(
      <WatchlistRow entry={entry({ ticker: "AAPL", price: null })} />,
    );

    // Both the price cell and the unresolved change cell render an
    // em-dash before any tick has arrived.
    expect(screen.getAllByText("—")).toHaveLength(2);
  });

  it("exposes the sparkline as an 'up' trending image after one tick", () => {
    stubFetch();
    renderWithProviders(
      <WatchlistRow entry={entry({ ticker: "AAPL", price: 190 })} />,
    );

    act(() => {
      StubEventSource.latest().emitPrices([tickFor("AAPL", 100)]);
    });

    expect(
      screen.getByRole("img", { name: "AAPL trending up" }),
    ).toBeInTheDocument();
  });

  it("exposes the sparkline as a 'down' trending image once the price drops below the first tick", () => {
    stubFetch();
    renderWithProviders(
      <WatchlistRow entry={entry({ ticker: "AAPL", price: 190 })} />,
    );

    act(() => {
      StubEventSource.latest().emitPrices([tickFor("AAPL", 100)]);
    });
    act(() => {
      StubEventSource.latest().emitPrices([tickFor("AAPL", 95)]);
    });

    expect(
      screen.getByRole("img", { name: "AAPL trending down" }),
    ).toBeInTheDocument();
  });

  it("selects its ticker for the main chart when clicked", () => {
    stubFetch();
    renderWithProviders(
      <>
        <WatchlistRow entry={entry({ ticker: "AAPL", price: 190 })} />
        <SelectionProbe />
      </>,
    );

    expect(screen.getByText("selected:none")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button"));
    expect(screen.getByText("selected:AAPL")).toBeInTheDocument();
  });

  it("selects its ticker for the main chart on Enter", () => {
    stubFetch();
    renderWithProviders(
      <>
        <WatchlistRow entry={entry({ ticker: "AAPL", price: 190 })} />
        <SelectionProbe />
      </>,
    );

    fireEvent.keyDown(screen.getByRole("button"), { key: "Enter" });
    expect(screen.getByText("selected:AAPL")).toBeInTheDocument();
  });
});
