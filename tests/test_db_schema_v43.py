"""v43 마이그레이션 — activity_streams.sample_idx (같은 초 샘플 보존)."""
import sqlite3

from src.db_schema_v43 import ensure_v43
from src.db_setup import SCHEMA_VERSION, create_tables
from src.sync.extractors.garmin_extractor import GarminExtractor
from src.utils.db_helpers import upsert_streams_batch


def _old_db():
    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE activity_streams (id INTEGER PRIMARY KEY AUTOINCREMENT, activity_id INTEGER NOT NULL,"
        " source TEXT NOT NULL, elapsed_sec INTEGER NOT NULL, distance_m REAL, heart_rate INTEGER,"
        " cadence INTEGER, power_watts REAL, altitude_m REAL, speed_ms REAL, latitude REAL, longitude REAL,"
        " grade_pct REAL, temperature_c REAL, created_at TEXT DEFAULT (datetime('now')), gap_speed_ms REAL,"
        " UNIQUE(activity_id, source, elapsed_sec))"
    )
    conn.execute("CREATE INDEX idx_streams_activity ON activity_streams(activity_id, source)")
    conn.execute("INSERT INTO activity_streams (activity_id, source, elapsed_sec, heart_rate, gap_speed_ms)"
                 " VALUES (1,'garmin',5,140,3.3)")
    return conn


def test_schema_version():
    assert SCHEMA_VERSION >= 43


def test_migration_preserves_rows_and_is_idempotent():
    conn = _old_db()
    ensure_v43(conn)
    ensure_v43(conn)
    row = conn.execute("SELECT activity_id, elapsed_sec, sample_idx, heart_rate, gap_speed_ms"
                       " FROM activity_streams").fetchall()
    assert row == [(1, 5, 0, 140, 3.3)]
    conn.execute("INSERT INTO activity_streams (activity_id, source, elapsed_sec, sample_idx)"
                 " VALUES (1,'garmin',5,1)")
    idx = [r[1] for r in conn.execute("PRAGMA index_list(activity_streams)")]
    assert "idx_streams_activity" in idx


def test_fresh_db_has_sample_idx():
    conn = sqlite3.connect(":memory:")
    create_tables(conn)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(activity_streams)")}
    assert "sample_idx" in cols


def test_same_second_samples_are_kept():
    conn = sqlite3.connect(":memory:")
    create_tables(conn)
    rows = [
        {"source": "garmin", "elapsed_sec": 10, "sample_idx": 0, "heart_rate": 150},
        {"source": "garmin", "elapsed_sec": 10, "sample_idx": 1, "heart_rate": 151},
    ]
    upsert_streams_batch(conn, 1, rows)
    assert conn.execute("SELECT COUNT(*) FROM activity_streams").fetchone()[0] == 2


def test_extractor_assigns_sample_idx():
    detail = {
        "metricDescriptors": [
            {"key": "directElapsedDuration", "metricsIndex": 0},
            {"key": "directHeartRate", "metricsIndex": 1},
        ],
        "activityDetailMetrics": [{"metrics": [10.2, 150]}, {"metrics": [10.4, 151]}, {"metrics": [12.0, 152]}],
    }
    out = GarminExtractor().extract_activity_streams(detail)
    assert [(r["elapsed_sec"], r["sample_idx"]) for r in out] == [(10, 0), (10, 1), (12, 0)]
