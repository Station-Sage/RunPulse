"""U16g: R6 MP 규칙(순수 함수)."""
from src.training import marathon_rules as M


def test_prescribed_mp_without_goal_and_data():
    assert M.prescribed_mp(300, None, 4) == 300
    assert M.prescribed_mp(None, 290, 4) == 290
    assert M.prescribed_mp(None, None, 0) is None


def test_prescribed_mp_weekly_progress():
    assert M.prescribed_mp(300, 280, 0) == 300
    assert M.prescribed_mp(300, 280, 2) == 295.0


def test_prescribed_mp_capped_by_12s_and_goal():
    assert M.prescribed_mp(300, 270, 10) == 288.0      # 25초 진행 → 12초 절단
    assert M.prescribed_mp(300, 295, 10) == 295        # 목표가 더 느리면 목표에서 멈춤


def test_long_run_pace_clamped():
    assert round(M.long_run_pace(300), 1) == 345.0
    assert round(M.long_run_pace(300, 1.5), 1) == 360.0
    assert round(M.long_run_pace(300, 1.0), 1) == 330.0


def test_long_mp_share_by_phase():
    assert M.long_mp_km(30, "build", 0) == 6.0
    assert M.long_mp_km(30, "build", 1) == 9.0
    assert M.long_mp_km(30, "peak", 0) == 12.0
    assert M.long_mp_km(30, "peak", 1) == 15.0
    assert M.long_mp_km(30, "base") == 0.0


def test_taper_week1_mp_range():
    assert M.taper_week1_mp_km(30) == 13.0
    assert M.taper_week1_mp_km(22) == 11.0
    assert M.taper_week1_mp_km(8) == 8.0


def test_race_week_session():
    s = M.race_week_session()
    assert 3 <= s["mp_km"] <= 5 and s["distance_km"] >= 6 and s["workout_type"] == "marathon"
