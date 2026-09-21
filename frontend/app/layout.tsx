import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { PriceStoreProvider } from "@/lib/priceStore";
import { PortfolioProvider } from "@/lib/portfolioStore";
import { ChatProvider } from "@/lib/chatStore";
import { PortfolioHistoryProvider } from "@/lib/portfolioHistoryStore";
import { ChartSelectionProvider } from "@/lib/chartSelection";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "FinAlly — AI Trading Workstation",
  description: "A visually stunning AI-powered trading workstation.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      {/* PriceStoreProvider is mounted once here so exactly one EventSource
          exists for the whole app (D-05); every future page/component reads
          live prices from this provider instead of opening its own.
          PortfolioProvider nests inside it and is the only way portfolio
          state (cash, positions, P&L) ever changes — via its refresh(),
          never client-derived (D-04). ChatProvider nests inside
          PortfolioProvider — load-bearing, not incidental: chatStore calls
          usePortfolio().refresh() after an assistant-executed trade, so it
          must render below that provider or the hook throws.
          ChartSelectionProvider holds only synchronous client state and
          depends on none of the three above it, so it nests innermost and
          the existing load-bearing orderings are untouched.
          PortfolioHistoryProvider is mounted once so exactly one 30-second
          history poll runs however many components read it. */}
      <body className="min-h-full flex flex-col bg-terminal-bg text-terminal-text">
        <PriceStoreProvider>
          <PortfolioProvider>
            <ChatProvider>
              <PortfolioHistoryProvider>
                <ChartSelectionProvider>{children}</ChartSelectionProvider>
              </PortfolioHistoryProvider>
            </ChatProvider>
          </PortfolioProvider>
        </PriceStoreProvider>
      </body>
    </html>
  );
}
