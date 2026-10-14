/**
 * StormRoute API client. Every page talks to the backend through these
 * functions; errors arrive as `ApiError` with the backend's code and any
 * field-specific messages.
 */
import type { ForecastSnapshot, RouteAnalysis, RouteDetail, TripInput } from "@/src/lib/types";

const BASE_URL = (import.meta.env.VITE_API_URL ?? "http://localhost:8000/api").replace(/\/$/, "");

export class ApiError extends Error {
  status: number;
  code: string;
  /** Field-specific messages, keyed by request field (e.g. `loadWeightLb`) */
  fields: Record<string, string[]>;

  constructor(status: number, code: string, message: string, fields: Record<string, string[]> = {}) {
    super(message);
    this.status = status;
    this.code = code;
    this.fields = fields;
  }
}

type ErrorBody = { error?: { code?: string; message?: string; fields?: Record<string, string[]> } };

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      ...init,
      headers: { Accept: "application/json", "Content-Type": "application/json", ...init?.headers },
    });
  } catch {
    throw new ApiError(0, "network_error", "Can't reach the StormRoute server. Check your connection and try again.");
  }

  const body = (await response.json().catch(() => null)) as unknown;
  if (!response.ok) {
    const error = (body as ErrorBody | null)?.error;
    throw new ApiError(
      response.status,
      error?.code ?? "http_error",
      error?.message ?? `Request failed (HTTP ${response.status}).`,
      error?.fields,
    );
  }
  return body as T;
}

export const api = {
  analyzeRoutes(trip: TripInput, options: { demo?: boolean } = {}): Promise<RouteAnalysis> {
    return request("/routes/analyze/", {
      method: "POST",
      body: JSON.stringify({ ...trip, ...(options.demo ? { mode: "demo" } : {}) }),
    });
  },

  loadDemo(): Promise<RouteAnalysis> {
    return request("/routes/demo/");
  },

  getRoute(routeId: string): Promise<RouteDetail> {
    return request(`/routes/${encodeURIComponent(routeId)}/`);
  },

  getForecast(analysisId: string, offsetHours: number): Promise<ForecastSnapshot> {
    return request(`/analyses/${encodeURIComponent(analysisId)}/forecast/?offset=${offsetHours}`);
  },
};
