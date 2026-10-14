"""
Trip input for POST /api/routes/analyze/.

Accepts the frontend's camelCase `TripInput` and the snake_case aliases from
the API checklist. Locations may be `{id, label, lat, lng}` objects or
free-text strings ("Dallas, TX").
"""

from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from apps.common.exceptions import ProviderError
from apps.common.geo import haversine_mi
from apps.routing import geocode

MAX_LOAD_LB = 80_000
MAX_DEPARTURE_DAYS = 7
PAST_GRACE = timedelta(minutes=5)
MAX_FORECAST_OFFSET_H = 48

#: snake_case alias → canonical field
ALIASES = {
    'departure_time': 'departureAt',
    'departure_at': 'departureAt',
    'load_weight_lb': 'loadWeightLb',
    'forecast_offset_hours': 'forecastOffsetHours',
    'checkpoint_spacing_mi': 'checkpointSpacingMi',
}


def normalize_keys(data: dict) -> tuple[dict, dict[str, str]]:
    """Canonical-keyed copy of `data`, plus canonical → original key map for error reporting."""
    out, used = {}, {}
    for key, value in data.items():
        canonical = ALIASES.get(key, key)
        out[canonical] = value
        if canonical != key:
            used[canonical] = key
    return out, used


class LocationField(serializers.Field):
    default_error_messages = {
        'invalid': 'Enter a place name or choose a location from the suggestions.',
        'blank': 'Enter a location.',
        'coords': 'Location coordinates are invalid.',
    }

    def to_internal_value(self, data):
        if isinstance(data, str):
            text = data.strip()
            if not text:
                self.fail('blank')
            return {'text': text}
        if not isinstance(data, dict):
            self.fail('invalid')
        try:
            lat, lng = float(data['lat']), float(data['lng'])
        except (KeyError, TypeError, ValueError):
            self.fail('coords')
        if not (-90 <= lat <= 90 and -180 <= lng <= 180):
            self.fail('coords')
        label = str(data.get('label') or f'{lat:.4f}, {lng:.4f}')
        return {'id': str(data.get('id') or label), 'label': label, 'lng': lng, 'lat': lat}

    def to_representation(self, value):
        return value


class TripSerializer(serializers.Serializer):
    origin = LocationField(error_messages={'required': 'Choose an origin.', 'null': 'Choose an origin.'})
    destination = LocationField(error_messages={'required': 'Choose a destination.',
                                                'null': 'Choose a destination.'})
    departureAt = serializers.DateTimeField(error_messages={
        'required': 'Choose a departure date and time.',
        'null': 'Choose a departure date and time.',
        'invalid': 'Departure must be an ISO-8601 date and time, e.g. 2026-10-15T08:00:00-05:00.',
    })
    loadWeightLb = serializers.FloatField(error_messages={
        'required': 'Enter the load weight in pounds.',
        'null': 'Enter the load weight in pounds.',
        'invalid': 'Load weight must be a number of pounds.',
    })
    forecastOffsetHours = serializers.IntegerField(
        default=0, min_value=0, max_value=MAX_FORECAST_OFFSET_H,
        error_messages={'min_value': 'Forecast offset must be between 0 and 48 hours.',
                        'max_value': 'Forecast offset must be between 0 and 48 hours.'},
    )
    checkpointSpacingMi = serializers.FloatField(
        default=25.0, min_value=5, max_value=100,
        error_messages={'min_value': 'Checkpoint spacing must be 5–100 miles.',
                        'max_value': 'Checkpoint spacing must be 5–100 miles.'},
    )
    mode = serializers.ChoiceField(choices=['live', 'demo'], required=False)

    def _resolve(self, value: dict, what: str) -> dict:
        if 'text' not in value:
            return value
        try:
            found = geocode.resolve(value['text'], api_key=self.context.get('geocode_key'),
                                    timeout=self.context.get('timeout', 8.0))
        except ProviderError:
            raise serializers.ValidationError(f"Couldn't look up this {what} right now. Pick one from the suggestions.")
        if not found:
            raise serializers.ValidationError(f"Couldn't find that {what}. Try a city and state, e.g. \"Dallas, TX\".")
        return found

    def validate_origin(self, value):
        return self._resolve(value, 'origin')

    def validate_destination(self, value):
        return self._resolve(value, 'destination')

    def validate_departureAt(self, value):
        now = timezone.now()
        if value < now - PAST_GRACE:
            raise serializers.ValidationError("Departure can't be in the past.")
        if value > now + timedelta(days=MAX_DEPARTURE_DAYS):
            raise serializers.ValidationError(
                f'Departure must be within the next {MAX_DEPARTURE_DAYS} days for forecast coverage.')
        return value

    def validate_loadWeightLb(self, value):
        if value <= 0:
            raise serializers.ValidationError('Load weight must be greater than 0 lb.')
        if value > MAX_LOAD_LB:
            raise serializers.ValidationError(f"Load weight can't exceed {MAX_LOAD_LB:,} lb (legal gross limit).")
        return value

    def validate(self, attrs):
        o, d = attrs['origin'], attrs['destination']
        if o['id'] == d['id'] or haversine_mi((o['lng'], o['lat']), (d['lng'], d['lat'])) < 1:
            raise serializers.ValidationError({'destination': 'Destination must be different from the origin.'})
        return attrs
