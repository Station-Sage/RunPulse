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
        "planned_workouts", "goals", "metric_store",
    }
    assert expected.issubset(tables)




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

    def test_schema_version_is_19(self):
        """조건 2 — v19: chat_messages.evidence_json 추가"""
        ver = self.conn.execute("PRAGMA user_version").fetchone()[0]
        assert ver == SCHEMA_VERSION
        assert ver == 19

    def test_pipeline_tables_count(self):
        """조건 3: pipeline 테이블 (daily_fitness 제거됨, ADR-005)"""
        tables = {r[0] for r in self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%'"
        ).fetchall()}
        pipeline = {
            "source_payloads", "activity_summaries", "daily_wellness",
            "metric_store", "activity_streams",
            "activity_laps", "activity_best_efforts", "gear",
            "weather_cache", "sync_jobs", "activity_groups", "milestones",
        }
        assert pipeline.issubset(tables), f"누락: {pipeline - tables}"
        assert "daily_fitness" not in tables, "daily_fitness가 삭제되지 않음 (ADR-005)"

    def test_app_tables_exist(self):
        """조건 3: 8개 앱 테이블 (D3: chat_threads/user_inputs/ai_feedback 추가)"""
        tables = {r[0] for r in self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        app = {"chat_messages", "goals", "planned_workouts",
               "user_training_prefs", "session_outcomes",
               "chat_threads", "user_inputs", "ai_feedback"}
        assert app.issubset(tables), f"누락: {app - tables}"

    def test_canonical_view_exists(self):
        """조건 3: v_canonical_activities 뷰"""
        views = {r[0] for r in self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='view'"
        ).fetchall()}
        assert "v_canonical_activities" in views

    def test_activity_summaries_38_columns(self):
        """조건 4: 38컬럼 (Phase 5-G: 6컬럼 → metric_store 이동)"""
        cols = self.conn.execute(
            "PRAGMA table_info(activity_summaries)"
        ).fetchall()
        assert len(cols) >= 38, f"컬럼 수: {len(cols)} (38개 이상 필요)"


def test_migrate_v18_adds_evidence_json():
    """구버전 chat_messages(evidence_json 없음)에서 migrate_db 후 컬럼이 생긴다."""
    conn = sqlite3.connect(":memory:")
    # v18 상태 시뮬레이션: 테이블 생성 후 user_version을 18로 고정
    create_tables(conn)
    conn.execute("PRAGMA user_version = 18")
    # evidence_json 컬럼 제거 시뮬레이션 — SQLite는 DROP COLUMN이 3.35+ 필요;
    # 대신 컬럼이 이미 없는 새 테이블로 재현: DROP + 구버전 스키마로 재생성
    conn.execute("DROP TABLE IF EXISTS chat_messages")
    conn.execute(
        "CREATE TABLE chat_messages ("
        "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "  role TEXT NOT NULL,"
        "  content TEXT NOT NULL,"
        "  chip_id TEXT,"
        "  ai_model TEXT,"
        "  thread_id INTEGER,"
        "  created_at TEXT NOT NULL DEFAULT (datetime('now'))"
        ")"
    )
    conn.commit()
    cols_before = {r[1] for r in conn.execute("PRAGMA table_info(chat_messages)").fetchall()}
    assert "evidence_json" not in cols_before

    migrate_db(conn)

    cols_after = {r[1] for r in conn.execute("PRAGMA table_info(chat_messages)").fetchall()}
    assert "evidence_json" in cols_after
    assert conn.execute("PRAGMA user_version").fetchone()[0] == 19
    conn.close()


def test_canonical_view_untouched_when_definition_unchanged(db_conn):
    """create_tables 재호출 시 정의가 같으면 뷰 DDL을 실행하지 않는다(schema_version 불변).

    before_request가 매 요청 migrate_db를 부르는데 그때마다 DROP VIEW하면 병렬 요청이 500.
    """
    before = db_conn.execute("PRAGMA schema_version").fetchone()[0]
    create_tables(db_conn)
    create_tables(db_conn)
    after = db_conn.execute("PRAGMA schema_version").fetchone()[0]
    assert after == before


def test_canonical_view_recreated_when_definition_differs(db_conn):
    """뷰 정의가 어긋나 있으면(구버전 등) 최신 정의로 복구한다."""
    db_conn.execute("DROP VIEW v_canonical_activities")
    db_conn.execute("CREATE VIEW v_canonical_activities AS SELECT 1 AS id")
    create_tables(db_conn)
    sql = db_conn.execute(
        "SELECT sql FROM sqlite_master WHERE name = 'v_canonical_activities'"
    ).fetchone()[0]
    assert "activity_summaries" in sql
    db_conn.execute("SELECT * FROM v_canonical_activities LIMIT 1")  # 조회 가능


def test_canonical_view_survives_concurrent_create_tables(tmp_path):
    """create_tables를 반복 호출하는 동안 다른 연결이 뷰를 계속 조회할 수 있다(회귀).

    앱은 WAL 모드라 리더가 라이터를 기다리지 않는다 — 옛 구현(매번 DROP VIEW→CREATE VIEW)은
    이 테스트에서 수 ms 안에 `no such table: v_canonical_activities`로 실패한다.
    """
    import threading
    import time

    db_file = tmp_path / "race.db"
    setup = sqlite3.connect(str(db_file))
    setup.execute("PRAGMA journal_mode=WAL")
    create_tables(setup)
    setup.close()

    errors: list[Exception] = []
    stop = threading.Event()

    def writer():
        conn = sqlite3.connect(str(db_file), timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")
        while not stop.is_set():
            try:
                create_tables(conn)
            except Exception as exc:  # 락 등 — 리더 검증과 무관
                errors.append(exc)
                break
        conn.close()

    t = threading.Thread(target=writer)
    t.start()
    try:
        reader = sqlite3.connect(str(db_file), timeout=10)
        deadline = time.monotonic() + 1.0
        while time.monotonic() < deadline:
            try:
                reader.execute("SELECT COUNT(*) FROM v_canonical_activities").fetchone()
            except sqlite3.OperationalError as exc:
                errors.append(exc)
                break
        reader.close()
    finally:
        stop.set()
        t.join()
    assert not errors, errors
