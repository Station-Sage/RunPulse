from src.training import personalize as P
from src.training.periodization import build_schedule


def test_is_comeback_boundaries():
    assert P.is_comeback(20, 40)           # 0.5
    assert not P.is_comeback(24, 40)       # 정확히 0.6 → 아님
    assert not P.is_comeback(0, 0)         # 16주 기록 없음


def test_comeback_ceiling():
    assert P.comeback_ceiling(10, 40) == 40
    assert P.comeback_ceiling(30, 40) == 0.0


def test_next_level_ramp():
    assert P.next_level(20, 100) == 20 * 1.10
    assert abs(P.next_level(20, 100, 40) - 23.0) < 1e-9      # 복귀 +15%
    assert abs(P.next_level(36, 100, 40) - 40.0) < 1e-9      # 16주 평균에서 멈춤
    assert abs(P.next_level(38, 100, 40) - 41.8) < 1e-9      # 넘는 부분은 10%
    assert abs(P.next_level(40, 100, 40) - 44.0) < 1e-9       # 넘으면 10%
    assert P.next_level(20, 21, 40) == 21                     # 피크로 자름


def test_start_long_km():
    assert P.start_long_km(10, 30) == 25.5
    assert P.start_long_km(28, 30) == 28


def test_schedule_comeback_ramps_faster_and_v1_unchanged():
    kw = dict(total_weeks=12, start_km=20.0, start_long_km=10.0, peak_km=60.0, long_max_km=32.0,
              long_cap_ratio=0.5, taper_weeks=2)
    base = build_schedule(**kw, rules_version=2)
    comeback = build_schedule(**kw, rules_version=2, comeback_ceiling=45.0)
    assert comeback[1].weekly_km > base[1].weekly_km
    assert comeback[1].weekly_km <= 20.0 * 1.15 + 0.1
    assert build_schedule(**kw, rules_version=1) == build_schedule(**kw, rules_version=1, comeback_ceiling=45.0)
