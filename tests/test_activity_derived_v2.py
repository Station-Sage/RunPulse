"""tests/test_activity_derived_v2.py — 1-3 활동 파생 수치(UX 리뷰 20 design S1): RE·디커플링·스트림 헬퍼."""
from __future__ import annotations

import sqlite3

from src.db_setup import create_tables
from src.metrics.base import CalcContext
from src.metrics.decoupling import AerobicDecouplingCalculator
from src.metrics.relative_effort import RelativeEffortCalculator
from src.metrics.stream_utils import moving_segments, sample_times


def _conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    create_tables(c)
    return c


def _act(conn, sid="1", day="2026-09-20", **kw):
    d = {"source": "garmin", "source_id": sid, "name": "Run", "activity_type": "running",
         "start_time": f"{day} 08:00:00", "distance_m": 8000, "moving_time_sec": 3000,
         "duration_sec": 3000, "avg_hr": 140, "max_hr": 150}
    d.update(kw)
    conn.execute(f"INSERT INTO activity_summaries ({', '.join(d)}) VALUES ({', '.join('?' * len(d))})",
                 list(d.values()))
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def _streams(conn, aid, rows):
    conn.executemany(
        "INSERT INTO activity_streams (activity_id, source, elapsed_sec, distance_m, speed_ms, heart_rate)"
        " VALUES (?, 'garmin', ?, ?, ?, ?)", [(aid, *r) for r in rows])


def _re(conn, aid):
    return RelativeEffortCalculator().compute(CalcContext(conn=conn, scope_type="activity", scope_id=str(aid)))


def test_easy_run_re_uses_athlete_max_not_activity_max():
    """이지런(평균 140 / 활동 최대 150 = 0.93)이 Z5로 잡혀 RE가 부풀던 결함 — 선수 최대 190 기준이면 Z3."""
    conn = _conn()
    _act(conn, sid="race", day="2026-09-01", max_hr=190)
    aid = _act(conn)
    r = _re(conn, aid)[0]
    assert r.numeric_value == 100.0  # 50분 × Z3 계수 2.0
    assert r.confidence == 0.6


def test_re_integrates_stream_zones():
    conn = _conn()
    _act(conn, sid="race", day="2026-09-01", max_hr=200)
    aid = _act(conn, moving_time_sec=1200, duration_sec=1200)
    # 10분 Z2(130/200=0.65) + 10분 Z4(170/200=0.85)
    rows = [(t, t * 3.0, 3.0, 130 if t < 600 else 170) for t in range(0, 1201)]
    _streams(conn, aid, rows)
    r = _re(conn, aid)[0]
    assert r.confidence == 0.85
    assert abs(r.numeric_value - (10 * 1.0 + 10 * 3.5)) < 0.2


def test_moving_segments_drop_stops_and_rescale_index_elapsed():
    rows = [{"elapsed_sec": i, "distance_m": d, "speed_ms": s, "heart_rate": 150}
            for i, (d, s) in enumerate([(0, 3), (3, 3), (3, 0.0), (3, 0.0), (6, 3)])]
    assert sample_times(rows, 40) == [0, 10, 20, 30, 40]  # 인덱스 저장 → 총 시간 비례
    segs = moving_segments(rows, 40)
    assert len(segs) == 2


def test_decoupling_excludes_warmup_and_stops():
    """첫 10분 워밍업(낮은 심박)과 중간 정지를 빼면 일정한 주행은 디커플링 ≈ 0."""
    conn = _conn()
    aid = _act(conn, moving_time_sec=3600, duration_sec=3900, elapsed_time_sec=3900)
    rows, d = [], 0.0
    for t in range(0, 3901):
        stopped = 2000 <= t < 2300
        speed = 0.0 if stopped else 3.0
        d += speed
        hr = 120 if t < 600 else 150
        rows.append((t, d, speed, hr))
    _streams(conn, aid, rows)
    r = AerobicDecouplingCalculator().compute(CalcContext(conn=conn, scope_type="activity", scope_id=str(aid)))
    assert len(r) == 1 and abs(r[0].numeric_value) < 0.5


def test_activity_vdot_and_low_confidence_re_hidden():
    from src.metrics.display_rules import visible_activity_metrics
    rows = [{"metric_name": "workout_type_classified", "text_value": "easy"},
            {"metric_name": "runpulse_vdot", "numeric_value": 38.0},
            {"metric_name": "relative_effort", "numeric_value": 250.0, "confidence": 0.6}]
    assert [r["metric_name"] for r in visible_activity_metrics(rows)] == ["workout_type_classified"]
    rows[0]["text_value"] = "race"
    rows[2]["confidence"] = 0.85
    assert len(visible_activity_metrics(rows)) == 3


def test_te_bands_follow_garmin_scale():
    from src.metrics.bands import grade
    assert grade("training_effect_aerobic", 2.5)["label"] == "유지"
    assert grade("training_effect_aerobic", 3.4)["status"] == "good"
    assert grade("training_effect_aerobic", 5.0)["status"] == "caution"


def test_gap_uphill_is_faster_than_actual_pace():
    """5% 오르막 1km를 5:00에 → Minetti 비용 배수 1.30 → GAP 약 3:50(v1은 나눠서 5:00보다 느려졌다).
    설계서 예시 4:25는 경험 모델(Strava식) 값 — 모델 선택은 실데이터 Garmin GAP 비교로 별도 판단."""
    from src.metrics.gap import GAPCalculator
    conn = _conn()
    aid = _act(conn, distance_m=1000, moving_time_sec=300, duration_sec=300, elapsed_time_sec=300)
    v = 1000 / 300
    _streams_alt = [(aid, t, t * v, v, 150, t * v * 0.05) for t in range(301)]
    conn.executemany(
        "INSERT INTO activity_streams (activity_id, source, elapsed_sec, distance_m, speed_ms, heart_rate, altitude_m)"
        " VALUES (?, 'garmin', ?, ?, ?, ?, ?)", _streams_alt)
    r = GAPCalculator().compute(CalcContext(conn=conn, scope_type="activity", scope_id=str(aid)))
    assert abs(r[0].numeric_value - 230.5) <= 3, r[0].numeric_value


def test_gap_without_elevation_is_empty():
    from src.metrics.gap import GAPCalculator
    conn = _conn()
    aid = _act(conn)
    _streams(conn, aid, [(t, t * 3.0, 3.0, 150) for t in range(3001)])
    assert GAPCalculator().compute(CalcContext(conn=conn, scope_type="activity", scope_id=str(aid))) == []
