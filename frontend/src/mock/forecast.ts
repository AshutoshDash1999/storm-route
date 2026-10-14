import { addHours } from "@/src/lib/format";
import type { ForecastSnapshot, RouteAnalysis } from "@/src/lib/types";
import { buildStorms } from "@/src/mock/scenario";
import {
  fieldIntensity,
  unavailableWeather,
  weatherAt,
} from "@/src/mock/weather-model";

/** Mock provider horizon: hours at or beyond this have no forecast */
export const MOCK_FORECAST_HORIZON_H = 45;

export function buildForecast(
  analysis: RouteAnalysis,
  offsetHours: number,
): ForecastSnapshot {
  const validAt = addHours(analysis.trip.departureAt, offsetHours);
  if (offsetHours >= MOCK_FORECAST_HORIZON_H) {
    return { offsetHours, validAt, available: false, grid: [], checkpoints: {} };
  }

  const storms = buildStorms(analysis.trip);
  const source = analysis.mode === "demo" ? "simulated" : "live";
  const all = analysis.routes.flatMap((r) => r.coordinates);
  const lngs = all.map((p) => p[0]);
  const lats = all.map((p) => p[1]);
  const pad = 1;
  const [minLng, maxLng] = [Math.min(...lngs) - pad, Math.max(...lngs) + pad];
  const [minLat, maxLat] = [Math.min(...lats) - pad, Math.max(...lats) + pad];

  const steps = 40;
  const grid: ForecastSnapshot["grid"] = [];
  for (let i = 0; i <= steps; i++) {
    for (let j = 0; j <= steps; j++) {
      const lng = minLng + ((maxLng - minLng) * i) / steps;
      const lat = minLat + ((maxLat - minLat) * j) / steps;
      const intensity = fieldIntensity(storms, [lng, lat], offsetHours);
      if (intensity > 0.04) grid.push({ lng, lat, intensity });
    }
  }

  const checkpoints: ForecastSnapshot["checkpoints"] = {};
  for (const route of analysis.routes) {
    for (const cp of route.checkpoints) {
      checkpoints[cp.id] =
        cp.weather.source === "unavailable"
          ? unavailableWeather()
          : weatherAt(storms, cp.position, offsetHours, analysis.trip.loadWeightLb, source);
    }
  }

  return { offsetHours, validAt, available: true, grid, checkpoints };
}
