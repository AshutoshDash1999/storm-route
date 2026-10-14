import { createContext, useContext, useState, type ReactNode } from "react";

import type { RouteAnalysis, TripInput } from "@/src/lib/types";

const STORAGE_KEY = "stormroute:trip";

type TripState = {
  /** Last submitted (or in-progress) planner input, to prefill on Edit Trip */
  draft: TripInput | null;
  analysis: RouteAnalysis | null;
};

type TripContextValue = TripState & {
  setDraft: (draft: TripInput) => void;
  setAnalysis: (analysis: RouteAnalysis) => void;
};

const TripContext = createContext<TripContextValue | null>(null);

function readStored(): TripState {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw) as TripState;
  } catch {
    // Storage blocked or corrupt: start fresh
  }
  return { draft: null, analysis: null };
}

function writeStored(state: TripState) {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch {
    // Non-fatal: context still lives in memory
  }
}

export function TripProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<TripState>(readStored);

  const update = (next: Partial<TripState>) => {
    setState((prev) => {
      const merged = { ...prev, ...next };
      writeStored(merged);
      return merged;
    });
  };

  return (
    <TripContext.Provider
      value={{
        ...state,
        setDraft: (draft) => update({ draft }),
        setAnalysis: (analysis) => update({ analysis, draft: analysis.trip }),
      }}
    >
      {children}
    </TripContext.Provider>
  );
}

export function useTrip() {
  const ctx = useContext(TripContext);
  if (!ctx) throw new Error("useTrip must be used within TripProvider");
  return ctx;
}
