import { cn } from "cn";

import { MapMarker, MarkerContent, MarkerTooltip } from "@/components/ui/map";
import { formatMiles } from "@/src/lib/format";
import { RISK } from "@/src/lib/risk";
import type { Checkpoint, CheckpointRisk } from "@/src/lib/types";

export function RiskDot({
  risk,
  selected,
  size = "md",
}: {
  risk: CheckpointRisk;
  selected?: boolean;
  size?: "sm" | "md";
}) {
  const meta = RISK[risk];
  return (
    <span
      className={cn(
        "flex items-center justify-center rounded-full border-2 font-bold shadow-sm transition-transform",
        size === "md" ? "size-6 text-[10px]" : "size-4 text-[8px]",
        risk === "unavailable" ? "border-dashed border-gray-600" : "border-white",
        selected && "scale-125 ring-3 ring-foreground",
      )}
      style={{ backgroundColor: meta.color, color: meta.onColor }}
      aria-hidden
    >
      {meta.glyph}
    </span>
  );
}

export function CheckpointMarker({
  checkpoint,
  risk,
  selected,
  onSelect,
}: {
  checkpoint: Checkpoint;
  risk: CheckpointRisk;
  selected: boolean;
  onSelect?: () => void;
}) {
  return (
    <MapMarker
      longitude={checkpoint.position[0]}
      latitude={checkpoint.position[1]}
      onClick={(e) => {
        e.stopPropagation();
        onSelect?.();
      }}
    >
      <MarkerContent className={cn("cursor-pointer", selected && "z-10")}>
        <button
          type="button"
          aria-label={`Checkpoint at ${formatMiles(checkpoint.mileFromOrigin)}: ${RISK[risk].label} risk`}
          aria-pressed={selected}
          className="rounded-full focus-visible:ring-3 focus-visible:ring-ring focus-visible:outline-none"
        >
          <RiskDot risk={risk} selected={selected} />
        </button>
      </MarkerContent>
      <MarkerTooltip>
        {formatMiles(checkpoint.mileFromOrigin)} · {RISK[risk].label}
      </MarkerTooltip>
    </MapMarker>
  );
}
