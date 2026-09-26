"""P7-PRED-13: 제자리 재추출 — id 유지, 랩 GAP·스트림 경과시간 채움."""
import json

from src.sync.reextract import reextract_laps_streams
from tests.helpers_pred import mem_conn, seed_run

SPLITS = {"lapDTOs": [
    {"duration": 300.0, "distance": 1000.0, "averageHR": 150, "averageSpeed": 3.333, "intensityType": "WARMUP",
     "avgGradeAdjustedSpeed": 3.40, "elapsedDuration": 305.0, "movingDuration": 300.0, "elevationLoss": 2.0},
    {"duration": 240.0, "distance": 1000.0, "averageHR": 172, "averageSpeed": 4.167, "intensityType": "ACTIVE",
     "avgGradeAdjustedSpeed": 4.20}]}
STREAMS = {"metricDescriptors": [{"key": "sumElapsedDuration", "metricsIndex": 0},
                                 {"key": "sumDistance", "metricsIndex": 1},
                                 {"key": "directGradeAdjustedSpeed", "metricsIndex": 2},
                                 {"key": "directHeartRate", "metricsIndex": 3}],
           "activityDetailMetrics": [{"metrics": [0.0, 0.0, 3.0, 120]}, {"metrics": [5.2, 16.0, 3.1, 125]},
                                     {"metrics": [10.4, 32.5, 3.2, 130]}]}


def _payload(c, et, sid, obj):
    c.execute("INSERT INTO source_payloads (source, entity_type, entity_id, payload) VALUES ('garmin', ?, ?, ?)",
              (et, sid, json.dumps(obj)))


def test_reextract_keeps_ids_and_fills_fields():
    c = mem_conn()
    seed_run(c, sid="999")                       # id 1: payload 없음(Strava 전용 등) — 그대로 남아야 함
    aid = seed_run(c, sid="12345")
    _payload(c, "activity_splits", "12345", SPLITS)
    _payload(c, "activity_streams", "12345", STREAMS)
    st = reextract_laps_streams(c)
    assert st == {"activities": 1, "laps": 2, "streams": 3, "metrics": 0, "missing_payload": 1, "errors": 0}
    laps = c.execute("SELECT lap_index, gap_speed_ms, elapsed_duration_sec, lap_trigger FROM activity_laps "
                     "WHERE activity_id=? ORDER BY lap_index", (aid,)).fetchall()
    assert laps[0][1:] == (3.40, 305.0, "WARMUP") and laps[1][1] == 4.20
    s = c.execute("SELECT elapsed_sec, distance_m, gap_speed_ms FROM activity_streams WHERE activity_id=? "
                  "ORDER BY elapsed_sec", (aid,)).fetchall()
    assert [r[0] for r in s] == [0, 5, 10] and s[2][1:] == (32.5, 3.2)
    assert c.execute("SELECT count(*) FROM activity_summaries").fetchone()[0] == 2


def test_activity_metrics_reextracted():
    c = mem_conn()
    aid = seed_run(c, sid="7")
    _payload(c, "activity_summary", "7", {"avgGradeAdjustedSpeed": 3.137})
    _payload(c, "activity_splits", "7", SPLITS)
    assert reextract_laps_streams(c)["metrics"] == 1
    r = c.execute("SELECT numeric_value FROM metric_store WHERE scope_id=? AND metric_name='gap' AND provider='garmin'",
                  (str(aid),)).fetchone()
    assert r[0] == 318.8


def test_dry_run_writes_nothing():
    c = mem_conn()
    seed_run(c, sid="1")
    _payload(c, "activity_splits", "1", SPLITS)
    assert reextract_laps_streams(c, dry_run=True)["laps"] == 2
    assert c.execute("SELECT count(*) FROM activity_laps").fetchone()[0] == 0


def test_orphan_guard_blocks_destructive_reprocess():
    import pytest
    from src.sync.reextract import orphan_activity_count
    from src.sync.reprocess import reprocess_all
    c = mem_conn()
    seed_run(c, sid="no_payload")                 # payload 없는 활동(Strava 등)
    assert orphan_activity_count(c) == 1
    with pytest.raises(RuntimeError):
        reprocess_all(c)
    assert c.execute("SELECT count(*) FROM activity_summaries").fetchone()[0] == 1
