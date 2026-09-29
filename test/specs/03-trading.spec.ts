import type { Page } from "@playwright/test";
import { test, expect } from "@playwright/test";
import {
  watchlistRow,
  readCash,
  positionRow,
  tradeViaBar,
  parseMoney,
  apiPortfolio,
} from "./helpers";

/**
 * Trade bar lifecycle (Task 1, 06-06-PLAN.md). Every trade uses AAPL or
 * GOOGL — default-watchlist tickers whose prices are always cached, so a
 * trade never fails on "No live price available" (backend/app/portfolio/
 * service.py). Runs immediately after 01-fresh-start.spec.ts in file-name
 * order (P-10) — AAPL/GOOGL are untouched by any other spec, but each test
 * still measures its own before/after deltas rather than assuming seed
 * state.
 */

/** Polls readCash until the header's Cash figure has actually rendered. */
async function waitForCash(page: Page): Promise<number> {
  let value = NaN;
  await expect
    .poll(
      async () => {
        try {
          value = await readCash(page);
          return true;
        } catch {
          return false;
        }
      },
      { timeout: 15_000 },
    )
    .toBe(true);
  return value;
}

/**
 * The trade bar's own `role="alert"` error paragraph, scoped to the "Trade"
 * section — `page.getByRole("alert")` alone also matches Next.js's own
 * `#__next-route-announcer__` live region and trips a strict-mode
 * violation.
 */
function tradeBarAlert(page: Page) {
  return page
    .locator("section", {
      has: page.getByRole("heading", { name: "Trade", exact: true }),
    })
    .getByRole("alert");
}

test.describe("trading via the trade bar", () => {
  test("buying and selling moves cash and positions", async ({ page }) => {
    await page.goto("/");

    await test.step("wait for AAPL to show a live price", async () => {
      await expect
        .poll(async () => watchlistRow(page, "AAPL").innerText())
        .not.toContain("—");
    });

    const cash0 = await waitForCash(page);

    await test.step("buy 5 AAPL", async () => {
      await tradeViaBar(page, "buy", "AAPL", 5);
      await expect(positionRow(page, "AAPL")).toBeVisible();
      await expect(positionRow(page, "AAPL").locator("td").nth(1)).toHaveText(
        "5",
      );
    });

    const avgCost = parseMoney(
      await positionRow(page, "AAPL").locator("td").nth(2).innerText(),
    );

    let cash1 = cash0;
    await test.step("cash drops by 5x average cost", async () => {
      await expect
        .poll(
          async () => {
            cash1 = await readCash(page);
            return cash1;
          },
          { timeout: 15_000 },
        )
        .toBeLessThan(cash0);

      const expectedDelta = 5 * avgCost;
      const actualDelta = cash0 - cash1;
      expect(Math.abs(actualDelta - expectedDelta)).toBeLessThanOrEqual(
        5 * 0.005 + 0.01,
      );
    });

    await test.step("sell 2 AAPL — quantity drops to 3, cash rises", async () => {
      await tradeViaBar(page, "sell", "AAPL", 2);
      await expect(positionRow(page, "AAPL").locator("td").nth(1)).toHaveText(
        "3",
      );

      let cash2 = cash1;
      await expect
        .poll(
          async () => {
            cash2 = await readCash(page);
            return cash2;
          },
          { timeout: 15_000 },
        )
        .toBeGreaterThan(cash1);

      // Sanity band, not an exact equality — the fill uses the live price,
      // which moves between the buy and this sell.
      const delta = cash2 - cash1;
      expect(delta).toBeGreaterThanOrEqual(2 * 0.8 * avgCost);
      expect(delta).toBeLessThanOrEqual(2 * 1.2 * avgCost);
    });

    await test.step("sell remaining 3 AAPL — row disappears", async () => {
      await tradeViaBar(page, "sell", "AAPL", 3);
      await expect(positionRow(page, "AAPL")).toHaveCount(0);
    });
  });

  test("rejected trades change nothing", async ({ page }) => {
    await page.goto("/");
    const before = await apiPortfolio(page);

    await test.step("selling shares not held is rejected", async () => {
      await tradeViaBar(page, "sell", "GOOGL", 1);
      await expect(tradeBarAlert(page)).toContainText(
        "Insufficient shares",
      );
    });

    await test.step("buying beyond available cash is rejected", async () => {
      await tradeViaBar(page, "buy", "GOOGL", 100000);
      await expect(tradeBarAlert(page)).toContainText(
        "Insufficient cash",
      );
    });

    await test.step("a zero quantity is refused before any request", async () => {
      await tradeViaBar(page, "buy", "GOOGL", 0);
      await expect(tradeBarAlert(page)).toHaveText(
        "Enter a quantity greater than 0.",
      );
    });

    // Server values, not the header — the header only refreshes after a
    // success, so it could not show a change (or lack of one) either way.
    const after = await apiPortfolio(page);
    expect(after.cash_balance).toBe(before.cash_balance);
    expect(after.positions.some((p) => p.ticker === "GOOGL")).toBe(false);
  });
});
