import type { Page } from "@playwright/test";

export function parseCurrency(text: string): number {
  return Number(text.replace(/[^0-9.-]/g, ""));
}

export async function readCash(page: Page): Promise<number> {
  const text = await page.getByTestId("cash-balance").textContent();
  return parseCurrency(text ?? "0");
}
