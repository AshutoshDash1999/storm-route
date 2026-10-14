import type { RouteAnalysis, TripInput } from "@/src/lib/types";
import { generateAnalysis } from "@/src/mock/scenario";
import { findLocation } from "@/src/mock/us-locations";

/** Denver → Chicago, departing tomorrow 6:00 AM with a 42,000 lb load */
export function demoTrip(): TripInput {
  const departure = new Date();
  departure.setDate(departure.getDate() + 1);
  departure.setHours(6, 0, 0, 0);
  return {
    origin: findLocation("denver-co")!,
    destination: findLocation("chicago-il")!,
    departureAt: departure.toISOString(),
    loadWeightLb: 42_000,
  };
}

export function demoAnalysis(): RouteAnalysis {
  return generateAnalysis(demoTrip(), "demo");
}
