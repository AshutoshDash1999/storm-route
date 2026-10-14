"""Simulated weather from the demo storm field. Never calls a provider."""

from datetime import datetime

from apps.common.geo import Corridor
from apps.demo.scenario import (
    DEMO_FORECAST_HORIZON_H,
    build_coverage_hole,
    build_storms,
    conditions_at,
)

from .base import WeatherRequest, WeatherSample


class DemoWeather:
    name = 'Demo weather'

    def __init__(self, corridor: Corridor, departure: datetime):
        self.departure = departure
        self.storms = build_storms(corridor)
        self.hole = build_coverage_hole(corridor)

    def hours_after_departure(self, t: datetime) -> float:
        return (t - self.departure).total_seconds() / 3600

    def samples(self, reqs: list[WeatherRequest]) -> list[WeatherSample]:
        return [self.sample(r) for r in reqs]

    def sample(self, req: WeatherRequest) -> WeatherSample:
        hour = self.hours_after_departure(req.valid_at)
        if hour < 0 or hour >= DEMO_FORECAST_HORIZON_H:
            return WeatherSample.unavailable(req.valid_at, 'out_of_range')
        if self.hole.contains(req.position):
            return WeatherSample.unavailable(req.valid_at, 'missing_values')
        wind, rain, snow = conditions_at(self.storms, req.position, hour)
        return WeatherSample(valid_at=req.valid_at, source='simulated', wind_mph=wind, rain_in_hr=rain, snow_in_hr=snow)
