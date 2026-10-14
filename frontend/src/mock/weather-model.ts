/**
 * Deterministic fake weather: a few storm cells placed relative to the trip
 * corridor, whose strength varies with time. Good enough to exercise every
 * risk level in the UI without any provider.
 */
import { worstRisk } from "@/src/lib/risk";
import type {
  CheckpointRisk,
  CheckpointWeather,
  DataSource,
  LngLat,
  RiskLevel,
} from "@/src/lib/types";

export type StormCell = {
  center: LngLat;
  /** Radius in degrees */
  radius: number;
  kind: "snow" | "rain";
  /** Peak intensity 0–1 */
  peak: number;
  /** Hours after departure when the cell is strongest */
  peakHour: number;
  /** Hours for intensity to fall to ~37% of peak */
  lifetime: number;
  /** Drift in degrees per hour */
  drift: LngLat;
};

export function cellIntensity(cell: StormCell, p: LngLat, hour: number) {
  const cx = cell.center[0] + cell.drift[0] * hour;
  const cy = cell.center[1] + cell.drift[1] * hour;
  const d2 = (p[0] - cx) ** 2 + (p[1] - cy) ** 2;
  const spatial = Math.exp(-d2 / cell.radius ** 2);
  const temporal = Math.exp(-(((hour - cell.peakHour) / cell.lifetime) ** 2));
  return cell.peak * spatial * temporal;
}

export function fieldIntensity(cells: StormCell[], p: LngLat, hour: number) {
  return Math.min(
    1,
    cells.reduce((sum, c) => sum + cellIntensity(c, p, hour), 0),
  );
}

type Thresholds = [number, number, number, number];

const LEVELS: RiskLevel[] = ["low", "moderate", "high", "severe", "no_travel"];

function classify(value: number, t: Thresholds): RiskLevel {
  const i = t.findIndex((limit) => value < limit);
  return LEVELS[i === -1 ? 4 : i];
}

const WIND_MPH: Thresholds = [20, 30, 40, 50];
const RAIN_IN_HR: Thresholds = [0.1, 0.3, 0.6, 1.0];
const SNOW_IN_HR: Thresholds = [0.2, 0.5, 1.0, 2.0];

export const LIGHT_LOAD_LB = 26_000;
export const HEAVY_LOAD_LB = 65_000;

function round(n: number, places = 1) {
  const f = 10 ** places;
  return Math.round(n * f) / f;
}

export function weatherAt(
  cells: StormCell[],
  p: LngLat,
  hour: number,
  loadLb: number,
  source: Exclude<DataSource, "unavailable">,
): CheckpointWeather {
  let wind = 6 + 4 * Math.abs(Math.sin(p[0] * 3 + p[1] * 2 + hour / 5));
  let rain = 0;
  let snow = 0;
  for (const cell of cells) {
    const i = cellIntensity(cell, p, hour);
    if (cell.kind === "snow") {
      snow += 2.6 * i;
      wind += 48 * i;
    } else {
      rain += 1.25 * i;
      wind += 34 * i;
    }
  }

  const appliedRules: string[] = [];
  let windT = WIND_MPH;
  let snowT = SNOW_IN_HR;
  if (loadLb < LIGHT_LOAD_LB) {
    windT = WIND_MPH.map((v) => v - 10) as Thresholds;
    appliedRules.push(
      `Light load (< ${LIGHT_LOAD_LB.toLocaleString()} lb): wind thresholds lowered 10 mph for rollover risk`,
    );
  }
  if (loadLb > HEAVY_LOAD_LB) {
    snowT = SNOW_IN_HR.map((v) => v * 0.75) as Thresholds;
    appliedRules.push(
      `Heavy load (> ${HEAVY_LOAD_LB.toLocaleString()} lb): snowfall thresholds tightened 25% for braking distance`,
    );
  }

  const windRisk = classify(wind, windT);
  const rainRisk = classify(rain, RAIN_IN_HR);
  const snowRisk = classify(snow, snowT);

  return {
    source,
    wind: { value: round(wind, 0), unit: "mph", risk: windRisk },
    rain: { value: round(rain, 2), unit: "in/hr", risk: rainRisk },
    snow: { value: round(snow, 2), unit: "in/hr", risk: snowRisk },
    overall: worstRisk([windRisk, rainRisk, snowRisk]),
    appliedRules,
  };
}

export function unavailableWeather(): CheckpointWeather {
  const missing = (unit: string) => ({
    value: null,
    unit,
    risk: "unavailable" as CheckpointRisk,
  });
  return {
    source: "unavailable",
    wind: missing("mph"),
    rain: missing("in/hr"),
    snow: missing("in/hr"),
    overall: "unavailable",
    appliedRules: [],
  };
}
