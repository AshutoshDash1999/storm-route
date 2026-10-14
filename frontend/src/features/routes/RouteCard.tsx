import { cn } from "cn";
import { ArrowRight, Ban, CircleCheck, Star } from "lucide-react";
import { Link } from "react-router";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatDuration, formatMiles, formatTime } from "@/src/lib/format";
import { hasNoTravel, isEligible, RISK } from "@/src/lib/risk";
import type { Route } from "@/src/lib/types";

export function EligibilityBadge({ route }: { route: Route }) {
  return isEligible(route) ? (
    <Badge variant="outline" className="text-emerald-700 dark:text-emerald-400">
      <CircleCheck />
      Eligible
    </Badge>
  ) : (
    <Badge variant="destructive">
      <Ban />
      {hasNoTravel(route) ? "Blocked · No Travel" : "Blocked · Missing data"}
    </Badge>
  );
}

export function RecommendedBadge() {
  return (
    <Badge>
      <Star />
      Recommended
    </Badge>
  );
}

function Stat({ label, value, swatch }: { label: string; value: string; swatch?: string }) {
  return (
    <div>
      <dt className="flex items-center gap-1.5 text-xs text-muted-foreground">
        {swatch && <span className="size-2 rounded-full" style={{ backgroundColor: swatch }} aria-hidden />}
        {label}
      </dt>
      <dd className="font-medium tabular-nums">{value}</dd>
    </div>
  );
}

export function RouteCard({
  route,
  selected,
  recommended,
  onSelect,
  detailsHref,
}: {
  route: Route;
  selected: boolean;
  recommended: boolean;
  onSelect: () => void;
  detailsHref: string;
}) {
  const eligible = isEligible(route);
  return (
    <article
      className={cn(
        "rounded-2xl border bg-card p-4 transition-colors",
        selected ? "border-blue-600 ring-2 ring-blue-600/30" : "hover:bg-muted/50",
      )}
    >
      <button
        type="button"
        onClick={onSelect}
        aria-pressed={selected}
        className="block w-full text-left focus-visible:outline-none"
      >
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div className="min-w-0">
            <h3 className="font-semibold">{route.name}</h3>
            <p className="text-xs text-muted-foreground">{route.via}</p>
          </div>
          <div className="flex flex-wrap gap-1">
            {recommended && eligible && <RecommendedBadge />}
            <EligibilityBadge route={route} />
          </div>
        </div>
        <dl className="mt-3 grid grid-cols-3 gap-x-3 gap-y-2 text-sm">
          <Stat label="Distance" value={formatMiles(route.distanceMi)} />
          <Stat label="Duration" value={formatDuration(route.durationMin)} />
          <Stat label="Arrives" value={formatTime(route.arrivalAt)} />
          <Stat label="Avg risk" value={`${route.weatherRiskScore.toFixed(1)} / 100`} />
          <Stat label="Severe" value={formatMiles(route.severeMiles)} swatch={RISK.severe.color} />
          <Stat label="High" value={formatMiles(route.highMiles)} swatch={RISK.high.color} />
        </dl>
      </button>
      <div className="mt-3 flex justify-end">
        <Button variant="ghost" size="sm" nativeButton={false} render={<Link to={detailsHref} />}>
          View details
          <ArrowRight data-icon="inline-end" />
        </Button>
      </div>
    </article>
  );
}
