import { FlaskConical, Radio } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import type { DataMode, Fallback } from "@/src/lib/types";

export function DataModeBadge({ mode, fallback }: { mode: DataMode | null; fallback?: Fallback }) {
  if (mode === null) {
    return (
      <Badge variant="outline" className="text-muted-foreground">
        No trip loaded
      </Badge>
    );
  }

  // Live routes with simulated weather still need the simulated styling
  const live = mode === "live" && !fallback?.weather;
  const label = live
    ? "Live data"
    : mode === "live"
      ? "Live routes · simulated weather"
      : fallback?.routing
        ? "Fallback · simulated"
        : "Demo · simulated";
  const tooltip = live
    ? "Routes from OpenRouteService, weather from Open-Meteo."
    : mode === "live"
      ? "The weather provider failed, so checkpoint weather is simulated. Do not rely on it."
      : fallback?.routing
        ? "Live routing failed, so this analysis is simulated. Do not rely on it."
        : "Simulated demo scenario. Not real weather.";
  return (
    <Tooltip>
      <TooltipTrigger
        render={
          <Badge
            variant="outline"
            className={
              live
                ? "border-emerald-600/40 text-emerald-700 dark:text-emerald-400"
                : "border-amber-600/40 bg-[repeating-linear-gradient(135deg,transparent_0_6px,--theme(--color-amber-500/12%)_6px_12px)] text-amber-700 dark:text-amber-400"
            }
          />
        }
      >
        {live ? <Radio /> : <FlaskConical />}
        {label}
      </TooltipTrigger>
      <TooltipContent>{tooltip}</TooltipContent>
    </Tooltip>
  );
}
