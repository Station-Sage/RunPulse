"""db_setup 테스트."""

import sqlite3
import pytest

from src.db_setup import create_tables, get_db_path, migrate_db


def test_get_db_path():
    """DB 경로가 running.db로 끝나는지 확인."""
    path = get_db_path()
    assert path.name == "running.db"


def test_create_tables(db_conn):
    """6개 테이블이 생성되는지 확인 (daily_fitness 포함)."""
    tables = {
        row[0]
        for row in db_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    expected = {
        "activity_summaries", "activity_detail_metrics", "daily_wellness",
        "planned_workouts", "goals", "daily_fitness", "daily_detail_metrics",
    }
    assert expected.issubset(tables)


def test_daily_fitness_unique_constraint(db_conn):
    """daily_fitness (date, source) UNIQUE 제약 확인."""
    db_conn.execute(
        "INSERT INTO daily_fitness (date, source, ctl) VALUES ('2026-01-01', 'intervals', 50.0)"
    )
    with pytest.raises(sqlite3.IntegrityError):
        db_conn.execute(
            "INSERT INTO daily_fitness (date, source, ctl) VALUES ('2026-01-01', 'intervals', 55.0)"
        )


def test_planned_workouts_new_columns(db_conn):
    """planned_workouts에 source, ai_model, garmin_workout_id 컬럼 존재 확인."""
    db_conn.execute("""
        INSERT INTO planned_workouts (date, workout_type, source, ai_model, garmin_workout_id)
        VALUES ('2026-01-01', 'easy', 'ai_genspark', 'genspark', 'gw_123')
    """)
    row = db_conn.execute(
        "SELECT source, ai_model, garmin_workout_id FROM planned_workouts"
    ).fetchone()
    assert row == ("ai_genspark", "genspark", "gw_123")


def test_migrate_db_idempotent(db_conn):
    """migrate_db()를 여러 번 실행해도 오류 없음."""
    migrate_db(db_conn)
    migrate_db(db_conn)  # 두 번째 실행도 안전해야 함


def test_migrate_db_adds_daily_fitness(db_conn):
    """migrate_db()가 daily_fitness 테이블을 생성."""
    # db_conn에는 이미 create_tables가 실행됨. migrate_db는 幂等.
    migrate_db(db_conn)
    tables = {row[0] for row in db_conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    assert "daily_fitness" in tables


def test_activities_unique_index(db_conn):
    """activities 테이블의 source+source_id UNIQUE 인덱스 확인."""
    db_conn.execute(
        "INSERT INTO activity_summaries (source, source_id, start_time) VALUES ('garmin', '123', '2026-01-01T08:00:00')"
    )
    import sqlite3
    import pytest
    with pytest.raises(sqlite3.IntegrityError):
        db_conn.execute(
            "INSERT INTO activity_summaries (source, source_id, start_time) VALUES ('garmin', '123', '2026-01-01T09:00:00')"
        )


def test_activities_insert(db_conn):
    """activities 테이블에 데이터 삽입 확인."""
    db_conn.execute(
        """INSERT INTO activity_summaries (source, source_id, start_time, distance_km, duration_sec)
           VALUES ('strava', '456', '2026-03-18T07:00:00', 10.5, 3200)"""
    )
    row = db_conn.execute("SELECT distance_km, duration_sec FROM activity_summaries WHERE source_id='456'").fetchone()
    assert row == (10.5, 3200)
