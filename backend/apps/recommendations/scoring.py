"""
Route-level risk metrics, scoring and ranking.

- Checkpoint i owns the segment from itself to checkpoint i+1; the destination
  checkpoint owns 0 mi.
- weather risk score = distance-weighted mean of per-level points (0–100).
- time score = min–max normalized duration (0 fastest, 100 slowest; all 0 when equal).
- weighted score = 0.70 · risk + 0.30 · time. Lower is better.
- Missing weather scores as Severe (75), so a gap can never make a route look
  safer than one with known High risk. Routes with less than half their miles
  covered are not eligible.
- Any No Travel checkpoint makes a route ineligible.
"""

from dataclasses import dataclass, field

from apps.risk.engine import Risk

RISK_WEIGHT = 0.70
TIME_WEIGHT = 0.30

RISK_POINTS: dict[Risk, float] = {
    Risk.LOW: 0,
    Risk.MODERATE: 25,
    Risk.HIGH: 50,
    Risk.SEVERE: 75,
    Risk.NO_TRAVEL: 100,
    Risk.UNKNOWN: 75,
}

MIN_COVERAGE = 0.5

#: Display order for exposure lists, matching the frontend legend
EXPOSURE_ORDER = [Risk.LOW, Risk.MODERATE, Risk.HIGH, Risk.SEVERE, Risk.NO_TRAVEL, Risk.UNKNOWN]


@dataclass(frozen=True)
class RouteInput:
    id: str
    name: str
    duration_min: float
    distance_mi: float
    checkpoint_miles: list[float]
    risks: list[Risk]


@dataclass
class RouteScore:
    id: str
    exposure_mi: dict[Risk, float]
    weather_risk_score: float
    time_score: float = 0.0
    weighted_score: float = 0.0
    coverage: float = 1.0
    severe_miles: float = 0.0
    no_travel_indices: list[int] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    rank: int | None = None

    @property
    def eligible(self) -> bool:
        return not self.blockers


def segment_lengths(miles: list[float]) -> list[float]:
    return [max(0.0, b - a) for a, b in zip(miles, miles[1:])] + [0.0]


def route_metrics(route: RouteInput) -> RouteScore:
    lengths = segment_lengths(route.checkpoint_miles)
    exposure = {level: 0.0 for level in EXPOSURE_ORDER}
    for length, risk in zip(lengths, route.risks):
        exposure[risk] += length
    total = sum(lengths)

    if total > 0:
        risk_score = sum(RISK_POINTS[level] * mi for level, mi in exposure.items()) / total
        coverage = 1 - exposure[Risk.UNKNOWN] / total
    else:
        # Degenerate single-point route: fall back to the worst checkpoint
        risk_score = max((RISK_POINTS[r] for r in route.risks), default=RISK_POINTS[Risk.UNKNOWN])
        coverage = 0.0 if Risk.UNKNOWN in route.risks else 1.0

    no_travel = [i for i, r in enumerate(route.risks) if r is Risk.NO_TRAVEL]
    blockers = []
    if no_travel:
        blockers.append(f'No Travel conditions at {len(no_travel)} checkpoint{"s" if len(no_travel) != 1 else ""}')
    if coverage < MIN_COVERAGE:
        blockers.append(f'Insufficient weather coverage ({coverage:.0%} of route)')

    return RouteScore(
        id=route.id,
        exposure_mi=exposure,
        weather_risk_score=risk_score,
        coverage=coverage,
        severe_miles=exposure[Risk.SEVERE] + exposure[Risk.NO_TRAVEL],
        no_travel_indices=no_travel,
        blockers=blockers,
    )


def time_scores(durations: list[float]) -> list[float]:
    if not durations:
        return []
    lo, hi = min(durations), max(durations)
    if hi - lo <= 1e-9:
        return [0.0] * len(durations)
    return [(d - lo) / (hi - lo) * 100 for d in durations]


def weighted_score(risk_score: float, time_score: float) -> float:
    return RISK_WEIGHT * risk_score + TIME_WEIGHT * time_score


def score_routes(routes: list[RouteInput]) -> list[RouteScore]:
    """Score every route and assign ranks (1 = best) to eligible ones. Order matches input."""
    scores = [route_metrics(r) for r in routes]
    for score, t in zip(scores, time_scores([r.duration_min for r in routes])):
        score.time_score = t
        score.weighted_score = weighted_score(score.weather_risk_score, t)

    by_id = {r.id: r for r in routes}
    eligible = sorted(
        (s for s in scores if s.eligible),
        # Round first so float noise can't reorder visually-equal scores; then faster, then id
        key=lambda s: (round(s.weighted_score, 6), by_id[s.id].duration_min, s.id),
    )
    for rank, score in enumerate(eligible, start=1):
        score.rank = rank
    return scores


def _miles(mi: float) -> str:
    return f'{mi:,.0f} mi'


def _duration(minutes: float) -> str:
    h, m = int(minutes // 60), round(minutes % 60)
    if m == 60:
        h, m = h + 1, 0
    return f'{h} h {m:02d} m' if h > 0 else f'{m} m'


def recommend(routes: list[RouteInput], scores: list[RouteScore]) -> dict:
    by_id = {r.id: r for r in routes}
    ranked = sorted((s for s in scores if s.rank is not None), key=lambda s: s.rank)
    reasons: list[str] = []

    if not ranked:
        reasons.append('Every route is blocked; no route is recommended.')
        for s in scores:
            reasons.append(f'{by_id[s.id].name}: {"; ".join(s.blockers)}.')
        return {'routeId': None, 'status': 'blocked', 'reasons': reasons}

    best = ranked[0]
    best_route = by_id[best.id]
    n = len(ranked)
    reasons.append(f'Lowest weighted score ({best.weighted_score:.1f}) among {n} eligible route{"" if n == 1 else "s"}.')
    reasons.append(
        f'{_miles(best.exposure_mi[Risk.SEVERE])} Severe and {_miles(best.exposure_mi[Risk.HIGH])} High exposure.'
    )
    fastest = min(routes, key=lambda r: (r.duration_min, r.id))
    if fastest.id != best.id:
        reasons.append(
            f'Adds {_duration(best_route.duration_min - fastest.duration_min)} vs. the fastest route '
            f'({fastest.name}) to avoid weather.'
        )
    else:
        reasons.append('Also the fastest available route.')
    if n > 1:
        runner = ranked[1]
        reasons.append(
            f'{by_id[runner.id].name} scores {runner.weighted_score:.1f} '
            f'(weather {runner.weather_risk_score:.0f}, time {runner.time_score:.0f}).'
        )
    for s in scores:
        if not s.eligible:
            reasons.append(f'{by_id[s.id].name} excluded: {"; ".join(s.blockers)}.')
    for s in scores:
        if s.exposure_mi[Risk.UNKNOWN] > 0 and s.eligible:
            reasons.append(
                f'{by_id[s.id].name} has {_miles(s.exposure_mi[Risk.UNKNOWN])} without weather data, scored as Severe.'
            )
    return {'routeId': best.id, 'status': 'available', 'reasons': reasons}
