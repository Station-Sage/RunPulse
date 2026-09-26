"""P7-PRED-41: 훈련 반응 r4(세트 기반, 기기 불필요)."""
from src.metrics.prediction import response as rs


def _lap(d, s, it=None):
    return {"dist_m": d, "dur_s": s, "speed_ms": d / s, "hr": None, "max_hr": None, "itype": it}


def _run(i, date, laps, dist=8000.0, atype="running"):
    return {"id": i, "date": date, "is_race": False, "activity_type": atype, "distance_m": dist, "moving_s": 2400, "laps": laps}


TEMPO = [_lap(1000, 360), _lap(1000, 360)] + [_lap(1000, 270)] * 4 + [_lap(1000, 370)]
INTER = [_lap(2000, 720, "WARMUP")] + [_lap(1000, 250, "ACTIVE"), _lap(300, 150, "RECOVERY")] * 5 + [_lap(1500, 540, "COOLDOWN")]


def test_weekly_zone_minutes_and_summary():
    runs = [_run(1, "2026-09-24", TEMPO), _run(2, "2026-09-16", INTER), _run(3, "2026-09-15", TEMPO, atype="treadmill")]
    w = rs.weekly_zone_minutes(runs, "2026-09-26")
    assert w["T"][0] == 18.0 and w["I"][1] == 20.8 and w["sessions"][:2] == [1, 1]
    s = rs.summarize(w)
    assert s["quality_min_avg_8w"] == 4.8 and s["quality_sessions_avg_8w"] == 0.25 and s["quality_min_avg_prev_8w"] == 0.0


def test_set_trend_needs_4():
    runs = [_run(i, f"2026-09-{10 + i:02d}", TEMPO) for i in range(3)]
    assert rs.set_trend(runs, "2026-09-26")["slope_4w"] is None
    runs.append(_run(9, "2026-09-20", [_lap(1000, 360)] * 2 + [_lap(1000, 260)] * 4 + [_lap(1000, 370)]))
    t = rs.set_trend(runs, "2026-09-26")
    assert t["n"] == 4 and t["slope_4w"] > 0


def test_long_mp_km():
    long = _run(5, "2026-09-20", [_lap(1000, 300)] * 10 + [_lap(1000, 360)] * 10, dist=20000.0)
    assert rs.long_mp_km([long], "2026-09-26", 1000 / 300) == 10.0
