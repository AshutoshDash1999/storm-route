"""
StormRoute risk engine.

Pure functions, no Django or provider imports: normalized weather (mph, in/hr)
and a load weight in, risk classifications out.

| Level     | Wind          | Rain rate          | Snowfall rate     |
|-----------|---------------|--------------------|-------------------|
| Low       | < 25 mph      | < 0.10 in/hr       | < 0.5 in/hr       |
| Moderate  | 25 to < 35    | 0.10 to < 0.25     | 0.5 to < 1.0      |
| High      | 35 to < 45    | 0.25 to < 0.50     | 1.0 to < 2.0      |
| Severe    | 45 to < 55    | 0.50 to 1.00       | 2.0 to 3.0        |
| No Travel | >= 55         | > 1.00             | > 3.0             |

Note the asymmetry: wind's No Travel bound is inclusive (>= 55), while rain and
snow Severe bands include their upper bound (1.00, 3.0).

Load overrides (wind only):
- wind >= 55                    -> No Travel regardless of load
- 45 <= wind < 55, load > 30,000 -> No Travel
- 35 <= wind < 45, load > 40,000 -> at least Severe

Missing data is never treated as Low. A condition with no value is UNKNOWN; a
checkpoint is UNKNOWN overall unless the known conditions already prove No
Travel, because the missing one could be anything.
"""

import math
from dataclasses import dataclass, field
from enum import IntEnum


class Risk(IntEnum):
    UNKNOWN = -1
    LOW = 0
    MODERATE = 1
    HIGH = 2
    SEVERE = 3
    NO_TRAVEL = 4

    @property
    def api(self) -> str:
        """Wire value shared with the frontend (`CheckpointRisk`)."""
        return 'unavailable' if self is Risk.UNKNOWN else self.name.lower()

    @property
    def label(self) -> str:
        return 'Unknown' if self is Risk.UNKNOWN else self.name.replace('_', ' ').title()


WIND_MODERATE_MPH = 25.0
WIND_HIGH_MPH = 35.0
WIND_SEVERE_MPH = 45.0
WIND_NO_TRAVEL_MPH = 55.0

RAIN_MODERATE_IN_HR = 0.10
RAIN_HIGH_IN_HR = 0.25
RAIN_SEVERE_IN_HR = 0.50
RAIN_SEVERE_MAX_IN_HR = 1.00

SNOW_MODERATE_IN_HR = 0.5
SNOW_HIGH_IN_HR = 1.0
SNOW_SEVERE_IN_HR = 2.0
SNOW_SEVERE_MAX_IN_HR = 3.0

LOAD_NO_TRAVEL_IN_SEVERE_WIND_LB = 30_000
LOAD_SEVERE_IN_HIGH_WIND_LB = 40_000


def _valid(value: float | None) -> bool:
    return value is not None and not math.isnan(value) and value >= 0


def classify_wind(mph: float | None) -> Risk:
    if not _valid(mph):
        return Risk.UNKNOWN
    if mph < WIND_MODERATE_MPH:
        return Risk.LOW
    if mph < WIND_HIGH_MPH:
        return Risk.MODERATE
    if mph < WIND_SEVERE_MPH:
        return Risk.HIGH
    if mph < WIND_NO_TRAVEL_MPH:
        return Risk.SEVERE
    return Risk.NO_TRAVEL


def classify_rain(in_hr: float | None) -> Risk:
    if not _valid(in_hr):
        return Risk.UNKNOWN
    if in_hr < RAIN_MODERATE_IN_HR:
        return Risk.LOW
    if in_hr < RAIN_HIGH_IN_HR:
        return Risk.MODERATE
    if in_hr < RAIN_SEVERE_IN_HR:
        return Risk.HIGH
    if in_hr <= RAIN_SEVERE_MAX_IN_HR:
        return Risk.SEVERE
    return Risk.NO_TRAVEL


