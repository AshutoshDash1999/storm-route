"""Weather checkpoints along a route: every N miles, plus origin and destination."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from apps.common.geo import LngLat, cumulative_miles, point_at_mile

DEFAULT_SPACING_MI = 25.0
_EPS = 1e-6


@dataclass(frozen=True)
class CheckpointPlan:
    index: int
    mile: float
    position: LngLat
    eta: datetime


def checkpoint_miles(total_mi: float, spacing_mi: float = DEFAULT_SPACING_MI) -> list[float]:
    """0, spacing, 2·spacing, … and always the destination. 62 mi @ 25 → [0, 25, 50, 62]."""
    if spacing_mi <= 0:
        raise ValueError('spacing must be positive')
    marks = []
    k = 0
    while k * spacing_mi < total_mi - _EPS:
        marks.append(k * spacing_mi)
        k += 1
    marks.append(total_mi)
    return marks


def plan_checkpoints(coords: list[LngLat], distance_mi: float, duration_s: float, departure: datetime,
                     spacing_mi: float = DEFAULT_SPACING_MI) -> list[CheckpointPlan]:
    """
    Place checkpoints by the provider's route distance, interpolated along the
    geometry. The geometry's own length differs slightly from the provider's
    distance, so marks are scaled onto it; the last checkpoint is exactly the
    destination vertex.

    ETA assumes constant average speed over the route (provider duration ×
    share of distance), which keeps results deterministic.
    """
    cumulative = cumulative_miles(coords)
    geom_total = cumulative[-1]
    scale = geom_total / distance_mi if distance_mi > 0 else 0.0
    plans = []
    for i, mile in enumerate(checkpoint_miles(distance_mi, spacing_mi)):
        share = mile / distance_mi if distance_mi > 0 else 0.0
        plans.append(CheckpointPlan(
            index=i,
            mile=mile,
            position=point_at_mile(coords, cumulative, mile * scale),
            eta=departure + timedelta(seconds=duration_s * share),
        ))
    return plans
