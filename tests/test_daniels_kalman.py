"""P7-PRED-20: Daniels–Gilbert 공식·강도 구간·세트 등가 지속시간, 로컬 레벨 칼만(순수)."""
from src.metrics.prediction import daniels as dn
from src.metrics.prediction.kalman import add_obs, filter_level


def test_formula_anchors():
    assert abs(dn.i_minutes() - dn.I_MIN) < 0.05                       # %VO2max = 1 인 레이스 ≈ 11분
    assert abs(dn.time_for_vdot(50, 42195) - 11449) < 60               # VDOT 50 마라톤 ≈ 3:10:49
    assert abs(dn.vdot(10000, dn.time_for_vdot(45, 10000)) - 45) < 0.01


def test_zone_order():
    z = dn.zone_speeds(50)
    assert z["E"][1] < z["M"] < z["T"] < z["I"] < z["R"]
    assert abs(1000 / dn.threshold_speed(50) - 253.3) < 0.5


def test_equivalent_minutes_rest_ratio():
    assert dn.equivalent_minutes(5, 0.1) == dn.T_MIN                  # 크루즈(짧은 휴식) = 60분 레이스
    assert dn.equivalent_minutes(5, 1.2) == dn.I_MIN                  # 휴식 ≥ 작업 = I
    assert dn.I_MIN < dn.equivalent_minutes(5, 0.5) < dn.T_MIN         # 사이는 ln ρ 보간


def test_kalman_weights_and_decay():
    obs = [{"date": "2026-01-01", "y": 44.0, "var": 1.0, "kind": "race"},
           {"date": "2026-06-01", "y": 46.0, "var": 3.0, "kind": "T"}]
    st = filter_level(obs, "2026-06-02", 0.01)
    assert 44.0 < st["x"] < 46.0 and abs(sum(st["weights"].values()) - 1) < 0.01
    near = filter_level(obs, "2026-06-02", 0.05)                      # q 크면 오래된 대회 가중이 준다
    assert near["weights"]["race"] < st["weights"]["race"]
    h = add_obs(st, 47.0, 1.0, "H")
    assert h["x"] > st["x"] and "H" in h["weights"]
    assert filter_level([], "2026-06-02", 0.01) is None
