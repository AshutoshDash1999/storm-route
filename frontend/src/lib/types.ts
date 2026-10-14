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

export type TripInput = {
  origin: Location;
  destination: Location;
  /** ISO timestamp */
  departureAt: string;
  loadWeightLb: number;
};

export type ConditionClass = {
  value: number | null;
  unit: string;
  risk: CheckpointRisk;
};

export type CheckpointWeather = {
  source: DataSource;
  wind: ConditionClass;
  rain: ConditionClass;
  snow: ConditionClass;
  overall: CheckpointRisk;
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
};

export type Recommendation = {
  routeId: string | null;
  reasons: string[];
};

export type RouteAnalysis = {
  id: string;
  mode: DataMode;
  trip: TripInput;
  generatedAt: string;
  routes: Route[];
  recommendation: Recommendation;
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
};
