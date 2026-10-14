# StormRoute API (Django)

Compares up to three truck routes between two places, checks the weather at
checkpoints every 10, 25 or 50 miles along each one at the time the truck would be
there, classifies risk, and recommends the best eligible route.

## Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # set SECRET_KEY; add ORS_API_KEY for live data
python manage.py runserver   # http://127.0.0.1:8000
pytest                        # run the test suite
```

No database is used. Results are kept in the Django cache.

## Environment

| Variable | Default | Purpose |
|---|---|---|
| `SECRET_KEY` | dev key | Django secret. Required in production |
| `DEBUG` | `False` | Django debug mode |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated hostnames |
| `CORS_ALLOWED_ORIGINS` | Vite dev URLs | Comma-separated frontend origins |
| `DATA_MODE` | `live` | `live` or `demo` |
| `ORS_API_KEY` | empty | OpenRouteService key. With no key, the API runs in demo mode |
| `DEMO_FALLBACK` | `True` | Use labelled simulated data when a live provider fails |
| `PROVIDER_TIMEOUT_S` | `8` | Timeout for each provider request |
| `RESULT_TTL_S` | `3600` | How long route IDs stay retrievable |
| `ANALYZE_RATE` | `30/min` | Per-client limit on analysis requests |
| `LOG_LEVEL` | `INFO` | `stormroute` logger level |

Provider keys stay on the backend. The frontend only talks to this API.

## Layout

```
apps/
  common/           error types and handler, geometry helpers
  trips/            input validation, views, URL routes, result store
  routing/          OpenRouteService adapter, geocoding, demo routing, route naming
  weather/          Open-Meteo adapter, unit normalization, demo weather
  risk/engine.py    pure risk classification (no Django)
  recommendations/  checkpoints, scoring and ranking, analysis orchestration
  locations/        US city and ZIP search over the bundled GeoNames data
  demo/             curated city list and the deterministic demo scenario
scripts/            rebuilds locations/data/us_zip_codes.json from GeoNames
tests/              pytest suite (providers mocked with `responses`)
```

## API

All responses are JSON in camelCase, matching `frontend/src/lib/types.ts`.

### Errors

Every error has the same shape. `fields` appears only for input errors.

```json
{"error": {"code": "validation_error", "message": "Load weight must be greater than 0 lb.",
           "fields": {"loadWeightLb": ["Load weight must be greater than 0 lb."]}}}
