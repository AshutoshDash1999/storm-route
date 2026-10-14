import { cn } from "cn";

import { Badge } from "@/components/ui/badge";
import { RISK } from "@/src/lib/risk";
import type { CheckpointRisk } from "@/src/lib/types";

export function RiskBadge({ risk, className }: { risk: CheckpointRisk; className?: string }) {
  const meta = RISK[risk];
  const Icon = meta.icon;
  return (
    <Badge
      className={cn(risk === "unavailable" && "border-dashed border-gray-500", className)}
      style={{ backgroundColor: meta.color, color: meta.onColor }}
    >
      <Icon />
      {meta.label}
    </Badge>
  );
}
