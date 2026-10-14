import { OctagonX, Sparkles } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { RecommendedBadge } from "@/src/features/routes/RouteCard";
import { formatDuration, formatMiles } from "@/src/lib/format";
import { isEligible, noTravelCheckpoints } from "@/src/lib/risk";
import type { Route, RouteAnalysis } from "@/src/lib/types";

/** The backend's ranking order (backend/apps/recommendations/scoring.py) */
const CRITERIA: { label: string; value: (r: Route) => string }[] = [
  { label: "Severe miles", value: (r) => formatMiles(r.severeMiles) },
  { label: "High miles", value: (r) => formatMiles(r.highMiles) },
  { label: "Average risk", value: (r) => `${r.weatherRiskScore.toFixed(1)} / 100` },
  { label: "Travel time", value: (r) => formatDuration(r.durationMin) },
];

export function RecommendationPanel({ analysis }: { analysis: RouteAnalysis }) {
  const recommended = analysis.routes.find(
    (r) => r.id === analysis.recommendation.routeId && isEligible(r),
  );
  const blocked = analysis.routes.filter((r) => !isEligible(r));

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Sparkles className="size-4" /> Recommendation
        </CardTitle>
        <CardDescription>
          Ranked by fewest Severe miles, then fewest High miles, then lowest average risk, then
          shortest travel time. Each step only breaks ties in the one before.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {recommended ? (
          <>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="font-semibold">{recommended.name}</p>
              <RecommendedBadge />
            </div>
            <ol className="grid gap-1.5 text-sm">
              {CRITERIA.map((c, i) => (
                <li key={c.label} className="flex items-center justify-between gap-2">
                  <span className="text-muted-foreground">
                    <span className="tabular-nums">{i + 1}.</span> {c.label}
                  </span>
                  <span className="font-medium tabular-nums">{c.value(recommended)}</span>
                </li>
              ))}
            </ol>
          </>
        ) : (
          <Alert variant="destructive">
            <OctagonX />
            <AlertTitle>No eligible route recommended</AlertTitle>
            <AlertDescription>
              Every route has a No Travel checkpoint or too little weather data. Consider a later
              departure or a different destination.
            </AlertDescription>
          </Alert>
        )}

        {analysis.recommendation.reasons.length > 0 && (
          <div>
            <p className="mb-1.5 text-xs font-medium text-muted-foreground">Why this ranking</p>
            <ul className="list-disc space-y-1 pl-5 text-sm">
              {analysis.recommendation.reasons.map((r) => (
                <li key={r}>{r}</li>
              ))}
            </ul>
          </div>
        )}

        {blocked.length > 0 && (
          <>
            <Separator />
            <div className="flex flex-col gap-2">
              {blocked.map((route) => {
                const stops = noTravelCheckpoints(route);
                return (
                  <Alert key={route.id} variant="destructive">
                    <OctagonX />
                    <AlertTitle>{route.name} is not eligible</AlertTitle>
                    <AlertDescription>
                      {stops.length > 0
                        ? `No Travel conditions at ${stops.map((c) => formatMiles(c.mileFromOrigin)).join(", ")}.`
                        : (route.warnings[0] ?? "Not enough weather data to assess this route.")}
                    </AlertDescription>
                  </Alert>
                );
              })}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
