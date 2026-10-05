from src.training.plan_gates import (
    Session, WeekPlan, f1_start_fit, f2_peak_long, f3_peak_week, f4_total_ratio, f5_race_pace,
    g1_rest_days, g3_min_session, g4_mp_sessions, g5_taper, g6_ramp, g7_mp_not_faster,
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


def _ctx_week(i, km, long_km, days, phase="build", pace=350, **kw):
    from src.training.long_run_rules import LongCtx
    w = wk(i, km, phase, long_km=long_km, days=days)
    for s in w.days:
        s.pace_sec = pace if s.type == "long" else None
    w.long_ctx = LongCtx("half", phase, 10, km, w.run_days, pace + 10, **kw)
    return w


def test_g2a_boundary_uses_recorded_ctx():
    from src.training.plan_gates_long import g2a_long_cap
    # 하프 build 50km·2일: r=0.60 → 30, 시간 150분/360 = 25, 절대 24 → 상한 24, 경계 +0.5
    assert g2a_long_cap([_ctx_week(0, 50, 24.5, 2)], "half").ok
    assert not g2a_long_cap([_ctx_week(0, 50, 24.6, 2)], "half").ok


def test_g2a_flags_ctx_mismatch():
    from dataclasses import replace
    from src.training.plan_gates_long import g2a_long_cap
    w = _ctx_week(0, 50, 20, 2)
    w.long_ctx = replace(w.long_ctx, week_km=52.0)
    assert "문맥 불일치" in g2a_long_cap([w], "half").worst
    w = _ctx_week(0, 50, 20, 2, pace=330)
    w.long_ctx = replace(w.long_ctx, long_pace_sec=360)
    assert not g2a_long_cap([w], "half").ok


def test_g2b_envelope_boundary():                                    # §8.1 #23
    from src.training.plan_gates_long import g2b_long_envelope
    def three_day(long_km):
        return WeekPlan(0, 5, "peak", [Session("easy", 7.2), Session("easy", 36 - 7.2 - long_km),
                                       Session("long", long_km, pace_sec=360)])
    assert g2b_long_envelope([three_day(21.6)]).ok and g2b_long_envelope([three_day(22.1)]).ok
    assert not g2b_long_envelope([three_day(22.2)]).ok
    long_slow = WeekPlan(0, 5, "peak", [Session("easy", 40), Session("easy", 10), Session("long", 30, pace_sec=420)])
    assert not g2b_long_envelope([long_slow]).ok                     # 210분 > 200


def test_g9_floor_boundary():                                        # §8.1 #24
    from src.training.plan_gates_long import g9_long_floor
    from src.training.long_run_rules import LongCtx
    def peak(long_km):
        w = WeekPlan(0, 5, "peak", [Session("easy", 12)] * 3 + [Session("long", long_km, pace_sec=350)])
        w.long_ctx = LongCtx("full", "peak", 5, w.km, 4, 360, 30, 30, 30)
        return w
    assert not g9_long_floor([peak(23.9)], "full").ok                 # 하한 24
    assert g9_long_floor([peak(23.96)], "full").ok


def test_g9_no_long_week_and_taper_exempt():
    from src.training.plan_gates_long import g9_long_floor
    two = WeekPlan(0, 5, "base", [Session("easy", 8), Session("easy", 8)])
    assert not g9_long_floor([two], "half").ok                        # 16 ≥ min_viable(half, 2)
    small = WeekPlan(0, 5, "base", [Session("easy", 7.5), Session("easy", 7.5)])
    assert g9_long_floor([small], "half").ok
    taper = WeekPlan(0, 1, "taper", [Session("easy", 8), Session("easy", 8)])
    assert g9_long_floor([taper], "half").ok and g9_long_floor([two], "3k").ok
    one_day = WeekPlan(0, 5, "base", [Session("easy", 10.8)])
    assert g9_long_floor([one_day], "half").ok                        # 1일 주는 2일 기준(10.8 < 16)
    short_long = WeekPlan(0, 5, "base", [Session("tempo", 6), Session("long", 5)])
    assert not g9_long_floor([short_long], "half").ok                 # G3 실패 사례(롱런 5.0)


def test_f6_long_step():
    from src.training.plan_gates_long import f6_long_step
    ws = [wk(0, 40, long_km=18), wk(1, 44, long_km=20.5), wk(2, 48, long_km=23.0)]
    assert f6_long_step(ws, 16).ok                                    # 18+2+0.5, 20.5+2.05+0.5
    assert not f6_long_step([wk(0, 40, long_km=18), wk(1, 44, long_km=20.6)], 0).ok


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
