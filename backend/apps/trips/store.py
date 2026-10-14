"""
Analysis results, kept in the Django cache so route-details endpoints can find
them. LocMem is per-process: with several workers or across restarts, point
CACHES at Redis (or persist to a database) instead.
"""

from django.conf import settings
from django.core.cache import cache


def _ttl() -> int:
    return settings.STORMROUTE['RESULT_TTL_S']


def save(analysis: dict) -> None:
    entries = {f'analysis:{analysis["id"]}': analysis}
    entries.update({f'route:{r["id"]}': analysis['id'] for r in analysis['routes']})
    cache.set_many(entries, _ttl())


def get_analysis(analysis_id: str) -> dict | None:
    return cache.get(f'analysis:{analysis_id}')


def get_route(route_id: str) -> tuple[dict, dict] | None:
    analysis_id = cache.get(f'route:{route_id}')
    analysis = get_analysis(analysis_id) if analysis_id else None
    if not analysis:
        return None
    route = next((r for r in analysis['routes'] if r['id'] == route_id), None)
    return (analysis, route) if route else None


def get_forecast(analysis_id: str, offset: int) -> dict | None:
    return cache.get(f'forecast:{analysis_id}:{offset}')


def save_forecast(analysis_id: str, offset: int, snapshot: dict) -> None:
    cache.set(f'forecast:{analysis_id}:{offset}', snapshot, _ttl())
