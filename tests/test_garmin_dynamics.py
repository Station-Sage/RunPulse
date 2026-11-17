"""v44 — Garmin 러닝 다이내믹스(스트림·랩) 컬럼. 키는 운영 계정 실응답(2026-11-17) 기준."""
import sqlite3

from src.db_schema_v44 import ensure_v44
from src.db_setup import create_tables
from src.sync.extractors.garmin_extractor import GarminExtractor
from src.utils.db_helpers import upsert_laps_batch, upsert_streams_batch

REAL_STREAM = {
    "metricDescriptors": [
        {"metricsIndex": 0, "key": "sumElapsedDuration"},
        {"metricsIndex": 1, "key": "directGroundContactTime"},
        {"metricsIndex": 2, "key": "directVerticalOscillation"},
        {"metricsIndex": 3, "key": "directStrideLength"},
        {"metricsIndex": 4, "key": "directVerticalRatio"},
        {"metricsIndex": 5, "key": "directBodyBattery"},
        {"metricsIndex": 6, "key": "directHeartRate"},
    ],
    "activityDetailMetrics": [{"metrics": [1.0, 251.0, 8.4, 112.5, 7.6, 61.0, 140.0]}],
}
REAL_LAP = {
    "lapDTOs": [{
        "lapIndex": 1, "startTimeGMT": "2026-11-04T01:00:00.0", "duration": 300.0, "distance": 1000.0,
        "averageSpeed": 3.3, "groundContactTime": 247.5, "verticalOscillation": 8.1,
        "strideLength": 110.2, "verticalRatio": 7.4, "normalizedPower": 231.0,
    }]
}


def test_stream_extracts_dynamics():
    row = GarminExtractor().extract_activity_streams(REAL_STREAM)[0]
    assert (row["ground_contact_ms"], row["vertical_osc_cm"], row["stride_length_cm"]) == (251.0, 8.4, 112.5)
    assert (row["vertical_ratio_pct"], row["body_battery"], row["heart_rate"]) == (7.6, 61.0, 140)


def test_lap_extracts_dynamics():
    lap = GarminExtractor().extract_activity_laps(REAL_LAP)[0]
    assert lap["avg_ground_contact_ms"] == 247.5
    assert lap["avg_stride_length_cm"] == 110.2
    assert lap["normalized_power"] == 231.0


def test_dynamics_persist_roundtrip():
    conn = sqlite3.connect(":memory:")
    create_tables(conn)
    ex = GarminExtractor()
    upsert_streams_batch(conn, 1, ex.extract_activity_streams(REAL_STREAM))
    upsert_laps_batch(conn, 1, ex.extract_activity_laps(REAL_LAP))
    assert conn.execute("SELECT ground_contact_ms, body_battery FROM activity_streams").fetchone() == (251.0, 61.0)
    assert conn.execute("SELECT avg_vertical_ratio_pct FROM activity_laps").fetchone() == (7.4,)


def test_ensure_v44_idempotent_on_old_tables():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE activity_streams (id INTEGER PRIMARY KEY, activity_id INTEGER)")
    conn.execute("CREATE TABLE activity_laps (id INTEGER PRIMARY KEY, activity_id INTEGER)")
    ensure_v44(conn)
    ensure_v44(conn)
    assert "respiration_rate" in {r[1] for r in conn.execute("PRAGMA table_info(activity_streams)")}
    assert "avg_ground_contact_ms" in {r[1] for r in conn.execute("PRAGMA table_info(activity_laps)")}
