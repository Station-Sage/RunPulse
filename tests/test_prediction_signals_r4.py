"""P7-PRED-22: 예측 관측 생성(순수, r4)."""
from src.metrics.prediction import signals_r4 as sg
from src.metrics.prediction.core_r4 import vdot_at_15c
from src.metrics.prediction.daniels import set_vdot


def _run(**k):
    base = {"id": 1, "date": "2026-08-01", "is_race": True, "nominal_m": 10000.0, "avg_hr": 176, "perf_time_s": 2700,
            "activity_type": "running", "ambient_c": 25.0, "effort": None, "official_time_s": None,
            "distance_m": 10000.0, "moving_s": 2700, "laps": []}
    base.update(k)
    return base


def _lap(d, s, hr=None, it=None, mx=None):
    return {"dist_m": d, "dur_s": s, "speed_ms": d / s, "hr": hr, "max_hr": mx, "itype": it}


def _interval(i, date, hr_peak=180):
    laps = [_lap(2000, 720, 130, "WARMUP")]
    for _ in range(5):
        laps += [_lap(1000, 250, 165, "ACTIVE", hr_peak), _lap(300, 150, 140, "RECOVERY")]
    laps += [_lap(1500, 540, 135, "COOLDOWN")]
    return _run(id=i, date=date, is_race=False, nominal_m=None, distance_m=11000.0, moving_s=4300, laps=laps)


def test_allout_rules():
    as_of = "2026-09-26"
    assert len(sg.allout_races([_run()], as_of, 190.0, -0.62, -0.84)) == 1
    assert sg.allout_races([_run(avg_hr=150)], as_of, 190.0, -0.62, -0.84) == []
    assert len(sg.allout_races([_run(avg_hr=None)], as_of, 190.0, -0.62, -0.84)) == 1      # T0
    assert len(sg.allout_races([_run(avg_hr=150)], as_of, None, -0.62, -0.84)) == 1
    assert sg.allout_races([_run(effort="fun")], as_of, 190.0, -0.62, -0.84) == []
    r = sg.allout_races([_run(effort="allout", official_time_s=2690)], as_of, 190.0, -0.62, -0.84)[0]
    assert r["time_s"] == 2690 and r["vdot15"] == vdot_at_15c(10000.0, 2690, 25.0, -0.62, -0.84) and r["day"] == -56
    assert sg.allout_races([_run(date="2025-09-01")], as_of, 190.0, -0.62, -0.84) == []


def test_set_observation_device_free():
    o = sg.set_obs(_interval(2, "2026-09-10"), 1000 / 360, None)              # HR·HRmax 없음(T0)
    assert o["kind"] == "I" and o["n"] == 5 and o["rho"] == 0.6 and o["var"] == 1.75 ** 2
    assert o["y"] == set_vdot("I", 4.0, 5, 0.6)
    low = sg.set_obs(_interval(3, "2026-09-10", hr_peak=165), 1000 / 360, 192.0)  # 후반 최대 HR 0.86·HRmax → 분산 증가
    assert low["var"] > o["var"] and low["hr_reach"] == 0.859
    assert sg.set_obs(_interval(4, "2026-09-10"), 1000 / 290, None) is None      # 이지 대비 1.16배 < 1.18 → 품질 아님


def test_observations_and_inputs():
    runs = [_run(id=1, date="2026-08-01"), _interval(2, "2026-09-10"),
            _run(id=3, is_race=False, nominal_m=None, date="2026-09-20", distance_m=30000.0, moving_s=9900)]
    obs = sg.observations(runs, "2026-09-26", sg.allout_races(runs, "2026-09-26", None, -0.62, -0.84), None)
    assert [o["kind"] for o in obs] == ["race", "I"]
    km_w, pace, long28 = sg.tanda_inputs(runs, "2026-09-26")
    assert (km_w, round(pace, 2), long28) == (6.375, 331.37, 1)
    assert sg.longest_run_m(runs, "2026-09-26") == 30000.0
