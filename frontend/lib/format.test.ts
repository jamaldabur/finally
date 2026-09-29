/**
 * Formatter tests (Phase 6, TEST-04). Every expected value below is
 * hand-computed from `format.ts`'s own documented formula (`n >= 0` gives
 * the "+" sign, `toFixed(2)` on the raw binary value) — never derived by
 * calling the function under test. The backend rounds every monetary or
 * percentage value to the cent before it ever reaches these formatters
 * (D-04); the binary-rounding and negative-zero cases below only matter for
 * the one client-side derivation (WatchlistRow's session change percentage)
 * that computes a percentage from raw floats at render time.
 */

import { describe, it, expect } from "vitest";
import { formatCurrency, formatSignedCurrency, formatPercent } from "@/lib/format";

describe("formatCurrency", () => {
  it("renders whole numbers with no thousands separator", () => {
    expect(formatCurrency(10000)).toBe("$10000.00");
  });

  it("renders a value already carrying cents", () => {
    expect(formatCurrency(1234.5)).toBe("$1234.50");
  });

  it("renders zero", () => {
    expect(formatCurrency(0)).toBe("$0.00");
  });

  it("applies toFixed(2) to the binary double — 1.005 rounds down to 1.00 (display-only; backend values arrive already cent-rounded)", () => {
    expect(formatCurrency(1.005)).toBe("$1.00");
  });
});

describe("formatSignedCurrency", () => {
  it("prefixes a positive value with +", () => {
    expect(formatSignedCurrency(200)).toBe("+$200.00");
  });

  it("prefixes a negative value with -", () => {
    expect(formatSignedCurrency(-120)).toBe("-$120.00");
  });

  it("treats zero as positive", () => {
    expect(formatSignedCurrency(0)).toBe("+$0.00");
  });

  it("renders a backend -0.0 (surviving JSON parsing as JS negative zero) with a plus sign, never a negative sign", () => {
    expect(formatSignedCurrency(-0)).toBe("+$0.00");
  });
});

describe("formatPercent", () => {
  it("prefixes a positive value with +", () => {
    expect(formatPercent(20)).toBe("+20.00%");
  });

  it("prefixes a negative value with -", () => {
    expect(formatPercent(-10)).toBe("-10.00%");
  });

  it("treats zero as positive", () => {
    expect(formatPercent(0)).toBe("+0.00%");
  });

  it("treats negative zero as positive", () => {
    expect(formatPercent(-0)).toBe("+0.00%");
  });

  it("rounds float noise away — a session change of 3.00 to 3.30 computes to 9.999999999999996 but displays as +10.00%", () => {
    expect(formatPercent(9.999999999999996)).toBe("+10.00%");
  });
});
