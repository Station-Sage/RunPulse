import pytest
from src.metrics.prediction.core import (vdot, time_for_vdot, threshold_speed, temp_factor, vdot_at_15c, time_at_temp, anchor,
                          best_block, combine, k_personal, convert, tanda_marathon, marathon_estimate, confidence, race_range)
from src.metrics.prediction.physio import hrmax_self, lthr_self, lthr_fallback, zones_hrr, zones_lthr, wbgt_approx, ambient_from_device

def test_vdot_roundtrip():
    assert round(vdot(10000, 2653), 1) == 46.2
    assert abs(time_for_vdot(46.2, 10000) - 2653) < 3
    assert round(threshold_speed(45.0), 3) == 3.625

def test_temp():
    assert temp_factor(15, -0.62, -0.84) == 1.0
    assert round(temp_factor(25, -0.62, -0.84), 4) == 0.938
    assert round(temp_factor(0, -0.62, -0.84), 4) == 0.958
    v = vdot_at_15c(10000, 2800, 25, -0.62, -0.84)
    assert abs(time_at_temp(v, 10000, 25, -0.62, -0.84) - 2800) < 3

def test_anchor_decay():
    a = anchor([{"vdot15": 46.2, "weeks": 20, "activity_id": 1}, {"vdot15": 43.1, "weeks": 2, "activity_id": 2}])
    assert a["activity_id"] == 1 and round(a["value"], 2) == 45.08

def test_best_block():
    laps = [{"dist_m": 1000, "dur_s": 360, "speed_ms": 1000/360, "hr": 135}] * 2 + \
           [{"dist_m": 1000, "dur_s": 272, "speed_ms": 1000/272, "hr": 168}] * 3 + \
           [{"dist_m": 1000, "dur_s": 370, "speed_ms": 1000/370, "hr": 150}]
    v = best_block(laps, lthr=177, v_t=None, is_race=False)
    assert round(v, 1) == 41.5          # 3km 13:36
    assert best_block(laps, lthr=None, v_t=None, is_race=False) is None
    assert round(best_block(laps, lthr=None, v_t=3.64, is_race=False), 1) == 41.5

def test_combine():
    v, w = combine(45.1, 43.2, 44.6)
    assert round(v, 2) == 44.62 and w == {"race": 0.6, "work": 0.2, "hr": 0.2}
    v, w = combine(45.1, 47.0, None)
    assert v == 47.0 and w["work"] == 1.0
    v, w = combine(None, 43.0, 44.0)
    assert round(v, 1) == 43.4
    assert combine(None, None, None) == (None, {})

def test_k_personal():
    k, sd, n = k_personal([])
    assert (k, n) == (1.06, 0) and round(sd, 3) == 0.03
    k, sd, n = k_personal([{"d1": 10000, "t1": 2676, "d2": 21097.5, "t2": 6147, "gap_days": 20}])
    assert n == 1 and 1.06 < k < 1.11

def test_convert_equals_daniels_at_k0():
    assert abs(convert(45.0, 10000, 42195, 1.06) - time_for_vdot(45.0, 42195)) < 1e-6

def test_marathon():
    t = tanda_marathon(42.3, 356)
    assert 13600 < t < 13800
    m = marathon_estimate(12588, 13702, 0)
    assert round(m["median_s"]) == 13133 and round(m["high_s"]) == 14395

def test_confidence_and_range():
    c, why = confidence(20, 4.3, 1.0, 3)
    assert c == 0.72 and "기준 대회가 20주 전" in why
    lo, hi = race_range(2734, c)
    assert round(lo) == 2594 and round(hi) == 2874
    c2, _ = confidence(None, 12, 4.2, 1)
    assert c2 < 0.15

def test_hr_profile():
    assert hrmax_self([193, 192, 191, 250, 110]) == 192.0
    assert round(lthr_self([(10000, 181.0), (21097.5, 182.0), (10000, 174.0)]), 1) == 177.4
    assert lthr_fallback(192) == 176.1
    assert zones_hrr(193, 43)[3] == (163.0, 178.0)
    assert zones_lthr(177)[3] == (168.2, 177.0)

def test_weather():
    assert round(wbgt_approx(25, 70), 1) == 26.8
    assert round(ambient_from_device(24.0), 1) == 20.0
