import { test, expect } from "@playwright/test";

test.describe("AI chat (LLM_MOCK=true)", () => {
  test("sends a message, gets a response, and shows an executed trade badge inline", async ({ page }) => {
    await page.goto("/");

    const chatInput = page.getByPlaceholder("Message FinAlly…");
    await chatInput.fill("buy 1 share of V");
    await page.getByRole("button", { name: "Send" }).click();

    await expect(page.getByTestId("chat-loading")).toBeVisible();

    // Mock response text (backend/app/llm/mock.py): "Mock: buying 1 share(s) of V."
    await expect(page.locator("text=Mock: buying 1 share(s) of V.")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByTestId("chat-loading")).toHaveCount(0);

    // Inline action badge confirming the trade actually executed.
    await expect(page.locator("text=Buy 1 V ✓")).toBeVisible();

    // The trade really executed against the portfolio, not just reported in chat.
    await expect(page.getByTestId("position-row-V")).toBeVisible();
  });

  test("reports a failed action as an inline error badge", async ({ page }) => {
    await page.goto("/");

    const chatInput = page.getByPlaceholder("Message FinAlly…");
    // 50,000 shares of NFLX (~$700/share in the simulator) costs far more
    // than any plausible remaining cash balance at this point in the suite.
    // (Deliberately avoiding a larger quantity: Python's `{:g}` formatting
    // in backend/app/llm/mock.py switches to scientific notation above 6
    // significant digits, which would change the expected badge text.)
    await chatInput.fill("buy 50000 shares of NFLX");
    await page.getByRole("button", { name: "Send" }).click();

    await expect(page.locator("text=Buy 50000 NFLX ✗")).toBeVisible({ timeout: 10_000 });
  });
});
