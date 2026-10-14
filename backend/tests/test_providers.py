import json
from datetime import UTC, date, datetime

import pytest
import requests
import responses

from apps.common.exceptions import (
    NoRouteFound,
    ProviderBadResponse,
    ProviderRateLimited,
    ProviderTimeout,
    ProviderUnavailable,
)
from apps.routing.ors import BASE_URL as ORS_URL
from apps.routing.ors import OrsRouting
from apps.weather.base import WeatherRequest
from apps.weather.open_meteo import BASE_URL as OM_URL
from apps.weather.open_meteo import OpenMeteoWeather
from apps.weather.units import to_inches, to_mph

from .conftest import open_meteo_location, ors_body, ors_feature

DIRECTIONS = f'{ORS_URL}/v2/directions/driving-hgv/geojson'
DALLAS = (-96.797, 32.7767)
HOUSTON = (-95.3698, 29.7604)
LINE = [DALLAS, (-96.0, 31.2), HOUSTON]


# Units

def test_unit_conversions():
    assert to_mph(10, 'km/h') == pytest.approx(6.21371)
    assert to_mph(10, 'm/s') == pytest.approx(22.36936)
    assert to_mph(10, 'mp/h') == 10
    assert to_inches(2.54, 'cm') == pytest.approx(1.0)
    assert to_inches(25.4, 'mm') == pytest.approx(1.0)
    assert to_inches(None, 'cm') is None


def test_unknown_unit_is_an_error_not_a_guess():
    with pytest.raises(ProviderBadResponse):
        to_mph(10, 'furlongs/fortnight')


# OpenRouteService

@responses.activate
def test_ors_returns_alternatives():
    responses.post(DIRECTIONS, json=ors_body(
        ors_feature(LINE, 240, 13000), ors_feature(LINE, 250, 14000), ors_feature(LINE, 265, 15000)))
    result = OrsRouting('k').routes(DALLAS, HOUSTON)
    assert [r.distance_mi for r in result.routes] == [240, 250, 265]
    assert [r.provider_ref for r in result.routes] == ['primary', 'alternative-1', 'alternative-2']
    assert result.routes[0].coordinates[0] == DALLAS
    assert result.warnings == []
    body = json.loads(responses.calls[0].request.body)
    assert body['alternative_routes']['target_count'] == 3
    assert body['units'] == 'mi'
    assert responses.calls[0].request.headers['Authorization'] == 'k'


@responses.activate
def test_ors_falls_back_to_via_detours_when_alternatives_exceed_limit():
    responses.post(DIRECTIONS, status=400, json={'error': {'code': 2004, 'message': 'distance > 100000 m'}})
    responses.post(DIRECTIONS, json=ors_body(ors_feature(LINE, 240, 13000)))
    responses.post(DIRECTIONS, json=ors_body(ors_feature(LINE, 260, 14500)))
    responses.post(DIRECTIONS, json=ors_body(ors_feature(LINE, 280, 15500)))
    result = OrsRouting('k').routes(DALLAS, HOUSTON)
    assert [r.provider_ref for r in result.routes] == ['primary', 'via-left', 'via-right']
    assert 'alternative_routes' not in json.loads(responses.calls[1].request.body)
    assert len(json.loads(responses.calls[2].request.body)['coordinates']) == 3


@responses.activate
def test_ors_reports_unavailable_alternatives():
    responses.post(DIRECTIONS, json=ors_body(ors_feature(LINE, 240, 13000)))
    # Both detours fail to snap / duplicate the primary
    responses.post(DIRECTIONS, status=404, json={'error': {'code': 2010, 'message': 'coordinate 1'}})
    responses.post(DIRECTIONS, json=ors_body(ors_feature(LINE, 240.5, 13010)))
    result = OrsRouting('k').routes(DALLAS, HOUSTON)
    assert len(result.routes) == 1
    assert result.warnings == ['Only 1 route alternative available for this trip.']


@responses.activate
def test_ors_rejects_overlong_detours():
    responses.post(DIRECTIONS, json=ors_body(ors_feature(LINE, 100, 6000)))
    responses.post(DIRECTIONS, json=ors_body(ors_feature(LINE, 200, 12000)))
    responses.post(DIRECTIONS, json=ors_body(ors_feature(LINE, 120, 7000)))
    result = OrsRouting('k').routes(DALLAS, HOUSTON)
    assert [r.provider_ref for r in result.routes] == ['primary', 'via-right']


@pytest.mark.parametrize('status, body, exc', [
    (429, {'error': 'Rate limit exceeded'}, ProviderRateLimited),
    (403, {'error': 'Access denied'}, ProviderUnavailable),
    (503, None, ProviderUnavailable),
    (200, {'features': [{'geometry': {}}]}, ProviderBadResponse),
    (200, {'unexpected': True}, ProviderBadResponse),
])
@responses.activate
def test_ors_error_mapping(status, body, exc):
    responses.post(DIRECTIONS, status=status, **({'json': body} if body is not None else {'body': 'down'}))
    with pytest.raises(exc):
        OrsRouting('k').routes(DALLAS, HOUSTON)


