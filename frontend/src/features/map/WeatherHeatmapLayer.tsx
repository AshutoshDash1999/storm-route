import { useEffect, useId } from "react";
import type * as MapLibreGL from "maplibre-gl";

import { useMap } from "@/components/ui/map";
import type { ForecastGridPoint } from "@/src/lib/types";

function toGeoJSON(points: ForecastGridPoint[]): GeoJSON.FeatureCollection<GeoJSON.Point> {
  return {
    type: "FeatureCollection",
    features: points.map((p) => ({
      type: "Feature",
      properties: { intensity: p.intensity },
      geometry: { type: "Point", coordinates: [p.lng, p.lat] },
    })),
  };
}

/**
 * MapLibre heatmap of normalized weather risk. mapcn has no heatmap
 * component, so this talks to the map instance directly. Render it before
 * route components so its layer sits underneath them.
 */
export function WeatherHeatmapLayer({
  points,
  opacity = 0.6,
}: {
  points: ForecastGridPoint[];
  opacity?: number;
}) {
  const { map, isLoaded } = useMap();
  const id = useId();
  const sourceId = `heatmap-source-${id}`;
  const layerId = `heatmap-layer-${id}`;

  useEffect(() => {
    if (!map || !isLoaded) return;
    map.addSource(sourceId, { type: "geojson", data: toGeoJSON([]) });
    map.addLayer({
      id: layerId,
      type: "heatmap",
      source: sourceId,
      paint: {
        "heatmap-weight": ["get", "intensity"],
        "heatmap-intensity": ["interpolate", ["linear"], ["zoom"], 3, 0.8, 8, 2],
        "heatmap-radius": ["interpolate", ["linear"], ["zoom"], 3, 18, 6, 40, 9, 70],
        "heatmap-opacity": opacity,
        "heatmap-color": [
          "interpolate",
          ["linear"],
          ["heatmap-density"],
          0,
          "rgba(0,0,0,0)",
          0.15,
          "rgba(22,163,74,0.35)",
          0.35,
          "#eab308",
          0.55,
          "#ea580c",
          0.75,
          "#dc2626",
          1,
          "#581c87",
        ],
      },
    });
    return () => {
      try {
        if (map.getLayer(layerId)) map.removeLayer(layerId);
        if (map.getSource(sourceId)) map.removeSource(sourceId);
      } catch {
        // map already torn down
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map, isLoaded]);

  useEffect(() => {
    if (!map || !isLoaded) return;
    const source = map.getSource(sourceId) as MapLibreGL.GeoJSONSource | undefined;
    source?.setData(toGeoJSON(points));
  }, [map, isLoaded, points, sourceId]);

  useEffect(() => {
    if (!map || !isLoaded || !map.getLayer(layerId)) return;
    map.setPaintProperty(layerId, "heatmap-opacity", opacity);
  }, [map, isLoaded, opacity, layerId]);

  return null;
}
