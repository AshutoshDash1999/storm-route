import math

import pytest

from apps.risk.engine import Risk, classify_rain, classify_snow, classify_wind, evaluate

LIGHT = 20_000


@pytest.mark.parametrize('mph, expected', [
    (0, Risk.LOW),
    (24.99, Risk.LOW),
    (25, Risk.MODERATE),
    (34.99, Risk.MODERATE),
    (35, Risk.HIGH),
    (44.99, Risk.HIGH),
    (45, Risk.SEVERE),
    (54.99, Risk.SEVERE),
    (55, Risk.NO_TRAVEL),
    (90, Risk.NO_TRAVEL),
])
def test_wind_thresholds(mph, expected):
    assert classify_wind(mph) is expected


@pytest.mark.parametrize('rate, expected', [
    (0, Risk.LOW),
    (0.0999, Risk.LOW),
    (0.10, Risk.MODERATE),
    (0.2499, Risk.MODERATE),
    (0.25, Risk.HIGH),
    (0.4999, Risk.HIGH),
    (0.50, Risk.SEVERE),
    (1.00, Risk.SEVERE),
    (1.0001, Risk.NO_TRAVEL),
])
def test_rain_thresholds(rate, expected):
    assert classify_rain(rate) is expected


@pytest.mark.parametrize('rate, expected', [
    (0, Risk.LOW),
    (0.4999, Risk.LOW),
    (0.5, Risk.MODERATE),
    (0.9999, Risk.MODERATE),
    (1.0, Risk.HIGH),
    (1.9999, Risk.HIGH),
    (2.0, Risk.SEVERE),
    (3.0, Risk.SEVERE),
    (3.0001, Risk.NO_TRAVEL),
])
def test_snow_thresholds(rate, expected):
    assert classify_snow(rate) is expected


@pytest.mark.parametrize('fn', [classify_wind, classify_rain, classify_snow])
@pytest.mark.parametrize('value', [None, math.nan, -1])
def test_missing_or_invalid_values_are_unknown(fn, value):
    assert fn(value) is Risk.UNKNOWN


@pytest.mark.parametrize('wind, load, expected', [
    # >= 55 is No Travel at any load
    (55, 1, Risk.NO_TRAVEL),
    (55, LIGHT, Risk.NO_TRAVEL),
    # 45 to < 55: No Travel only above 30,000 lb
    (45, 30_000, Risk.SEVERE),
    (45, 30_001, Risk.NO_TRAVEL),
    (54.99, 30_001, Risk.NO_TRAVEL),
    # 35 to < 45: at least Severe only above 40,000 lb
    (35, 40_000, Risk.HIGH),
    (35, 40_001, Risk.SEVERE),
    (44.99, 40_001, Risk.SEVERE),
    # Below 35 mph load has no effect
    (34.99, 80_000, Risk.MODERATE),
])
def test_load_overrides(wind, load, expected):
    result = evaluate(wind, 0, 0, load)
    assert result.overall is expected
    assert result.wind is expected


def test_load_override_reports_rule():
    result = evaluate(46, 0, 0, 35_000)
    assert result.overall is Risk.NO_TRAVEL
    assert result.applied_rules == ['Load over 30,000 lb in 45–55 mph wind: No Travel']
    assert result.triggers == ['Wind 46 mph with 35,000 lb load → No Travel']


def test_no_override_reports_no_rule():
    assert evaluate(40, 0, 0, 40_000).applied_rules == []


def test_heavy_load_in_high_wind_does_not_lower_worse_conditions():
    # 'At least Severe' never downgrades
    result = evaluate(40, 1.5, 0, 45_000)
    assert result.wind is Risk.SEVERE
    assert result.overall is Risk.NO_TRAVEL


def test_highest_condition_wins():
    result = evaluate(10, 0.3, 0.6, LIGHT)
    assert (result.wind, result.rain, result.snow) == (Risk.LOW, Risk.HIGH, Risk.MODERATE)
    assert result.overall is Risk.HIGH
    assert result.triggers == ['Rain 0.30 in/hr → High']


def test_no_travel_takes_precedence():
    result = evaluate(10, 0, 3.5, LIGHT)
    assert result.overall is Risk.NO_TRAVEL
    assert result.triggers == ['Snowfall 3.50 in/hr → No Travel']


def test_ties_list_every_trigger():
    result = evaluate(47, 0.6, 2.5, LIGHT)
    assert result.overall is Risk.SEVERE
    assert len(result.triggers) == 3


def test_all_low_has_no_triggers():
    result = evaluate(5, 0, 0, LIGHT)
    assert result.overall is Risk.LOW
    assert result.triggers == []
    assert result.complete


def test_all_missing_is_unknown_never_low():
    result = evaluate(None, None, None, LIGHT)
    assert result.overall is Risk.UNKNOWN
    assert result.overall.api == 'unavailable'


def test_partial_data_is_unknown_even_when_known_values_are_low():
    result = evaluate(5, None, 0, LIGHT)
    assert result.overall is Risk.UNKNOWN
    assert result.triggers == ['No rain data']
    assert not result.complete


def test_partial_data_still_reports_proven_no_travel():
    result = evaluate(60, None, None, LIGHT)
    assert result.overall is Risk.NO_TRAVEL


@pytest.mark.parametrize('risk, api', [
    (Risk.LOW, 'low'), (Risk.NO_TRAVEL, 'no_travel'), (Risk.UNKNOWN, 'unavailable'),
])
def test_wire_values_match_frontend(risk, api):
    assert risk.api == api
