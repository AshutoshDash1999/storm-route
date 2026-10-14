"""Internal weather schema. Every provider returns these, already in mph and in/hr."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol

from apps.common.geo import LngLat

Source = Literal['live', 'simulated', 'unavailable']
#: Why a sample has no values
MissingReason = Literal['out_of_range', 'missing_values', 'provider_error']


@dataclass(frozen=True)
class WeatherRequest:
    position: LngLat
    valid_at: datetime


@dataclass(frozen=True)
class WeatherSample:
    valid_at: datetime
    source: Source
    #: Max of sustained wind and gusts, mph
    wind_mph: float | None = None
    #: Liquid precipitation rate, in/hr
    rain_in_hr: float | None = None
    #: Snowfall rate (snow depth, not water equivalent), in/hr
    snow_in_hr: float | None = None
    missing: MissingReason | None = None

    @classmethod
    def unavailable(cls, valid_at: datetime, reason: MissingReason) -> 'WeatherSample':
        return cls(valid_at=valid_at, source='unavailable', missing=reason)


class WeatherProvider(Protocol):
    name: str

    def samples(self, requests: list[WeatherRequest]) -> list[WeatherSample]:
        """One sample per request, same order. Raises ProviderError only if nothing could be fetched."""
