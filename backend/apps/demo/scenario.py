"""
Deterministic demo world: three corridors between any two points and a few
storm cells placed relative to them. Nothing here is random or time-of-day
dependent, so the same trip always produces the same analysis.

Storm timing is measured in hours after departure, so the scenario plays out
the same whatever the departure date.
"""

import math
from dataclasses import dataclass

from apps.common.geo import Corridor, LngLat, haversine_mi

#: Hours after departure beyond which the demo "forecast" has no data
DEMO_FORECAST_HORIZON_H = 45


@dataclass(frozen=True)
class RouteSpec:
    key: str
    bend: float
    wiggle: float
    speed_mph: float


ROUTE_SPECS = [
    RouteSpec('a', bend=0.03, wiggle=0.015, speed_mph=60),
    RouteSpec('b', bend=0.20, wiggle=0.020, speed_mph=57),
    RouteSpec('c', bend=-0.22, wiggle=0.018, speed_mph=61),
]


def build_geometry(c: Corridor, spec: RouteSpec, n: int = 80) -> list[LngLat]:
    pts = []
    for i in range(n + 1):
        s = i / n
        envelope = math.sin(math.pi * s)
        offset = spec.bend * envelope + spec.wiggle * math.sin(5 * math.pi * s) * envelope
        pts.append(c.at(s, offset))
    return pts


@dataclass(frozen=True)
class StormCell:
    kind: str  # 'snow' | 'rain'
    center: LngLat
    #: Radius in degrees
    radius: float
    #: Peak intensity 0–1
    peak: float
    #: Hours after departure when strongest
    peak_hour: float
    #: Hours for intensity to fall to ~37% of peak
    lifetime: float
    #: Degrees per hour
    drift: LngLat


@dataclass(frozen=True)
class CoverageHole:
    """Area with no weather data, to exercise missing-data handling."""
    center: LngLat
    radius: float

    def contains(self, p: LngLat) -> bool:
        return math.hypot(p[0] - self.center[0], p[1] - self.center[1]) <= self.radius


def build_storms(c: Corridor) -> list[StormCell]:
    def radius(f: float) -> float:
        return min(2.4, max(0.35, c.span * f))

    straight_mi = haversine_mi(c.origin, c.destination)

    def eta_hour(s: float) -> float:
        return straight_mi * 1.05 * s / 60

    return [
        # Blizzard core across the direct route
        StormCell('snow', c.at(0.55, 0.03), radius(0.085), 0.95, eta_hour(0.55), 14, (0.01, 0)),
        # Heavy rain band brushing the left-hand bypass
        StormCell('rain', c.at(0.3, 0.19), radius(0.06), 0.62, eta_hour(0.3) + 1, 10, (0.02, 0.005)),
        # Light rain on the right-hand bypass
        StormCell('rain', c.at(0.78, -0.21), radius(0.05), 0.32, eta_hour(0.78) + 2, 12, (0, 0)),
    ]


def build_coverage_hole(c: Corridor) -> CoverageHole:
    # Sits on route B's corridor partway along, so a stretch of B has no data
    return CoverageHole(c.at(0.62, 0.2), max(0.15, c.span * 0.04))


def cell_intensity(cell: StormCell, p: LngLat, hour: float) -> float:
    cx = cell.center[0] + cell.drift[0] * hour
    cy = cell.center[1] + cell.drift[1] * hour
    d2 = (p[0] - cx) ** 2 + (p[1] - cy) ** 2
    spatial = math.exp(-d2 / cell.radius ** 2)
    temporal = math.exp(-(((hour - cell.peak_hour) / cell.lifetime) ** 2))
    return cell.peak * spatial * temporal


def field_intensity(cells: list[StormCell], p: LngLat, hour: float) -> float:
    return min(1.0, sum(cell_intensity(cell, p, hour) for cell in cells))


def conditions_at(cells: list[StormCell], p: LngLat, hour: float) -> tuple[float, float, float]:
    """(wind mph, rain in/hr, snow in/hr), scaled so peak cells reach No Travel."""
    wind = 6 + 4 * abs(math.sin(p[0] * 3 + p[1] * 2 + hour / 5))
    rain = snow = 0.0
    for cell in cells:
        i = cell_intensity(cell, p, hour)
        if cell.kind == 'snow':
            snow += 3.6 * i
            wind += 52 * i
        else:
            rain += 1.4 * i
            wind += 36 * i
    return wind, rain, snow
