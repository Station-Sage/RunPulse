"""P7-PRED-90: fearp v2 — 외기·이슬점 보정, 기기 온도 미사용."""
from src.metrics.fearp import heat_penalty


def test_heat_penalty_table():
    assert heat_penalty(None, None) == 0.0
    assert heat_penalty(10.0, 5.0) == 0.0                      # 50+41 = 91°F
    assert abs(heat_penalty(25.0, 20.0) - 3.8) < 0.1           # 77+68 = 145°F → 3~4.5% 사이
    assert heat_penalty(40.0, 30.0) == 10.0                    # 상한
    assert heat_penalty(25.0, None) == 5.0                     # 이슬점 없음 → 15℃ 초과 1℃당 0.5%
