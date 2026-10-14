"""Human-readable names for alternatives, by which side of the direct line they run."""

from string import ascii_uppercase

from apps.common.geo import Corridor, LngLat

#: Mean sideways offset (fraction of trip span) below which a route counts as direct
DIRECT_THRESHOLD = 0.06


def _side(c: Corridor, offset: float) -> str:
    nx, ny = (v * (1 if offset > 0 else -1) for v in c.normal)
    if abs(ny) >= abs(nx):
        return 'Northern' if ny > 0 else 'Southern'
    return 'Eastern' if nx > 0 else 'Western'


def describe(origin: LngLat, destination: LngLat, geometries: list[list[LngLat]]) -> list[tuple[str, str]]:
    """(name, via) for each route, e.g. ("Route B · Northern bypass", "Swings north of the direct line")."""
    c = Corridor(origin, destination)
    out = []
    for i, coords in enumerate(geometries):
        offset = sum(c.lateral_offset(p) for p in coords) / len(coords)
        letter = ascii_uppercase[i % 26]
        if abs(offset) < DIRECT_THRESHOLD:
            out.append((f'Route {letter} · Direct', 'Most direct corridor'))
        else:
            side = _side(c, offset)
            out.append((f'Route {letter} · {side} bypass', f'Swings {side[:-3].lower()} of the direct line'))
    return out
