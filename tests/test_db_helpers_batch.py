"""db_helpers batch 함수 테스트 (Phase 3 추가분)."""

import sqlite3
from src.db_setup import create_tables
from src.utils.db_helpers import (
    upsert_activity,
    upsert_laps_batch,
    upsert_streams_batch,
    upsert_best_efforts_batch,
)


def _conn():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    return c


def _insert_activity(conn, source="garmin", source_id="123"):
    return upsert_activity(conn, {
        "source": source, "source_id": source_id,
        "activity_type": "running", "start_time": "2026-04-01T08:00:00",
    })


class TestLapsBatch:
    def test_insert_laps(self):
        conn = _conn()
        aid = _insert_activity(conn)
        laps = [
            {"source": "garmin", "lap_index": 0, "duration_sec": 300, "distance_m": 1000},
            {"source": "garmin", "lap_index": 1, "duration_sec": 310, "distance_m": 1050},
        ]
        count = upsert_laps_batch(conn, aid, laps)
        assert count == 2
        rows = conn.execute("SELECT COUNT(*) FROM activity_laps WHERE activity_id = ?", (aid,)).fetchone()
        assert rows[0] == 2

    def test_upsert_laps_update(self):
        conn = _conn()
        aid = _insert_activity(conn)
        upsert_laps_batch(conn, aid, [{"source": "garmin", "lap_index": 0, "duration_sec": 300}])
        upsert_laps_batch(conn, aid, [{"source": "garmin", "lap_index": 0, "duration_sec": 350}])
        row = conn.execute("SELECT duration_sec FROM activity_laps WHERE activity_id = ?", (aid,)).fetchone()
        assert row[0] == 350

    def test_skip_no_lap_index(self):
        conn = _conn()
        aid = _insert_activity(conn)
        count = upsert_laps_batch(conn, aid, [{"source": "garmin", "duration_sec": 300}])
        assert count == 0


class TestStreamsBatch:
    def test_insert_streams(self):
        conn = _conn()
        aid = _insert_activity(conn)
        rows = [
            {"source": "garmin", "elapsed_sec": 0, "heart_rate": 120},
            {"source": "garmin", "elapsed_sec": 1, "heart_rate": 125},
        ]
        count = upsert_streams_batch(conn, aid, rows)
        assert count == 2

    def test_replace_on_reinsert(self):
        conn = _conn()
        aid = _insert_activity(conn)
        rows = [{"source": "garmin", "elapsed_sec": 0, "heart_rate": 120}]
        upsert_streams_batch(conn, aid, rows)
        upsert_streams_batch(conn, aid, [
            {"source": "garmin", "elapsed_sec": 0, "heart_rate": 130},
            {"source": "garmin", "elapsed_sec": 1, "heart_rate": 135},
        ])
        total = conn.execute("SELECT COUNT(*) FROM activity_streams WHERE activity_id = ?", (aid,)).fetchone()
        assert total[0] == 2  # DELETE + re-INSERT


class TestBestEffortsBatch:
    def test_insert_efforts(self):
        conn = _conn()
        aid = _insert_activity(conn)
        efforts = [
            {"source": "strava", "effort_name": "1k", "elapsed_sec": 240},
            {"source": "strava", "effort_name": "5k", "elapsed_sec": 1260},
        ]
        count = upsert_best_efforts_batch(conn, aid, efforts)
        assert count == 2

    def test_upsert_effort(self):
        conn = _conn()
        aid = _insert_activity(conn)
        upsert_best_efforts_batch(conn, aid, [{"source": "strava", "effort_name": "1k", "elapsed_sec": 240}])
        upsert_best_efforts_batch(conn, aid, [{"source": "strava", "effort_name": "1k", "elapsed_sec": 235}])
        row = conn.execute("SELECT elapsed_sec FROM activity_best_efforts WHERE effort_name = '1k'").fetchone()
        assert row[0] == 235

    def test_skip_no_effort_name(self):
        conn = _conn()
        aid = _insert_activity(conn)
        count = upsert_best_efforts_batch(conn, aid, [{"source": "strava", "elapsed_sec": 100}])
        assert count == 0
