# StormRoute frontend

React single-page app for StormRoute. A user enters a trip, then compares
up to three routes on a map, checkpoint by checkpoint, against the weather at
the time the truck would reach each one. The backend does all the routing,
weather and risk work; this app only renders the results.

See the [root README](../README.md) for the full picture and the
[backend README](../backend/README.md) for the API.

## Stack

- React 19 with TypeScript, built by Vite 8. The React Compiler runs through a Babel plugin.
- Tailwind CSS v4 and shadcn-style components (`components/ui/`, lucide icons, base-ui primitives).
- MapLibre GL for the map. The `components/ui/map.tsx` component comes from the mapcn registry.
- TanStack Query for server state, React Router for routing, react-hook-form with zod for the trip form.

## Setup

Requires Node.js `^20.19.0` or `>=22.12.0`, the range Vite 8 declares.

```bash
cd frontend
npm install
cp .env.example .env   # points VITE_API_URL at the backend
npm run dev            # http://localhost:5173
```

The backend must be running on the URL in `VITE_API_URL` (default
`http://localhost:8000/api`). Its `CORS_ALLOWED_ORIGINS` already includes the
Vite dev port.

| Script | What it does |
|---|---|
| `npm run dev` | Vite dev server with hot reload |
| `npm run build` | Type-check with `tsc -b`, then production build to `dist/` |
| `npm run preview` | Serve the production build locally |
| `npm run lint` | Oxlint, configured in `.oxlintrc.json` |

There is no test runner in this package yet.

## Environment

| Variable | Default | Purpose |
|---|---|---|
| `VITE_API_URL` | `http://localhost:8000/api` | Base URL of the StormRoute API. Read at build time |

Vite inlines `VITE_*` variables into the bundle, so they are public. Never put
provider keys here. The OpenRouteService key stays on the backend.

## Pages

| Route | Page | Purpose |
|---|---|---|
| `/` | `TripPlannerPage` | Trip form: origin, destination, departure, load weight, checkpoint spacing |
| `/routes` | `RouteAnalysisPage` | Map and route cards for the latest analysis, with a forecast slider |
| `/routes/:routeId` | `RouteDetailsPage` | One route with its full checkpoint table. Also works for a shared link, by fetching the route from the API |

The latest analysis and the last trip form input are kept by `src/app/trip-context.tsx`
in `sessionStorage`, so they survive a reload in the same tab but not a new tab. If
there is no analysis, `/routes` shows the empty state. A route detail link opened
outside this session falls back to the API.

### Selection lives in the URL

The selected route, checkpoint, forecast hour and view are query parameters
(`?route=&cp=&t=&view=`), read and written by `src/features/routes/use-route-selection.ts`.
This keeps the map, cards and drawer in sync, and makes back/forward and
"Back to Routes" keep the same selection.

## Source layout

```
src/
  app/              shell: header, trip context, empty and error states
  pages/            one component per route
  features/
    trip/           trip form, location combobox, date-time picker, zod schema
    map/            RouteMap, checkpoint markers, forecast heatmap, legend
    routes/         route cards, checkpoint table and drawer, recommendation, forecast controls
  lib/
    api.ts          typed client; errors arrive as ApiError with the backend's code and field messages
    types.ts        request and response shapes, camelCase, mirroring the backend
    risk.ts         risk levels, labels and colors
    constants.ts    checkpoint spacing options, forecast window
components/ui/      shadcn-style primitives and the mapcn map
```

## Conventions

- **Colors and themes.** The app follows the OS light or dark setting. Risk colors
  come from `src/lib/risk.ts`, so the map, badges and table always agree.
- **Unknown weather is not Low.** A checkpoint with no data shows as unavailable,
  which matches the backend's `unavailable` risk value.
- **Types follow the API.** When the backend response changes, update
  `src/lib/types.ts` in the same change.
- **Path alias.** `@/` points at the `frontend/` folder, so `@/src/lib/api` is `src/lib/api.ts`.
