"""
Route analysis: routing → checkpoints → weather → risk → scoring → response.

Responses are camelCase dicts matching `frontend/src/lib/types.ts`.

Data modes
- demo: simulated routes and weather, no provider calls.
- live: OpenRouteService + Open-Meteo. If routing fails and DEMO_FALLBACK is on,
  the whole analysis becomes a labelled demo (simulated routes with live weather
  would be meaningless). If weather fails, live routes are kept and checkpoint
  weather is simulated (fallback) or Unknown, and every value says which.
"""

import logging
import math
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from django.conf import settings

from apps.common.exceptions import ApiError, NoRouteFound, ProviderError
from apps.common.geo import Corridor, LngLat, haversine_mi, place_label
from apps.demo import us_locations
from apps.demo.scenario import DEMO_FORECAST_HORIZON_H, build_storms, field_intensity
from apps.recommendations.checkpoints import DEFAULT_SPACING_MI, CheckpointPlan, plan_checkpoints
from apps.recommendations.scoring import EXPOSURE_ORDER, RISK_POINTS, RouteInput, recommend, score_routes
from apps.risk.engine import Risk, evaluate
from apps.routing.base import RoutingResult
from apps.routing.demo import DemoRouting
from apps.routing.naming import describe
from apps.routing.ors import OrsRouting
from apps.weather.base import WeatherRequest, WeatherSample
from apps.weather.demo import DemoWeather
from apps.weather.open_meteo import OpenMeteoWeather

logger = logging.getLogger('stormroute')

TRUCK_ROUTING_WARNING = (
    'Routes use a heavy-vehicle profile but are not checked for truck legality '
    '(bridge heights, weight limits, hazmat or local restrictions). Verify before dispatch.'
)
DEMO_WARNING = 'Demo mode: routes and weather are simulated and must not be used for real trips.'

#: Checkpoints within this distance of a gazetteer city are labelled with it
PLACE_RADIUS_MI = 40


@dataclass(frozen=True)
class Trip:
    origin: dict
    destination: dict
    departure: datetime
    load_lb: float
    offset_h: int = 0
    spacing_mi: float = DEFAULT_SPACING_MI

    @property
    def origin_point(self) -> LngLat:
        return (self.origin['lng'], self.origin['lat'])

    @property
    def destination_point(self) -> LngLat:
        return (self.destination['lng'], self.destination['lat'])

    @property
    def corridor(self) -> Corridor:
        return Corridor(self.origin_point, self.destination_point)


# Provider wiring (module-level so tests can swap them)

def config() -> dict:
    return settings.STORMROUTE


def resolve_mode(force_demo: bool = False) -> str:
    cfg = config()
    if force_demo or cfg['DATA_MODE'] == 'demo' or not cfg['ORS_API_KEY']:
        return 'demo'
    return 'live'


def live_routing() -> OrsRouting:
    cfg = config()
    return OrsRouting(cfg['ORS_API_KEY'], timeout=cfg['PROVIDER_TIMEOUT_S'])


def live_weather() -> OpenMeteoWeather:
    return OpenMeteoWeather(timeout=config()['PROVIDER_TIMEOUT_S'])


# Formatting helpers

def iso(t: datetime) -> str:
    return t.astimezone(UTC).isoformat(timespec='seconds').replace('+00:00', 'Z')


def parse_iso(s: str) -> datetime:
    return datetime.fromisoformat(s.replace('Z', '+00:00'))


def _round_half_up(x: float | None, places: int) -> float | None:
    if x is None:
        return None
    f = 10 ** places
    return math.floor(x * f + 0.5) / f


def _r1(x: float) -> float:
    return round(x, 1)


def new_id(prefix: str) -> str:
    return f'{prefix}_{uuid.uuid4().hex[:12]}'


def nearest_place(p: LngLat) -> str:
    best = min(us_locations.US_LOCATIONS, key=lambda loc: haversine_mi(p, (loc['lng'], loc['lat'])))
    if haversine_mi(p, (best['lng'], best['lat'])) <= PLACE_RADIUS_MI:
        return f"near {best['label']}"
    return place_label(p)


# Weather

def fetch_weather(reqs: list[WeatherRequest], mode: str, trip: Trip) -> tuple[list[WeatherSample], bool, list[str]]:
    """Samples, whether simulated fallback was used, and warnings."""
    demo = DemoWeather(trip.corridor, trip.departure)
    if mode == 'demo':
        return demo.samples(reqs), False, []
    try:
        return live_weather().samples(reqs), False, []
    except ProviderError as e:
        logger.warning('Weather provider failed: %s', e)
        if config()['DEMO_FALLBACK']:
            return demo.samples(reqs), True, [
                f'Live weather is unavailable ({e.message}). Checkpoint weather below is SIMULATED '
                f'and labelled as such; do not rely on it.'
            ]
        return [WeatherSample.unavailable(r.valid_at, 'provider_error') for r in reqs], False, [
            f'Live weather is unavailable ({e.message}). Every checkpoint is Unknown.'
        ]


