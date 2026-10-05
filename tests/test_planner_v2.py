"""planner_v2 후처리 단위 테스트(순수 함수)."""
from src.training import planner_v2 as P


def _row(d, t, km):
    return {"date": d, "workout_type": t, "distance_km": km, "target_pace_min": 360}


def _week(types_km):
    return [_row(f"2026-03-{2 + i:02d}", t, km) for i, (t, km) in enumerate(types_km)]


def test_rebalance_trims_easy_then_long():
    rows = _week([("easy", 8), ("easy", 8), ("long", 20)])
    P._rebalance(rows, 24.0, long_floor=12.0)          # 이지 6·6 → 롱런은 하한 12까지
    assert abs(P._total(rows) - 24.0) < 0.05 and rows[2]["distance_km"] == 12.0
    rows = _week([("easy", 8), ("easy", 8), ("long", 20)])
    P._rebalance(rows, 24.0, long_floor=14.0)          # 하한 아래로는 깎지 않는다(일수 감소는 예산 단계 몫)
    assert rows[2]["distance_km"] == 14.0 and P._total(rows) == 26.0


def test_rebalance_grow_never_drops_km():
    rows = _week([("easy", 11), ("tempo", 8), ("long", 16)])
    P._rebalance(rows, 45.0, long_fill=18.0, long_cap=20.0)    # 이지 12 → 롱런 18 → 나머지 퀄리티
    assert P._total(rows) == 45.0 and rows[2]["distance_km"] == 18.0 and rows[1]["distance_km"] == 15.0


def test_rebalance_grows_easy():
    rows = _week([("easy", 6), ("easy", 6), ("long", 12)])
    P._rebalance(rows, 36.0)
    assert abs(P._total(rows) - 36.0) < 0.2


def test_shakeout_sets_eve_row():
    rows = _week([("easy", 8), ("easy", 8)])
    assert P._shakeout(rows, "2026-03-04") == "2026-03-03"
    assert rows[1]["distance_km"] == P.SHAKEOUT_KM
    assert P._shakeout(rows, None) is None


def test_shakeout_fits_low_volume_race_week():
    rows = _week([("marathon", 6), ("easy", 8)])
    assert P._shakeout(rows, "2026-03-04", 8.7) == "2026-03-03" and rows[1]["distance_km"] == 2.7
    rows = _week([("marathon", 6), ("easy", 8)])
    assert P._shakeout(rows, "2026-03-04", 6.5) is None and rows[1]["workout_type"] == "rest"


def test_note_cold_start_adds_source_to_rationale():
    rows = _week([("easy", 6), ("rest", 0)])
    P._note_cold_start(rows, "default", 16.0)
    assert "거리별 기본값" in rows[0]["rationale"] and "rationale" not in rows[1]
    P._note_cold_start(rows, "history", 16.0)
    assert rows[0]["rationale"].count("기본값") == 1


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


def _v2(rows, **kw):
    base = dict(dlabel="half", phase="base", weeks_to_race=8, taper_first=False, mp_now=300.0, mp_goal=None,
                weeks_since_build=0, run_days=3, week_km=13.2, long_max_12w=0.0, race_date=None)
    return P.apply_v2(rows, **{**base, **kw})


def _run(out):
    return [r for r in out if r["workout_type"] not in ("rest", "race")]


def test_apply_v2_low_volume_week_has_no_long():                      # §8.1 #18
    out = _v2(_week([("easy", 4.0), ("tempo", 2.6), ("long", 6.6)]), long_max_6w=16.2)
    assert not any(r["workout_type"] in ("long", "long_mp") for r in out)
    assert abs(P._total(out) - 13.2) <= 0.05 and len(_run(out)) == 2
    assert all(r["distance_km"] >= 6.0 for r in _run(out)) and "_long_ctx" not in out[0]


def test_apply_v2_full_build_low_budget_mp_inside_long():             # §8.1 #19
    rows = _week([("easy", 4.0), ("tempo", 4.0), ("rest", 0), ("rest", 0), ("rest", 0), ("long", 20.0)])
    out = _v2(rows, dlabel="full", phase="build", run_days=3, week_km=26.0, long_max_6w=18.0, mp_goal=290.0)
    run = _run(out)
    lg = next(r for r in run if r["workout_type"] == "long_mp")
    assert len(run) == 2 and lg["distance_km"] >= 18.0 and lg["mp_km"] == 8.0
    assert not any(r["workout_type"] == "marathon" for r in out) and abs(P._total(out) - 26.0) <= 0.05
    assert out[0]["_long_ctx"]["run_days"] == 2


def test_apply_v2_preserves_weekly_total():                           # §8.1 #20
    cases = [("half", "build", 26.6, 3, [("easy", 8), ("tempo", 7), ("long", 11.6)]),
             ("full", "peak", 46.0, 4, [("easy", 8), ("interval", 8), ("easy", 8), ("long", 22)]),
             ("full", "peak", 73.5, 6, [("easy", 10), ("tempo", 10), ("easy", 10), ("easy", 10), ("easy", 8.5), ("long", 25)]),
             ("half", "recovery_week", 18.0, 4, [("easy", 4), ("tempo", 4), ("easy", 4), ("long", 6)])]
    for d, ph, w, n, spec in cases:
        out = _v2(_week(spec), dlabel=d, phase=ph, run_days=n, week_km=w, long_max_6w=16.0, long_max_12w=18.0)
        assert abs(P._total(out) - w) <= 0.05, (d, ph, w)
        assert all(r["distance_km"] >= 6.0 for r in _run(out)), (d, ph, w)


def test_apply_for_goal_without_target_returns_rows():
    rows = _week([("easy", 8)])
    assert P.apply_for_goal(None, {}, rows, None, "full", {}, None, 3) is rows
