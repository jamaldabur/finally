/**
 * RTL `render()` wrapped in the exact provider nesting
 * `frontend/app/layout.tsx` uses (Phase 6, TEST-04). That order is
 * load-bearing there — `ChatProvider` calls `usePortfolio()`, so it must
 * render below `PortfolioProvider` — and is reproduced verbatim here rather
 * than re-derived, so a component test never silently drifts from the
 * app's real provider tree.
 *
 * This helper does not stub `fetch` itself; call `stubFetch()` before
 * rendering so the route data a test asserts against stays visible in the
 * test body rather than hidden inside a shared wrapper.
 */

import { render, type RenderOptions, type RenderResult } from "@testing-library/react";
import type { ReactElement, ReactNode } from "react";
import { PriceStoreProvider } from "@/lib/priceStore";
import { PortfolioProvider } from "@/lib/portfolioStore";
import { ChatProvider } from "@/lib/chatStore";
import { PortfolioHistoryProvider } from "@/lib/portfolioHistoryStore";
import { ChartSelectionProvider } from "@/lib/chartSelection";

function AllProviders({ children }: { children: ReactNode }) {
  return (
    <PriceStoreProvider>
      <PortfolioProvider>
        <ChatProvider>
          <PortfolioHistoryProvider>
            <ChartSelectionProvider>{children}</ChartSelectionProvider>
          </PortfolioHistoryProvider>
        </ChatProvider>
      </PortfolioProvider>
    </PriceStoreProvider>
  );
}

export function renderWithProviders(
  ui: ReactElement,
  options?: Omit<RenderOptions, "wrapper">,
): RenderResult {
  return render(ui, { wrapper: AllProviders, ...options });
}
