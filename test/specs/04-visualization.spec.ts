import { test, expect } from "@playwright/test";
import {
  DEFAULT_TICKERS,
  watchlistRow,
  apiPortfolio,
  heatmapTiles,
  expectedHeatmapFill,
  type HeatmapTile,
} from "./helpers";

/**
 * Sparklines, the main chart, heatmap sizing/colour, and the P&L line
 * (Task 3, 06-06-PLAN.md). Runs after 03-trading.spec.ts in file-name order
 * (P-10) — AAPL/GOOGL are fully unwound by then, so the heatmap test's
 * NVDA/JPM buys land as the only positions.
 */

test.describe("visualization", () => {
  test("sparklines and the main chart draw live price history", async ({
    page,
  }) => {
    await page.goto("/");

    for (const ticker of DEFAULT_TICKERS) {
      await expect(
        page.getByRole("img", {
          name: new RegExp(`^${ticker} trending (up|down)$`),
        }),
      ).toBeVisible();
    }

    await watchlistRow(page, "NVDA").click();
    const mainSection = page.locator("main section").first();
    await expect(
      mainSection.getByRole("heading", { name: "NVDA", exact: true }),
    ).toBeVisible();
    await expect(mainSection.locator(".recharts-line-curve")).toBeVisible({
      timeout: 20_000,
    });
  });

  test("the heatmap sizes tiles by weight and colours them by P&L", async ({
    page,
  }) => {
    const buyNvda = await page.request.post("/api/portfolio/trade", {
      data: { ticker: "NVDA", side: "buy", quantity: 10 },
    });
    expect(buyNvda.ok()).toBeTruthy();
    const buyJpm = await page.request.post("/api/portfolio/trade", {
      data: { ticker: "JPM", side: "buy", quantity: 1 },
    });
    expect(buyJpm.ok()).toBeTruthy();

    await page.goto("/");
    const portfolio = await apiPortfolio(page);
    expect(portfolio.positions.length).toBeGreaterThan(0);

    let tiles: HeatmapTile[] = [];
    await expect
      .poll(
        async () => {
          tiles = await heatmapTiles(page);
          return tiles.length;
        },
        { timeout: 15_000 },
      )
      .toBe(portfolio.positions.length);

    const sortedByValue = [...portfolio.positions].sort(
      (a, b) => b.market_value - a.market_value,
    );
    const largestTicker = sortedByValue[0].ticker;
    const largestValue = sortedByValue[0].market_value;
    const smallestValue = sortedByValue[sortedByValue.length - 1].market_value;

    const sortedByArea = [...tiles].sort((a, b) => b.area - a.area);
    const largestTile = sortedByArea[0];
    const smallestTile = sortedByArea[sortedByArea.length - 1];

    expect(largestTile.ticker).toBe(largestTicker);

    const areaRatio = largestTile.area / smallestTile.area;
    const valueRatio = largestValue / smallestValue;
    expect(Math.abs(areaRatio - valueRatio)).toBeLessThanOrEqual(
      valueRatio * 0.25,
    );

    const nvdaTile = tiles.find((t) => t.ticker === "NVDA");
    expect(nvdaTile?.pct).not.toBeNull();

    for (const tile of tiles) {
      if (tile.pct !== null) {
        expect(tile.fill).toBe(expectedHeatmapFill(parseFloat(tile.pct)));
      }
    }
  });

  test("the P&L chart plots recorded snapshots", async ({ page }) => {
    // Guarantees a snapshot beyond the startup one even if this test runs
    // alone (execute_trade() records one inside the same lock as the fill).
    const buyJpm = await page.request.post("/api/portfolio/trade", {
      data: { ticker: "JPM", side: "buy", quantity: 1 },
    });
    expect(buyJpm.ok()).toBeTruthy();

    const historyRes = await page.request.get(
      "/api/portfolio/history?limit=180",
    );
    expect(historyRes.ok()).toBeTruthy();
    const history: { snapshots: unknown[] } = await historyRes.json();
    expect(history.snapshots.length).toBeGreaterThanOrEqual(2);

    // The history store only fetches on mount and every 30s, so a fresh
    // navigation is what actually picks up the snapshot just recorded.
    await page.goto("/");
    const pnlSection = page.locator("section", {
      has: page.getByRole("heading", { name: "Portfolio Value", exact: true }),
    });
    await expect(pnlSection.locator(".recharts-line-curve")).toBeVisible();
    await expect(pnlSection.getByText("Not enough history yet")).toHaveCount(
      0,
    );
  });
});
