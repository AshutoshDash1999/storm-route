import { isEligible, milesAt, noTravelCheckpoints } from "@/src/lib/risk";
import { addHours, formatDuration, formatMiles } from "@/src/lib/format";
import type {
  Checkpoint,
  CheckpointRisk,
  DataMode,
  LngLat,
  Route,
  RouteAnalysis,
  TripInput,
} from "@/src/lib/types";
import {
  unavailableWeather,
  weatherAt,
  type StormCell,
} from "@/src/mock/weather-model";

export const CHECKPOINT_INTERVAL_MI = 25;
export const FORECAST_HOURS = 48;

const EARTH_RADIUS_MI = 3958.8;

export function haversineMi(a: LngLat, b: LngLat) {
  const toRad = (d: number) => (d * Math.PI) / 180;
  const dLat = toRad(b[1] - a[1]);
  const dLng = toRad(b[0] - a[0]);
  const h =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(a[1])) * Math.cos(toRad(b[1])) * Math.sin(dLng / 2) ** 2;
  return 2 * EARTH_RADIUS_MI * Math.asin(Math.sqrt(h));
}

type Corridor = {
  origin: LngLat;
  destination: LngLat;
  /** Span in degrees */
  span: number;
  /** Unit normal (left of travel direction), in degrees */
  normal: LngLat;
  at: (s: number, offset: number) => LngLat;
};

function corridor(origin: LngLat, destination: LngLat): Corridor {
  const dx = destination[0] - origin[0];
  const dy = destination[1] - origin[1];
  const span = Math.hypot(dx, dy);
  const normal: LngLat = [-dy / span, dx / span];
  return {
    origin,
    destination,
    span,
    normal,
    at: (s, offset) => [
      origin[0] + dx * s + normal[0] * offset * span,
      origin[1] + dy * s + normal[1] * offset * span,
    ],
  };
}

type RouteSpec = {
  id: string;
  bend: number;
  wiggle: number;
  speedMph: number;
  /** Checkpoint indices (mod 6) with no weather coverage */
  gapEvery?: number;
};

const ROUTE_SPECS: RouteSpec[] = [
  { id: "a", bend: 0.03, wiggle: 0.015, speedMph: 60 },
  { id: "b", bend: 0.2, wiggle: 0.02, speedMph: 57, gapEvery: 6 },
  { id: "c", bend: -0.22, wiggle: 0.018, speedMph: 61 },
];

function sideName(c: Corridor, bend: number) {
  const [nx, ny] = c.normal.map((v) => v * Math.sign(bend));
  if (Math.abs(ny) >= Math.abs(nx)) return ny > 0 ? "Northern" : "Southern";
  return nx > 0 ? "Eastern" : "Western";
}

function buildGeometry(c: Corridor, spec: RouteSpec): LngLat[] {
  const n = 80;
  return Array.from({ length: n + 1 }, (_, i) => {
    const s = i / n;
    const envelope = Math.sin(Math.PI * s);
    const offset =
      spec.bend * envelope + spec.wiggle * Math.sin(5 * Math.PI * s) * envelope;
    return c.at(s, offset);
  });
}

function placeCheckpoints(coords: LngLat[]) {
  const cumulative = [0];
  for (let i = 1; i < coords.length; i++) {
    cumulative.push(cumulative[i - 1] + haversineMi(coords[i - 1], coords[i]));
  }
  const total = cumulative[cumulative.length - 1];
  const marks: number[] = [];
  for (let m = CHECKPOINT_INTERVAL_MI; m < total - 5; m += CHECKPOINT_INTERVAL_MI) {
    marks.push(m);
  }
  marks.push(total);

  let seg = 1;
  const points = marks.map((mile) => {
    while (seg < cumulative.length - 1 && cumulative[seg] < mile) seg++;
    const a = coords[seg - 1];
    const b = coords[seg];
    const len = cumulative[seg] - cumulative[seg - 1] || 1;
    const f = (mile - cumulative[seg - 1]) / len;
    const p: LngLat = [a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f];
    return { mile, position: p };
  });
  return { total, points };
}

function placeLabel(p: LngLat) {
  const lat = `${Math.abs(p[1]).toFixed(1)}°${p[1] >= 0 ? "N" : "S"}`;
  const lng = `${Math.abs(p[0]).toFixed(1)}°${p[0] >= 0 ? "E" : "W"}`;
  return `${lat} ${lng}`;
}

const RISK_POINTS: Record<CheckpointRisk, number> = {
  low: 0,
  moderate: 25,
  high: 50,
  severe: 75,
  no_travel: 100,
  // Missing data is scored conservatively, never as Low
  unavailable: 50,
};

export function buildStorms(trip: TripInput): StormCell[] {
  const c = corridor(
    [trip.origin.lng, trip.origin.lat],
    [trip.destination.lng, trip.destination.lat],
  );
  const radius = (f: number) => Math.min(2.4, Math.max(0.35, c.span * f));
  const etaHour = (s: number) =>
    (haversineMi(c.origin, c.destination) * 1.05 * s) / 60;
  return [
    {
      kind: "snow",
      center: c.at(0.55, 0.03),
      radius: radius(0.085),
      peak: 0.95,
      peakHour: etaHour(0.55),
      lifetime: 14,
      drift: [0.01, 0],
    },
    {
      kind: "rain",
      center: c.at(0.3, 0.19),
      radius: radius(0.06),
      peak: 0.62,
      peakHour: etaHour(0.3) + 1,
      lifetime: 10,
      drift: [0.02, 0.005],
    },
    {
      kind: "rain",
      center: c.at(0.78, -0.21),
      radius: radius(0.05),
      peak: 0.32,
      peakHour: etaHour(0.78) + 2,
      lifetime: 12,
      drift: [0, 0],
    },
  ];
}

