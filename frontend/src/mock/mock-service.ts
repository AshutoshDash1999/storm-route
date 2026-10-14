/**
 * Stand-in for the backend. Every page talks to data through these functions,
 * so swapping in real API calls later touches only this file.
 */
import type { ForecastSnapshot, RouteAnalysis, TripInput } from "@/src/lib/types";
import { demoAnalysis } from "@/src/mock/demo-scenario";
import { buildForecast } from "@/src/mock/forecast";
import { generateAnalysis, haversineMi } from "@/src/mock/scenario";
import { UNREACHABLE_IDS } from "@/src/mock/us-locations";

const LATENCY_MS = 800;

function delay<T>(value: () => T, ms = LATENCY_MS): Promise<T> {
  return new Promise((resolve, reject) =>
    setTimeout(() => {
      try {
        resolve(value());
      } catch (e) {
        reject(e);
      }
    }, ms),
  );
}

export class TripInputError extends Error {
  field: "origin" | "destination";
  constructor(field: "origin" | "destination", message: string) {
    super(message);
    this.field = field;
  }
}

export const mockService = {
  analyzeRoutes(trip: TripInput): Promise<RouteAnalysis> {
    return delay(() => {
      if (UNREACHABLE_IDS.has(trip.origin.id)) {
        throw new TripInputError("origin", `No drivable route from ${trip.origin.label}.`);
      }
      if (UNREACHABLE_IDS.has(trip.destination.id)) {
        throw new TripInputError(
          "destination",
          `No drivable route to ${trip.destination.label}.`,
        );
      }
      const miles = haversineMi(
        [trip.origin.lng, trip.origin.lat],
        [trip.destination.lng, trip.destination.lat],
      );
      if (miles < 60) {
        throw new TripInputError(
          "destination",
          "Destination is too close to the origin to compare routes (minimum 60 mi).",
        );
      }
      if (miles > 2200) {
        throw new Error(
          "Route service timed out for this distance. Try a shorter trip.",
        );
      }
      return generateAnalysis(trip, "live");
    }, LATENCY_MS + 600);
  },

  loadDemo(): Promise<RouteAnalysis> {
    return delay(demoAnalysis, 300);
  },

  getForecast(analysis: RouteAnalysis, offsetHours: number): Promise<ForecastSnapshot> {
    return delay(() => buildForecast(analysis, offsetHours), 250);
  },
};
