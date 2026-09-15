import { test, expect } from "@playwright/test";

const DEFAULT_TICKERS = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "NFLX"];

test.describe("fresh start", () => {
  test("shows the default watchlist, $10k cash, and streaming prices", async ({ page }) => {
    await page.goto("/");

    for (const ticker of DEFAULT_TICKERS) {
      await expect(page.getByTestId(`watchlist-row-${ticker}`)).toBeVisible();
    }

    await expect(page.getByTestId("cash-balance")).toHaveText("$10,000.00");
    await expect(page.getByTestId("total-value")).toHaveText("$10,000.00");

    // Connection indicator should reach "connected" once the SSE stream is flowing.
    await expect(page.getByTestId("connection-dot")).toHaveAttribute("data-status", "connected");

    // Prices stream in from the simulator — the AAPL row's "—" placeholder
    // should resolve to a real price within a couple of SSE broadcast ticks.
    const aaplPrice = page.getByTestId("watchlist-row-AAPL").locator("td").nth(1);
    await expect(aaplPrice).not.toHaveText("—", { timeout: 10_000 });

    // Confirm it's actually live-updating, not a one-shot render: at least
    // one of the ten rows should change value within a few seconds (the
    // simulator ticks ~every 500ms and rarely leaves all ten unchanged).
    const readAll = () =>
      Promise.all(
        DEFAULT_TICKERS.map((t) => page.getByTestId(`watchlist-row-${t}`).locator("td").nth(1).textContent())
      );
    const before = await readAll();
    await expect(async () => {
      const after = await readAll();
      expect(after.some((text, i) => text !== before[i])).toBeTruthy();
    }).toPass({ timeout: 10_000 });
  });
});
