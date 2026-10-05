"""목표 대회 역산 주기화."""
from src.training.periodization import build_schedule

KW = dict(start_km=42.0, start_long_km=23.0, peak_km=73.5, long_max_km=32.0, long_cap_ratio=0.5, taper_weeks=3)


def test_last_week_is_race_week_and_taper_comes_last():
    s = build_schedule(9, **KW)
    assert len(s) == 9 and s[-1].weeks_to_race == 0 and s[0].weeks_to_race == 8
    assert [w.phase for w in s[-3:]] == ["taper"] * 3
    assert all(w.phase != "taper" for w in s[:-3])


def test_ramp_is_capped_and_peak_week_is_not_recovery():
    s = build_schedule(9, **KW)
    train = s[:-3]
    assert train[-1].phase != "recovery_week"
    loads = [w.weekly_km for w in train if w.phase != "recovery_week"]
    assert all(b <= a * 1.1 + 0.1 for a, b in zip(loads, loads[1:]))      # 부하주 간 +10% 이하
    assert max(w.weekly_km for w in train) < KW["peak_km"]                  # 6주로는 목표 피크까지 못 감 → 캡이 우선
    rec = [w for w in train if w.phase == "recovery_week"]
    assert rec and rec[0].weekly_km < train[rec[0].index - 1].weekly_km


def test_long_run_progresses_then_tapers_off():
    s = build_schedule(9, **KW)
    longs = [w.long_km for w in s]
    assert longs[0] >= 20 and max(longs) <= 32.0 and max(longs) > longs[0]
    assert s[-3].long_km > 0 and s[-2].long_km == 0 and s[-1].long_km == 0    # 감량 첫 주만 롱런
    assert s[-3].long_km < max(longs[:-3])


def test_taper_volume_falls_below_peak():
    s = build_schedule(9, **KW)
    peak = max(w.weekly_km for w in s[:-3])
    assert s[-3].weekly_km < peak and s[-1].weekly_km < s[-2].weekly_km < s[-3].weekly_km


def test_short_or_invalid_inputs():
    assert build_schedule(0, **KW) == [] and build_schedule(5, **{**KW, "start_km": 0}) == []
    s = build_schedule(2, **KW)                       # 계획이 감량 기간보다 짧으면 전부 감량
    assert [w.phase for w in s] == ["taper", "taper"]


def test_v2_full_taper_is_two_weeks_with_d14_long():
    s = build_schedule(12, **KW, rules_version=2)
    assert [w.phase for w in s[-2:]] == ["taper"] * 2 and s[-3].phase != "taper"
    peak = s[-3].weekly_km if s[-3].phase != "recovery_week" else s[-4].weekly_km
    assert abs(s[-2].weekly_km - peak * 0.70) < 1.0 and abs(s[-1].weekly_km - peak * 0.50) < 1.0
    assert s[-2].long_km == 0 and s[-1].long_km == 0
    assert 20.0 <= s[-3].long_km <= 24.0 and s[-3].weeks_to_race == 2


def test_v2_three_week_taper_only_for_long_high_volume_plans():
    s = build_schedule(18, **{**KW, "peak_km": 90.0, "start_km": 70.0}, rules_version=2)
    assert [w.phase for w in s[-3:]] == ["taper"] * 3 and s[-3].weeks_to_race == 2
    assert 20.0 <= s[-3].long_km <= 24.0
    s2 = build_schedule(18, **KW, rules_version=2)          # 피크 80km 미만 → 2주
    assert [w.phase for w in s2].count("taper") == 2


