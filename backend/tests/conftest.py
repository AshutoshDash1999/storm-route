from datetime import UTC, datetime, timedelta

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient


@pytest.fixture(autouse=True)
def _isolated(settings):
    cache.clear()
    settings.STORMROUTE = {
        'ORS_API_KEY': '',
        'DATA_MODE': 'live',
        'DEMO_FALLBACK': True,
        'PROVIDER_TIMEOUT_S': 2.0,
        'RESULT_TTL_S': 600,
    }
    yield
    cache.clear()


@pytest.fixture
def live(settings):
    """Live mode with a fake ORS key; pair with `responses` to mock providers."""
    settings.STORMROUTE = {**settings.STORMROUTE, 'ORS_API_KEY': 'test-key'}
    return settings.STORMROUTE


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def tomorrow():
    t = datetime.now(UTC) + timedelta(days=1)
    return t.replace(hour=13, minute=0, second=0, microsecond=0)


def ors_feature(coords, distance_mi, duration_s):
    return {
        'type': 'Feature',
        'geometry': {'type': 'LineString', 'coordinates': [list(c) for c in coords]},
        'properties': {'summary': {'distance': distance_mi, 'duration': duration_s}},
    }


def ors_body(*features):
    return {'type': 'FeatureCollection', 'features': list(features)}


def open_meteo_location(day: str, wind=5.0, gust=8.0, rain=0.0, showers=0.0, snow=0.0, units=None):
    times = [f'{day}T{h:02d}:00' for h in range(24)]
    return {
        'hourly_units': units or {'time': 'iso8601', 'wind_speed_10m': 'mp/h', 'wind_gusts_10m': 'mp/h',
                                  'rain': 'inch', 'showers': 'inch', 'snowfall': 'inch'},
        'hourly': {
            'time': times,
            'wind_speed_10m': [wind] * 24,
            'wind_gusts_10m': [gust] * 24,
            'rain': [rain] * 24,
            'showers': [showers] * 24,
            'snowfall': [snow] * 24,
        },
    }
