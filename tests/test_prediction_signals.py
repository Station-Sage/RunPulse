"""P7-PRED-22: 예측 신호(순수)."""
from src.metrics.prediction import signals as sg
from src.metrics.prediction.core import vdot_at_15c


def _run(**k):
    base = {"id": 1, "date": "2026-08-01", "is_race": True, "nominal_m": 10000.0, "avg_hr": 176, "perf_time_s": 2700,
            "activity_type": "running", "ambient_c": 25.0, "effort": None, "official_time_s": None,
            "distance_m": 10000.0, "moving_s": 2700, "laps": []}
    base.update(k)
    return base


def test_allout_rules():
    as_of = "2026-09-26"
    assert len(sg.allout_races([_run()], as_of, 190.0, -0.62, -0.84)) == 1           # 176 ≥ 0.84×190
    assert sg.allout_races([_run(avg_hr=150)], as_of, 190.0, -0.62, -0.84) == []      # HR 미달
    assert len(sg.allout_races([_run(avg_hr=None)], as_of, 190.0, -0.62, -0.84)) == 1  # 대회 HR 없음(T0) → 전력 간주
    assert len(sg.allout_races([_run(avg_hr=150)], as_of, None, -0.62, -0.84)) == 1    # HRmax 없음(T0) → 전력 간주
    assert len(sg.allout_races([_run(avg_hr=150, effort="allout")], as_of, 190.0, -0.62, -0.84)) == 1
    assert sg.allout_races([_run(effort="fun")], as_of, 190.0, -0.62, -0.84) == []
    r = sg.allout_races([_run(effort="allout", official_time_s=2690)], as_of, 190.0, -0.62, -0.84)[0]
    assert r["time_s"] == 2690 and r["vdot15"] == vdot_at_15c(10000.0, 2690, 25.0, -0.62, -0.84) and r["weeks"] == 8.0
    assert sg.allout_races([_run(date="2025-09-01")], as_of, 190.0, -0.62, -0.84) == []  # 52주 초과


def test_tanda_inputs():
    runs = [_run(is_race=False, date="2026-09-20", distance_m=30000.0, moving_s=9900),
            _run(is_race=False, date="2026-09-10", distance_m=10000.0, moving_s=3300)]
    km_w, pace, long28 = sg.tanda_inputs(runs, "2026-09-26")
    assert (km_w, pace, long28) == (5.0, 330.0, 1)


def test_spread_pct():
    assert sg.spread_pct([45.0], 10000.0) == 0.0
    assert round(sg.spread_pct([44.0, 46.0], 10000.0), 1) == 3.7        # (느린−빠른)/ts[n//2]
