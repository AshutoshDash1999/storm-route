import { FlaskConical, Radio } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import type { DataMode } from "@/src/lib/types";

export function DataModeBadge({ mode }: { mode: DataMode | null }) {
  if (mode === null) {
    return (
      <Badge variant="outline" className="text-muted-foreground">
        No trip loaded
      </Badge>
    );
  }

  const live = mode === "live";
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
        {live ? "Live data" : "Demo · simulated"}
      </TooltipTrigger>
      <TooltipContent>
        {live
          ? "Routes and weather from live providers."
          : "Simulated demo scenario. Not real weather."}
      </TooltipContent>
    </Tooltip>
  );
}
