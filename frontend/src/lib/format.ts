const dateTime = new Intl.DateTimeFormat("en-US", {
  weekday: "short",
  month: "short",
  day: "numeric",
  hour: "numeric",
  minute: "2-digit",
});

const timeOnly = new Intl.DateTimeFormat("en-US", {
  weekday: "short",
  hour: "numeric",
  minute: "2-digit",
});

const number = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });

export function formatDateTime(iso: string) {
  return dateTime.format(new Date(iso));
}

export function formatTime(iso: string) {
  return timeOnly.format(new Date(iso));
}

export function formatMiles(mi: number) {
  return `${number.format(mi)} mi`;
}

export function formatDuration(min: number) {
  const h = Math.floor(min / 60);
  const m = Math.round(min % 60);
  return h > 0 ? `${h} h ${m.toString().padStart(2, "0")} m` : `${m} m`;
}

export function formatWeight(lb: number) {
  return `${number.format(lb)} lb`;
}

export function formatPercent(p: number) {
  return `${p < 1 && p > 0 ? "<1" : number.format(p)}%`;
}

export function formatMeasure(value: number | null, unit: string) {
  if (value === null) return "—";
  // Rates are classified at 0.01 in/hr precision, so show them that way
  if (unit === "in/hr") return `${value.toFixed(2)} ${unit}`;
  return `${value.toFixed(value < 10 && value % 1 !== 0 ? 1 : 0)} ${unit}`;
}

export function addHours(iso: string, hours: number) {
  return new Date(new Date(iso).getTime() + hours * 3_600_000).toISOString();
}