export function generateAnalysis(trip: TripInput, mode: DataMode): RouteAnalysis {
  const c = corridor(
    [trip.origin.lng, trip.origin.lat],
    [trip.destination.lng, trip.destination.lat],
  );
  const storms = buildStorms(trip);
  const source = mode === "demo" ? "simulated" : "live";

  const draft = ROUTE_SPECS.map((spec) => {
    const coordinates = buildGeometry(c, spec);
    const { total, points } = placeCheckpoints(coordinates);
    const durationMin = (total / spec.speedMph) * 60;
    const checkpoints: Checkpoint[] = points.map(({ mile, position }, index) => {
      const hour = mile / spec.speedMph;
      const missing =
        spec.gapEvery !== undefined && index % spec.gapEvery === spec.gapEvery - 2;
      return {
        id: `${spec.id}-${index}`,
        index,
        mileFromOrigin: mile,
        position,
        etaAt: addHours(trip.departureAt, hour),
        place: placeLabel(position),
        weather: missing
          ? unavailableWeather()
          : weatherAt(storms, position, hour, trip.loadWeightLb, source),
      };
    });
    const weatherRiskScore =
      checkpoints.reduce((s, cp) => s + RISK_POINTS[cp.weather.overall], 0) /
      checkpoints.length;
    return { spec, coordinates, total, durationMin, checkpoints, weatherRiskScore };
  });

  const minDuration = Math.min(...draft.map((d) => d.durationMin));
  const sides = draft.map((d) =>
    Math.abs(d.spec.bend) < 0.1 ? "Direct" : `${sideName(c, d.spec.bend)} bypass`,
  );

  const routes: Route[] = draft.map((d, i) => {
    // 0 for the fastest route, 100 for one taking 50% longer
    const timeScore = Math.min(100, ((d.durationMin - minDuration) / minDuration) * 200);
    const weightedScore = 0.7 * d.weatherRiskScore + 0.3 * timeScore;
    return {
      id: d.spec.id,
      name: `Route ${d.spec.id.toUpperCase()} · ${sides[i]}`,
      via:
        sides[i] === "Direct"
          ? "Most direct corridor"
          : `Swings ${sides[i].split(" ")[0].replace(/ern$/, "").toLowerCase()} of the direct line`,
      distanceMi: d.total,
      durationMin: d.durationMin,
      arrivalAt: addHours(trip.departureAt, d.durationMin / 60),
      coordinates: d.coordinates,
      checkpoints: d.checkpoints,
      weatherRiskScore: Math.round(d.weatherRiskScore * 10) / 10,
      timeScore: Math.round(timeScore * 10) / 10,
      weightedScore: Math.round(weightedScore * 10) / 10,
      eligible: !d.checkpoints.some((cp) => cp.weather.overall === "no_travel"),
    };
  });

  return {
    id: `analysis-${Date.now().toString(36)}`,
    mode,
    trip,
    generatedAt: new Date().toISOString(),
    routes,
    recommendation: recommend(routes),
  };
}

function recommend(routes: Route[]) {
  const eligible = routes.filter(isEligible).sort((a, b) => a.weightedScore - b.weightedScore);
  const best = eligible[0];
  const reasons: string[] = [];

  if (best) {
    reasons.push(
      `Lowest weighted score (${best.weightedScore.toFixed(1)}) among ${eligible.length} eligible route${eligible.length === 1 ? "" : "s"}.`,
    );
    reasons.push(
      `${formatMiles(milesAt(best, "severe"))} Severe and ${formatMiles(milesAt(best, "high"))} High exposure.`,
    );
    const fastest = [...routes].sort((a, b) => a.durationMin - b.durationMin)[0];
    if (fastest.id !== best.id) {
      reasons.push(
        `Adds ${formatDuration(best.durationMin - fastest.durationMin)} vs. the fastest route (${fastest.name}) to avoid weather.`,
      );
    } else {
      reasons.push("Also the fastest available route.");
    }
    const runnerUp = eligible[1];
    if (runnerUp) {
      reasons.push(
        `${runnerUp.name} scores ${runnerUp.weightedScore.toFixed(1)} (weather ${runnerUp.weatherRiskScore.toFixed(0)}, time ${runnerUp.timeScore.toFixed(0)}).`,
      );
    }
  }

  for (const r of routes) {
    const gaps = r.checkpoints.filter((cp) => cp.weather.overall === "unavailable").length;
    if (gaps > 0) {
      reasons.push(
        `${r.name} has ${gaps} checkpoint${gaps === 1 ? "" : "s"} without weather data, scored conservatively.`,
      );
    }
    const blocked = noTravelCheckpoints(r);
    if (blocked.length > 0 && !best) {
      reasons.push(`${r.name} is blocked at ${blocked.length} checkpoint${blocked.length === 1 ? "" : "s"}.`);
    }
  }

  return { routeId: best?.id ?? null, reasons };
}
