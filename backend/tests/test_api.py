from datetime import UTC, datetime, timedelta

import pytest
import requests
import responses

from apps.routing.ors import BASE_URL as ORS_URL
from apps.weather.open_meteo import BASE_URL as OM_URL

from .conftest import open_meteo_location, ors_body, ors_feature

DIRECTIONS = f'{ORS_URL}/v2/directions/driving-hgv/geojson'
DALLAS = {'id': 'dallas-tx', 'label': 'Dallas, TX', 'lng': -96.797, 'lat': 32.7767}
HOUSTON = {'id': 'houston-tx', 'label': 'Houston, TX', 'lng': -95.3698, 'lat': 29.7604}
LINE = [(-96.797, 32.7767), (-96.0, 31.2), (-95.3698, 29.7604)]


def trip(when: datetime, **overrides):
    body = {'origin': DALLAS, 'destination': HOUSTON, 'departureAt': when.isoformat(), 'loadWeightLb': 35000}
    body.update(overrides)
    return body


def analyze(client, body):
    return client.post('/api/routes/analyze/', body, format='json')


def mock_live_providers(weather_kw=None):
    responses.post(DIRECTIONS, json=ors_body(
        ors_feature(LINE, 240, 4 * 3600), ors_feature(LINE, 255, 4.5 * 3600), ors_feature(LINE, 270, 5 * 3600)))

    def weather(request):
        import json
        n = len(request.params['latitude'].split(','))
        days = sorted({request.params['start_date'], request.params['end_date']})
        locs = []
        for _ in range(n):
            loc = open_meteo_location(days[0], **(weather_kw or {}))
            if len(days) > 1:
                extra = open_meteo_location(days[1], **(weather_kw or {}))
                for k in loc['hourly']:
                    loc['hourly'][k] += extra['hourly'][k]
            locs.append(loc)
        return 200, {}, json.dumps(locs)

    responses.add_callback(responses.GET, OM_URL, callback=weather)


# Health

def test_health(client):
    r = client.get('/api/health/')
    assert r.status_code == 200
    assert r.json() == {'status': 'ok', 'mode': 'demo', 'providers': {'routing': 'Simulated', 'weather': 'Simulated'}}


def test_health_live(client, live):
    assert client.get('/api/health/').json()['mode'] == 'live'


# Validation

@pytest.mark.parametrize('overrides, field, message', [
    ({'origin': None}, 'origin', 'Choose an origin.'),
    ({'origin': 'Atlantis, ZZ'}, 'origin', "Couldn't find that origin"),
    ({'destination': {'lat': 200, 'lng': 0}}, 'destination', 'Location coordinates are invalid.'),
    ({'destination': DALLAS}, 'destination', 'Destination must be different from the origin.'),
    ({'departureAt': 'next tuesday'}, 'departureAt', 'ISO-8601'),
    ({'loadWeightLb': 0}, 'loadWeightLb', 'greater than 0'),
    ({'loadWeightLb': -5}, 'loadWeightLb', 'greater than 0'),
    ({'loadWeightLb': 90000}, 'loadWeightLb', "can't exceed 80,000"),
    ({'loadWeightLb': 'heavy'}, 'loadWeightLb', 'must be a number'),
    ({'forecastOffsetHours': 49}, 'forecastOffsetHours', 'between 0 and 48'),
])
def test_field_specific_validation_errors(client, tomorrow, overrides, field, message):
    r = analyze(client, trip(tomorrow, **overrides))
    assert r.status_code == 400
    err = r.json()['error']
    assert err['code'] == 'validation_error'
    assert message in err['fields'][field][0]


def test_missing_fields_are_all_reported(client):
    r = analyze(client, {})
    assert r.status_code == 400
    assert set(r.json()['error']['fields']) == {'origin', 'destination', 'departureAt', 'loadWeightLb'}


@pytest.mark.parametrize('delta, message', [
    (timedelta(hours=-1), "can't be in the past"),
    (timedelta(days=8), 'within the next 7 days'),
])
def test_departure_window(client, delta, message):
    r = analyze(client, trip(datetime.now(UTC) + delta))
    assert message in r.json()['error']['fields']['departureAt'][0]


