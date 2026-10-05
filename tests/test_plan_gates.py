from src.training.plan_gates import (
    Session, WeekPlan, f1_start_fit, f2_peak_long, f3_peak_week, f4_total_ratio, f5_race_pace,
    g1_rest_days, g2_long_cap, g3_min_session, g4_mp_sessions, g5_taper, g6_ramp, g7_mp_not_faster,
    g8_deterministic,
)


def wk(i, km, phase="build", long_km=0.0, mp_km=0.0, days=1, to_race=10, mp_sec=None):
    ds = [Session("easy", km - long_km)] if km > long_km else []
    if long_km:
        ds.append(Session("long_mp" if mp_km else "long", long_km, mp_km=mp_km))
    while len(ds) < days:
        ds.append(Session("rest"))
    return WeekPlan(i, to_race, phase, ds, mp_sec)


def test_g1():
    w = WeekPlan(0, 5, "build", [Session("easy", 8)] * 6 + [Session("rest")])
    assert g1_rest_days([w], 6).ok
    assert not g1_rest_days([w], 5).ok


def test_g2_boundary():
    ok = wk(0, 30, long_km=20.5)
    bad = wk(1, 30, long_km=20.6)
    assert g2_long_cap([ok], lambda w: 20).ok
    assert not g2_long_cap([bad], lambda w: 20).ok


def test_g3():
    assert g3_min_session([WeekPlan(0, 3, "build", [Session("easy", 6.0)])]).ok
    assert not g3_min_session([WeekPlan(0, 3, "build", [Session("easy", 4.0, pace_sec=360)])]).ok
    assert g3_min_session([WeekPlan(0, 3, "build", [Session("easy", 5.0, minutes=36)])]).ok


def test_g4():
    good = [wk(0, 50, "build", 20, mp_km=8), wk(1, 30, "taper", 12, mp_km=8, to_race=1)]
    bad = [wk(0, 50, "build", 20, mp_km=4), wk(1, 30, "taper", 12, mp_km=8, to_race=1)]
    assert g4_mp_sessions(good, "full").ok
    assert not g4_mp_sessions(bad, "full").ok
    assert g4_mp_sessions(bad, "half").ok


def test_g5():
    ws = [wk(0, 100, "peak"), wk(1, 70, "taper", to_race=1), wk(2, 50, "taper", to_race=0)]
    assert g5_taper(ws, "full", 100, 12).ok
    ws[1] = wk(1, 90, "taper", to_race=1)
    assert not g5_taper(ws, "full", 100, 12).ok


def test_g6_boundary():
    assert g6_ramp([wk(0, 40), wk(1, 44)], 40).ok
    assert not g6_ramp([wk(0, 40), wk(1, 44.5)], 40).ok
    assert not g6_ramp([wk(0, 50)], 40).ok
    assert g6_ramp([wk(0, 40), wk(1, 46)], 40, comeback_ceiling=50).ok


def test_g7():
    assert g7_mp_not_faster([wk(0, 40, mp_sec=300)], lambda w: 312).ok
    assert not g7_mp_not_faster([wk(0, 40, mp_sec=299)], lambda w: 312).ok


def test_g8():
    assert g8_deterministic(lambda: [wk(0, 40)]).ok
    n = iter(range(10))
    assert not g8_deterministic(lambda: [wk(next(n), 40)]).ok


def test_soft_gates():
    ws = [wk(0, 40, long_km=18), wk(1, 50, long_km=20)]
    assert f1_start_fit(ws, 40).ok and not f1_start_fit(ws, 30).ok
    assert f2_peak_long(ws, 14).ok and not f2_peak_long(ws, 13).ok
    assert f3_peak_week(ws, 40).ok and not f3_peak_week(ws, 39).ok
    assert f4_total_ratio(ws, ws).ok and not f4_total_ratio(ws, [wk(0, 200)]).ok
    assert f5_race_pace(300, 300).ok and not f5_race_pace(330, 300).ok
    assert not f5_race_pace(300, None).ok
