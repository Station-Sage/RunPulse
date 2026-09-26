"""P7-PRED-88: TIDS 시간 기준."""
from src.metrics.tids import distribution, pattern


def _run(laps):
    return {"activity_type": "running", "moving_s": 0, "distance_m": 0, "laps": [{"dur_s": s, "speed_ms": v} for s, v in laps]}


def test_time_based_distribution_and_patterns():
    v_m, v_t = 1000 / 296, 1000 / 276
    runs = [_run([(3000, 2.8)]), _run([(600, 2.8), (1200, 3.7), (300, 2.9)]), _run([(2400, 3.2)])]
    d = distribution(runs, v_m, v_t)
    assert d == {"z1": 84.0, "z2": 0.0, "z3": 16.0} and pattern(d)[0] == "polarized"
    assert pattern({"z1": 80.0, "z2": 15.0, "z3": 5.0})[0] == "pyramidal"
    assert pattern({"z1": 30.0, "z2": 50.0, "z3": 20.0})[0] == "threshold"
    assert pattern({"z1": 60.0, "z2": 10.0, "z3": 30.0}) == ("polarized", 2.26)
    assert pattern({"z1": 40.0, "z2": 25.0, "z3": 35.0})[0] == "mixed"
    assert distribution([], v_m, v_t) is None