def test_snake_case_request_from_checklist(client, tomorrow):
    r = analyze(client, {
        'origin': 'Dallas, TX', 'destination': 'Houston, TX',
        'departure_time': tomorrow.isoformat(), 'load_weight_lb': 35000, 'forecast_offset_hours': 0,
    })
    assert r.status_code == 200
    data = r.json()
    assert data['trip']['origin'] == DALLAS
    assert data['trip']['forecastOffsetHours'] == 0
    assert data['trip']['checkpointSpacingMi'] == 25


@pytest.mark.parametrize('spacing', [10, 25, 50])
def test_checkpoint_spacing_options(client, tomorrow, spacing):
    data = analyze(client, trip(tomorrow, mode='demo', checkpointSpacingMi=spacing)).json()
    assert data['trip']['checkpointSpacingMi'] == spacing
    miles = [cp['mileFromOrigin'] for cp in data['routes'][0]['checkpoints']]
    assert miles[1] == spacing


@pytest.mark.parametrize('spacing', [5, 30, 100])
def test_other_checkpoint_spacing_is_rejected(client, tomorrow, spacing):
    r = analyze(client, trip(tomorrow, mode='demo', checkpointSpacingMi=spacing))
    assert r.status_code == 400
    assert r.json()['error']['fields']['checkpointSpacingMi'] == ['Checkpoint spacing must be 10, 25 or 50 miles.']


def test_snake_case_errors_use_the_sent_key(client, tomorrow):
    r = analyze(client, {'origin': DALLAS, 'destination': HOUSTON, 'departure_time': tomorrow.isoformat(),
                         'load_weight_lb': 0})
    assert 'load_weight_lb' in r.json()['error']['fields']


def test_non_object_body(client):
    r = client.post('/api/routes/analyze/', [1, 2], format='json')
    assert r.status_code == 400
    assert r.json()['error']['code'] == 'invalid_body'


def test_unreachable_destination_in_demo(client, tomorrow):
    honolulu = {'id': 'honolulu-hi', 'label': 'Honolulu, HI', 'lng': -157.8583, 'lat': 21.3069}
    r = analyze(client, trip(tomorrow, destination=honolulu))
    assert r.status_code == 422
    assert r.json()['error']['code'] == 'no_route'
    assert 'destination' in r.json()['error']['fields']


# Demo mode

def _strip_volatile(analysis):
    """Remove ids and timestamps that legitimately differ between runs."""
    routes = [{k: v for k, v in r.items() if k not in ('id', 'noTravelCheckpointIds')} for r in analysis['routes']]
    for r in routes:
        r['checkpoints'] = [{k: v for k, v in cp.items() if k != 'id'} for cp in r['checkpoints']]
    rec = {k: v for k, v in analysis['recommendation'].items() if k != 'routeId'}
    return {**{k: v for k, v in analysis.items() if k not in ('id', 'generatedAt')}, 'routes': routes,
            'recommendation': rec}


def test_demo_is_deterministic_and_labelled(client, tomorrow):
    a = analyze(client, trip(tomorrow, mode='demo')).json()
    b = analyze(client, trip(tomorrow, mode='demo')).json()
    assert _strip_volatile(a) == _strip_volatile(b)
    assert a['mode'] == 'demo'
    assert a['sources'] == {'routing': 'Simulated', 'weather': 'Simulated'}
    assert any('Demo mode' in w for w in a['warnings'])
    sources = {cp['weather']['source'] for r in a['routes'] for cp in r['checkpoints']}
    assert sources <= {'simulated', 'unavailable'}


