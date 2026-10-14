import { z } from "zod";

import type { Location, TripInput } from "@/src/lib/types";

export const MAX_LOAD_LB = 80_000;
const MAX_DEPARTURE_DAYS = 7;

const locationSchema = z.object({
  id: z.string(),
  label: z.string(),
  lng: z.number(),
  lat: z.number(),
});

const pickLocation = (what: string) =>
  locationSchema
    .nullable()
    .refine((v) => v !== null, `Choose ${what} from the suggestions.`)
    .transform((v) => v as Location);

export const tripFormSchema = z
  .object({
    origin: pickLocation("an origin"),
    destination: pickLocation("a destination"),
    departureDate: z
      .date()
      .nullable()
      .refine((v) => v !== null, "Choose a departure date.")
      .transform((v) => v as Date),
    departureTime: z.string().regex(/^\d{2}:\d{2}$/, "Enter a departure time."),
    loadWeightLb: z.coerce
      .number<string | number>({ error: "Enter the load weight in pounds." })
      .gt(0, "Load weight must be greater than 0 lb.")
      .max(MAX_LOAD_LB, `Load weight can't exceed ${MAX_LOAD_LB.toLocaleString()} lb (legal gross limit).`),
  })
  .superRefine((v, ctx) => {
    if (v.origin && v.destination && v.origin.id === v.destination.id) {
      ctx.addIssue({
        code: "custom",
        path: ["destination"],
        message: "Destination must be different from the origin.",
      });
    }
    if (v.departureDate && /^\d{2}:\d{2}$/.test(v.departureTime)) {
      const at = combineDateTime(v.departureDate, v.departureTime);
      const now = Date.now();
      if (at.getTime() < now - 5 * 60_000) {
        ctx.addIssue({
          code: "custom",
          path: ["departureTime"],
          message: "Departure can't be in the past.",
        });
      } else if (at.getTime() > now + MAX_DEPARTURE_DAYS * 86_400_000) {
        ctx.addIssue({
          code: "custom",
          path: ["departureDate"],
          message: `Departure must be within the next ${MAX_DEPARTURE_DAYS} days for forecast coverage.`,
        });
      }
    }
  });

export type TripFormInput = z.input<typeof tripFormSchema>;
export type TripFormOutput = z.output<typeof tripFormSchema>;

export function combineDateTime(date: Date, time: string) {
  const [h, m] = time.split(":").map(Number);
  const d = new Date(date);
  d.setHours(h, m, 0, 0);
  return d;
}

export function toTripInput(v: TripFormOutput): TripInput {
  return {
    origin: v.origin,
    destination: v.destination,
    departureAt: combineDateTime(v.departureDate, v.departureTime).toISOString(),
    loadWeightLb: v.loadWeightLb,
  };
}

const pad = (n: number) => n.toString().padStart(2, "0");

export function toFormValues(trip: TripInput | null): TripFormInput {
  if (!trip) {
    const next = new Date(Date.now() + 60 * 60_000);
    next.setMinutes(0, 0, 0);
    return {
      origin: null,
      destination: null,
      departureDate: next,
      departureTime: `${pad(next.getHours())}:00`,
      loadWeightLb: "",
    };
  }
  const at = new Date(trip.departureAt);
  return {
    origin: trip.origin,
    destination: trip.destination,
    departureDate: at,
    departureTime: `${pad(at.getHours())}:${pad(at.getMinutes())}`,
    loadWeightLb: trip.loadWeightLb,
  };
}
