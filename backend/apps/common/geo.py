"""Small spherical-geometry helpers. Coordinates are (lng, lat) like GeoJSON."""

import math
from bisect import bisect_left
from dataclasses import dataclass

LngLat = tuple[float, float]

EARTH_RADIUS_MI = 3958.8


def haversine_mi(a: LngLat, b: LngLat) -> float:
    lng1, lat1 = map(math.radians, a)
    lng2, lat2 = map(math.radians, b)
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lng2 - lng1) / 2) ** 2
    return 2 * EARTH_RADIUS_MI * math.asin(min(1.0, math.sqrt(h)))


def cumulative_miles(coords: list[LngLat]) -> list[float]:
    """Running distance from the first vertex to each vertex."""
    out = [0.0]
    for prev, cur in zip(coords, coords[1:]):
        out.append(out[-1] + haversine_mi(prev, cur))
    return out


def point_at_mile(coords: list[LngLat], cumulative: list[float], mile: float) -> LngLat:
    """Linear interpolation of the point `mile` miles along the polyline (clamped to its ends)."""
    if mile <= 0:
        return tuple(coords[0])
    if mile >= cumulative[-1]:
        return tuple(coords[-1])
    i = max(1, bisect_left(cumulative, mile))
    seg = cumulative[i] - cumulative[i - 1]
    f = (mile - cumulative[i - 1]) / seg if seg > 0 else 0.0
    a, b = coords[i - 1], coords[i]
    return (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)


def place_label(p: LngLat) -> str:
    lng, lat = p
    return f"{abs(lat):.1f}°{'N' if lat >= 0 else 'S'} {abs(lng):.1f}°{'E' if lng >= 0 else 'W'}"


def in_contiguous_us(p: LngLat) -> bool:
    lng, lat = p
    return -125.0 <= lng <= -66.5 and 24.0 <= lat <= 49.6


@dataclass(frozen=True)
class Corridor:
    origin: LngLat
    destination: LngLat

    @property
    def delta(self) -> LngLat:
        return (self.destination[0] - self.origin[0], self.destination[1] - self.origin[1])

    @property
    def span(self) -> float:
        """Straight-line length in degrees."""
        return math.hypot(*self.delta) or 1e-9

    @property
    def normal(self) -> LngLat:
        """Unit normal, left of the direction of travel, in degrees."""
        dx, dy = self.delta
        return (-dy / self.span, dx / self.span)

    def at(self, s: float, offset: float) -> LngLat:
        """Point at fraction `s` along the line, pushed `offset`·span sideways."""
        dx, dy = self.delta
        nx, ny = self.normal
        return (self.origin[0] + dx * s + nx * offset * self.span,
                self.origin[1] + dy * s + ny * offset * self.span)

    def lateral_offset(self, p: LngLat) -> float:
        """Signed sideways distance of `p` from the line, as a fraction of span."""
        nx, ny = self.normal
        return ((p[0] - self.origin[0]) * nx + (p[1] - self.origin[1]) * ny) / self.span
