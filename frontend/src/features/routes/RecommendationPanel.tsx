import { OctagonX, Sparkles } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Progress,
  ProgressLabel,
  ProgressValue,
} from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { RecommendedBadge } from "@/src/features/routes/RouteCard";
import { formatMiles } from "@/src/lib/format";
import { isEligible, noTravelCheckpoints } from "@/src/lib/risk";
import type { RouteAnalysis } from "@/src/lib/types";

export const WEATHER_WEIGHT = 0.7;
export const TIME_WEIGHT = 0.3;

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
          Lower is better. Score = {WEATHER_WEIGHT * 100}% weather risk + {TIME_WEIGHT * 100}% travel time.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {recommended ? (
          <>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <p className="font-semibold">{recommended.name}</p>
                <p className="text-sm text-muted-foreground">
                  Weighted score{" "}
                  <span className="font-semibold text-foreground tabular-nums">
                    {recommended.weightedScore.toFixed(1)}
                  </span>
                </p>
              </div>
              <RecommendedBadge />
            </div>
            <div className="grid gap-3">
              <Progress value={recommended.weatherRiskScore}>
                <ProgressLabel>Weather risk · {WEATHER_WEIGHT * 100}%</ProgressLabel>
                <ProgressValue>
                  {() =>
                    `${recommended.weatherRiskScore.toFixed(0)} → ${(recommended.weatherRiskScore * WEATHER_WEIGHT).toFixed(1)} pts`
                  }
                </ProgressValue>
              </Progress>
              <Progress value={recommended.timeScore}>
                <ProgressLabel>Travel time · {TIME_WEIGHT * 100}%</ProgressLabel>
                <ProgressValue>
                  {() =>
                    `${recommended.timeScore.toFixed(0)} → ${(recommended.timeScore * TIME_WEIGHT).toFixed(1)} pts`
                  }
                </ProgressValue>
              </Progress>
            </div>
          </>
        ) : (
          <Alert variant="destructive">
            <OctagonX />
            <AlertTitle>No eligible route recommended</AlertTitle>
            <AlertDescription>
              Every route crosses at least one No Travel checkpoint. Consider a later departure or
              a different destination.
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
                      No Travel conditions at{" "}
                      {stops.map((c) => formatMiles(c.mileFromOrigin)).join(", ")}.
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