def test_v1_unchanged_by_rules_version():
    """v1 불변만 단언한다 — 하프 v2는 반올림 내림·진행 상한으로 v1과 달라진다(DESIGN-U16-LONGRUN §7.3)."""
    assert build_schedule(9, **KW) == build_schedule(9, **KW, rules_version=1)
    half = {**KW, "taper_weeks": 2}
    v1 = build_schedule(9, **half)
    assert v1 == build_schedule(9, **half, rules_version=1, long_cap=lambda *a: 0.0)   # v1은 long_cap 무시
    v2 = build_schedule(9, **half, rules_version=2)
    assert [w.phase for w in v1] == [w.phase for w in v2]
    assert all(b.weekly_km <= a.weekly_km + 1e-9 for a, b in zip(v1, v2))      # 내림이라 v1 이하


def _load_ratios(s):
    loads = [w.weekly_km for w in s if w.phase not in ("recovery_week", "taper")]
    return [b / a for a, b in zip(loads, loads[1:])]


def test_v2_low_volume_ramp_never_exceeds_ten_percent():              # §8.1 #21
    s = build_schedule(12, 7.4, 6.0, 30.0, 22.0, 0.5, 2, rules_version=2)
    assert s[0].weekly_km == 7.4 and max(_load_ratios(s)) <= 1.10 + 1e-9
    v1 = build_schedule(12, 7.4, 6.0, 30.0, 22.0, 0.5, 2)
    assert max(_load_ratios(v1)) > 1.10 + 0.005                          # v1 반올림은 10%를 넘는다(R7)


def _shared_cap(n_days=4, lp=352.0, long6=18.0, long12=18.0):
    from src.training import long_run_rules as LR
    def cap(phase, w2r, week_km, sched, prev):
        return LR.long_cap_km(LR.LongCtx("full", phase, w2r, week_km, n_days, lp, sched, long6, long12,
                                         prev_long_km=prev))
    return cap


def test_v2_long_progresses_from_capped_value():                     # §8.1 #22 150→180분 전환
    s = build_schedule(16, 70.0, 24.0, 80.0, 32.0, 0.5, 3, rules_version=2, long_cap=_shared_cap(6, 380.0, 24, 24))
    longs = [w.long_km for w in s if w.phase != "taper" and w.long_km > 0]
    base_last = max(w.long_km for w in s if w.phase == "base")
    assert base_last <= 150 * 60 / 380 + 0.05                            # base는 150분 상한(23.7)에 눌린다
    prev = 0.0
    for k in longs:
        assert prev == 0.0 or k <= prev + max(2.0, 0.1 * prev) + 0.05    # 전환 주에도 +2km/10% 이내
        prev = max(prev, k)
    assert max(longs) > base_last                                         # 180분으로 풀리면 진행한다


def test_v2_d14_long_respects_shared_cap():
    s = build_schedule(12, 40.0, 14.0, 46.0, 32.0, 0.5, 3, rules_version=2, long_cap=_shared_cap(4, 352.0, 14, 14))
    d14 = next(w for w in s if w.weeks_to_race == 2)
    prev = max(w.long_km for w in s if w.index < d14.index)
    assert d14.long_km <= prev + max(2.0, 0.1 * prev) + 0.05 and d14.long_km >= min(20.0, prev)


def test_schedule_for_goal_uses_goal_rules_version(tmp_path):
    import sqlite3
    from datetime import date
    from src.db_setup import create_tables
    from src.training.goals import add_goal, set_rules_version
    from src.training.planner_schedule import _rules_version
    conn = sqlite3.connect(tmp_path / "t.db")
    create_tables(conn)
    gid = add_goal(conn, "m", 42.195, date(2027, 3, 7).isoformat(), rules_version=1)
    assert _rules_version(conn, {"id": gid}) == 1
    set_rules_version(conn, gid, 2)
    assert _rules_version(conn, {"id": gid}) == 2
    assert _rules_version(conn, {}) == 1


def test_build_schedule_max_week_km_caps_volume():
    from src.training.periodization import build_schedule
    s = build_schedule(12, 60, 18, 90, 32, 0.35, 2, max_week_km=45.0)
    assert s and max(w.weekly_km for w in s) <= 45.0 + 0.01
