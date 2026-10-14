"""
OpenRouteService adapter (https://openrouteservice.org/dev/#/api-docs/v2/directions).

Uses the `driving-hgv` (heavy goods vehicle) profile. That avoids some roads
closed to trucks, but StormRoute does not pass vehicle dimensions or hazmat
restrictions, so routes are not guaranteed to be truck-legal.

ORS only computes `alternative_routes` for short trips (about 100 km on the
public API). For longer trips, or when it returns fewer alternatives than
asked, we request detours through via points either side of the direct line.
"""

import logging
import re

import requests

from apps.common.exceptions import (
    NoRouteFound,
    ProviderBadResponse,
    ProviderRateLimited,
    ProviderTimeout,
    ProviderUnavailable,
)
from apps.common.geo import Corridor, LngLat

from .base import RawRoute, RoutingResult

logger = logging.getLogger('stormroute')

BASE_URL = 'https://api.openrouteservice.org'
PROFILE = 'driving-hgv'

# ORS internal error codes
ROUTE_NOT_FOUND = 2009
POINT_NOT_FOUND = 2010
LIMIT_EXCEEDED = 2004

#: Sideways offset of detour via points, as a fraction of the straight-line span
DETOUR_OFFSET = 0.18
#: Detours longer than this multiple of the primary route are discarded
MAX_DETOUR_FACTOR = 1.6
#: Alternatives within this fraction of an existing route's distance and duration are duplicates
DUPLICATE_TOLERANCE = 0.01


class _LimitExceeded(ProviderBadResponse):
    pass


class OrsRouting:
    name = 'OpenRouteService'

    def __init__(self, api_key: str, timeout: float = 8.0, session: requests.Session | None = None):
        self.api_key = api_key
        self.timeout = timeout
        self.session = session or requests.Session()

    def routes(self, origin: LngLat, destination: LngLat, max_routes: int = 3) -> RoutingResult:
        warnings: list[str] = []
        try:
            routes = self._directions([origin, destination], alternatives=max_routes)
        except _LimitExceeded:
            routes = self._directions([origin, destination])

        if len(routes) < max_routes:
            routes += self._detours(origin, destination, routes, max_routes - len(routes))
        if len(routes) < max_routes:
            warnings.append(
                f'Only {len(routes)} route alternative{"" if len(routes) == 1 else "s"} available for this trip.'
            )
        return RoutingResult(routes[:max_routes], warnings)

    def _detours(self, origin: LngLat, destination: LngLat, existing: list[RawRoute], wanted: int) -> list[RawRoute]:
        c = Corridor(origin, destination)
        primary = existing[0]
        found: list[RawRoute] = []
        for ref, offset in (('via-left', DETOUR_OFFSET), ('via-right', -DETOUR_OFFSET)):
            if len(found) >= wanted:
                break
            via = c.at(0.5, offset)
            try:
                # Via points are rarely on a road; let ORS snap them from any distance
                route = self._directions([origin, via, destination], radiuses=[-1, -1, -1], ref=ref)[0]
            except (NoRouteFound, ProviderBadResponse) as e:
                logger.info('Skipping %s detour: %s', ref, e)
                continue
            if route.distance_mi > primary.distance_mi * MAX_DETOUR_FACTOR:
                continue
            if any(_same(route, r) for r in existing + found):
                continue
            found.append(route)
        return found

    def _directions(self, coords: list[LngLat], *, alternatives: int = 1, radiuses: list[float] | None = None,
                    ref: str | None = None) -> list[RawRoute]:
        body: dict = {
            'coordinates': [list(p) for p in coords],
            'units': 'mi',
            'instructions': False,
            'radiuses': radiuses or [5000] * len(coords),
        }
        if alternatives > 1:
            body['alternative_routes'] = {'target_count': alternatives, 'share_factor': 0.6, 'weight_factor': 1.6}

        data = self._post(f'/v2/directions/{PROFILE}/geojson', body)
        try:
            features = data['features']
            routes = []
            for i, f in enumerate(features):
                summary = f['properties']['summary']
                geometry = [(float(p[0]), float(p[1])) for p in f['geometry']['coordinates']]
                if len(geometry) < 2:
                    raise ValueError('degenerate geometry')
                routes.append(RawRoute(
                    coordinates=geometry,
                    distance_mi=float(summary['distance']),
                    duration_s=float(summary['duration']),
                    provider='openrouteservice',
                    provider_ref=ref or ('primary' if i == 0 else f'alternative-{i}'),
                ))
        except (KeyError, TypeError, ValueError, IndexError) as e:
            raise ProviderBadResponse(self.name, f'unexpected directions payload ({e})') from None
        if not routes:
            raise NoRouteFound(self.name, 'No drivable route between these locations.')
        return routes

    def _post(self, path: str, body: dict) -> dict:
        try:
            resp = self.session.post(
                BASE_URL + path, json=body, timeout=self.timeout,
                headers={'Authorization': self.api_key, 'Accept': 'application/geo+json, application/json'},
            )
        except requests.Timeout:
            raise ProviderTimeout(self.name, 'request timed out') from None
        except requests.RequestException as e:
            raise ProviderUnavailable(self.name, f'connection failed ({type(e).__name__})') from None
        return self._decode(resp)

    def _decode(self, resp: requests.Response) -> dict:
        if resp.status_code == 429:
            raise ProviderRateLimited(self.name, 'rate limit reached')
        if resp.status_code in (401, 403):
            raise ProviderUnavailable(self.name, 'API key rejected')
        # ORS reports some routing errors as HTTP 500 with an error code, so only
        # gateway-level 5xx are treated as an outage before reading the body
        if resp.status_code in (502, 503, 504):
            raise ProviderUnavailable(self.name, f'HTTP {resp.status_code}')
        try:
            data = resp.json()
        except ValueError:
            if resp.status_code >= 500:
                raise ProviderUnavailable(self.name, f'HTTP {resp.status_code}') from None
            raise ProviderBadResponse(self.name, 'response is not JSON') from None

        if resp.status_code == 200:
            if not isinstance(data, dict):
                raise ProviderBadResponse(self.name, 'response is not an object')
            return data

        error = data.get('error') if isinstance(data, dict) else None
        code = error.get('code') if isinstance(error, dict) else None
        message = (error.get('message') if isinstance(error, dict) else error) or f'HTTP {resp.status_code}'
        if code == POINT_NOT_FOUND:
            field = 'origin' if re.search(r'coordinate 0\b', str(message)) else 'destination'
            raise NoRouteFound(self.name, f"Couldn't find a road near this {field}.", field)
        if code == ROUTE_NOT_FOUND:
            raise NoRouteFound(self.name, 'No drivable route between these locations.')
        if code == LIMIT_EXCEEDED:
            raise _LimitExceeded(self.name, str(message))
        if resp.status_code >= 500:
            raise ProviderUnavailable(self.name, str(message))
        raise ProviderBadResponse(self.name, str(message))


def _same(a: RawRoute, b: RawRoute) -> bool:
    def close(x: float, y: float) -> bool:
        return abs(x - y) <= DUPLICATE_TOLERANCE * max(x, y, 1e-9)
    return close(a.distance_mi, b.distance_mi) and close(a.duration_s, b.duration_s)
