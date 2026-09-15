import { describe, expect, it } from "vitest";
import { formatCurrency, formatPercent, pctChange } from "@/lib/format";

describe("format helpers", () => {
  it("formats currency with two decimal places", () => {
    expect(formatCurrency(1234.5)).toBe("$1,234.50");
    expect(formatCurrency(-50)).toBe("-$50.00");
  });

  it("prefixes a positive percent with a plus sign", () => {
    expect(formatPercent(5.5)).toBe("+5.50%");
    expect(formatPercent(-5.5)).toBe("-5.50%");
    expect(formatPercent(0)).toBe("0.00%");
  });

  it("computes percent change relative to the previous price", () => {
    expect(pctChange(110, 100)).toBeCloseTo(10);
    expect(pctChange(90, 100)).toBeCloseTo(-10);
    expect(pctChange(100, 0)).toBe(0);
  });
});
