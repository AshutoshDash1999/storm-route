# StormRoute

Weather-aware truck route planning for US trips. Enter an origin, a destination,
a departure time and a load weight. StormRoute finds up to three truck routes,
checks the forecast at checkpoints along each one at the time the truck would
actually be there, and recommends the route with the least weather exposure.

- **Checkpoints every 10, 25 or 50 miles** along each route, placed by distance and
  timed by estimated arrival.
- **Risk per checkpoint** from wind, rain and snow, with load-aware overrides for heavy trucks.
- **A strict ranking** of eligible routes: fewest severe miles, then fewest high
  miles, then lowest average risk, then shortest time. Each route that loses says
  which rule put it below the winner.
- **A forecast slider** of up to 48 hours to see how the weather changes along the route.
- **Demo mode** with fixed, labelled simulated data, for development and when
  provider keys are missing.

## Architecture

```
┌──────────────────────────┐     JSON over HTTP      ┌──────────────────────────────┐
│ frontend/                │ ──────────────────────▶ │ backend/                     │
│ React + Vite SPA         │   /api/routes/analyze/  │ Django REST API              │
│ map, forecast, planning  │ ◀────────────────────── │ routing, weather, risk,      │
└──────────────────────────┘                         │ scoring, recommendation      │
                                                     └──────┬──────────────┬────────┘
                                                            │              │
                                                 OpenRouteService     Open-Meteo
                                                 (routes, geocoding)  (forecast)
```

The browser never sees a provider key. The backend holds the OpenRouteService
key, calls both providers, and returns one analysis for the frontend to draw.
Results are kept in the server's cache for an hour, so the frontend can ask for
route details and forecast slices by ID. Nothing is stored in a database.

## Repository layout

| Path | What it is |
|---|---|
| [backend/](backend/) | Django API: routing, weather, risk engine, scoring, tests |
| [frontend/](frontend/) | React app: trip form, route map, checkpoint views |
| [.gitignore](.gitignore) | Repo-wide ignore rules. Each app also has its own |

## Quick start

You need Python 3.12 or newer and Node.js `^20.19.0` or `>=22.12.0`.

Run the backend and the frontend in two terminals.

**1. Backend**

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # set SECRET_KEY; add ORS_API_KEY for live data
python manage.py runserver    # http://127.0.0.1:8000
```

**2. Frontend**

```bash
cd frontend
npm install
cp .env.example .env          # VITE_API_URL=http://localhost:8000/api
npm run dev                   # http://localhost:5173
```

Open http://localhost:5173. Without an `ORS_API_KEY`, the backend runs in demo
mode. Every weather value in a demo result has `source: "simulated"`.

To get a live OpenRouteService key, sign up at
[openrouteservice.org](https://openrouteservice.org/dev/#/signup). Open-Meteo
needs no key.

## Running the checks

```bash
# backend: pytest suite, with providers mocked
cd backend && pytest

# frontend: type-check and production build, then lint
cd frontend && npm run build && npm run lint
```

## Data sources and attribution

| Source | Used for | Terms |
|---|---|---|
| [OpenRouteService](https://openrouteservice.org) | Truck routes (`driving-hgv`) and text geocoding in live mode | Needs an API key, kept on the backend |
| [Open-Meteo](https://open-meteo.com) | Hourly wind, gusts, rain, showers and snowfall, up to 16 days out | Free tier is non-commercial. Attribution under CC BY 4.0 |
| [GeoNames](https://download.geonames.org/export/zip/) | US city and ZIP code search data (`backend/apps/locations/data/`) | CC BY 4.0 |
| [CARTO](https://carto.com) basemaps | Map tiles in the frontend | Attribution shown in the map corner |

## Limits

- **Not legal truck routing.** Routes are not checked for bridges, weight limits,
  height, or hazmat restrictions. Every live response carries a warning saying so.
  Check the route with a truck-specific navigation tool before you drive it.
- **US only.** Trips are planned within the United States. Demo routing only
  works in the contiguous 48 states. Departures must be within 7 days.
- **Forecasts are forecasts.** Weather is only as current as the provider's model
  run. Where data is missing, a checkpoint is shown as Unknown and is never
  treated as Low.

## Documentation

- [Backend README](backend/README.md): setup, environment variables, API reference, risk and scoring rules, deployment
- [Frontend README](frontend/README.md): stack, scripts, pages, source layout
