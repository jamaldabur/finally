import { test, expect } from "@playwright/test";
import { connectionStatus, waitForPricesToMove } from "./helpers";

/**
 * SSE reconnection (P-13, TEST-05). Two independent proofs:
 *
 *   1. A live stream that drops (browser goes offline) reconnects without
 *      a reload, exercising priceStore.tsx's onerror/onopen state machine
 *      via a real network interruption.
 *   2. A stream that is unreachable from the very first request keeps
 *      retrying on its own — proving EventSource's built-in retry loop,
 *      not any app-level reconnect code — and connects as soon as it
 *      becomes reachable.
 *
 * Per frontend/lib/priceStore.tsx's docblock: `onerror` sets
 * "reconnecting" and arms a 5s grace timer before "disconnected"; the
 * browser itself retries roughly every 3s. A sustained outage should
 * settle on "Reconnecting" once the first error fires, but either
 * "Reconnecting" or "Disconnected" is accepted per the plan — this test
 * does not assume the grace timer's exact race against the retry cadence.
 */

test("a live stream that drops reconnects without a reload", async ({
  page,
  context,
}) => {
  await page.goto("/");
  await expect(connectionStatus(page)).toHaveText("Connected");

  try {
    await context.setOffline(true);
    await expect(connectionStatus(page)).toHaveText(
      /^(Reconnecting|Disconnected)$/,
      { timeout: 15_000 },
    );
  } finally {
    // Always restore, even if the assertion above failed — a failing
    // assertion must never leave the browser context offline for
    // whatever runs next.
    await context.setOffline(false);
  }

  await expect(connectionStatus(page)).toHaveText("Connected", {
    timeout: 30_000,
  });
  await waitForPricesToMove(page);
});

test("an unreachable stream keeps retrying and connects once reachable", async ({
  page,
}) => {
  let blocked = true;
  let attempts = 0;

  await page.route("**/api/stream/prices", async (route) => {
    if (blocked) {
      attempts += 1;
      // "internetdisconnected" is load-bearing: Chromium treats an
      // "aborted" error code as a cancellation, after which EventSource
      // gives up instead of retrying (P-13). This code keeps the browser's
      // own retry loop running.
      await route.abort("internetdisconnected");
      return;
    }
    await route.continue();
  });

  await page.goto("/");

  // The browser re-requested the stream on its own at least twice, with
  // no app code reopening it.
  await expect
    .poll(() => attempts, { timeout: 20_000 })
    .toBeGreaterThanOrEqual(2);
  await expect(connectionStatus(page)).toHaveText(
    /^(Reconnecting|Disconnected)$/,
  );

  blocked = false;

  await expect(connectionStatus(page)).toHaveText("Connected", {
    timeout: 20_000,
  });
  await waitForPricesToMove(page);
});
