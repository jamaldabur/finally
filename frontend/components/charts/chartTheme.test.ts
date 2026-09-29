/**
 * Colour-scale arithmetic tests (Phase 6, TEST-04). Every expected value
 * below is hand-computed from `mixColor`'s own documented formula
 * (`channel = round(a + (b - a) * t)`) against the hex constants in
 * `chartTheme.ts` — never derived by calling the function under test (a
 * prohibition in this plan). Comments beside each assertion show the
 * per-channel arithmetic so the values can be independently re-checked.
 *
 * Non-vacuity check performed for this task: temporarily changed
 * `HEATMAP_CAP_PCT` from 10 to 20 in `chartTheme.ts`. Result: the `10 ->
 * #4ade80` and `9.9 -> #4adc7f` cases both failed (intensity at 10% halved
 * to 0.5 under a 20% cap, producing the mid-scale colour instead of the
 * capped one). Restored `HEATMAP_CAP_PCT` to 10; all tests passed again.
 * File confirmed byte-identical to `726046a`.
 */

import { describe, it, expect } from "vitest";
import {
  heatmapIntensity,
  divergingFill,
  mixColor,
  tileTextColor,
  trendDirection,
  trendStroke,
  HEX_NEUTRAL,
  HEX_GAIN,
  CHART_GAIN,
  CHART_LOSS,
} from "@/components/charts/chartTheme";

describe("heatmapIntensity", () => {
  it("is 0 at 0% change", () => {
    expect(heatmapIntensity(0)).toBe(0);
  });

  it("is 0.5 at exactly half the cap, either sign", () => {
    expect(heatmapIntensity(5)).toBe(0.5);
    expect(heatmapIntensity(-5)).toBe(0.5);
  });

  it("saturates at 1 at and beyond the cap, either sign", () => {
    expect(heatmapIntensity(10)).toBe(1);
    expect(heatmapIntensity(-10)).toBe(1);
    expect(heatmapIntensity(25)).toBe(1);
    expect(heatmapIntensity(-25)).toBe(1);
  });

  it("is close to but short of full saturation one step inside the cap", () => {
    // min(9.99, 10) / 10 = 0.999
    expect(heatmapIntensity(9.99)).toBeCloseTo(0.999);
  });

  it("treats non-finite input as neutral", () => {
    expect(heatmapIntensity(NaN)).toBe(0);
    expect(heatmapIntensity(Infinity)).toBe(0);
  });
});

describe("divergingFill", () => {
  it("is the neutral colour at 0% change", () => {
    expect(divergingFill(0)).toBe("#30363d");
  });

  it("mixes to the mid-scale gain colour at 5% (t=0.5 between #30363d and #4ade80)", () => {
    // R: 48 + (74-48)*0.5 = 61 -> 3d
    // G: 54 + (222-54)*0.5 = 138 -> 8a
    // B: 61 + (128-61)*0.5 = round(94.5) = 95 -> 5f
    expect(divergingFill(5)).toBe("#3d8a5f");
  });

  it("mixes to the mid-scale loss colour at -5% (t=0.5 between #30363d and #f87171)", () => {
    // R: 48 + (248-48)*0.5 = 148 -> 94
    // G: 54 + (113-54)*0.5 = round(83.5) = 84 -> 54
    // B: 61 + (113-61)*0.5 = 87 -> 57
    expect(divergingFill(-5)).toBe("#945457");
  });

  it("is one step inside the cap at 9.9% — close to but distinct from the full gain colour", () => {
    // intensity = min(9.9,10)/10 = 0.99
    // R: 48 + (74-48)*0.99 = round(73.74) = 74 -> 4a
    // G: 54 + (222-54)*0.99 = round(220.32) = 220 -> dc
    // B: 61 + (128-61)*0.99 = round(127.33) = 127 -> 7f
    expect(divergingFill(9.9)).toBe("#4adc7f");
  });

  it("reaches the full gain colour at and beyond the cap", () => {
    expect(divergingFill(10)).toBe("#4ade80");
    expect(divergingFill(10.01)).toBe("#4ade80");
    expect(divergingFill(50)).toBe("#4ade80");
  });

  it("reaches the full loss colour at and beyond the cap", () => {
    expect(divergingFill(-10)).toBe("#f87171");
    expect(divergingFill(-50)).toBe("#f87171");
  });

  it("treats a non-finite change as neutral", () => {
    expect(divergingFill(NaN)).toBe("#30363d");
  });
});

describe("mixColor", () => {
  it("clamps t above 1 to the second colour", () => {
    expect(mixColor(HEX_NEUTRAL, HEX_GAIN, 1.5)).toBe(HEX_GAIN);
  });

  it("clamps t below 0 to the first colour", () => {
    expect(mixColor(HEX_NEUTRAL, HEX_GAIN, -1)).toBe(HEX_NEUTRAL);
  });

  it("treats a non-finite t as the first colour", () => {
    expect(mixColor(HEX_NEUTRAL, HEX_GAIN, NaN)).toBe(HEX_NEUTRAL);
  });
});

describe("tileTextColor", () => {
  it("uses light ink just below the ink threshold, either sign", () => {
    expect(tileTextColor(4.99)).toBe("#e6edf3");
    expect(tileTextColor(-4.99)).toBe("#e6edf3");
  });

  it("uses light ink at 0% change", () => {
    expect(tileTextColor(0)).toBe("#e6edf3");
  });

  it("switches to dark ink exactly at the 5% threshold, either sign", () => {
    expect(tileTextColor(5)).toBe("#0d1117");
    expect(tileTextColor(-5)).toBe("#0d1117");
  });
});

describe("trendDirection / trendStroke", () => {
  it("is up when the latest price equals the first price", () => {
    expect(trendDirection(100, 100)).toBe("up");
  });

  it("is down when the latest price is below the first price", () => {
    expect(trendDirection(100, 99.99)).toBe("down");
  });

  it("is down when either value is unknown", () => {
    expect(trendDirection(undefined, 5)).toBe("down");
    expect(trendDirection(5, undefined)).toBe("down");
  });

  it("maps up/down to the shared gain/loss stroke constants", () => {
    expect(trendStroke("up")).toBe(CHART_GAIN);
    expect(trendStroke("down")).toBe(CHART_LOSS);
  });
});
