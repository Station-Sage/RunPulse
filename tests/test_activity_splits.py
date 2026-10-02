"""activity_splits — 서버 스플릿·series 계산 테스트."""
from src.services.activity_splits import (
    build_series, compute_splits, cumulative_distance, series_step_m, stopped_flags,
)


def _run(km=5.0, pace=360, hr=140, stop=None):
    """1초 간격 등속 스트림. stop=(시작초, 길이초)면 그 구간은 정지."""
    speed = 1000 / pace
    out, dist, t = [], 0.0, 0
    total = int(km * pace)
    while t <= total + (stop[1] if stop else 0):
        stopped = stop and stop[0] <= t < stop[0] + stop[1]
        sp = 0.0 if stopped else speed
        out.append({"elapsed_sec": t, "distance_m": dist, "speed_ms": sp, "heart_rate": hr,
                    "altitude_m": 10.0 + (t % 7) * 0.1, "latitude": 37 + t * 1e-6, "longitude": 127.0})
        dist += sp
        t += 1
    return out


def test_splits_even_pace():
    s = compute_splits(_run(5.01, 360), 1800, 5010)
    assert len(s) == 5 and not any(x["partial"] for x in s)
    assert all(abs(x["pace_sec_km"] - 360) < 2 for x in s)
    assert s[0]["avg_hr"] == 140 and s[0]["stop_sec"] == 0


def test_splits_stop_excluded_from_pace():
    streams = _run(3.0, 360, stop=(500, 100))
    total_sec = streams[-1]["elapsed_sec"]
    s = compute_splits(streams, total_sec, 3000)
    stopped = [x for x in s if x["stop_sec"] > 0]
    assert stopped and sum(x["stop_sec"] for x in stopped) >= 95
    assert all(abs(x["pace_sec_km"] - 360) < 3 for x in s)
    assert sum(x["moving_sec"] for x in s) < total_sec - 90


def test_splits_partial_and_short():
    s = compute_splits(_run(2.4, 360), 864, 2400)
    assert [x["partial"] for x in s] == [False, False, True]
    assert s[-1]["dist_m"] == 400
    assert compute_splits(_run(0.9, 360), 324, 900) == []
    assert compute_splits([], 0, 0) == []


def test_cumulative_distance_integrates_speed_when_missing():
    streams = [{"elapsed_sec": i, "distance_m": None, "speed_ms": 3.0} for i in range(11)]
    d = cumulative_distance(streams, 10, 100)
    assert abs(d[-1] - 100) < 1e-6
    assert stopped_flags(streams, list(range(11)), d)[0] is False


def test_series_bounded_and_aligned():
    series = build_series(_run(42.0, 300, hr=150)[:: 1], 12600, 42000)
    n = len(series["dist_m"])
    assert n <= 601 and series["step_m"] in (70, 75)
    assert all(len(series[k]) == n for k in ("pace_sec_km", "hr", "alt_m", "lat", "lon"))
    assert abs(series["pace_sec_km"][n // 2] - 300) < 3


def test_series_none_without_distance():
    assert build_series([], 0, 0) is None
    assert series_step_m(5000) == 10


def test_detail_includes_splits_series_siblings(tmp_path):
    import sqlite3
    from src.db_setup import create_tables
    from src.services.activity_detail_service import get_activity_detail
    conn = sqlite3.connect(tmp_path / "t.db")
    create_tables(conn)
    conn.execute("INSERT INTO activity_summaries (id, source, source_id, activity_type, start_time,"
                 " distance_m, duration_sec, elapsed_time_sec) VALUES (1,'garmin','g1','running',"
                 "'2026-09-01T07:00:00',3010,1086,1086)")
    for s in _run(3.01, 360):
        conn.execute("INSERT INTO activity_streams (activity_id, source, elapsed_sec, distance_m, speed_ms,"
                     " heart_rate, altitude_m, latitude, longitude) VALUES (1,'garmin',?,?,?,?,?,?,?)",
                     (s["elapsed_sec"], s["distance_m"], s["speed_ms"], s["heart_rate"],
                      s["altitude_m"], s["latitude"], s["longitude"]))
    conn.commit()
    d = get_activity_detail(conn, 1)
    assert len(d["splits"]) == 3 and d["series"]["step_m"] == 10
    assert d["siblings"] == []
