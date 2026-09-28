import type { Page, Locator } from "@playwright/test";
import { expect } from "@playwright/test";

/**
 * Shared locators and readers for the E2E specs (Task 3, 06-05-PLAN.md).
 * `01-fresh-start.spec.ts` stays self-contained as the harness's own smoke
 * test and does not use these — this file exists for every spec added
 * after it (Plan 06-06 extends it further), so each helper here is kept
 * small and independent rather than assuming a particular spec's flow.
 */

// The ten tickers backend/app/market/simulator.py's DEFAULT_WATCHLIST seeds
// on a fresh database (root PLAN.md §7).
export const DEFAULT_TICKERS = [
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
] as const;

/** The section carrying the exact heading "Watchlist" (WatchlistPanel.tsx). */
export function watchlistSection(page: Page): Locator {
  return page.locator("section", {
    has: page.getByRole("heading", { name: "Watchlist", exact: true }),
  });
}

/**
 * A row button within the watchlist section whose accessible name starts
 * with `ticker` followed by a word boundary (WatchlistRow.tsx renders the
 * ticker as the row's first text node, so this never matches a ticker
 * that is merely a substring of another, e.g. "V" vs "NVDA").
 */
export function watchlistRow(page: Page, ticker: string): Locator {
  return watchlistSection(page).getByRole("button", {
    name: new RegExp(`^${ticker}\\b`),
  });
}

/**
 * The header's connection-status text, exactly one of Connected,
 * Reconnecting or Disconnected (ConnectionDot.tsx — a visible label, not
 * color alone).
 */
export function connectionStatus(page: Page): Locator {
  return page.getByText(/^(Connected|Reconnecting|Disconnected)$/, {
    exact: true,
  });
}

async function readHeaderDollarFigure(
  page: Page,
  label: "Cash" | "Total Value",
): Promise<number> {
  const headerText = await page.locator("header").innerText();
  const match = headerText.match(
    new RegExp(`${label}\\s*\\$([0-9]+(?:\\.[0-9]+)?)`),
  );
  if (!match) {
    throw new Error(
      `Could not find "${label} $<amount>" in header text: ${headerText}`,
    );
  }
  return Number(match[1]);
}

/** Parses the header's rendered "Cash $X.XX" figure into a number. */
export function readCash(page: Page): Promise<number> {
  return readHeaderDollarFigure(page, "Cash");
}

/** Parses the header's rendered "Total Value $X.XX" figure into a number. */
export function readTotalValue(page: Page): Promise<number> {
  return readHeaderDollarFigure(page, "Total Value");
}

/**
 * Captures the watchlist section's rendered text once, then polls until it
 * differs — proves the SSE stream is actually delivering ticks rather than
 * asserting on a single render. No fixed sleep.
 */
export async function waitForPricesToMove(
  page: Page,
  timeoutMs = 15_000,
): Promise<void> {
  const section = watchlistSection(page);
  const initialText = await section.innerText();
  await expect
    .poll(async () => section.innerText(), { timeout: timeoutMs })
    .not.toBe(initialText);
}
