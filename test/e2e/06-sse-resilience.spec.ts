import { test, expect } from "@playwright/test";

test.describe("SSE connection resilience", () => {
  test("connection indicator reflects connected/reconnecting/connected across a dropped stream", async ({
    page,
  }) => {
    await page.goto("/");

    const dot = page.getByTestId("connection-dot");
    await expect(dot).toHaveAttribute("data-status", "connected");

    // `context.setOffline(true)` doesn't reliably sever an already-open
    // keep-alive SSE stream in Chromium (confirmed: the dot stayed
    // "connected" for 30s+ with the connection merely going idle instead of
    // erroring). Aborting only the stream endpoint at the route level, then
    // reloading, forces a fresh `EventSource` attempt that fails
    // immediately — reliably exercising the "reconnecting" state the
    // frontend maps CONNECTING (mid-retry) to (marketData.tsx), while
    // leaving the document/JS/CSS fetches (and thus the reload itself)
    // unaffected.
    await page.route("**/api/stream/prices", (route) => route.abort());
    await page.reload();
    await expect(dot).toHaveAttribute("data-status", "reconnecting", { timeout: 10_000 });
    // Confirm it's genuinely stuck retrying (not just the transient initial
    // state before the first connection attempt resolves either way).
    await page.waitForTimeout(3_000);
    await expect(dot).toHaveAttribute("data-status", "reconnecting");

    await page.unroute("**/api/stream/prices");
    await expect(dot).toHaveAttribute("data-status", "connected", { timeout: 15_000 });
  });
});
