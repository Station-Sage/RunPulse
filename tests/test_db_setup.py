"""db_setup 테스트."""

from src.db_setup import create_tables, get_db_path


def test_get_db_path():
    """DB 경로가 running.db로 끝나는지 확인."""
    path = get_db_path()
    assert path.name == "running.db"


def test_create_tables(db_conn):
    """5개 테이블이 생성되는지 확인."""
    tables = {
        row[0]
        for row in db_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    expected = {"activities", "source_metrics", "daily_wellness", "planned_workouts", "goals"}
    assert expected.issubset(tables)


def test_activities_unique_index(db_conn):
    """activities 테이블의 source+source_id UNIQUE 인덱스 확인."""
    db_conn.execute(
        "INSERT INTO activities (source, source_id, start_time) VALUES ('garmin', '123', '2026-01-01T08:00:00')"
    )
    import sqlite3
    import pytest
    with pytest.raises(sqlite3.IntegrityError):
        db_conn.execute(
            "INSERT INTO activities (source, source_id, start_time) VALUES ('garmin', '123', '2026-01-01T09:00:00')"
        )


def test_activities_insert(db_conn):
    """activities 테이블에 데이터 삽입 확인."""
    db_conn.execute(
        """INSERT INTO activities (source, source_id, start_time, distance_km, duration_sec)
           VALUES ('strava', '456', '2026-03-18T07:00:00', 10.5, 3200)"""
    )
    row = db_conn.execute("SELECT distance_km, duration_sec FROM activities WHERE source_id='456'").fetchone()
    assert row == (10.5, 3200)
