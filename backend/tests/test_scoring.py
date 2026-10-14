import pytest

from apps.recommendations.scoring import (
    RouteInput,
    recommend,
    route_metrics,
    score_routes,
    segment_lengths,
    time_scores,
)
from apps.risk.engine import Risk

L, M, H, S, NT, U = Risk.LOW, Risk.MODERATE, Risk.HIGH, Risk.SEVERE, Risk.NO_TRAVEL, Risk.UNKNOWN


def route(id_, risks, duration=60.0, miles=None):
    miles = miles or [i * 25.0 for i in range(len(risks))]
    return RouteInput(id=id_, name=f'Route {id_.upper()}', duration_min=duration, distance_mi=miles[-1],
                      checkpoint_miles=miles, risks=risks)


def test_each_checkpoint_owns_the_segment_to_the_next():
    assert segment_lengths([0, 25, 50, 62]) == [25, 25, 12, 0]
    s = route_metrics(route('a', [L, H, S, NT], miles=[0, 25, 50, 62]))
    # Destination checkpoint (NT) owns 0 miles but still blocks the route
    assert s.exposure_mi[L] == 25
    assert s.exposure_mi[H] == 25
    assert s.exposure_mi[S] == 12
    assert s.exposure_mi[NT] == 0
    assert s.no_travel_indices == [3]
    assert not s.eligible


def test_distance_weighted_risk_score():
    s = route_metrics(route('a', [L, S, L], miles=[0, 10, 100]))
    # 10 mi Low (0) + 90 mi Severe (75) over 100 mi
    assert s.weather_risk_score == pytest.approx(67.5)
    assert s.severe_miles == 90


def test_time_scores_min_max_normalized():
    assert time_scores([100, 150, 200]) == [0, 50, 100]


def test_equal_durations_get_zero_time_penalty():
    assert time_scores([90, 90, 90]) == [0, 0, 0]


def test_weighted_score_and_ranking():
    routes = [
        route('a', [M, M, L], duration=100),  # risk 25, time 0   -> 17.5
        route('b', [L, L, L], duration=150),  # risk 0,  time 100 -> 30
        route('c', [L, M, L], duration=110),  # risk 12.5, time 20 -> 14.75
    ]
    scores = {s.id: s for s in score_routes(routes)}
    assert scores['a'].weighted_score == pytest.approx(17.5)
    assert scores['b'].weighted_score == pytest.approx(30)
    assert scores['c'].weighted_score == pytest.approx(14.75)
    assert [scores[k].rank for k in 'cab'] == [1, 2, 3]


def test_ties_break_by_duration_then_id():
    routes = [route('b', [L, L]), route('a', [L, L])]
    scores = {s.id: s for s in score_routes(routes)}
    assert scores['a'].rank == 1 and scores['b'].rank == 2


def test_no_travel_route_is_never_recommended_even_when_fastest_and_otherwise_clean():
    routes = [
        route('fast', [L, L, L, NT], duration=60),
        route('slow', [S, S, L], duration=300),
    ]
    scores = score_routes(routes)
    rec = recommend(routes, scores)
    assert rec['routeId'] == 'slow'
    assert rec['status'] == 'available'
    assert next(s for s in scores if s.id == 'fast').rank is None


def test_all_routes_blocked_returns_no_recommendation():
    routes = [route('a', [NT, L]), route('b', [L, NT, L])]
    rec = recommend(routes, score_routes(routes))
    assert rec['routeId'] is None
    assert rec['status'] == 'blocked'
    assert any('Route A' in r for r in rec['reasons'])


def test_missing_weather_cannot_make_a_route_look_safer():
    known_high = route('known', [H, H, L])
    gappy = route('gappy', [U, H, L])
    scores = {s.id: s for s in score_routes([known_high, gappy])}
    assert scores['gappy'].weather_risk_score > scores['known'].weather_risk_score
    assert scores['known'].rank == 1
    assert scores['gappy'].coverage == pytest.approx(0.5)


def test_mostly_missing_weather_is_ineligible():
    s = route_metrics(route('a', [U, U, L, L]))
    assert s.coverage == pytest.approx(1 / 3)
    assert not s.eligible
    assert 'Insufficient weather coverage' in s.blockers[0]


def test_recommendation_reasons_mention_detour_cost():
    routes = [route('a', [S, S, L], duration=60), route('b', [L, L, L], duration=90)]
    rec = recommend(routes, score_routes(routes))
    assert rec['routeId'] == 'b'
    assert any(r.startswith('Adds 30 m vs. the fastest route (Route A)') for r in rec['reasons'])