```

| Status | `code` | When |
|---|---|---|
| 400 | `validation_error`, `invalid_body` | Bad input |
| 404 | `route_not_found`, `analysis_not_found` | Unknown or expired ID |
| 422 | `no_route` | Provider found no drivable route (`fields` names origin or destination) |
| 429 | `throttled` | Over `ANALYZE_RATE` |
| 503 / 504 | `routing_unavailable`, `provider_*` | Provider down and fallback disabled |

### `POST /api/routes/analyze/`

```json
{
  "origin": "Dallas, TX",
  "destination": {"id": "houston-tx", "label": "Houston, TX", "lat": 29.7604, "lng": -95.3698},
  "departureAt": "2026-10-15T08:00:00-05:00",
  "loadWeightLb": 35000,
  "forecastOffsetHours": 0,
  "checkpointSpacingMi": 25,
  "mode": "demo"
}
```

- `origin` and `destination`: a `{id, label, lat, lng}` object, or text. Text is
  matched against the bundled US city list, then OpenRouteService geocoding (live mode only).
- `departureAt` (alias `departure_time`): ISO-8601. Must be between 5 minutes
  ago and 7 days from now.
- `loadWeightLb` (alias `load_weight_lb`): must be over 0 and at most 80,000.
- `forecastOffsetHours` (alias `forecast_offset_hours`): 0–48, default 0.
  Shifts every checkpoint's weather time later by this many hours.
- `checkpointSpacingMi`: 10, 25 or 50 miles, default 25.
- `mode`: `"demo"` forces simulated data.

The response is a `RouteAnalysis`. Abridged:

```json
{
  "id": "an_…",
  "mode": "live",
  "fallback": {"routing": false, "weather": false},
  "sources": {"routing": "OpenRouteService", "weather": "Open-Meteo"},
  "trip": {"origin": {…}, "destination": {…}, "departureAt": "…Z", "loadWeightLb": 35000, …},
  "warnings": ["Routes use a heavy-vehicle profile but are not checked for truck legality …"],
  "recommendation": {"routeId": "rt_…", "status": "available", "reasons": ["…"]},
  "routes": [{
    "id": "rt_…", "name": "Route A · Direct", "via": "Most direct corridor",
    "distanceMi": 240.1, "durationMin": 231.0, "arrivalAt": "…Z",
    "coordinates": [[-96.797, 32.7767], …],
    "weatherRiskScore": 12.5, "eligible": true, "rank": 1, "coverage": 1.0,
    "severeMiles": 0, "highMiles": 25,
    "exposure": [{"level": "low", "miles": 190.1, "percent": 79.2}, …],
    "noTravelCheckpointIds": [], "warnings": [],
    "checkpoints": [{
      "id": "rt_…-cp0", "index": 0, "mileFromOrigin": 0, "position": [-96.797, 32.7767],
      "etaAt": "…Z", "place": "near Dallas, TX",
      "weather": {
        "source": "live", "validAt": "…Z",
        "wind": {"value": 18, "unit": "mph", "risk": "low"},
        "rain": {"value": 0.12, "unit": "in/hr", "risk": "moderate"},
        "snow": {"value": 0, "unit": "in/hr", "risk": "low"},
        "overall": "moderate", "triggers": ["Rain 0.12 in/hr → Moderate"], "appliedRules": []
      }
    }]
  }]
}
```

Risk values are `low | moderate | high | severe | no_travel | unavailable`.
`unavailable` means Unknown and is never treated as Low.

### Other endpoints

| Endpoint | Returns |
|---|---|
| `GET /api/locations/search/?q=dall&limit=10` | `{query, results}`: matching US cities and ZIP codes (`limit` 1–50, default 10) |
| `GET /api/locations/{location_id}/` | One location, or 404 `location_not_found` |
| `GET /api/routes/{route_id}/` | `{analysisId, mode, fallback, trip, recommended, route}` |
| `GET /api/routes/{route_id}/checkpoints/` | `{routeId, mode, checkpoints}` |
| `GET /api/analyses/{analysis_id}/forecast/?offset=N` | `ForecastSnapshot`: weather at every checkpoint at departure + N hours, plus a heatmap grid |
| `GET /api/health/` | `{status, mode, providers}` |

## How the decision is made

**Checkpoints.** A checkpoint is placed every 10, 25 (default) or 50 miles of
route distance, plus one at the destination. At 25 miles, a 62-mile route gets
checkpoints at 0, 25, 50 and 62.
Positions are interpolated along the route geometry. The ETA at each checkpoint
assumes a constant speed over the provider's total duration.

**Risk** (`apps/risk/engine.py`):

| Level | Wind | Rain rate | Snowfall rate |
|---|---:|---:|---:|
| Low | <25 mph | <0.10 in/hr | <0.5 in/hr |
| Moderate | 25 to <35 | 0.10 to <0.25 | 0.5 to <1.0 |
| High | 35 to <45 | 0.25 to <0.50 | 1.0 to <2.0 |
| Severe | 45 to <55 | 0.50–1.00 | 2.0–3.0 |
| No Travel | ≥55 | >1.00 | >3.0 |

Load overrides: wind ≥55 mph is No Travel at any load. Wind of 45 to <55 mph
with a load over 30,000 lb is No Travel. Wind of 35 to <45 mph with a load over
40,000 lb is at least Severe. A checkpoint's risk is its worst condition.
If any condition is missing, the checkpoint is Unknown, unless the known values
already prove No Travel. Values are rounded for display (whole mph, 0.01 in/hr)
before classification, so the number shown always matches its level.

**Scoring** (`apps/recommendations/scoring.py`):
- Each checkpoint's risk covers the stretch up to the next checkpoint.
- Average risk (`weatherRiskScore`) is a distance-weighted average of points
  per mile: Low 0, Moderate 25, High 50, Severe 75, No Travel 100.
- Unknown miles count as Severe, both in `severeMiles` and in average risk, so
  a gap in the data never makes a route look safer.
- A route is not eligible if it has any No Travel checkpoint, or if less than
  half its miles have weather data.
- Eligible routes are ranked strictly, each step only breaking ties in the one
  before: (1) fewest Severe miles, (2) fewest High miles, (3) lowest average
  risk, (4) shortest travel time. Miles and average risk are compared at 0.1
  precision. The top route is recommended, and `reasons` names the criterion
  that put each other route below it. If no route is eligible, `routeId` is `null` and
  `status` is `"blocked"`.

## Providers

- **OpenRouteService** `driving-hgv` profile. On the public API, ORS only
  returns alternative routes for trips under about 100 km. For longer trips the
  adapter asks for detours through points either side of the direct line, and
  drops any that duplicate another route or are more than 60% longer than it.
  Routes are **not** checked for truck legality (bridges, weight limits,
  hazmat); every live response includes a warning saying so.
- **Open-Meteo** hourly `wind_speed_10m`, `wind_gusts_10m`, `rain`, `showers`
  and `snowfall`. Wind is the larger of sustained speed and gusts. Each value
  is converted using the unit the response reports. The forecast covers 16
  days. Times outside that window are Unknown. The free tier is for
  non-commercial use only (about 10,000 calls a day) and requires attribution
  under CC BY 4.0. Commercial use needs a paid plan.

## Demo mode and fallback

Demo mode builds three fixed corridors between the two points and moves storm
cells along them. The same trip always gives the same result. The scenario has:
- a blizzard that blocks the direct route,
- a heavy rain band on one bypass,
- an area with no weather data, to show how Unknown is handled,
- no forecast beyond 45 hours after departure.

Demo mode is used when the request sends `mode: "demo"`, when `DATA_MODE=demo`,
or when no `ORS_API_KEY` is set. In demo mode, `mode` is `"demo"` and every
weather value has `source: "simulated"`.

In live mode with `DEMO_FALLBACK=True`:
- **Routing fails:** the whole analysis is simulated, with `mode: "demo"`,
  `fallback.routing: true` and a warning.
- **Weather fails:** live routes are kept and checkpoint weather is simulated,
  with `fallback.weather: true`, `source: "simulated"` on each checkpoint and a
  warning.
- **Weather fails for only some checkpoints:** those checkpoints are Unknown
  and the response includes a warning.

With `DEMO_FALLBACK=False`, a routing failure returns 503. A weather failure
returns every checkpoint as Unknown, which means no route is recommended.

## Deployment

1. Set `DEBUG=False`, a real `SECRET_KEY`, `ALLOWED_HOSTS`, and set
   `CORS_ALLOWED_ORIGINS` to the hosted frontend URL.
2. Set `ORS_API_KEY` as a secret in the hosting platform.
3. Run `gunicorn config.wsgi --workers 2 --timeout 60`.
4. The default cache is per-process memory. With more than one worker or
   instance, a route ID created by one process cannot be found by another.
   Before scaling out, set `CACHES` to Redis (or store results in a database).
5. Set `VITE_API_URL` in the frontend build to `https://<api-host>/api`.
