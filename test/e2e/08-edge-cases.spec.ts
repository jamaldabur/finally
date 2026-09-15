import { test, expect } from "@playwright/test";

// Regression coverage for round-2 fixes:
//  - frontend-engineer: Treemap ghost-rendering bug (a synthetic depth-0
//    root node was rendered with `content` too, producing a duplicate label
//    overlapping one real cell) — backend/../PortfolioHeatmap.tsx now skips
//    depth === 0.
//  - llm-engineer: mock ticker extraction on "buy 5 more AAPL" used to
//    return "MORE" instead of "AAPL" — backend/app/llm/mock.py now checks
//    the ticker universe before falling back to the bare-stopword heuristic.
//  - backend-engineer: a buy whose cost lands a hair above cash_balance due
//    to float rounding was spuriously rejected as "insufficient cash" —
//    backend/app/portfolio/service.py now tolerates a 1e-6 epsilon.
//
// Runs last (numeric prefix) since the float-epsilon case deliberately
// spends down close to all remaining cash.
test.describe("round-2 edge cases", () => {
  test("heatmap renders each position's label at most once (no ghost duplicate)", async ({ page, request }) => {
    const portfolioRes = await request.get("/api/portfolio");
    const portfolio = await portfolioRes.json();
    expect(portfolio.positions.length).toBeGreaterThan(0);

    await page.goto("/");
    const heatmap = page.locator("text=Positions Heatmap").locator("..");
    await expect(heatmap.locator("svg rect").first()).toBeVisible({ timeout: 10_000 });

    // Not every cell is necessarily large enough to render a label
    // (CellContent only draws text above a size threshold), but whichever
    // labels ARE rendered must each appear exactly once. The old ghost-node
    // bug duplicated one label by rendering the synthetic root node's
    // content at the same coordinates as a real leaf.
    const labels = await heatmap.locator("svg text tspan:first-child").allTextContents();
    expect(labels.length).toBeGreaterThan(0);
    expect(new Set(labels).size).toBe(labels.length);
  });

  test('chat: "buy N more TICKER" extracts the ticker, not the word "more"', async ({ page }) => {
    await page.goto("/");

    await page.getByPlaceholder("Message FinAlly…").fill("buy 3 more AAPL");
    await page.getByRole("button", { name: "Send" }).click();

    await expect(page.locator("text=Mock: buying 3 share(s) of AAPL.")).toBeVisible({ timeout: 10_000 });
    await expect(page.locator("text=Buy 3 AAPL ✓")).toBeVisible();
    // The bug would have produced a "MORE" trade action badge instead.
    await expect(page.getByText(/\bMORE\b/)).toHaveCount(0);
  });

  test("a buy that exhausts cash to within float noise is not spuriously rejected", async ({ request }) => {
    // `quantity * price` computed this way essentially never lands exactly
    // on cash_balance — float division-then-multiplication non-associativity
    // puts it a few ULPs (~1e-12 for balances in the thousands) to one side
    // or the other, which the 1e-6 epsilon in execute_trade must absorb.
    // That noise is tiny and reliable; the one real source of flakiness is
    // the *live* simulator ticking the price between the GET and the POST
    // (~500ms cadence). Wrapped in toPass so a rare mid-attempt tick just
    // means re-fetching fresh numbers and trying again, rather than a false
    // failure of this regression test.
    await expect(async () => {
      const before = await (await request.get("/api/portfolio")).json();
      const watchlist = await (await request.get("/api/watchlist")).json();
      const amzn = watchlist.find((w: { ticker: string; price: number | null }) => w.ticker === "AMZN");
      expect(amzn?.price).toBeGreaterThan(0);

      const quantity = before.cash_balance / amzn.price;
      const res = await request.post("/api/portfolio/trade", {
        data: { ticker: "AMZN", quantity, side: "buy" },
      });

      expect(res.status(), await res.text()).toBe(200);
      const body = await res.json();
      expect(body.ticker).toBe("AMZN");
    }).toPass({ timeout: 10_000, intervals: [200] });
  });
});
