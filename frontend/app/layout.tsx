import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { PriceStoreProvider } from "@/lib/priceStore";

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
          live prices from this provider instead of opening its own. */}
      <body className="min-h-full flex flex-col bg-terminal-bg text-terminal-text">
        <PriceStoreProvider>{children}</PriceStoreProvider>
      </body>
    </html>
  );
}
