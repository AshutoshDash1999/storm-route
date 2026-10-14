"""Resolve free-text locations: bundled US cities and ZIP codes first, then ORS geocoding (live mode only)."""

import requests

from apps.common.exceptions import ProviderBadResponse, ProviderTimeout, ProviderUnavailable
from apps.locations import gazetteer

GEOCODE_URL = 'https://api.openrouteservice.org/geocode/search'


def resolve(text: str, *, api_key: str | None, timeout: float = 8.0,
            session: requests.Session | None = None) -> dict | None:
    """A `Location` dict ({id, label, lng, lat}) or None if nothing matched."""
    found = gazetteer.find(text)
    if found or not api_key:
        return {k: found[k] for k in ('id', 'label', 'lng', 'lat')} if found else None

    session = session or requests.Session()
    try:
        resp = session.get(GEOCODE_URL, timeout=timeout, params={
            'api_key': api_key, 'text': text, 'boundary.country': 'US', 'size': 1,
        })
    except requests.Timeout:
        raise ProviderTimeout('OpenRouteService geocoding', 'request timed out') from None
    except requests.RequestException as e:
        raise ProviderUnavailable('OpenRouteService geocoding', type(e).__name__) from None
    if resp.status_code != 200:
        raise ProviderUnavailable('OpenRouteService geocoding', f'HTTP {resp.status_code}')
    try:
        features = resp.json()['features']
        if not features:
            return None
        f = features[0]
        lng, lat = f['geometry']['coordinates'][:2]
        props = f['properties']
        return {'id': f"ors:{props.get('gid', props.get('id', ''))}", 'label': props['label'],
                'lng': float(lng), 'lat': float(lat)}
    except (KeyError, TypeError, ValueError, IndexError) as e:
        raise ProviderBadResponse('OpenRouteService geocoding', f'unexpected payload ({e})') from None

