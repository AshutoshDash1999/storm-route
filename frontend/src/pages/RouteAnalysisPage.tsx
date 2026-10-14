import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Pencil } from "lucide-react";
import { useNavigate } from "react-router";

import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { AppHeader } from "@/src/app/AppHeader";
import { NoTripState } from "@/src/app/NoTripState";
import { TripSummary } from "@/src/app/TripSummary";
import { useTrip } from "@/src/app/trip-context";
import { RouteMap } from "@/src/features/map/RouteMap";
import { CheckpointDrawer } from "@/src/features/routes/CheckpointDrawer";
import { CheckpointSpacingControl } from "@/src/features/routes/CheckpointSpacingControl";
import { ForecastControls } from "@/src/features/routes/ForecastControls";
import { RecommendationPanel } from "@/src/features/routes/RecommendationPanel";
import { RouteCard } from "@/src/features/routes/RouteCard";
import { useRouteSelection } from "@/src/features/routes/use-route-selection";
import type { Checkpoint, CheckpointWeather, RouteAnalysis } from "@/src/lib/types";
import { api } from "@/src/lib/api";
import { unavailableWeather } from "@/src/lib/risk";

export function RouteAnalysisPage() {
  const { analysis } = useTrip();
  if (!analysis || analysis.routes.length === 0) {
    return (
      <NoTripState
        title={analysis ? "No routes found" : undefined}
        description={analysis ? "The route service returned no alternatives for this trip." : undefined}
      />
    );
  }
  return <RouteAnalysis analysis={analysis} />;
}

function RouteAnalysis({ analysis }: { analysis: RouteAnalysis }) {
  const navigate = useNavigate();
  const sel = useRouteSelection(analysis.recommendation.routeId ?? analysis.routes[0].id);
  const route = analysis.routes.find((r) => r.id === sel.routeId) ?? analysis.routes[0];
  const checkpoint = route.checkpoints.find((c) => c.id === sel.checkpointId) ?? null;

  const forecast = useQuery({
    queryKey: ["forecast", analysis.id, sel.offset],
    queryFn: () => api.getForecast(analysis.id, sel.offset),
    placeholderData: keepPreviousData,
  });
  // While the next hour loads (e.g. during playback), keep showing the previous one
  const snapshot = forecast.data;
  const unavailable = snapshot ? !snapshot.available : false;

  const forecastWeather = (cp: Checkpoint): CheckpointWeather | undefined =>
    snapshot?.available ? snapshot.checkpoints[cp.id] : undefined;

  const riskFor = (cp: Checkpoint) => {
    if (sel.view === "eta") return cp.weather.overall;
    return forecastWeather(cp)?.overall ?? "unavailable";
  };

  const detailsHref = (id: string) => {
    const p = new URLSearchParams(sel.params);
    p.set("route", id);
    p.delete("cp");
    return `/routes/${id}?${p}`;
  };

  return (
    <div className="flex h-svh flex-col">
      <AppHeader
        actions={
          <Button variant="outline" size="sm" onClick={() => navigate("/")}>
            <Pencil data-icon="inline-start" />
            Edit Trip
          </Button>
        }
      >
        <TripSummary trip={analysis.trip} />
      </AppHeader>

      <main className="flex min-h-0 flex-1 flex-col overflow-y-auto lg:grid lg:grid-cols-[minmax(0,1fr)_26rem] lg:overflow-hidden">
        <div className="flex min-h-[60svh] flex-col lg:min-h-0">
          <RouteMap
            className="flex-1"
            trip={analysis.trip}
            routes={analysis.routes}
            selectedRouteId={route.id}
            onSelectRoute={sel.selectRoute}
            selectedCheckpointId={sel.checkpointId}
            onSelectCheckpoint={sel.selectCheckpoint}
            riskFor={riskFor}
            heatmap={snapshot?.available ? snapshot.grid : null}
          />
          <ForecastControls
            departureAt={analysis.trip.departureAt}
            offset={sel.offset}
            onOffsetChange={sel.setOffset}
            view={sel.view}
            onViewChange={sel.setView}
            loading={forecast.isFetching}
            unavailable={unavailable}
            error={forecast.error}
          />
        </div>

        <ScrollArea className="border-l lg:min-h-0">
          <div className="flex flex-col gap-4 p-4">
            <CheckpointSpacingControl analysis={analysis} onAnalyzed={sel.clearRoute} />
            <section aria-label="Route comparison" className="flex flex-col gap-3">
              <h2 className="text-sm font-medium text-muted-foreground">
                {analysis.routes.length} route{analysis.routes.length === 1 ? "" : "s"} compared
              </h2>
              {analysis.routes.map((r) => (
                <RouteCard
                  key={r.id}
                  route={r}
                  selected={r.id === route.id}
                  recommended={r.id === analysis.recommendation.routeId}
                  onSelect={() => sel.selectRoute(r.id)}
                  detailsHref={detailsHref(r.id)}
                />
              ))}
            </section>
            <RecommendationPanel analysis={analysis} />
          </div>
        </ScrollArea>
      </main>

      <CheckpointDrawer
        route={route}
        checkpoint={checkpoint}
        weather={checkpoint && sel.view === "forecast" ? (forecastWeather(checkpoint) ?? unavailableWeather()) : undefined}
        weatherLabel={sel.view === "forecast" ? `forecast +${sel.offset} h` : "at arrival"}
        onClose={() => sel.selectCheckpoint(null)}
      />
    </div>
  );
}

