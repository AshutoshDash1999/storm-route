"""
Open-Meteo forecast adapter (https://open-meteo.com/en/docs).

Hourly variables, requested in mph and inches and converted using the units
the response declares:
- wind_speed_10m, wind_gusts_10m → wind = max(sustained, gust). Gusts drive
  rollover risk for high-profile trucks, so the stronger value is used.
- rain + showers → liquid precipitation over the preceding hour (= in/hr)
- snowfall → snow depth over the preceding hour (= in/hr)

Precipitation values cover the hour *ending* at each timestamp, so a valid
time is matched to the next whole hour.

Free tier: non-commercial use, ~10,000 calls/day, CC BY 4.0 attribution.
"""

import logging
from datetime import UTC, date, datetime, timedelta

import requests

from apps.common.exceptions import (
    ProviderBadResponse,
    ProviderError,
    ProviderRateLimited,
    ProviderTimeout,
    ProviderUnavailable,
)

from .base import WeatherRequest, WeatherSample
from .units import to_inches, to_mph

logger = logging.getLogger('stormroute')

BASE_URL = 'https://api.open-meteo.com/v1/forecast'
HOURLY = ['wind_speed_10m', 'wind_gusts_10m', 'rain', 'showers', 'snowfall']
FORECAST_DAYS = 16
CHUNK_SIZE = 50


def _ceil_hour(t: datetime) -> datetime:
    t = t.astimezone(UTC)
    floor = t.replace(minute=0, second=0, microsecond=0)
    return floor if floor == t else floor + timedelta(hours=1)


def _hour_key(t: datetime) -> str:
    return _ceil_hour(t).strftime('%Y-%m-%dT%H:%M')


def _sum(*values):
    present = [v for v in values if v is not None]
    return sum(present) if present else None


class OpenMeteoWeather:
    name = 'Open-Meteo'

    def __init__(self, timeout: float = 8.0, session: requests.Session | None = None, today: date | None = None):
        self.timeout = timeout
        self.session = session or requests.Session()
        self._today = today

    @property
    def today(self) -> date:
        return self._today or datetime.now(UTC).date()

    def samples(self, reqs: list[WeatherRequest]) -> list[WeatherSample]:
        out: list[WeatherSample | None] = [None] * len(reqs)
        last_day = self.today + timedelta(days=FORECAST_DAYS - 1)

        in_range = []
        for i, r in enumerate(reqs):
            day = _ceil_hour(r.valid_at).date()
            if self.today <= day <= last_day:
                in_range.append(i)
            else:
                out[i] = WeatherSample.unavailable(r.valid_at, 'out_of_range')

        errors: list[ProviderError] = []
        for start in range(0, len(in_range), CHUNK_SIZE):
            idx = in_range[start:start + CHUNK_SIZE]
            try:
                for i, sample in zip(idx, self._fetch([reqs[i] for i in idx])):
                    out[i] = sample
            except ProviderError as e:
                logger.warning('Open-Meteo chunk failed: %s', e)
                errors.append(e)
                for i in idx:
                    out[i] = WeatherSample.unavailable(reqs[i].valid_at, 'provider_error')

        if errors and len(errors) == -(-len(in_range) // CHUNK_SIZE):
            raise errors[-1]
        return out

    def _fetch(self, reqs: list[WeatherRequest]) -> list[WeatherSample]:
        days = [_ceil_hour(r.valid_at).date() for r in reqs]
        params = {
            'latitude': ','.join(f'{r.position[1]:.4f}' for r in reqs),
            'longitude': ','.join(f'{r.position[0]:.4f}' for r in reqs),
            'hourly': ','.join(HOURLY),
            'wind_speed_unit': 'mph',
            'precipitation_unit': 'inch',
            'timezone': 'UTC',
            'start_date': min(days).isoformat(),
            'end_date': max(days).isoformat(),
        }
        try:
            resp = self.session.get(BASE_URL, params=params, timeout=self.timeout)
        except requests.Timeout:
            raise ProviderTimeout(self.name, 'request timed out') from None
        except requests.RequestException as e:
            raise ProviderUnavailable(self.name, f'connection failed ({type(e).__name__})') from None

        if resp.status_code == 429:
            raise ProviderRateLimited(self.name, 'rate limit reached')
        if resp.status_code >= 500:
            raise ProviderUnavailable(self.name, f'HTTP {resp.status_code}')
        try:
            body = resp.json()
        except ValueError:
            raise ProviderBadResponse(self.name, 'response is not JSON') from None
        if resp.status_code != 200 or (isinstance(body, dict) and body.get('error')):
            reason = body.get('reason', f'HTTP {resp.status_code}') if isinstance(body, dict) else resp.status_code
            raise ProviderBadResponse(self.name, str(reason))

        locations = body if isinstance(body, list) else [body]
        if len(locations) != len(reqs):
            raise ProviderBadResponse(self.name, f'expected {len(reqs)} locations, got {len(locations)}')
        return [self._parse(loc, r) for loc, r in zip(locations, reqs)]

    def _parse(self, loc: dict, req: WeatherRequest) -> WeatherSample:
        try:
            hourly = loc['hourly']
            units = loc['hourly_units']
            index = {t: i for i, t in enumerate(hourly['time'])}
        except (KeyError, TypeError):
            raise ProviderBadResponse(self.name, 'missing hourly data') from None

        i = index.get(_hour_key(req.valid_at))
        if i is None:
            return WeatherSample.unavailable(req.valid_at, 'out_of_range')

        def value(var: str):
            series = hourly.get(var)
            return series[i] if isinstance(series, list) and i < len(series) else None

        def unit(var: str):
            return units.get(var, '')

        speed = to_mph(value('wind_speed_10m'), unit('wind_speed_10m'), self.name)
        gust = to_mph(value('wind_gusts_10m'), unit('wind_gusts_10m'), self.name)
        rain = _sum(to_inches(value('rain'), unit('rain'), self.name),
                    to_inches(value('showers'), unit('showers'), self.name))
        snow = to_inches(value('snowfall'), unit('snowfall'), self.name)
        wind = max((v for v in (speed, gust) if v is not None), default=None)

        missing = None if None not in (wind, rain, snow) else 'missing_values'
        return WeatherSample(valid_at=req.valid_at, source='live', wind_mph=wind, rain_in_hr=rain,
                             snow_in_hr=snow, missing=missing)
