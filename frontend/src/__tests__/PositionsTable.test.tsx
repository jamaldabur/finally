import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import PositionsTable from "@/components/PositionsTable";
import type { Position } from "@/lib/types";

const positions: Position[] = [
  { ticker: "AAPL", quantity: 10, avg_cost: 180, current_price: 190, unrealized_pnl: 100, unrealized_pnl_pct: 0.0556 },
  { ticker: "TSLA", quantity: 2, avg_cost: 300, current_price: 250, unrealized_pnl: -100, unrealized_pnl_pct: -0.1667 },
];

describe("PositionsTable", () => {
  it("shows an empty state with no positions", () => {
    render(<PositionsTable positions={[]} />);
    expect(screen.getByText(/No open positions/)).toBeInTheDocument();
  });

  it("renders each position's computed values", () => {
    render(<PositionsTable positions={positions} />);
    expect(screen.getByTestId("position-row-AAPL")).toHaveTextContent("AAPL");
    expect(screen.getByTestId("position-row-AAPL")).toHaveTextContent("$180.00");
    expect(screen.getByTestId("position-row-AAPL")).toHaveTextContent("$190.00");
    expect(screen.getByTestId("position-row-AAPL")).toHaveTextContent("$100.00");
    expect(screen.getByTestId("position-row-AAPL")).toHaveTextContent("+5.56%");

    expect(screen.getByTestId("position-row-TSLA")).toHaveTextContent("-$100.00");
    expect(screen.getByTestId("position-row-TSLA")).toHaveTextContent("-16.67%");
  });
});