@responses.activate
def test_ors_malformed_json():
    responses.post(DIRECTIONS, body='<html>oops</html>')
    with pytest.raises(ProviderBadResponse):
        OrsRouting('k').routes(DALLAS, HOUSTON)


@responses.activate
def test_ors_timeout():
    responses.post(DIRECTIONS, body=requests.Timeout())
    with pytest.raises(ProviderTimeout):
        OrsRouting('k').routes(DALLAS, HOUSTON)


@pytest.mark.parametrize('code, message, field', [
    (2010, 'Could not find routable point within a radius of 5000.0 meters of specified coordinate 0: ...', 'origin'),
    (2010, '... of specified coordinate 1: ...', 'destination'),
    (2009, 'Route could not be found', 'destination'),
])
@responses.activate
def test_ors_no_route(code, message, field):
    responses.post(DIRECTIONS, status=404, json={'error': {'code': code, 'message': message}})
    with pytest.raises(NoRouteFound) as e:
        OrsRouting('k').routes(DALLAS, HOUSTON)
    assert e.value.field == field


# Open-Meteo

TODAY = date(2026, 10, 14)
AT = datetime(2026, 10, 15, 13, 20, tzinfo=UTC)


def om(**kw):
    return OpenMeteoWeather(today=TODAY, **kw)


@responses.activate
def test_open_meteo_normalizes_and_matches_next_hour():
    loc = open_meteo_location('2026-10-15', wind=30, gust=41, rain=0.2, showers=0.1, snow=0)
    loc['hourly']['rain'][14] = 0.4  # value for 13:00–14:00 is stamped 14:00
    responses.get(OM_URL, json=[loc, open_meteo_location('2026-10-15')])
    s1, s2 = om().samples([WeatherRequest(DALLAS, AT), WeatherRequest(HOUSTON, AT)])
    assert s1.source == 'live'
    assert s1.wind_mph == 41  # gusts win
    assert s1.rain_in_hr == pytest.approx(0.5)  # rain + showers at 14:00
    assert s1.snow_in_hr == 0
    assert s1.missing is None
    params = responses.calls[0].request.params
    assert params['latitude'] == '32.7767,29.7604'
    assert params['start_date'] == params['end_date'] == '2026-10-15'


@responses.activate
def test_open_meteo_single_location_object_and_metric_units():
    loc = open_meteo_location('2026-10-15', wind=36, gust=0, snow=2.54, units={
        'wind_speed_10m': 'km/h', 'wind_gusts_10m': 'km/h', 'rain': 'mm', 'showers': 'mm', 'snowfall': 'cm'})
    responses.get(OM_URL, json=loc)
    [s] = om().samples([WeatherRequest(DALLAS, AT)])
    assert s.wind_mph == pytest.approx(22.369, abs=0.01)
    assert s.snow_in_hr == pytest.approx(1.0)


@responses.activate
def test_open_meteo_missing_values_are_none_not_zero():
    loc = open_meteo_location('2026-10-15')
    loc['hourly']['snowfall'] = [None] * 24
    responses.get(OM_URL, json=[loc])
    [s] = om().samples([WeatherRequest(DALLAS, AT)])
    assert s.snow_in_hr is None
    assert s.missing == 'missing_values'


def test_open_meteo_outside_coverage_skips_request():
    far = datetime(2026, 11, 30, 12, tzinfo=UTC)
    [s] = om().samples([WeatherRequest(DALLAS, far)])
    assert s.source == 'unavailable'
    assert s.missing == 'out_of_range'


@responses.activate
def test_open_meteo_hour_missing_from_response_is_out_of_range():
    responses.get(OM_URL, json=[open_meteo_location('2026-10-14')])
    [s] = om().samples([WeatherRequest(DALLAS, AT)])
    assert s.missing == 'out_of_range'


@responses.activate
def test_open_meteo_total_failure_raises():
    responses.get(OM_URL, status=429, json={'error': True, 'reason': 'Too many requests'})
    with pytest.raises(ProviderRateLimited):
        om().samples([WeatherRequest(DALLAS, AT)])


@responses.activate
def test_open_meteo_partial_failure_marks_only_failed_chunk(monkeypatch):
    monkeypatch.setattr('apps.weather.open_meteo.CHUNK_SIZE', 1)
    responses.get(OM_URL, json=[open_meteo_location('2026-10-15')])
    responses.get(OM_URL, status=500, json={'error': True, 'reason': 'boom'})
    s1, s2 = om().samples([WeatherRequest(DALLAS, AT), WeatherRequest(HOUSTON, AT)])
    assert s1.source == 'live'
    assert s2.source == 'unavailable' and s2.missing == 'provider_error'


@responses.activate
def test_open_meteo_wrong_location_count():
    responses.get(OM_URL, json=[open_meteo_location('2026-10-15')])
    with pytest.raises(ProviderBadResponse):
        om().samples([WeatherRequest(DALLAS, AT), WeatherRequest(HOUSTON, AT)])
