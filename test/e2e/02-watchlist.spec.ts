import { test, expect } from "@playwright/test";

test.describe("watchlist management", () => {
  test("adds and removes a valid ticker", async ({ page }) => {
    await page.goto("/");

    const input = page.getByPlaceholder("Add ticker…");
    await input.fill("pypl"); // lowercase on purpose — the UI uppercases before sending
    await page.getByRole("button", { name: "Add" }).click();

    const row = page.getByTestId("watchlist-row-PYPL");
    await expect(row).toBeVisible();

    await page.getByRole("button", { name: "Remove PYPL" }).click();
    await expect(row).not.toBeVisible();
  });

  test("rejects an unrecognized ticker with an inline error", async ({ page }) => {
    await page.goto("/");

    const input = page.getByPlaceholder("Add ticker…");
    await input.fill("ZZZZZ");
    await page.getByRole("button", { name: "Add" }).click();

    // Scoped by text, not just role="alert" — Next.js also renders a hidden
    // route-announcer div with role="alert" that would otherwise collide.
    const errorAlert = page.getByText(/unrecognized/i);
    await expect(errorAlert).toBeVisible();
    await expect(page.getByTestId("watchlist-row-ZZZZZ")).toHaveCount(0);
  });
});
