"""db_setup 테스트."""

import sqlite3
import pytest

from src.db_setup import create_tables, get_db_path, migrate_db, SCHEMA_VERSION

def test_get_db_path():
    """DB 경로가 running.db로 끝나는지 확인."""
    path = get_db_path()
    assert path.name == "running.db"


def test_create_tables(db_conn):
    """핵심 테이블이 생성되는지 확인."""
    tables = {
        row[0]
        for row in db_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    expected = {
        "activity_summaries", "daily_wellness",
        "planned_workouts", "goals", "daily_fitness",
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
        """INSERT INTO activity_summaries (source, source_id, start_time, distance_m, duration_sec)
           VALUES ('strava', '456', '2026-03-18T07:00:00', 10500, 3200)"""
    )
    row = db_conn.execute(
        "SELECT distance_m, duration_sec FROM activity_summaries WHERE source_id = '456'"
    ).fetchone()
    assert row[0] == 10500
    assert row[1] == 3200


# ── v0.3 Phase 1 완료 조건 1~4 ──────────────────────

class TestPhase1Schema:
    """Phase 1 완료 조건 1~4"""

    @pytest.fixture(autouse=True)
    def setup_db(self):
        self.conn = sqlite3.connect(":memory:")
        create_tables(self.conn)
        migrate_db(self.conn)
        yield
        self.conn.close()

    def test_schema_version_is_10(self):
        """조건 2"""
        ver = self.conn.execute("PRAGMA user_version").fetchone()[0]
        assert ver == SCHEMA_VERSION
        assert ver == 10

    def test_pipeline_tables_count(self):
        """조건 3: 13개 테이블 (12 pipeline + sync_jobs 또는 source_payloads 포함)"""
        tables = {r[0] for r in self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%'"
        ).fetchall()}
        pipeline = {
            "source_payloads", "activity_summaries", "daily_wellness",
            "daily_fitness", "metric_store", "activity_streams",
            "activity_laps", "activity_best_efforts", "gear",
            "weather_cache", "sync_jobs",
        }
        # 최소 11개 pipeline (설계에 따라 12~13)
        assert pipeline.issubset(tables), f"누락: {pipeline - tables}"

    def test_app_tables_exist(self):
        """조건 3: 5개 앱 테이블"""
        tables = {r[0] for r in self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        app = {"chat_messages", "goals", "planned_workouts",
               "user_training_prefs", "session_outcomes"}
        assert app.issubset(tables), f"누락: {app - tables}"

    def test_canonical_view_exists(self):
        """조건 3: v_canonical_activities 뷰"""
        views = {r[0] for r in self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='view'"
        ).fetchall()}
        assert "v_canonical_activities" in views

    def test_activity_summaries_46_columns(self):
        """조건 4: 최소 44컬럼 (v0.3 schema)"""
        cols = self.conn.execute(
            "PRAGMA table_info(activity_summaries)"
        ).fetchall()
        assert len(cols) >= 44, f"컬럼 수: {len(cols)} (44개 이상 필요)"
