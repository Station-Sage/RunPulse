"""planner_v2 후처리 단위 테스트(순수 함수)."""
from src.training import planner_v2 as P


def _row(d, t, km):
    return {"date": d, "workout_type": t, "distance_km": km, "target_pace_min": 360}


def _week(types_km):
    return [_row(f"2026-03-{2 + i:02d}", t, km) for i, (t, km) in enumerate(types_km)]


def test_rebalance_trims_easy_then_long():
    rows = _week([("easy", 8), ("easy", 8), ("long", 20)])
    P._rebalance(rows, 24.0)
    assert abs(P._total(rows) - 24.0) < 0.2


def test_rebalance_grows_easy():
    rows = _week([("easy", 6), ("easy", 6), ("long", 12)])
    P._rebalance(rows, 36.0)
    assert abs(P._total(rows) - 36.0) < 0.2


def test_shakeout_sets_eve_row():
    rows = _week([("easy", 8), ("easy", 8)])
    assert P._shakeout(rows, "2026-03-04") == "2026-03-03"
    assert rows[1]["distance_km"] == P.SHAKEOUT_KM
    assert P._shakeout(rows, None) is None


def test_mp_session_retypes_longest_quality():
    rows = _week([("easy", 8), ("tempo", 9)])
    assert P._mp_session(rows, 300.0, 8.0)
    assert rows[1]["workout_type"] == "marathon" and rows[1]["distance_km"] >= 11.0
    assert not P._mp_session(_week([("rest", 0)]), 300.0, 8.0)


def test_race_week_adds_mp_session():
    rows = _week([("easy", 8), ("easy", 8), ("easy", 8), ("easy", 4)])
    P._race_week(rows, 300.0, "2026-03-08")
    assert any(r["workout_type"] == "marathon" for r in rows)


def test_apply_v2_full_build_has_mp_and_no_input_mutation():
    rows = _week([("easy", 8), ("tempo", 8), ("easy", 8), ("long", 22), ("easy", 6)])
    snap = [dict(r) for r in rows]
    out = P.apply_v2(rows, dlabel="full", phase="build", weeks_to_race=8, taper_first=False, mp_now=300.0,
                     mp_goal=290.0, weeks_since_build=4, run_days=5, week_km=55.0, long_max_12w=20.0, race_date=None)
    assert rows == snap
    assert any(r["workout_type"] in ("marathon", "long_mp") for r in out)
    assert sum(r["distance_km"] for r in out) <= 55.05


def test_apply_v2_half_has_no_mp():
    rows = _week([("easy", 8), ("tempo", 8), ("easy", 8), ("long", 18)])
    out = P.apply_v2(rows, dlabel="half", phase="build", weeks_to_race=8, taper_first=False, mp_now=300.0,
                     mp_goal=None, weeks_since_build=4, run_days=4, week_km=42.0, long_max_12w=0.0, race_date=None)
    assert not any(r["workout_type"] in ("marathon", "long_mp") for r in out)


def test_apply_for_goal_without_target_returns_rows():
    rows = _week([("easy", 8)])
    assert P.apply_for_goal(None, {}, rows, None, "full", {}, None, 3) is rows