def coverage_warnings(samples: list[WeatherSample]) -> list[str]:
    counts: dict[str, int] = {}
    for s in samples:
        if s.missing:
            counts[s.missing] = counts.get(s.missing, 0) + 1
    messages = {
        'out_of_range': '{n} checkpoint{s} fall outside forecast coverage and are Unknown.',
        'missing_values': '{n} checkpoint{s} have incomplete weather data and are Unknown.',
        'provider_error': 'The weather provider failed for {n} checkpoint{s}; they are Unknown.',
    }
    return [messages[k].format(n=n, s='' if n == 1 else 's') for k, n in counts.items()]


def checkpoint_weather(sample: WeatherSample, load_lb: float) -> tuple[dict, Risk]:
    # Classify the displayed (rounded) values so the UI never shows a number on the other side of a threshold
    wind = _round_half_up(sample.wind_mph, 0)
    rain = _round_half_up(sample.rain_in_hr, 2)
    snow = _round_half_up(sample.snow_in_hr, 2)
    a = evaluate(wind, rain, snow, load_lb)
    return {
        'source': sample.source,
        'validAt': iso(sample.valid_at),
        'wind': {'value': wind, 'unit': 'mph', 'risk': a.wind.api},
        'rain': {'value': rain, 'unit': 'in/hr', 'risk': a.rain.api},
        'snow': {'value': snow, 'unit': 'in/hr', 'risk': a.snow.api},
        'overall': a.overall.api,
        'triggers': a.triggers,
        'appliedRules': a.applied_rules,
    }, a.overall


# Analysis

def get_routes(trip: Trip, mode: str) -> tuple[RoutingResult, str, bool, list[str]]:
    """Routing result, effective mode, whether routing fell back, warnings."""
    if mode == 'live':
        try:
            return live_routing().routes(trip.origin_point, trip.destination_point), 'live', False, []
        except NoRouteFound:
            raise
        except ProviderError as e:
            logger.warning('Routing provider failed: %s', e)
            if not config()['DEMO_FALLBACK']:
                raise ApiError(f'Routing is unavailable right now ({e.message}). Try again shortly.',
                               code='routing_unavailable', status_code=e.http_status)
            warning = (f'Live routing is unavailable ({e.message}), so this is a SIMULATED analysis. '
                       f'Do not use it for dispatch decisions.')
            return DemoRouting().routes(trip.origin_point, trip.destination_point), 'demo', True, [warning]
    return DemoRouting().routes(trip.origin_point, trip.destination_point), 'demo', False, []


def trip_dict(trip: Trip) -> dict:
    return {
        'origin': trip.origin,
        'destination': trip.destination,
        'departureAt': iso(trip.departure),
        'loadWeightLb': trip.load_lb,
        'forecastOffsetHours': trip.offset_h,
        'checkpointSpacingMi': trip.spacing_mi,
    }


def analyze(trip: Trip, force_demo: bool = False) -> dict:
    requested_mode = resolve_mode(force_demo)
    routing, mode, routing_fallback, warnings = get_routes(trip, requested_mode)
    if mode == 'demo' and not routing_fallback:
        warnings.append(DEMO_WARNING)
    warnings += routing.warnings
    if mode == 'live':
        warnings.append(TRUCK_ROUTING_WARNING)

    raw = routing.routes
    names = describe(trip.origin_point, trip.destination_point, [r.coordinates for r in raw])
    ids = [new_id('rt') for _ in raw]
    plans: list[list[CheckpointPlan]] = [
        plan_checkpoints(r.coordinates, r.distance_mi, r.duration_s, trip.departure, trip.spacing_mi) for r in raw
    ]

    offset = timedelta(hours=trip.offset_h)
    reqs = [WeatherRequest(p.position, p.eta + offset) for route_plans in plans for p in route_plans]
    samples, weather_fallback, weather_warnings = fetch_weather(reqs, mode, trip)
    warnings += weather_warnings + coverage_warnings(samples)

    sample_iter = iter(samples)
    route_cps: list[list[dict]] = []
    route_risks: list[list[Risk]] = []
    for rid, route_plans in zip(ids, plans):
        cps, risks = [], []
        for p in route_plans:
            weather, risk = checkpoint_weather(next(sample_iter), trip.load_lb)
            cps.append({
                'id': f'{rid}-cp{p.index}',
                'index': p.index,
                'mileFromOrigin': _r1(p.mile),
                'position': [round(p.position[0], 5), round(p.position[1], 5)],
                'etaAt': iso(p.eta),
                'place': nearest_place(p.position),
                'weather': weather,
            })
            risks.append(risk)
        route_cps.append(cps)
        route_risks.append(risks)

    inputs = [
        RouteInput(id=rid, name=name, duration_min=r.duration_s / 60, distance_mi=r.distance_mi,
                   checkpoint_miles=[p.mile for p in route_plans], risks=risks)
        for rid, (name, _), r, route_plans, risks in zip(ids, names, raw, plans, route_risks)
    ]
    scores = score_routes(inputs)

    routes = []
    for r, (name, via), inp, score, cps in zip(raw, names, inputs, scores, route_cps):
        unknown = sum(1 for risk in inp.risks if risk is Risk.UNKNOWN)
        route_warnings = list(score.blockers)
        if unknown and score.eligible:
            route_warnings.append(
                f'{unknown} of {len(cps)} checkpoints have no weather data; those miles are scored as Severe.'
            )
        total = r.distance_mi or 1
        routes.append({
            'id': inp.id,
            'name': name,
            'via': via,
            'provider': {'name': r.provider, 'ref': r.provider_ref},
            'distanceMi': _r1(r.distance_mi),
            'durationMin': _r1(inp.duration_min),
            'arrivalAt': iso(trip.departure + timedelta(seconds=r.duration_s)),
            'coordinates': [[round(lng, 5), round(lat, 5)] for lng, lat in r.coordinates],
            'checkpoints': cps,
            'weatherRiskScore': _r1(score.weather_risk_score),
            'eligible': score.eligible,
            'rank': score.rank,
            'exposure': [
                {'level': level.api, 'miles': _r1(score.exposure_mi[level]),
                 'percent': _r1(score.exposure_mi[level] / total * 100)}
                for level in EXPOSURE_ORDER
            ],
            'severeMiles': _r1(score.severe_miles),
            'highMiles': _r1(score.high_miles),
            'noTravelCheckpointIds': [cps[i]['id'] for i in score.no_travel_indices],
            'coverage': round(score.coverage, 3),
            'warnings': route_warnings,
        })

    return {
        'id': new_id('an'),
        'mode': mode,
        'fallback': {'routing': routing_fallback, 'weather': weather_fallback},
        'sources': {
            'routing': 'OpenRouteService' if mode == 'live' else 'Simulated',
            'weather': 'Open-Meteo' if mode == 'live' and not weather_fallback else 'Simulated',
        },
        'trip': trip_dict(trip),
        'generatedAt': iso(datetime.now(UTC)),
        'routes': routes,
        'recommendation': recommend(inputs, scores),
        'warnings': warnings,
    }


