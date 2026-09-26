"""P7-PRED-20·22: Daniels 공식·강도 역산, 칼만 결합, 예측 코어(r4)."""
from src.metrics.prediction import daniels as dn
from src.metrics.prediction.core_r4 import (vdot, time_for_vdot, threshold_speed, temp_factor, vdot_at_15c, time_at_temp,
                                         k_personal, to_target, longrun_k_sd, hr_reach_mult, summarize, tanda_marathon,
                                         combine_marathon)
from src.metrics.prediction.kalman import add_obs, filter_level
from src.metrics.prediction.physio import hrmax_self, lthr_self, lthr_fallback, zones_hrr, zones_lthr, wbgt_approx, ambient_from_device


def test_daniels_formula_and_zones():
    assert round(vdot(10000, 2653), 1) == 46.2 and abs(time_for_vdot(46.2, 10000) - 2653) < 3
    assert round(time_for_vdot(50, 42195)) == 11440                 # 내장 get_race_predictions 와 같은 식
    assert round(dn.i_minutes(), 2) == 11.03 and round(dn.pct_vo2max(60), 3) == 0.888
    z = {k: (round(1000 / v) if not isinstance(v, tuple) else tuple(round(1000 / x) for x in v)) for k, v in dn.zone_speeds(45).items()}
    assert z == {"E": (382, 319), "M": 296, "T": 276, "I": 251, "R": 239}
    assert round(1000 / threshold_speed(45)) == 276


def test_set_zone_and_equivalent_minutes():
    assert [dn.set_zone(1, 1200, 0, 1200), dn.set_zone(1, 3000, 0, 3000), dn.set_zone(1, 300, 0, 300)] == ["T", "M", None]
    assert [dn.set_zone(8, 90, 2.0, 720), dn.set_zone(6, 250, 0.48, 1500), dn.set_zone(6, 300, 0.25, 1800),
            dn.set_zone(3, 100, 0.5, 300)] == ["R", "I", "T", None]
    assert dn.equivalent_minutes(1, 0.0) == 60.0 and dn.equivalent_minutes(5, 0.1) == 60.0
    assert dn.equivalent_minutes(5, 1.2) == dn.I_MIN and round(dn.equivalent_minutes(4, 0.45), 2) == 25.56
    assert round(dn.set_vdot("I", 4.0, 5, 0.6), 2) == 47.18 and round(dn.set_vdot("T", 1000 / 272, 1, 0), 2) == 45.79
    assert round(dn.set_vdot("R", 1000 / 220, 8, 2.0), 2) == 49.33 and round(dn.set_vdot("M", 1000 / 295, 1, 0), 2) == 45.21


def test_temp():
    assert temp_factor(15, -0.62, -0.84) == 1.0 and round(temp_factor(25, -0.62, -0.84), 4) == 0.938
    v = vdot_at_15c(10000, 2800, 25, -0.62, -0.84)
    assert abs(time_at_temp(v, 10000, 25, -0.62, -0.84) - 2800) < 3


def test_k_personal_disjoint_pairs():
    assert k_personal([]) == (1.06, 0.03, 0)
    r = [{"nominal_m": 10000.0, "vdot15": 45.7, "day": -160}, {"nominal_m": 21097.5, "vdot15": 43.9, "day": -180},
         {"nominal_m": 10000.0, "vdot15": 46.2, "day": -140}, {"nominal_m": 21097.5, "vdot15": 43.0, "day": -200}]
    k, sd, n = k_personal(r)
    assert n == 2 and round(k, 4) == 1.0966 and round(sd, 4) == 0.0205       # 4개 대회 → 겹치지 않는 쌍 2개


def test_distance_extrapolation():
    y, ev = to_target(45.0, 10000, 42195, 1.06, 0.03)
    assert round(y, 3) == 45.0 and round(ev, 3) == 5.431                      # k=1.06 → 값 불변, 분산만 증가
    assert round(longrun_k_sd(0.02, 42195, 10000, 24000), 4) == 0.0232       # 최장 24km 넘는 외삽분
    assert longrun_k_sd(0.02, 21097.5, 10000, 24000) == 0.02


def test_quality_multiplier():
    assert round(hr_reach_mult(0.88), 3) == 4.221 and hr_reach_mult(None) == 1.0 and hr_reach_mult(0.95) == 1.0


def test_kalman_weights_and_add():
    obs = [{"date": "2026-01-01", "y": 44, "var": 1, "kind": "race"}, {"date": "2026-02-01", "y": 46, "var": 3.0625, "kind": "T"}]
    st = filter_level(obs, "2026-03-01", 0.01)
    assert round(st["x"], 4) == 44.5664 and round(st["var"], 4) == 1.1473 and st["weights"] == {"T": 0.283, "race": 0.717}
    st2 = add_obs(st, 45, 1.5625, "H")
    assert round(st2["x"], 2) == 44.75 and st2["weights"] == {"H": 0.423, "T": 0.163, "race": 0.413}
    assert filter_level([], "2026-01-01", 0.01) is None


def test_summary_and_marathon():
    s = summarize(45.0, 1.0, 10000)
    assert round(s["median_s"]) == 2713 and round(s["low_s"]) == 2623 and round(s["high_s"]) == 2811 and s["confidence"] == 0.74
    m = combine_marathon(summarize(45.0, 1.0, 42195), 12000)
    assert round(m["median_s"]) == 12407 and m["tanda_weight"] == 0.177 and m["confidence"] == 0.77
    assert 13600 < tanda_marathon(42.3, 356) < 13800


def test_hr_profile_and_weather_helpers():
    assert hrmax_self([193, 192, 191, 250, 110]) == 192.0
    assert round(lthr_self([(10000, 181.0), (21097.5, 182.0), (10000, 174.0)]), 1) == 177.4
    assert lthr_fallback(192) == 176.1 and zones_hrr(193, 43)[3] == (163.0, 178.0) and zones_lthr(177)[3] == (168.2, 177.0)
    assert round(wbgt_approx(25, 70), 1) == 26.8 and round(ambient_from_device(24.0), 1) == 20.0


def test_kalman_low_mult_weakens_low_observations():
    from src.metrics.prediction.kalman import filter_level
    obs = [{"date": "2026-01-01", "y": 50.0, "var": 1.0, "kind": "race"},
           {"date": "2026-01-02", "y": 46.0, "var": 1.0, "kind": "race"}]
    sym = filter_level(obs, "2026-01-03", 0.01)
    asym = filter_level(obs, "2026-01-03", 0.01, {"race": 4.0, "set": 4.0})
    assert asym["x"] > sym["x"]
