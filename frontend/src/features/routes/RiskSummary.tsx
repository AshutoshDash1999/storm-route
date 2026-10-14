import { CloudOff, OctagonX } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { RiskBadge } from "@/src/features/routes/RiskBadge";
import { formatMiles, formatPercent } from "@/src/lib/format";
import { noTravelCheckpoints, RISK, riskExposure } from "@/src/lib/risk";
import type { Route } from "@/src/lib/types";

export function RiskSummary({
  route,
  onSelectCheckpoint,
}: {
  route: Route;
  onSelectCheckpoint: (id: string) => void;
}) {
  const exposure = riskExposure(route);
  const noTravel = noTravelCheckpoints(route);
  const missing = route.checkpoints.filter((c) => c.weather.overall === "unavailable");

  return (
    <Card>
      <CardHeader>
        <CardTitle>Risk exposure</CardTitle>
        <CardDescription>
          Miles by checkpoint risk at estimated arrival time. Average normalized weather risk:{" "}
          <span className="font-semibold text-foreground tabular-nums">
            {(route.weatherRiskScore / 100).toFixed(2)}
          </span>
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <ul className="grid gap-3">
          {exposure.map((e) => (
            <li key={e.level} className="grid grid-cols-[7rem_1fr_auto] items-center gap-3 text-sm">
              <RiskBadge risk={e.level} />
              <Progress
                value={e.percent}
                aria-label={`${RISK[e.level].label} share of route`}
                className="*:data-[slot=progress-track]:h-2.5 **:data-[slot=progress-indicator]:bg-(--risk)"
                style={{ "--risk": RISK[e.level].color } as React.CSSProperties}
              />
              <span className="w-28 text-right tabular-nums">
                {formatMiles(e.miles)} · {formatPercent(e.percent)}
              </span>
            </li>
          ))}
        </ul>

        {noTravel.length > 0 && (
          <Alert variant="destructive">
            <OctagonX />
            <AlertTitle>
              {noTravel.length} No Travel checkpoint{noTravel.length === 1 ? "" : "s"}
            </AlertTitle>
            <AlertDescription>
              <ul className="mt-1 flex flex-wrap gap-1.5">
                {noTravel.map((c) => (
                  <li key={c.id}>
                    <button
                      type="button"
                      className="underline underline-offset-2"
                      onClick={() => onSelectCheckpoint(c.id)}
                    >
                      {formatMiles(c.mileFromOrigin)} ({c.place})
                    </button>
                  </li>
                ))}
              </ul>
            </AlertDescription>
          </Alert>
        )}

        {missing.length > 0 && (
          <Alert>
            <CloudOff />
            <AlertTitle>Incomplete weather coverage</AlertTitle>
            <AlertDescription>
              {missing.length} of {route.checkpoints.length} checkpoints have no weather data (
              {formatMiles(exposure.find((e) => e.level === "unavailable")?.miles ?? 0)}). They're
              shown as Unknown and scored as Severe, never as Low.
            </AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
}
