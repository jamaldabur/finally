import { test, expect } from "@playwright/test";
import { readCash } from "./helpers";

// Uses GOOGL, which no other spec file trades, to avoid cross-file
// interference now that all specs share one running app/database.
const TICKER = "GOOGL";

test.describe("trading", () => {
  test("buy increases the position and decreases cash, sell reverses it", async ({ page }) => {
    await page.goto("/");

    // GET /api/portfolio resolves asynchronously after mount; wait for the
    // real balance to render before using it as a baseline (otherwise the
    // unresolved "—" placeholder parses to 0).
    await expect(page.getByTestId("cash-balance")).not.toHaveText("—");
    const cashBefore = await readCash(page);

    await page.getByPlaceholder("Ticker", { exact: true }).fill(TICKER);
    await page.getByPlaceholder("Qty").fill("2");
    await page.getByRole("button", { name: "Buy" }).click();

    await expect(page.getByRole("status")).toContainText(`Bought 2 ${TICKER}`);
    const positionRow = page.getByTestId(`position-row-${TICKER}`);
    await expect(positionRow).toBeVisible();
    await expect(positionRow.locator("td").nth(1)).toHaveText("2");

    await expect(async () => {
      const cashAfterBuy = await readCash(page);
      expect(cashAfterBuy).toBeLessThan(cashBefore);
    }).toPass({ timeout: 10_000 });

    const cashAfterBuy = await readCash(page);

    // Sell the full position back.
    await page.getByPlaceholder("Ticker", { exact: true }).fill(TICKER);
    await page.getByPlaceholder("Qty").fill("2");
    await page.getByRole("button", { name: "Sell" }).click();

    await expect(page.getByRole("status")).toContainText(`Sold 2 ${TICKER}`);
    await expect(positionRow).not.toBeVisible();

    await expect(async () => {
      const cashAfterSell = await readCash(page);
      expect(cashAfterSell).toBeGreaterThan(cashAfterBuy);
    }).toPass({ timeout: 10_000 });
  });
});