def classify_snow(in_hr: float | None) -> Risk:
    if not _valid(in_hr):
        return Risk.UNKNOWN
    if in_hr < SNOW_MODERATE_IN_HR:
        return Risk.LOW
    if in_hr < SNOW_HIGH_IN_HR:
        return Risk.MODERATE
    if in_hr < SNOW_SEVERE_IN_HR:
        return Risk.HIGH
    if in_hr <= SNOW_SEVERE_MAX_IN_HR:
        return Risk.SEVERE
    return Risk.NO_TRAVEL


@dataclass(frozen=True)
class Assessment:
    overall: Risk
    wind: Risk
    rain: Risk
    snow: Risk
    #: Human-readable conditions that set `overall`
    triggers: list[str] = field(default_factory=list)
    #: Load rules that changed the wind classification
    applied_rules: list[str] = field(default_factory=list)

    @property
    def complete(self) -> bool:
        return Risk.UNKNOWN not in (self.wind, self.rain, self.snow)


def apply_load_overrides(wind_mph: float | None, wind_risk: Risk, load_lb: float) -> tuple[Risk, list[str]]:
    """Raise the wind classification for heavy loads. Returns the new risk and the rules that fired."""
    if not _valid(wind_mph):
        return wind_risk, []
    if wind_mph >= WIND_NO_TRAVEL_MPH:
        return Risk.NO_TRAVEL, [f'Wind ≥ {WIND_NO_TRAVEL_MPH:.0f} mph: No Travel regardless of load']
    if wind_mph >= WIND_SEVERE_MPH and load_lb > LOAD_NO_TRAVEL_IN_SEVERE_WIND_LB:
        return Risk.NO_TRAVEL, [
            f'Load over {LOAD_NO_TRAVEL_IN_SEVERE_WIND_LB:,} lb in {WIND_SEVERE_MPH:.0f}–{WIND_NO_TRAVEL_MPH:.0f} mph wind: No Travel'
        ]
    if wind_mph >= WIND_HIGH_MPH and load_lb > LOAD_SEVERE_IN_HIGH_WIND_LB:
        return max(wind_risk, Risk.SEVERE), [
            f'Load over {LOAD_SEVERE_IN_HIGH_WIND_LB:,} lb in {WIND_HIGH_MPH:.0f}–{WIND_SEVERE_MPH:.0f} mph wind: at least Severe'
        ]
    return wind_risk, []


def _fmt(value: float, places: int) -> str:
    return f'{value:.{places}f}'


def evaluate(wind_mph: float | None, rain_in_hr: float | None, snow_in_hr: float | None,
             load_lb: float) -> Assessment:
    base_wind = classify_wind(wind_mph)
    wind, rules = apply_load_overrides(wind_mph, base_wind, load_lb)
    rain = classify_rain(rain_in_hr)
    snow = classify_snow(snow_in_hr)

    known = [r for r in (wind, rain, snow) if r is not Risk.UNKNOWN]
    worst = max(known, default=Risk.UNKNOWN)
    complete = len(known) == 3
    overall = worst if complete or worst is Risk.NO_TRAVEL else Risk.UNKNOWN

    triggers: list[str] = []
    if overall is Risk.UNKNOWN:
        missing = [name for name, r in (('wind', wind), ('rain', rain), ('snowfall', snow)) if r is Risk.UNKNOWN]
        triggers.append(f"No {', '.join(missing)} data")
    elif overall > Risk.LOW:
        if wind is overall:
            reason = f'Wind {_fmt(wind_mph, 0)} mph'
            if wind is not base_wind:
                reason += f' with {load_lb:,.0f} lb load'
            triggers.append(f'{reason} → {overall.label}')
        if rain is overall:
            triggers.append(f'Rain {_fmt(rain_in_hr, 2)} in/hr → {overall.label}')
        if snow is overall:
            triggers.append(f'Snowfall {_fmt(snow_in_hr, 2)} in/hr → {overall.label}')

    return Assessment(overall=overall, wind=wind, rain=rain, snow=snow, triggers=triggers, applied_rules=rules)
