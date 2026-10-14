import { ArrowRight, Calendar, Weight } from "lucide-react";

import { formatDateTime, formatWeight } from "@/src/lib/format";
import type { TripInput } from "@/src/lib/types";

export function TripSummary({ trip }: { trip: TripInput }) {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
      <span className="flex min-w-0 items-center gap-1.5 font-medium">
        <span className="truncate">{trip.origin.label}</span>
        <ArrowRight className="size-3.5 shrink-0 text-muted-foreground" aria-label="to" />
        <span className="truncate">{trip.destination.label}</span>
      </span>
      <span className="flex items-center gap-1.5 text-muted-foreground">
        <Calendar className="size-3.5" />
        Departs {formatDateTime(trip.departureAt)}
      </span>
      <span className="flex items-center gap-1.5 text-muted-foreground">
        <Weight className="size-3.5" />
        {formatWeight(trip.loadWeightLb)}
      </span>
    </div>
  );
}
