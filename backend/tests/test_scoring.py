import pytest

from apps.recommendations.scoring import (
    RouteInput,
    recommend,
    route_metrics,
    score_routes,
    segment_lengths,
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


def test_fewest_severe_miles_wins_over_everything_else():
    routes = [
        route('fast', [S, L, L], duration=60),     # 25 Severe
        route('slow', [H, H, H, L], duration=300),  # 0 Severe, 75 High, much slower
    ]
    scores = {s.id: s for s in score_routes(routes)}
    assert scores['fast'].severe_miles == 25 and scores['slow'].severe_miles == 0
    assert scores['slow'].rank == 1 and scores['fast'].rank == 2


def test_then_fewest_high_miles():
    routes = [
        route('a', [H, L, L], duration=60),           # 0 Severe, 25 High, avg 25
        route('b', [M, M, M, M, L], duration=200),    # 0 Severe, 0 High, avg 25
    ]
    scores = {s.id: s for s in score_routes(routes)}
    assert scores['b'].rank == 1


def test_then_lowest_average_risk():
    routes = [
        route('a', [M, M, L], duration=60),   # avg 25
        route('b', [L, M, L], duration=120),  # avg 12.5
    ]
    scores = {s.id: s for s in score_routes(routes)}
    assert scores['b'].weather_risk_score == pytest.approx(12.5)
    assert scores['b'].rank == 1


def test_then_shortest_travel_time():
    routes = [route('a', [M, L, L], duration=90), route('b', [L, M, L], duration=80)]
    scores = {s.id: s for s in score_routes(routes)}
    assert scores['b'].rank == 1 and scores['a'].rank == 2


def test_float_noise_does_not_decide_ranking():
    # 25.000001 vs 25 Severe miles is a display-level tie, so time decides
    a = route('a', [S, L, L], duration=60, miles=[0, 25.000001, 50, 75])
    b = route('b', [S, L, L], duration=50, miles=[0, 25, 50, 75])
    scores = {s.id: s for s in score_routes([a, b])}
    assert scores['b'].rank == 1


def test_reasons_name_the_deciding_criterion():
    routes = [
        route('a', [S, L, L], duration=60),
        route('b', [H, L, L], duration=90),
        route('c', [H, L, L], duration=100),
    ]
    rec = recommend(routes, score_routes(routes))
    assert rec['routeId'] == 'b'
    assert rec['reasons'][0].startswith('Route B ranks first of 3 eligible routes: 0 mi Severe, 25 mi High')
    assert 'Route C ranks #2: longer travel time (1 h 40 m vs. 1 h 30 m).' in rec['reasons']
    assert 'Route A ranks #3: more Severe miles (25 mi vs. 0 mi).' in rec['reasons']


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
