export type LngLat = [number, number];

export type RiskLevel = "low" | "moderate" | "high" | "severe" | "no_travel";

/** A risk level, or `unavailable` when weather data is missing. Never coerced to `low`. */
export type CheckpointRisk = RiskLevel | "unavailable";

export type DataSource = "live" | "simulated" | "unavailable";

export type DataMode = "live" | "demo";

export type Location = {
  id: string;
  label: string;
  lng: number;
  lat: number;
};

/** A `/locations/search/` result: a city, or a single ZIP code inside one */
export type LocationResult = Location & {
  type: "city" | "zip";
  city: string;
  state: string;
  county: string | null;
  /** 5-digit ZIP for `zip` results, null for cities */
  zipCode: string | null;
};

export type LocationSearchResponse = {
  query: string;
  results: LocationResult[];
};

export type TripInput = {
  origin: Location;
  destination: Location;
  /** ISO timestamp */
  departureAt: string;
  loadWeightLb: number;
  /** Hours added to every checkpoint's weather time (0–48). Backend default 0. */
  forecastOffsetHours?: number;
  /** Backend default 25 */
  checkpointSpacingMi?: number;
};

export type ConditionClass = {
  value: number | null;
  unit: string;
  risk: CheckpointRisk;
};

export type CheckpointWeather = {
  source: DataSource;
  /** ISO timestamp the weather describes */
  validAt?: string;
  wind: ConditionClass;
  rain: ConditionClass;
  snow: ConditionClass;
  overall: CheckpointRisk;
  /** Conditions that set `overall`, e.g. "Wind 47 mph → Severe" */
  triggers: string[];
  /** Load-dependent rules that changed the classification */
  appliedRules: string[];
};

export type Checkpoint = {
  id: string;
  index: number;
  mileFromOrigin: number;
  position: LngLat;
  /** ISO timestamp */
  etaAt: string;
  /** Nearest place name, for "No Travel at …" warnings */
  place: string;
  weather: CheckpointWeather;
};

export type Route = {
  id: string;
  name: string;
  via: string;
  distanceMi: number;
  durationMin: number;
  /** ISO timestamp */
  arrivalAt: string;
  coordinates: LngLat[];
  checkpoints: Checkpoint[];
  /** 0–100, normalized weather risk (higher is riskier) */
  weatherRiskScore: number;
  /** 0–100, normalized travel-time score (higher is slower) */
  timeScore: number;
  /** 0.7 · weather + 0.3 · time */
  weightedScore: number;
  eligible: boolean;
  /** 1 = recommended; null when not eligible */
  rank: number | null;
  /** Miles per risk level; each checkpoint owns the stretch up to the next one */
  exposure: RiskExposure[];
  /** Severe + No Travel miles */
  severeMiles: number;
  noTravelCheckpointIds: string[];
  /** Share of miles with weather data, 0–1 */
  coverage: number;
  /** Why the route is ineligible, coverage gaps, etc. */
  warnings: string[];
  provider: { name: string; ref: string };
};

export type RiskExposure = {
  level: CheckpointRisk;
  miles: number;
  percent: number;
};

export type Recommendation = {
  routeId: string | null;
  status: "available" | "blocked";
  reasons: string[];
};

/** Which layers fell back to simulated data after a live provider failed */
export type Fallback = { routing: boolean; weather: boolean };

export type RouteAnalysis = {
  id: string;
  mode: DataMode;
  fallback: Fallback;
  sources: { routing: string; weather: string };
  trip: TripInput;
  generatedAt: string;
  routes: Route[];
  recommendation: Recommendation;
  /** Truck-routing limits, missing forecasts, fallbacks */
  warnings: string[];
};

export type RouteDetail = {
  analysisId: string;
  mode: DataMode;
  fallback: Fallback;
  trip: TripInput;
  recommended: boolean;
  route: Route;
};

export type ForecastGridPoint = {
  lng: number;
  lat: number;
  /** 0–1 normalized risk */
  intensity: number;
};

export type ForecastSnapshot = {
  offsetHours: number;
  validAt: string;
  available: boolean;
  grid: ForecastGridPoint[];
  /** Checkpoint weather keyed by checkpoint id, at `validAt` */
  checkpoints: Record<string, CheckpointWeather>;
  fallback: boolean;
  warnings: string[];
};
