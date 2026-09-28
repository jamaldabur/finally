import { defineConfig, devices } from "@playwright/test";

// All specs share one single-user SQLite database (no auth, no tenancy —
// PLAN.md §3/§7), so they must never run concurrently against each other:
// one worker, file-name order, zero retries (P-10). Only 01-fresh-start
// asserts absolute seed values; every later spec measures its own
// before/after deltas so ordering within that constraint doesn't matter.
export default defineConfig({
  testDir: "./specs",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  forbidOnly: !!process.env.CI,
  timeout: 60_000,
  expect: {
    timeout: 15_000,
  },
  outputDir: "test-results",
  reporter: [
    ["list"],
    ["html", { open: "never", outputFolder: "playwright-report" }],
  ],
  use: {
    baseURL: process.env.BASE_URL ?? "http://localhost:8000",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        // The layout is desktop-first (root PLAN.md §2); the default
        // 1280px viewport cramps the heatmap and other dense panels.
        viewport: { width: 1600, height: 1000 },
      },
    },
  ],
});
