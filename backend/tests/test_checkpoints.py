from datetime import UTC, datetime, timedelta

import pytest

from apps.common.geo import cumulative_miles, haversine_mi
from apps.recommendations.checkpoints import checkpoint_miles, plan_checkpoints

DEPART = datetime(2026, 10, 15, 13, 0, tzinfo=UTC)


@pytest.mark.parametrize('total, expected', [
    (62, [0, 25, 50, 62]),
    (50, [0, 25, 50]),
    (25, [0, 25]),
    (10, [0, 10]),
    (75.5, [0, 25, 50, 75, 75.5]),
])
def test_checkpoint_spacing_includes_origin_and_destination(total, expected):
    assert checkpoint_miles(total, 25) == expected


def test_custom_spacing():
    assert checkpoint_miles(100, 40) == [0, 40, 80, 100]


def test_spacing_must_be_positive():
    with pytest.raises(ValueError):
        checkpoint_miles(10, 0)


def _line(miles: float, steps: int = 50):
    """Due-north polyline of roughly `miles` length from (−97, 32)."""
    dlat = miles / 69.05
    return [(-97.0, 32.0 + dlat * i / steps) for i in range(steps + 1)]


def test_checkpoints_are_interpolated_onto_geometry():
    coords = _line(62)
    total = cumulative_miles(coords)[-1]
    plans = plan_checkpoints(coords, total, 3600, DEPART)
    assert [round(p.mile, 6) for p in plans] == [0, 25, 50, round(total, 6)]
    assert plans[0].position == coords[0]
    assert plans[-1].position == coords[-1]
    for p in plans:
        # Every point lies on the line (constant lng) at the right distance from the origin
        assert p.position[0] == pytest.approx(-97.0)
        assert haversine_mi(coords[0], p.position) == pytest.approx(p.mile, abs=0.01)


def test_marks_scale_onto_geometry_when_provider_distance_differs():
    coords = _line(60)
    # Provider says the road is 120 mi; checkpoint at 60 mi should land halfway along the geometry
    plans = plan_checkpoints(coords, 120, 7200, DEPART, spacing_mi=60)
    assert [p.mile for p in plans] == [0, 60, 120]
    geom = cumulative_miles(coords)[-1]
    assert haversine_mi(coords[0], plans[1].position) == pytest.approx(geom / 2, abs=0.01)


def test_eta_is_proportional_to_distance():
    coords = _line(100)
    plans = plan_checkpoints(coords, 100, 2 * 3600, DEPART)
    assert [p.eta - DEPART for p in plans] == [
        timedelta(0), timedelta(minutes=30), timedelta(minutes=60), timedelta(minutes=90), timedelta(hours=2),
    ]
