"""
Route-level risk metrics and ranking.

- Checkpoint i owns the segment from itself to checkpoint i+1; the destination
  checkpoint owns 0 mi.
- Eligible routes are ranked strictly, in this order:
    1. fewest Severe miles
    2. fewest High miles
    3. lowest average risk (distance-weighted mean of per-level points, 0–100)
    4. shortest travel time
  Mileages and average risk are compared at display precision (0.1) so float
  noise can't decide a ranking the user can't see.
- Missing weather counts as Severe (in Severe miles and in average risk), so a
  gap can never make a route look safer than one with known High risk. Routes
  with less than half their miles covered are not eligible.
- Any No Travel checkpoint makes a route ineligible.
"""

from dataclasses import dataclass, field

from apps.risk.engine import Risk

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

#: Ranking criteria in priority order, as (label, short reason) pairs
CRITERIA = [
    ('fewest Severe miles', 'more Severe miles'),
    ('fewest High miles', 'more High miles'),
    ('lowest average risk', 'higher average risk'),
    ('shortest travel time', 'longer travel time'),
]


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
    #: Average risk, 0–100
    weather_risk_score: float
    duration_min: float = 0.0
    coverage: float = 1.0
    #: Severe, No Travel and Unknown miles
    severe_miles: float = 0.0
    high_miles: float = 0.0
    no_travel_indices: list[int] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    rank: int | None = None

    @property
    def eligible(self) -> bool:
        return not self.blockers

    @property
    def ranking_key(self) -> tuple[float, float, float, float]:
        return (round(self.severe_miles, 1), round(self.high_miles, 1), round(self.weather_risk_score, 1),
                self.duration_min)


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
        duration_min=route.duration_min,
        coverage=coverage,
        severe_miles=exposure[Risk.SEVERE] + exposure[Risk.NO_TRAVEL] + exposure[Risk.UNKNOWN],
        high_miles=exposure[Risk.HIGH],
        no_travel_indices=no_travel,
        blockers=blockers,
    )


def score_routes(routes: list[RouteInput]) -> list[RouteScore]:
    """Score every route and assign ranks (1 = best) to eligible ones. Order matches input."""
    scores = [route_metrics(r) for r in routes]
    eligible = sorted((s for s in scores if s.eligible), key=lambda s: (s.ranking_key, s.id))
    for rank, score in enumerate(eligible, start=1):
        score.rank = rank
    return scores


def deciding_criterion(better: RouteScore, worse: RouteScore) -> int | None:
    """Index into CRITERIA of the first criterion that separates two routes; None for a full tie."""
    for i, (a, b) in enumerate(zip(better.ranking_key, worse.ranking_key)):
        if a != b:
            return i
    return None


def _miles(mi: float) -> str:
    return f'{mi:,.0f} mi'


def _duration(minutes: float) -> str:
    h, m = int(minutes // 60), round(minutes % 60)
    if m == 60:
        h, m = h + 1, 0
    return f'{h} h {m:02d} m' if h > 0 else f'{m} m'


def _criterion_value(score: RouteScore, i: int) -> str:
    if i == 0:
        return _miles(score.severe_miles)
    if i == 1:
        return _miles(score.high_miles)
    if i == 2:
        return f'{score.weather_risk_score:.1f}/100'
    return _duration(score.duration_min)


def _summary(score: RouteScore) -> str:
    return ', '.join(f'{_criterion_value(score, i)} {label}' for i, label in
                     enumerate(['Severe', 'High', 'average risk', 'travel time']))


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
    reasons.append(
        f'{best_route.name} ranks first of {n} eligible route{"" if n == 1 else "s"}: '
        f'{_summary(best)}.'
    )
    for other in ranked[1:]:
        i = deciding_criterion(best, other)
        why = 'tied on every criterion' if i is None else (
            f'{CRITERIA[i][1]} ({_criterion_value(other, i)} vs. {_criterion_value(best, i)})')
        reasons.append(f'{by_id[other.id].name} ranks #{other.rank}: {why}.')
    fastest = min(routes, key=lambda r: (r.duration_min, r.id))
    if fastest.id != best.id:
        reasons.append(
            f'Adds {_duration(best_route.duration_min - fastest.duration_min)} vs. the fastest route '
            f'({fastest.name}) to avoid weather.'
        )
    else:
        reasons.append('Also the fastest available route.')
    for s in scores:
        if not s.eligible:
            reasons.append(f'{by_id[s.id].name} excluded: {"; ".join(s.blockers)}.')
    for s in scores:
        if s.exposure_mi[Risk.UNKNOWN] > 0 and s.eligible:
            reasons.append(
                f'{by_id[s.id].name} has {_miles(s.exposure_mi[Risk.UNKNOWN])} without weather data, scored as Severe.'
            )
    return {'routeId': best.id, 'status': 'available', 'reasons': reasons}