def trip_from_dict(d: dict) -> Trip:
    return Trip(origin=d['origin'], destination=d['destination'], departure=parse_iso(d['departureAt']),
                load_lb=d['loadWeightLb'], offset_h=d.get('forecastOffsetHours', 0),
                spacing_mi=d.get('checkpointSpacingMi', DEFAULT_SPACING_MI))


# Forecast scrubber

GRID_PAD_DEG = 1.0


def _bbox(analysis: dict) -> tuple[float, float, float, float]:
    pts = [p for r in analysis['routes'] for p in r['coordinates']]
    lngs, lats = [p[0] for p in pts], [p[1] for p in pts]
    return (min(lngs) - GRID_PAD_DEG, min(lats) - GRID_PAD_DEG, max(lngs) + GRID_PAD_DEG, max(lats) + GRID_PAD_DEG)


def _grid_points(bbox, steps: int) -> list[LngLat]:
    x0, y0, x1, y1 = bbox
    return [(x0 + (x1 - x0) * i / steps, y0 + (y1 - y0) * j / steps)
            for i in range(steps + 1) for j in range(steps + 1)]


def forecast(analysis: dict, offset_h: int) -> dict:
    """Weather at every checkpoint (and a heatmap grid) at departure + offset."""
    trip = trip_from_dict(analysis['trip'])
    valid_at = trip.departure + timedelta(hours=offset_h)
    cps = [cp for r in analysis['routes'] for cp in r['checkpoints']]
    mode = 'demo' if analysis['mode'] == 'demo' else 'live'

    samples, weather_fallback, warnings = fetch_weather(
        [WeatherRequest(tuple(cp['position']), valid_at) for cp in cps], mode, trip)
    checkpoints = {cp['id']: checkpoint_weather(s, trip.load_lb)[0] for cp, s in zip(cps, samples)}

    grid = []
    if mode == 'demo' or weather_fallback:
        if 0 <= offset_h < DEMO_FORECAST_HORIZON_H:
            storms = build_storms(trip.corridor)
            for p in _grid_points(_bbox(analysis), 40):
                intensity = field_intensity(storms, p, offset_h)
                if intensity > 0.04:
                    grid.append({'lng': p[0], 'lat': p[1], 'intensity': round(intensity, 3)})
    else:
        points = _grid_points(_bbox(analysis), 9)
        try:
            grid_samples = live_weather().samples([WeatherRequest(p, valid_at) for p in points])
        except ProviderError as e:
            logger.warning('Forecast grid failed: %s', e)
            grid_samples = []
            warnings.append('Weather heatmap is unavailable for this hour.')
        for p, s in zip(points, grid_samples):
            _, risk = checkpoint_weather(s, trip.load_lb)
            if risk is not Risk.UNKNOWN and RISK_POINTS[risk] > 0:
                grid.append({'lng': p[0], 'lat': p[1], 'intensity': RISK_POINTS[risk] / 100})

    return {
        'offsetHours': offset_h,
        'validAt': iso(valid_at),
        'available': any(s.source != 'unavailable' for s in samples),
        'fallback': weather_fallback,
        'grid': grid,
        'checkpoints': checkpoints,
        'warnings': warnings,
    }
