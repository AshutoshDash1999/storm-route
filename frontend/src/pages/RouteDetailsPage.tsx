import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, MousePointerClick } from "lucide-react";
import { Link, useParams } from "react-router";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Spinner } from "@/components/ui/spinner";
import { AppHeader } from "@/src/app/AppHeader";
import { NoTripState } from "@/src/app/NoTripState";
import { TripSummary } from "@/src/app/TripSummary";
import { useTrip } from "@/src/app/trip-context";
import { RouteMap } from "@/src/features/map/RouteMap";
import { CheckpointDetails } from "@/src/features/routes/CheckpointDetails";
import { CheckpointTable } from "@/src/features/routes/CheckpointTable";
import { EligibilityBadge, RecommendedBadge } from "@/src/features/routes/RouteCard";
import { RiskSummary } from "@/src/features/routes/RiskSummary";
import { useRouteSelection } from "@/src/features/routes/use-route-selection";
import { api } from "@/src/lib/api";
import { CHECKPOINT_INTERVAL_MI } from "@/src/lib/constants";
import { formatDateTime, formatDuration, formatMiles } from "@/src/lib/format";
import { isEligible } from "@/src/lib/risk";
import type { RouteDetail } from "@/src/lib/types";

export function RouteDetailsPage() {
  const { routeId } = useParams();
  const { analysis } = useTrip();
  const local = analysis?.routes.find((r) => r.id === routeId);
  // Not in this session (e.g. a shared link): ask the backend, which keeps results for a while
  const remote = useQuery({
    queryKey: ["route", routeId],
    queryFn: () => api.getRoute(routeId!),
    enabled: !!routeId && !local,
    retry: false,
  });
  const detail: RouteDetail | undefined =
    analysis && local
      ? {
          analysisId: analysis.id,
          mode: analysis.mode,
          fallback: analysis.fallback,
          trip: analysis.trip,
          recommended: analysis.recommendation.routeId === local.id,
          route: local,
        }
      : remote.data;
  const sel = useRouteSelection(routeId);

  const backParams = new URLSearchParams(sel.params);
  backParams.delete("cp");
  if (routeId) backParams.set("route", routeId);
  const backHref = `/routes?${backParams}`;

  if (!detail && remote.isPending) {
    return (
      <div className="flex min-h-svh items-center justify-center gap-2 text-sm text-muted-foreground">
        <Spinner /> Loading route…
      </div>
    );
  }
  if (!detail) {
    return (
      <NoTripState
        title="Route not found"
        description={
          remote.error?.message ?? `There's no route "${routeId}" in the current analysis.`
        }
        action={<Button nativeButton={false} render={<Link to="/routes" />}>Back to Routes</Button>}
      />
    );
  }

  const { route, trip } = detail;
  const checkpoint = route.checkpoints.find((c) => c.id === sel.checkpointId) ?? null;
  const recommended = detail.recommended && isEligible(route);

  return (
    <div className="flex min-h-svh flex-col bg-muted/40">
      <AppHeader mode={detail.mode} fallback={detail.fallback}>
        <TripSummary trip={trip} />
      </AppHeader>

      <main className="mx-auto flex w-full max-w-7xl flex-col gap-4 p-4 md:p-6">
        <Card>
          <CardContent className="flex flex-wrap items-center gap-x-8 gap-y-4">
            <Button variant="ghost" size="sm" nativeButton={false} render={<Link to={backHref} />}>
              <ArrowLeft data-icon="inline-start" />
              Back to Routes
            </Button>
            <div className="min-w-0 flex-1">
              <h1 className="text-xl font-semibold tracking-tight">{route.name}</h1>
              <p className="text-sm text-muted-foreground">{route.via}</p>
            </div>
            <dl className="flex flex-wrap gap-x-6 gap-y-2 text-sm">
              <div>
                <dt className="text-xs text-muted-foreground">Distance</dt>
                <dd className="font-medium tabular-nums">{formatMiles(route.distanceMi)}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">Duration</dt>
                <dd className="font-medium tabular-nums">{formatDuration(route.durationMin)}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">Arrives</dt>
                <dd className="font-medium tabular-nums">{formatDateTime(route.arrivalAt)}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">Weighted score</dt>
                <dd className="font-medium tabular-nums">{route.weightedScore.toFixed(1)}</dd>
              </div>
            </dl>
            <div className="flex flex-wrap gap-1">
              {recommended && <RecommendedBadge />}
              <EligibilityBadge route={route} />
            </div>
          </CardContent>
        </Card>

        <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_24rem]">
          <div className="flex min-w-0 flex-col gap-4">
            <RouteMap
              className="h-[420px] rounded-2xl border"
              trip={trip}
              routes={[route]}
              selectedRouteId={route.id}
              selectedCheckpointId={sel.checkpointId}
              onSelectCheckpoint={sel.selectCheckpoint}
              riskFor={(cp) => cp.weather.overall}
              focusSelectedCheckpoint
            />
            <Card>
              <CardHeader>
                <CardTitle>Checkpoints</CardTitle>
                <CardDescription>
                  {route.checkpoints.length} checkpoints every{" "}
                  {trip.checkpointSpacingMi ?? CHECKPOINT_INTERVAL_MI} mi. Weather at estimated arrival.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-[420px]">
                  <CheckpointTable
                    checkpoints={route.checkpoints}
                    selectedId={sel.checkpointId}
                    onSelect={sel.selectCheckpoint}
                  />
                </ScrollArea>
              </CardContent>
            </Card>
          </div>

          <div className="flex flex-col gap-4">
            <Card>
              <CardHeader>
                <CardTitle>
                  {checkpoint ? `Checkpoint at ${formatMiles(checkpoint.mileFromOrigin)}` : "Checkpoint details"}
                </CardTitle>
              </CardHeader>
              <CardContent>
                {checkpoint ? (
                  <CheckpointDetails checkpoint={checkpoint} weatherLabel="at arrival" />
                ) : (
                  <p className="flex items-center gap-2 text-sm text-muted-foreground">
                    <MousePointerClick className="size-4" />
                    Select a checkpoint on the map or in the table.
                  </p>
                )}
              </CardContent>
            </Card>
            <RiskSummary route={route} onSelectCheckpoint={sel.selectCheckpoint} />
          </div>
        </div>
      </main>
    </div>
  );
}
