import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import WatchlistPanel from "@/components/WatchlistPanel";
import * as api from "@/lib/api";
import * as marketData from "@/lib/marketData";
import type { PriceTick } from "@/lib/types";

vi.mock("@/lib/marketData", async () => {
  const actual = await vi.importActual<typeof import("@/lib/marketData")>("@/lib/marketData");
  return { ...actual, useMarketData: vi.fn() };
});

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, addToWatchlist: vi.fn(), removeFromWatchlist: vi.fn() };
});

const mockUseMarketData = vi.mocked(marketData.useMarketData);
const mockAdd = vi.mocked(api.addToWatchlist);
const mockRemove = vi.mocked(api.removeFromWatchlist);

function tick(ticker: string, price: number, previous: number): PriceTick {
  return {
    ticker,
    price,
    previous_price: previous,
    timestamp: new Date().toISOString(),
    direction: price > previous ? "up" : price < previous ? "down" : "unchanged",
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  mockUseMarketData.mockReturnValue({
    status: "connected",
    prices: {
      AAPL: tick("AAPL", 191.5, 190),
      GOOGL: tick("GOOGL", 174, 175),
    },
    history: {
      AAPL: [{ time: 1, price: 190 }, { time: 2, price: 191.5 }],
      GOOGL: [{ time: 1, price: 175 }, { time: 2, price: 174 }],
    },
  });
});

describe("WatchlistPanel", () => {
  it("renders each watched ticker with its live price", () => {
    render(
      <WatchlistPanel tickers={["AAPL", "GOOGL"]} selected={null} onSelect={() => {}} onWatchlistChanged={() => {}} />
    );
    expect(screen.getByText("AAPL")).toBeInTheDocument();
    expect(screen.getByText("GOOGL")).toBeInTheDocument();
    expect(screen.getByText("$191.50")).toBeInTheDocument();
    expect(screen.getByText("$174.00")).toBeInTheDocument();
  });

  it("calls onSelect when a row is clicked", () => {
    const onSelect = vi.fn();
    render(
      <WatchlistPanel tickers={["AAPL"]} selected={null} onSelect={onSelect} onWatchlistChanged={() => {}} />
    );
    fireEvent.click(screen.getByTestId("watchlist-row-AAPL"));
    expect(onSelect).toHaveBeenCalledWith("AAPL");
  });

  it("adds a ticker via the form and reports the updated list", async () => {
    mockAdd.mockResolvedValue({ ticker: "MSFT" });
    const onWatchlistChanged = vi.fn();
    render(
      <WatchlistPanel tickers={["AAPL"]} selected={null} onSelect={() => {}} onWatchlistChanged={onWatchlistChanged} />
    );
    fireEvent.change(screen.getByPlaceholderText("Add ticker…"), { target: { value: "msft" } });
    fireEvent.click(screen.getByRole("button", { name: "Add" }));

    await waitFor(() => expect(mockAdd).toHaveBeenCalledWith("MSFT"));
    expect(onWatchlistChanged).toHaveBeenCalledWith(["AAPL", "MSFT"]);
  });

  it("shows an error when adding an unrecognized ticker fails", async () => {
    mockAdd.mockRejectedValue(new api.ApiError(400, "Unrecognized ticker"));
    render(
      <WatchlistPanel tickers={["AAPL"]} selected={null} onSelect={() => {}} onWatchlistChanged={() => {}} />
    );
    fireEvent.change(screen.getByPlaceholderText("Add ticker…"), { target: { value: "ZZZZ" } });
    fireEvent.click(screen.getByRole("button", { name: "Add" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Unrecognized ticker");
  });

  it("removes a ticker and reports the updated list", async () => {
    mockRemove.mockResolvedValue(undefined);
    const onWatchlistChanged = vi.fn();
    render(
      <WatchlistPanel
        tickers={["AAPL", "GOOGL"]}
        selected={null}
        onSelect={() => {}}
        onWatchlistChanged={onWatchlistChanged}
      />
    );
    fireEvent.click(screen.getByLabelText("Remove AAPL"));

    await waitFor(() => expect(mockRemove).toHaveBeenCalledWith("AAPL"));
    expect(onWatchlistChanged).toHaveBeenCalledWith(["GOOGL"]);
  });
});
