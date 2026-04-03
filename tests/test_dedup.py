"""Dedup 단위 테스트."""

import sqlite3
from src.db_setup import create_tables
from src.sync.dedup import run as run_dedup


def _conn_with_activities(activities):
    conn = sqlite3.connect(":memory:")
    create_tables(conn)
    for a in activities:
        conn.execute(
            "INSERT INTO activity_summaries (source, source_id, activity_type, start_time, distance_m) "
            "VALUES (?, ?, 'running', ?, ?)",
            (a["source"], a["source_id"], a["start_time"], a.get("distance_m")),
        )
    conn.commit()
    return conn


class TestDedup:
    def test_same_activity_different_sources(self):
        conn = _conn_with_activities([
            {"source": "garmin", "source_id": "g1", "start_time": "2026-04-01T08:00:00", "distance_m": 10000},
            {"source": "strava", "source_id": "s1", "start_time": "2026-04-01T08:01:00", "distance_m": 10050},
        ])
        groups = run_dedup(conn)
        assert groups == 1
        rows = conn.execute("SELECT matched_group_id FROM activity_summaries").fetchall()
        assert rows[0][0] == rows[1][0]
        assert rows[0][0] is not None

    def test_different_activities_not_grouped(self):
        conn = _conn_with_activities([
            {"source": "garmin", "source_id": "g1", "start_time": "2026-04-01T08:00:00", "distance_m": 10000},
            {"source": "strava", "source_id": "s1", "start_time": "2026-04-01T18:00:00", "distance_m": 5000},
        ])
        groups = run_dedup(conn)
        assert groups == 0

    def test_same_source_not_grouped(self):
        conn = _conn_with_activities([
            {"source": "garmin", "source_id": "g1", "start_time": "2026-04-01T08:00:00", "distance_m": 10000},
            {"source": "garmin", "source_id": "g2", "start_time": "2026-04-01T08:01:00", "distance_m": 10050},
        ])
        groups = run_dedup(conn)
        assert groups == 0

    def test_distance_threshold_exceeded(self):
        conn = _conn_with_activities([
            {"source": "garmin", "source_id": "g1", "start_time": "2026-04-01T08:00:00", "distance_m": 10000},
            {"source": "strava", "source_id": "s1", "start_time": "2026-04-01T08:01:00", "distance_m": 15000},
        ])
        groups = run_dedup(conn)
        assert groups == 0

    def test_three_sources_same_activity(self):
        conn = _conn_with_activities([
            {"source": "garmin", "source_id": "g1", "start_time": "2026-04-01T08:00:00", "distance_m": 10000},
            {"source": "strava", "source_id": "s1", "start_time": "2026-04-01T08:01:00", "distance_m": 10020},
            {"source": "intervals", "source_id": "i1", "start_time": "2026-04-01T08:00:30", "distance_m": 10010},
        ])
        groups = run_dedup(conn)
        assert groups == 1
        gids = conn.execute("SELECT DISTINCT matched_group_id FROM activity_summaries WHERE matched_group_id IS NOT NULL").fetchall()
        assert len(gids) == 1

    def test_no_distance_falls_back_to_time(self):
        conn = _conn_with_activities([
            {"source": "garmin", "source_id": "g1", "start_time": "2026-04-01T08:00:00", "distance_m": None},
            {"source": "strava", "source_id": "s1", "start_time": "2026-04-01T08:02:00", "distance_m": None},
        ])
        groups = run_dedup(conn)
        assert groups == 1
