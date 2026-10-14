import {
  CircleCheck,
  CircleHelp,
  Info,
  OctagonX,
  TriangleAlert,
  ShieldAlert,
  type LucideIcon,
} from "lucide-react";

import type {
  Checkpoint,
  CheckpointRisk,
  CheckpointWeather,
  RiskExposure,
  Route,
} from "@/src/lib/types";

type RiskMeta = {
  label: string;
  /** Short glyph rendered inside map markers so risk is never color-only */
  glyph: string;
  /** Hex, shared by Tailwind inline styles and MapLibre paint */
  color: string;
  /** Text color with enough contrast on `color` */
  onColor: string;
  icon: LucideIcon;
  rank: number;
};

export const RISK: Record<CheckpointRisk, RiskMeta> = {
  low: {
    label: "Low",
    glyph: "L",
    color: "#16a34a",
    onColor: "#ffffff",
    icon: CircleCheck,
    rank: 0,
  },
  moderate: {
    label: "Moderate",
    glyph: "M",
    color: "#eab308",
    onColor: "#1c1917",
    icon: Info,
    rank: 1,
  },
  high: {
    label: "High",
    glyph: "H",
    color: "#ea580c",
    onColor: "#ffffff",
    icon: TriangleAlert,
    rank: 2,
  },
  severe: {
    label: "Severe",
    glyph: "S",
    color: "#dc2626",
    onColor: "#ffffff",
    icon: ShieldAlert,
    rank: 3,
  },
  no_travel: {
    label: "No Travel",
    glyph: "✕",
    color: "#581c87",
    onColor: "#ffffff",
    icon: OctagonX,
    rank: 4,
  },
  unavailable: {
    label: "Unknown",
    glyph: "?",
    color: "#9ca3af",
    onColor: "#111827",
    icon: CircleHelp,
    rank: -1,
  },
};

export const LEGEND_LEVELS: CheckpointRisk[] = [
  "low",
  "moderate",
  "high",
  "severe",
  "no_travel",
  "unavailable",
];

export const MEASURED_LEVELS = [
  "low",
  "moderate",
  "high",
  "severe",
  "no_travel",
] as const;

/** Worst of a set of risks. Missing data stays `unavailable` unless something is known to be worse. */
export function worstRisk(risks: CheckpointRisk[]): CheckpointRisk {
  if (risks.length === 0) return "unavailable";
  return risks.reduce((worst, r) => (RISK[r].rank > RISK[worst].rank ? r : worst));
}

export function hasNoTravel(route: Route) {
  return route.checkpoints.some((c) => c.weather.overall === "no_travel");
}

/** Defensive: a route with a No Travel checkpoint is never eligible, whatever the payload says. */
export function isEligible(route: Route) {
  return route.eligible && !hasNoTravel(route);
}

export function noTravelCheckpoints(route: Route): Checkpoint[] {
  return route.checkpoints.filter((c) => c.weather.overall === "no_travel");
}

/**
 * Miles per risk level, in legend order, as computed by the backend: each
 * checkpoint owns the stretch from itself to the next checkpoint.
 */
export function riskExposure(route: Route): RiskExposure[] {
  const byLevel = new Map(route.exposure.map((e) => [e.level, e]));
  return LEGEND_LEVELS.map((level) => byLevel.get(level) ?? { level, miles: 0, percent: 0 });
}

export function milesAt(route: Route, level: CheckpointRisk) {
  return riskExposure(route).find((e) => e.level === level)?.miles ?? 0;
}

/** Placeholder when a forecast snapshot has nothing for a checkpoint. Never coerced to Low. */
export function unavailableWeather(): CheckpointWeather {
  const missing = (unit: string) => ({ value: null, unit, risk: "unavailable" as CheckpointRisk });
  return {
    source: "unavailable",
    wind: missing("mph"),
    rain: missing("in/hr"),
    snow: missing("in/hr"),
    overall: "unavailable",
    triggers: [],
    appliedRules: [],
  };
}
