import { useEffect, useRef } from "react";
import { cn } from "cn";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { RiskBadge } from "@/src/features/routes/RiskBadge";
import { formatMeasure, formatMiles, formatTime } from "@/src/lib/format";
import type { Checkpoint } from "@/src/lib/types";

export function CheckpointTable({
  checkpoints,
  selectedId,
  onSelect,
}: {
  checkpoints: Checkpoint[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  const selectedRow = useRef<HTMLTableRowElement>(null);

  // Keep the selected row visible when selection comes from the map
  useEffect(() => {
    selectedRow.current?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [selectedId]);

  return (
    <Table>
      <TableHeader className="sticky top-0 z-10 bg-card">
        <TableRow>
          <TableHead>Distance</TableHead>
          <TableHead>ETA</TableHead>
          <TableHead className="text-right">Wind</TableHead>
          <TableHead className="text-right">Rain</TableHead>
          <TableHead className="text-right">Snowfall</TableHead>
          <TableHead>Risk</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {checkpoints.map((cp) => {
          const selected = cp.id === selectedId;
          const w = cp.weather;
          return (
            <TableRow
              key={cp.id}
              ref={selected ? selectedRow : undefined}
              data-state={selected ? "selected" : undefined}
              aria-selected={selected}
              tabIndex={0}
              onClick={() => onSelect(cp.id)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  onSelect(cp.id);
                }
              }}
              className={cn("cursor-pointer", selected && "bg-blue-600/10 hover:bg-blue-600/15")}
            >
              <TableCell className="font-medium tabular-nums">{formatMiles(cp.mileFromOrigin)}</TableCell>
              <TableCell className="tabular-nums">{formatTime(cp.etaAt)}</TableCell>
              <TableCell className="text-right tabular-nums">{formatMeasure(w.wind.value, w.wind.unit)}</TableCell>
              <TableCell className="text-right tabular-nums">{formatMeasure(w.rain.value, w.rain.unit)}</TableCell>
              <TableCell className="text-right tabular-nums">{formatMeasure(w.snow.value, w.snow.unit)}</TableCell>
              <TableCell>
                <RiskBadge risk={w.overall} />
              </TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
}
