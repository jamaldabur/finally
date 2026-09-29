import { test, expect } from "@playwright/test";
import { sendChat, chatInput, apiPortfolio, positionRow } from "./helpers";

/**
 * Mocked chat trade execution (Task 2, 06-06-PLAN.md): the pending
 * indicator + disabled input, the exact deterministic mock reply, the
 * inline success/error badges, the resulting position/cash change, and
 * history surviving a reload. Every phrase sent here is confirmed against
 * `build_mock_response()` directly before this browser suite runs (see this
 * plan's `<verify>`).
 */

test.describe("the copilot trades on my behalf", () => {
  test("a chat trade executes and is confirmed inline", async ({ page }) => {
    const before = await apiPortfolio(page);
    expect(before.positions.some((p) => p.ticker === "MSFT")).toBe(false);

    // Delay only the POST so the pending state is observable without
    // touching the app; GET (chat history hydration) passes straight
    // through.
    await page.route("**/api/chat", async (route) => {
      if (route.request().method() === "POST") {
        await new Promise((resolve) => setTimeout(resolve, 1500));
      }
      await route.continue();
    });

    await page.goto("/");
    const input = chatInput(page);
    await input.fill("buy 2 MSFT");
    await input.press("Enter");

    await test.step("pending state is observable", async () => {
      await expect(page.getByText("FinAlly is thinking")).toBeAttached();
      await expect(input).toBeDisabled();
    });

    await test.step("the mock reply, success badge and position land", async () => {
      await expect(
        page.getByText(
          "[LLM_MOCK] Requesting to buy 2.0 shares of MSFT.",
          { exact: true },
        ),
      ).toBeVisible();

      await expect(page.getByText(/buy 2 MSFT @ \$\d+\.\d{2}/i)).toBeVisible();
      // An executed action renders no role="alert" wrapper at all — proves
      // the badge above is a success badge, not an error one.
      await expect(
        page.getByRole("alert").filter({ hasText: "MSFT" }),
      ).toHaveCount(0);

      await expect(page.getByText("FinAlly is thinking")).toHaveCount(0);
      await expect(positionRow(page, "MSFT").locator("td").nth(1)).toHaveText(
        "2",
      );
    });

    const after = await apiPortfolio(page);
    const msft = after.positions.find((p) => p.ticker === "MSFT");
    expect(msft?.quantity).toBe(2);
    expect(before.cash_balance - after.cash_balance).toBeCloseTo(
      2 * (msft?.avg_cost ?? 0),
      2,
    );
  });

  test("a rejected chat trade changes nothing", async ({ page }) => {
    await page.goto("/");
    const before = await apiPortfolio(page);

    await sendChat(page, "sell 500 TSLA");

    const alert = page
      .getByRole("alert")
      .filter({ hasText: /sell 500 tsla/i });
    await expect(alert).toBeVisible();
    await expect(alert).toContainText("Insufficient shares");

    const after = await apiPortfolio(page);
    expect(after.cash_balance).toBe(before.cash_balance);
    expect(after.positions.some((p) => p.ticker === "TSLA")).toBe(false);
  });

  test("the conversation survives a reload", async ({ page }) => {
    await page.goto("/");

    await sendChat(page, "what is my cash balance?");
    await expect(
      page.getByText(
        "[LLM_MOCK] I received your message but found no trade or watchlist request in it.",
        { exact: true },
      ),
    ).toBeVisible();

    await page.reload();
    await expect(
      page.getByText("what is my cash balance?", { exact: true }),
    ).toBeVisible();
  });
});
