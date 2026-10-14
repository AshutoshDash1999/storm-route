"""Simulated routing for demo mode: three deterministic corridors between the two points."""

from apps.common.exceptions import NoRouteFound
from apps.common.geo import Corridor, LngLat, cumulative_miles, in_contiguous_us
from apps.demo.scenario import ROUTE_SPECS, build_geometry

from .base import RawRoute, RoutingResult


class DemoRouting:
    name = 'Demo routing'

    def routes(self, origin: LngLat, destination: LngLat, max_routes: int = 3) -> RoutingResult:
        for field, point in (('origin', origin), ('destination', destination)):
            if not in_contiguous_us(point):
                raise NoRouteFound(self.name, f'No drivable route from the contiguous US to this {field}.', field)
        c = Corridor(origin, destination)
        routes = []
        for spec in ROUTE_SPECS[:max_routes]:
            coords = build_geometry(c, spec)
            miles = cumulative_miles(coords)[-1]
            routes.append(RawRoute(coordinates=coords, distance_mi=miles, duration_s=miles / spec.speed_mph * 3600,
                                   provider='demo', provider_ref=f'demo-{spec.key}'))
        return RoutingResult(routes)