def test_response_contract(client, tomorrow):
    data = analyze(client, trip(tomorrow, mode='demo')).json()
    assert set(data) >= {'id', 'mode', 'fallback', 'sources', 'trip', 'generatedAt', 'routes', 'recommendation',
                         'warnings'}
    route = data['routes'][0]
    assert set(route) >= {'id', 'name', 'via', 'distanceMi', 'durationMin', 'arrivalAt', 'coordinates', 'checkpoints',
                          'weatherRiskScore', 'eligible', 'rank', 'exposure',
                          'severeMiles', 'highMiles', 'noTravelCheckpointIds', 'coverage', 'warnings'}
    cps = route['checkpoints']
    assert cps[0]['mileFromOrigin'] == 0
    assert cps[-1]['mileFromOrigin'] == route['distanceMi']
    assert cps[0]['etaAt'] == data['trip']['departureAt']
    assert cps[-1]['etaAt'] == route['arrivalAt']
    weather = cps[0]['weather']
    assert set(weather) >= {'source', 'validAt', 'wind', 'rain', 'snow', 'overall', 'triggers', 'appliedRules'}
    assert weather['wind']['unit'] == 'mph'
    assert sum(e['miles'] for e in route['exposure']) == pytest.approx(route['distanceMi'], abs=0.5)


def test_forecast_offset_shifts_weather_times(client, tomorrow):
    data = analyze(client, trip(tomorrow, mode='demo', forecastOffsetHours=6)).json()
    cp = data['routes'][0]['checkpoints'][0]
    assert cp['weather']['validAt'] == (tomorrow + timedelta(hours=6)).isoformat().replace('+00:00', 'Z')


def test_offset_beyond_demo_horizon_is_unknown_not_low(client, tomorrow):
    data = analyze(client, trip(tomorrow, mode='demo', forecastOffsetHours=48)).json()
    overall = {cp['weather']['overall'] for r in data['routes'] for cp in r['checkpoints']}
    assert overall == {'unavailable'}
    assert data['recommendation']['routeId'] is None
    assert any('outside forecast coverage' in w for w in data['warnings'])


# Route details

def test_route_detail_round_trip(client, tomorrow):
    data = analyze(client, trip(tomorrow, mode='demo')).json()
    route = data['routes'][1]
    r = client.get(f"/api/routes/{route['id']}/")
    assert r.status_code == 200
    detail = r.json()
    assert detail['analysisId'] == data['id']
    assert detail['route'] == route
    assert detail['recommended'] == (data['recommendation']['routeId'] == route['id'])

    cps = client.get(f"/api/routes/{route['id']}/checkpoints/").json()
    assert cps['routeId'] == route['id']
    assert cps['checkpoints'] == route['checkpoints']


def test_route_not_found(client):
    r = client.get('/api/routes/rt_missing/')
    assert r.status_code == 404
    assert r.json()['error']['code'] == 'route_not_found'


def test_forecast_snapshot(client, tomorrow):
    data = analyze(client, trip(tomorrow, mode='demo')).json()
    r = client.get(f"/api/analyses/{data['id']}/forecast/?offset=3")
    assert r.status_code == 200
    snap = r.json()
    assert snap['offsetHours'] == 3
    assert snap['available'] is True
    assert set(snap['checkpoints']) == {cp['id'] for rt in data['routes'] for cp in rt['checkpoints']}
    assert all(0 < g['intensity'] <= 1 for g in snap['grid'])
    assert client.get(f"/api/analyses/{data['id']}/forecast/?offset=99").status_code == 400
    assert client.get('/api/analyses/an_missing/forecast/').status_code == 404


# Live mode with mocked providers

@responses.activate
def test_live_analysis_with_mocked_providers(client, live, tomorrow):
    mock_live_providers({'wind': 10, 'gust': 15})
    r = analyze(client, trip(tomorrow))
    assert r.status_code == 200
    data = r.json()
    assert data['mode'] == 'live'
    assert data['fallback'] == {'routing': False, 'weather': False}
    assert data['sources'] == {'routing': 'OpenRouteService', 'weather': 'Open-Meteo'}
    assert any('truck legality' in w for w in data['warnings'])
    assert [rt['distanceMi'] for rt in data['routes']] == [240, 255, 270]
    assert {cp['weather']['source'] for rt in data['routes'] for cp in rt['checkpoints']} == {'live'}
    # All Low weather: ranking falls through to travel time, so the fastest wins
    best = next(rt for rt in data['routes'] if rt['id'] == data['recommendation']['routeId'])
    assert best['distanceMi'] == 240 and best['rank'] == 1
    assert [rt['rank'] for rt in data['routes']] == [1, 2, 3]


