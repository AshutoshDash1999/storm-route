import {
  CircleCheck,
  CircleHelp,
  Info,
  OctagonX,
  TriangleAlert,
  ShieldAlert,
  type LucideIcon,
} from "lucide-react";

import type { Checkpoint, CheckpointRisk, Route } from "@/src/lib/types";

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
    label: "No data",
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

export type RiskExposure = {
  level: CheckpointRisk;
  miles: number;
  percent: number;
};

/**
 * Miles per risk level. Each checkpoint owns the segment from the previous
 * checkpoint (or origin) up to itself; the final stretch to the destination
 * belongs to the last checkpoint.
 */
export function riskExposure(route: Route): RiskExposure[] {
  const miles: Record<CheckpointRisk, number> = {
    low: 0,
    moderate: 0,
    high: 0,
    severe: 0,
    no_travel: 0,
    unavailable: 0,
  };
  const cps = route.checkpoints;
  cps.forEach((cp, i) => {
    const start = i === 0 ? 0 : cps[i - 1].mileFromOrigin;
    const end = i === cps.length - 1 ? route.distanceMi : cp.mileFromOrigin;
    miles[cp.weather.overall] += Math.max(0, end - start);
  });
  return LEGEND_LEVELS.map((level) => ({
    level,
    miles: miles[level],
    percent: route.distanceMi > 0 ? (miles[level] / route.distanceMi) * 100 : 0,
  }));
}

export function milesAt(route: Route, level: CheckpointRisk) {
  return riskExposure(route).find((e) => e.level === level)?.miles ?? 0;
}
