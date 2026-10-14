import { useSearchParams } from "react-router";

import { FORECAST_HOURS } from "@/src/lib/constants";

/** "eta": checkpoints colored by weather at arrival; "forecast": by the slider hour */
export type CheckpointView = "eta" | "forecast";

/**
 * Selection lives in the URL (`?route=&cp=&t=&view=`) so the map, cards and
 * drawer stay in sync and back/forward and Back to Routes keep it.
 */
export function useRouteSelection(defaultRouteId: string | undefined) {
  const [params, setParams] = useSearchParams();

  const routeId = params.get("route") ?? defaultRouteId ?? "";
  const checkpointId = params.get("cp");
  const rawOffset = Number(params.get("t") ?? 0);
  const offset = Number.isFinite(rawOffset)
    ? Math.min(FORECAST_HOURS, Math.max(0, Math.round(rawOffset)))
    : 0;
  const view: CheckpointView = params.get("view") === "forecast" ? "forecast" : "eta";

  const patch = (next: Record<string, string | null>) =>
    setParams(
      (prev) => {
        const p = new URLSearchParams(prev);
        for (const [k, v] of Object.entries(next)) {
          if (v === null) p.delete(k);
          else p.set(k, v);
        }
        return p;
      },
      { replace: true },
    );

  return {
    params,
    routeId,
    checkpointId,
    offset,
    view,
    selectRoute: (id: string) => patch({ route: id, cp: null }),
    selectCheckpoint: (id: string | null) => patch({ cp: id }),
    /** After a re-analysis: route IDs change, so fall back to the recommendation */
    clearRoute: () => patch({ route: null, cp: null }),
    setOffset: (h: number) => patch({ t: String(h), view: "forecast" }),
    setView: (v: CheckpointView) => patch({ view: v === "eta" ? null : v }),
  };
}
