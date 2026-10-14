import { useEffect } from "react";
import { cn } from "cn";
import { Flag, MapPin } from "lucide-react";

import {
  Map,
  MapControls,
  MapMarker,
  MapRoute,
  MarkerContent,
  MarkerLabel,
  RouteMarker,
  useMap,
} from "@/components/ui/map";
import { CheckpointMarker } from "@/src/features/map/CheckpointMarker";
import { FitRouteButton } from "@/src/features/map/FitRouteButton";
import { RiskLegend } from "@/src/features/map/RiskLegend";
import { WeatherHeatmapLayer } from "@/src/features/map/WeatherHeatmapLayer";
import { boundsOf, FIT_PADDING } from "@/src/lib/geo";
import type {
  Checkpoint,
  CheckpointRisk,
  ForecastGridPoint,
  Route,
  TripInput,
} from "@/src/lib/types";

const SELECTED_COLOR = "#2563eb";
const OTHER_COLOR = "#64748b";
/** Gap between the route line and the bottom of its label: half a checkpoint dot plus its ring */
const LABEL_GAP_PX = 16;

function FocusCheckpoint({ checkpoint }: { checkpoint: Checkpoint | null }) {
  const { map } = useMap();
  useEffect(() => {
    if (!map || !checkpoint) return;
    const [lng, lat] = checkpoint.position;
    if (!map.getBounds().contains([lng, lat])) {
      map.easeTo({ center: [lng, lat], duration: 500 });
    }
  }, [map, checkpoint]);
  return null;
}

function EndpointMarker({ lng, lat, label, kind }: { lng: number; lat: number; label: string; kind: "origin" | "destination" }) {
  const Icon = kind === "origin" ? MapPin : Flag;
  return (
    <MapMarker longitude={lng} latitude={lat}>
      <MarkerContent>
        <span
          className="flex size-8 items-center justify-center rounded-full border-2 border-white bg-foreground text-background shadow-md"
          aria-label={`${kind === "origin" ? "Origin" : "Destination"}: ${label}`}
        >
          <Icon className="size-4" />
        </span>
        <MarkerLabel position="bottom">
          <span className="rounded-md bg-background/90 px-1.5 py-0.5 font-medium shadow-sm">
            {label}
          </span>
        </MarkerLabel>
      </MarkerContent>
    </MapMarker>
  );
}

export function RouteMap({
  trip,
  routes,
  selectedRouteId,
  onSelectRoute,
  selectedCheckpointId,
  onSelectCheckpoint,
  riskFor,
  heatmap,
  focusSelectedCheckpoint = false,
  loading,
  className,
}: {
  trip: TripInput;
  routes: Route[];
  selectedRouteId: string;
  onSelectRoute?: (id: string) => void;
  selectedCheckpointId: string | null;
  onSelectCheckpoint: (id: string) => void;
  /** Risk shown on each checkpoint marker (ETA weather or a forecast snapshot) */
  riskFor: (cp: Checkpoint) => CheckpointRisk;
  heatmap?: ForecastGridPoint[] | null;
  focusSelectedCheckpoint?: boolean;
  loading?: boolean;
  className?: string;
}) {
  const selected = routes.find((r) => r.id === selectedRouteId) ?? routes[0];
  const allCoords = routes.flatMap((r) => r.coordinates);
  const selectedCheckpoint =
    selected?.checkpoints.find((c) => c.id === selectedCheckpointId) ?? null;
  const multi = routes.length > 1;

  return (
    <div className={cn("relative overflow-hidden", className)}>
      <Map
        bounds={allCoords.length ? boundsOf(allCoords) : undefined}
        fitBoundsOptions={{ padding: FIT_PADDING }}
        loading={loading}
      >
        {heatmap && <WeatherHeatmapLayer points={heatmap} />}

        {routes.map((route) => {
          const active = route.id === selected?.id;
          return (
            <MapRoute
              key={route.id}
              id={route.id}
              coordinates={route.coordinates}
              color={OTHER_COLOR}
              opacity={0.55}
              width={4}
              active={active}
              activeColor={SELECTED_COLOR}
              activeOpacity={0.95}
              activeWidth={6}
              interactive={!!onSelectRoute}
              onClick={() => onSelectRoute?.(route.id)}
            >
              {multi && (
                // Sits above the line, clear of the 24px checkpoint dots, and stacks over them
                <RouteMarker
                  at={0.5}
                  anchor="bottom"
                  offset={[0, -LABEL_GAP_PX]}
                  className="z-10"
                  onClick={() => onSelectRoute?.(route.id)}
                >
                  <MarkerContent className="cursor-pointer">
                    <span
                      className="flex h-6 items-center rounded-full border-2 border-white px-2 text-xs font-semibold text-white shadow-md"
                      style={{ backgroundColor: active ? SELECTED_COLOR : OTHER_COLOR }}
                    >
                      {/* "Route A · Direct" → "Route A" */}
                      {route.name.split(" · ")[0]}
                    </span>
                  </MarkerContent>
                </RouteMarker>
              )}
            </MapRoute>
          );
        })}

        {selected?.checkpoints.map((cp) => (
          <CheckpointMarker
            key={cp.id}
            checkpoint={cp}
            risk={riskFor(cp)}
            selected={cp.id === selectedCheckpointId}
            onSelect={() => onSelectCheckpoint(cp.id)}
          />
        ))}

        <EndpointMarker kind="origin" lng={trip.origin.lng} lat={trip.origin.lat} label={trip.origin.label} />
        <EndpointMarker
          kind="destination"
          lng={trip.destination.lng}
          lat={trip.destination.lat}
          label={trip.destination.label}
        />

        <MapControls position="bottom-right" showZoom showCompass showFullscreen />
        {selected && <FitRouteButton coordinates={selected.coordinates} />}
        {focusSelectedCheckpoint && <FocusCheckpoint checkpoint={selectedCheckpoint} />}
      </Map>
      <RiskLegend className="absolute bottom-3 left-3 z-10" />
    </div>
  );
}
