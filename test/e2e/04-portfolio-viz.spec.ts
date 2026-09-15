import { test, expect } from "@playwright/test";

// Buys and holds JPM (untouched by other spec files) so this file always has
// at least one open position to render, regardless of run order among specs
// that buy-then-sell elsewhere.
const TICKER = "JPM";

test.describe("portfolio visualization", () => {
  test("heatmap renders a position rectangle and the P&L chart has data points", async ({ page }) => {
    await page.goto("/");

    // Buy twice so this file records >=2 portfolio snapshots on its own
    // (PLAN.md §7: a snapshot is recorded immediately after every trade),
    // independent of whichever other spec files ran before it.
    await page.getByPlaceholder("Ticker", { exact: true }).fill(TICKER);
    await page.getByPlaceholder("Qty").fill("3");
    await page.getByRole("button", { name: "Buy" }).click();
    await expect(page.getByRole("status")).toContainText(`Bought 3 ${TICKER}`);
    await expect(page.getByTestId(`position-row-${TICKER}`)).toBeVisible();

    await page.getByPlaceholder("Ticker", { exact: true }).fill(TICKER);
    await page.getByPlaceholder("Qty").fill("1");
    await page.getByRole("button", { name: "Buy" }).click();
    await expect(page.getByRole("status")).toContainText(`Bought 1 ${TICKER}`);

    // Heatmap: recharts Treemap renders one <rect> per position node.
    const heatmapRect = page.locator("text=Positions Heatmap").locator("..").locator("svg rect");
    await expect(heatmapRect.first()).toBeVisible({ timeout: 10_000 });

    // P&L chart needs >=2 snapshots to render a line instead of the
    // "Not enough history yet" placeholder.
    await expect(async () => {
      const res = await page.request.get("/api/portfolio/history");
      expect(res.ok()).toBeTruthy();
      const snapshots = await res.json();
      expect(snapshots.length).toBeGreaterThanOrEqual(2);
    }).toPass({ timeout: 10_000 });

    await page.reload();
    const pnlChartLine = page.locator("text=Portfolio Value").locator("..").locator(".recharts-line");
    await expect(pnlChartLine.first()).toBeVisible({ timeout: 10_000 });
  });
});
