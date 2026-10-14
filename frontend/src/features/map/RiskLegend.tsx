import { cn } from "cn";

import { RiskDot } from "@/src/features/map/CheckpointMarker";
import { LEGEND_LEVELS, RISK } from "@/src/lib/risk";

export function RiskLegend({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "rounded-2xl border bg-background/95 p-3 text-xs shadow-md backdrop-blur",
        className,
      )}
    >
      <p className="mb-2 font-medium">Weather risk</p>
      <ul className="grid grid-cols-2 gap-x-4 gap-y-1.5 sm:grid-cols-1">
        {LEGEND_LEVELS.map((level) => (
          <li key={level} className="flex items-center gap-2">
            <RiskDot risk={level} size="sm" />
            {RISK[level].label}
          </li>
        ))}
      </ul>
    </div>
  );
}
