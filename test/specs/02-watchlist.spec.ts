import { test, expect } from "@playwright/test";
import { watchlistSection, watchlistRow, sendChat } from "./helpers";

/**
 * Chat-driven watchlist add/remove/reject (Task 2, 06-06-PLAN.md, P-06: chat
 * is the frontend's only watchlist mutation path). Every phrase here is
 * confirmed against `build_mock_response()` directly (see this plan's
 * `<verify>`) before this browser suite runs — "add PYPL to my watchlist",
 * not "add PYPL" (D-07, RESEARCH Pitfall 1: the mock's watchlist branch
 * requires the literal word "watchlist" in the message).
 */

test.describe("the copilot manages the watchlist", () => {
  test("adds and removes a ticker, and the change persists", async ({
    page,
  }) => {
    await page.goto("/");
    // WatchlistPanel's own mount-time GET /api/watchlist fetch can still be
    // in flight here; waiting for a known default ticker's row is a
    // deterministic barrier before reading a baseline count (the panel
    // renders its whole list from one fetch, never progressively, so any
    // one default row appearing proves the rest are present too).
    await expect(watchlistRow(page, "AAPL")).toBeVisible();

    const rowCount = () => watchlistSection(page).getByRole("button").count();
    const before = await rowCount();

    await test.step("add PYPL via chat", async () => {
      await sendChat(page, "add PYPL to my watchlist");
      await expect(page.getByText(/Added PYPL to watchlist/i)).toBeVisible();
      await expect(watchlistRow(page, "PYPL")).toBeVisible();
      await expect.poll(rowCount).toBe(before + 1);
    });

    await test.step("PYPL survives a reload", async () => {
      await page.reload();
      await expect(watchlistRow(page, "PYPL")).toBeVisible();
    });

    await test.step("remove PYPL via chat", async () => {
      await sendChat(page, "remove PYPL from my watchlist");
      await expect(
        page.getByText(/Removed PYPL from watchlist/i),
      ).toBeVisible();
      await expect(watchlistRow(page, "PYPL")).toHaveCount(0);
      await expect.poll(rowCount).toBe(before);
    });
  });

  test("an unknown ticker is refused inline", async ({ page }) => {
    await page.goto("/");
    await expect(watchlistRow(page, "AAPL")).toBeVisible();

    const rowCount = () => watchlistSection(page).getByRole("button").count();
    const before = await rowCount();

    await sendChat(page, "add ZZZZ to my watchlist");

    const alert = page.getByRole("alert").filter({ hasText: "ZZZZ" });
    await expect(alert).toContainText("ZZZZ");
    await expect(alert).toContainText("Unknown ticker");

    await expect.poll(rowCount).toBe(before);

    const res = await page.request.get("/api/watchlist");
    expect(res.ok()).toBeTruthy();
    const body: { watchlist: { ticker: string }[] } = await res.json();
    expect(body.watchlist.some((entry) => entry.ticker === "ZZZZ")).toBe(
      false,
    );
  });
});