@responses.activate
def test_live_high_wind_heavy_load_blocks_every_route(client, live, tomorrow):
    mock_live_providers({'wind': 40, 'gust': 47})
    data = analyze(client, trip(tomorrow, loadWeightLb=35000)).json()
    assert all(not rt['eligible'] for rt in data['routes'])
    assert data['recommendation'] == {**data['recommendation'], 'routeId': None, 'status': 'blocked'}
    cp = data['routes'][0]['checkpoints'][1]['weather']
    assert cp['overall'] == 'no_travel'
    assert cp['appliedRules'] == ['Load over 30,000 lb in 45–55 mph wind: No Travel']


@responses.activate
def test_routing_failure_falls_back_to_labelled_demo(client, live, tomorrow):
    responses.post(DIRECTIONS, body=requests.ConnectionError())
    data = analyze(client, trip(tomorrow)).json()
    assert data['mode'] == 'demo'
    assert data['fallback']['routing'] is True
    assert any('SIMULATED analysis' in w for w in data['warnings'])


@responses.activate
def test_routing_failure_without_fallback_is_503(client, live, tomorrow):
    live['DEMO_FALLBACK'] = False
    responses.post(DIRECTIONS, status=429, json={'error': 'Rate limit exceeded'})
    r = analyze(client, trip(tomorrow))
    assert r.status_code == 503
    assert r.json()['error']['code'] == 'routing_unavailable'


@responses.activate
def test_weather_failure_falls_back_with_labels(client, live, tomorrow):
    responses.post(DIRECTIONS, json=ors_body(ors_feature(LINE, 240, 4 * 3600)))
    responses.post(DIRECTIONS, status=404, json={'error': {'code': 2010, 'message': 'coordinate 1'}})
    responses.post(DIRECTIONS, status=404, json={'error': {'code': 2010, 'message': 'coordinate 1'}})
    responses.get(OM_URL, body=requests.Timeout())
    data = analyze(client, trip(tomorrow)).json()
    assert data['mode'] == 'live'
    assert data['fallback'] == {'routing': False, 'weather': True}
    assert data['sources']['weather'] == 'Simulated'
    assert {cp['weather']['source'] for cp in data['routes'][0]['checkpoints']} <= {'simulated', 'unavailable'}
    assert any('SIMULATED' in w for w in data['warnings'])
    assert any('Only 1 route alternative' in w for w in data['warnings'])


@responses.activate
def test_weather_failure_without_fallback_returns_partial_unknown_result(client, live, tomorrow):
    live['DEMO_FALLBACK'] = False
    responses.post(DIRECTIONS, json=ors_body(ors_feature(LINE, 240, 4 * 3600), ors_feature(LINE, 250, 4.2 * 3600)))
    responses.get(OM_URL, status=503)
    r = analyze(client, trip(tomorrow))
    assert r.status_code == 200
    data = r.json()
    assert {cp['weather']['overall'] for rt in data['routes'] for cp in rt['checkpoints']} == {'unavailable'}
    assert data['recommendation']['routeId'] is None
    assert any('Every checkpoint is Unknown' in w for w in data['warnings'])


@responses.activate
def test_no_route_from_provider_is_a_field_error(client, live, tomorrow):
    responses.post(DIRECTIONS, status=404, json={'error': {'code': 2009, 'message': 'Route could not be found'}})
    r = analyze(client, trip(tomorrow))
    assert r.status_code == 422
    assert r.json()['error']['fields']['destination']


def test_analyze_is_throttled(client, monkeypatch, tomorrow):
    # Throttle rates are read at import time, so patch the class rather than settings
    monkeypatch.setattr('apps.trips.views.AnalyzeThrottle.THROTTLE_RATES', {'analyze': '2/min'})
    codes = [analyze(client, trip(tomorrow, mode='demo')).status_code for _ in range(3)]
    assert codes == [200, 200, 429]
