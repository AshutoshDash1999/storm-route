import type { LngLat } from "@/src/lib/types";

export function boundsOf(coords: LngLat[]): [LngLat, LngLat] {
  const lngs = coords.map((c) => c[0]);
  const lats = coords.map((c) => c[1]);
  return [
    [Math.min(...lngs), Math.min(...lats)],
    [Math.max(...lngs), Math.max(...lats)],
  ];
}

export const FIT_PADDING = { top: 60, bottom: 60, left: 60, right: 60 };
