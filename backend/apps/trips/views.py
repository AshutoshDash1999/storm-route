from datetime import UTC, datetime, time, timedelta

from rest_framework import serializers
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle

from apps.common.exceptions import ApiError, NotFound
from apps.demo import us_locations
from apps.locations import gazetteer
from apps.recommendations import service
from apps.trips import store
from apps.trips.serializers import MAX_FORECAST_OFFSET_H, TripSerializer, normalize_keys


class AnalyzeThrottle(SimpleRateThrottle):
    """Per-client limit on analyses, which each fan out to several provider calls."""
    scope = 'analyze'

    def get_cache_key(self, request, view):
        return self.cache_format % {'scope': self.scope, 'ident': self.get_ident(request)}


@api_view(['GET'])
def health(request):
    mode = service.resolve_mode()
    return Response({
        'status': 'ok',
        'mode': mode,
        'providers': {
            'routing': 'OpenRouteService' if mode == 'live' else 'Simulated',
            'weather': 'Open-Meteo' if mode == 'live' else 'Simulated',
        },
    })


@api_view(['GET'])
def location_search(request):
    query = request.query_params.get('q', '').strip()
    if not query:
        raise ApiError('Enter a city name or ZIP code to search.', code='validation_error',
                       fields={'q': ['This parameter is required.']})
    try:
        limit = int(request.query_params.get('limit', 10))
    except ValueError:
        limit = 0
    if not 1 <= limit <= gazetteer.MAX_LIMIT:
        raise ApiError(f'limit must be a whole number from 1 to {gazetteer.MAX_LIMIT}.', code='validation_error',
                       fields={'limit': [f'Must be 1–{gazetteer.MAX_LIMIT}.']})
    return Response({'query': query, 'results': gazetteer.search(query, limit)})


@api_view(['GET'])
def location_detail(request, location_id: str):
    location = gazetteer.get(location_id)
    if not location:
        raise NotFound(f'Location "{location_id}" was not found.', code='location_not_found')
    return Response(location)


@api_view(['POST'])
@throttle_classes([AnalyzeThrottle])
def analyze(request):
    if not isinstance(request.data, dict):
        raise ApiError('Send the trip as a JSON object.', code='invalid_body')
    data, aliases = normalize_keys(request.data)
    cfg = service.config()
    force_demo = data.get('mode') == 'demo'
    ser = TripSerializer(data=data, context={
        # Free-text geocoding only calls the provider in live mode
        'geocode_key': None if force_demo else cfg['ORS_API_KEY'] or None,
        'timeout': cfg['PROVIDER_TIMEOUT_S'],
    })
    if not ser.is_valid():
        # Report errors under the key the client actually sent
        raise serializers.ValidationError({aliases.get(k, k): v for k, v in ser.errors.items()})
    v = ser.validated_data
    trip = service.Trip(
        origin=v['origin'], destination=v['destination'], departure=v['departureAt'],
        load_lb=v['loadWeightLb'], offset_h=v['forecastOffsetHours'], spacing_mi=v['checkpointSpacingMi'],
    )
    analysis = service.analyze(trip, force_demo=force_demo)
    store.save(analysis)
    return Response(analysis)


def demo_trip() -> service.Trip:
    """Denver → Chicago, tomorrow 12:00 UTC (6 AM Mountain), 42,000 lb."""
    tomorrow = datetime.now(UTC).date() + timedelta(days=1)
    return service.Trip(
        origin=dict(us_locations.find('denver-co')),
        destination=dict(us_locations.find('chicago-il')),
        departure=datetime.combine(tomorrow, time(12, 0), tzinfo=UTC),
        load_lb=42_000,
    )


@api_view(['GET'])
def demo(request):
    analysis = service.analyze(demo_trip(), force_demo=True)
    store.save(analysis)
    return Response(analysis)


def _route_or_404(route_id: str) -> tuple[dict, dict]:
    found = store.get_route(route_id)
    if not found:
        raise NotFound(f'Route "{route_id}" was not found or has expired. Run the analysis again.',
                       code='route_not_found')
    return found


@api_view(['GET'])
def route_detail(request, route_id: str):
    analysis, route = _route_or_404(route_id)
    return Response({
        'analysisId': analysis['id'],
        'mode': analysis['mode'],
        'fallback': analysis['fallback'],
        'trip': analysis['trip'],
        'recommended': analysis['recommendation']['routeId'] == route['id'],
        'route': route,
    })


@api_view(['GET'])
def route_checkpoints(request, route_id: str):
    analysis, route = _route_or_404(route_id)
    return Response({'routeId': route['id'], 'mode': analysis['mode'], 'checkpoints': route['checkpoints']})


@api_view(['GET'])
def analysis_forecast(request, analysis_id: str):
    analysis = store.get_analysis(analysis_id)
    if not analysis:
        raise NotFound(f'Analysis "{analysis_id}" was not found or has expired.', code='analysis_not_found')
    try:
        offset = int(request.query_params.get('offset', 0))
    except ValueError:
        offset = -1
    if not 0 <= offset <= MAX_FORECAST_OFFSET_H:
        raise ApiError('offset must be a whole number of hours from 0 to 48.', code='validation_error',
                       fields={'offset': ['Must be 0–48.']})
    snapshot = store.get_forecast(analysis_id, offset)
    if snapshot is None:
        snapshot = service.forecast(analysis, offset)
        store.save_forecast(analysis_id, offset, snapshot)
    return Response(snapshot)
