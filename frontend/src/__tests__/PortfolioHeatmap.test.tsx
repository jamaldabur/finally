import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import PortfolioHeatmap, { pnlColor } from "@/components/PortfolioHeatmap";

describe("pnlColor", () => {
  it("is neutral gray at zero P&L", () => {
    expect(pnlColor(0)).toBe("rgb(35, 42, 53)");
  });

  it("saturates to full green at or beyond +10%", () => {
    expect(pnlColor(10)).toBe("rgb(63, 185, 80)");
    expect(pnlColor(25)).toBe("rgb(63, 185, 80)");
  });

  it("saturates to full red at or beyond -10%", () => {
    expect(pnlColor(-10)).toBe("rgb(229, 83, 75)");
    expect(pnlColor(-25)).toBe("rgb(229, 83, 75)");
  });

  it("is paler than the saturated color for a small gain", () => {
    const small = pnlColor(1);
    const large = pnlColor(10);
    expect(small).not.toBe(large);
  });
});

describe("PortfolioHeatmap", () => {
  it("shows an empty state with no positions", () => {
    render(<PortfolioHeatmap positions={[]} />);
    expect(screen.getByText(/No open positions/)).toBeInTheDocument();
  });
});
