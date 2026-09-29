import { test, expect } from "@playwright/test";

// The harness's own smoke test (Task 2, 06-05-PLAN.md): a fresh app opens
// seeded, connected and streaming. Kept self-contained (no shared helpers)
// so it also proves the compose harness end-to-end on its own — Task 3
// adds test/specs/helpers.ts for later specs, but this file stays the
// harness's own baseline. This is the only spec that asserts absolute
// seed values (P-10) — every ticker/price/cash figure here comes straight
// from backend/app/market/simulator.py's DEFAULT_WATCHLIST and root
// PLAN.md §7's seeded $10,000 cash balance.
const DEFAULT_TICKERS = [
  "AAPL",
  "GOOGL",
  "MSFT",
  "AMZN",
  "TSLA",
  "NVDA",
  "META",
  "JPM",
  "V",
  "NFLX",
];

test("fresh start shows seeded cash, default watchlist, and streaming prices", async ({
  page,
}) => {
  await page.goto("/");

  // Header: cash and total value both read $10000.00 on a fresh database
  // (P-11 — formatCurrency has no thousands separator).
  await expect(page.getByText("Total Value $10000.00")).toBeVisible();
  await expect(page.getByText("Cash $10000.00")).toBeVisible();

  // Connection status: exact text, not color alone (frontend/components/
  // ui/ConnectionDot.tsx).
  await expect(page.getByText("Connected", { exact: true })).toBeVisible();

  // Watchlist: exactly the ten seeded tickers, each its own row button.
  const watchlistSection = page.locator("section", {
    has: page.getByRole("heading", { name: "Watchlist", exact: true }),
  });
  await expect(watchlistSection.getByRole("button")).toHaveCount(
    DEFAULT_TICKERS.length,
  );
  for (const ticker of DEFAULT_TICKERS) {
    await expect(
      watchlistSection.getByRole("button", {
        name: new RegExp(`^${ticker}\\b`),
      }),
    ).toBeVisible();
  }

  // Fresh-state copy across the other panels.
  await expect(page.getByText("No positions held yet")).toBeVisible();
  await expect(
    page.getByText("Ask FinAlly anything", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText("No ticker selected")).toBeVisible();

  // Prices stream: capture the watchlist's rendered text once, then poll
  // until it differs — proves the SSE connection is actually delivering
  // ticks, not just that the panel rendered once at load. No fixed sleep.
  const initialText = await watchlistSection.innerText();
  await expect
    .poll(async () => watchlistSection.innerText(), { timeout: 15_000 })
    .not.toBe(initialText);
});
