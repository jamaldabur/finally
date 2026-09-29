"use client";

/**
 * Selected-ticker client state shared by the watchlist (writer) and the main
 * chart (reader). A context rather than state lifted into page.tsx: the writer
 * (WatchlistRow) sits two levels down the left column under WatchlistPanel and
 * the reader sits in the centre column, so lifting would mean threading a
 * setter through WatchlistPanel purely as a pass-through.
 *
 * Nothing is selected on first load — the empty state is deliberate.
 */

import { createContext, useContext, useState, type ReactNode } from "react";

type ChartSelectionValue = {
  selectedTicker: string | null;
  setSelectedTicker: (ticker: string | null) => void;
};

const ChartSelectionContext = createContext<ChartSelectionValue | null>(null);

export function ChartSelectionProvider({ children }: { children: ReactNode }) {
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);
  return (
    <ChartSelectionContext.Provider value={{ selectedTicker, setSelectedTicker }}>
      {children}
    </ChartSelectionContext.Provider>
  );
}

export function useChartSelection(): ChartSelectionValue {
  const ctx = useContext(ChartSelectionContext);
  if (ctx === null) {
    throw new Error("useChartSelection must be used within ChartSelectionProvider");
  }
  return ctx;
}
