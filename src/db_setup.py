"""SQLite 데이터베이스 초기화 및 스키마 생성."""

import sqlite3
from pathlib import Path


def get_db_path() -> Path:
    """프로젝트 루트의 running.db 경로 반환."""
    return Path(__file__).resolve().parent.parent / "running.db"


def create_tables(conn: sqlite3.Connection) -> None:
    """6개 테이블 생성 (IF NOT EXISTS)."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL CHECK(source IN ('garmin', 'strava', 'intervals', 'runalyze')),
            source_id TEXT NOT NULL,
            activity_type TEXT NOT NULL DEFAULT 'running',
            start_time TEXT NOT NULL,
            distance_km REAL,
            duration_sec INTEGER,
            avg_pace_sec_km INTEGER,
            avg_hr INTEGER,
            max_hr INTEGER,
            avg_cadence INTEGER,
            elevation_gain REAL,
            calories INTEGER,
            description TEXT,
            matched_group_id TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_activities_source
            ON activities(source, source_id);

        CREATE INDEX IF NOT EXISTS idx_activities_start_time
            ON activities(start_time);
        CREATE INDEX IF NOT EXISTS idx_activities_group
            ON activities(matched_group_id);


        CREATE TABLE IF NOT EXISTS source_payloads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            activity_id INTEGER,
            payload_json TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(source, entity_type, entity_id)
        );

        CREATE INDEX IF NOT EXISTS idx_source_payloads_lookup
            ON source_payloads(source, entity_type, entity_id);

        CREATE TABLE IF NOT EXISTS source_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            activity_id INTEGER NOT NULL REFERENCES activities(id),
            source TEXT NOT NULL,
            metric_name TEXT NOT NULL,
            metric_value REAL,
            metric_json TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_source_metrics_activity
            ON source_metrics(activity_id);

        CREATE TABLE IF NOT EXISTS daily_wellness (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            source TEXT NOT NULL,
            sleep_score REAL,
            sleep_hours REAL,
            hrv_value REAL,
            resting_hr INTEGER,
            body_battery INTEGER,
            stress_avg INTEGER,
            readiness_score REAL
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_wellness_date_source
            ON daily_wellness(date, source);

        CREATE TABLE IF NOT EXISTS daily_fitness (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            source TEXT NOT NULL,
            ctl REAL,
            atl REAL,
            tsb REAL,
            ramp_rate REAL,
            garmin_vo2max REAL,
            runalyze_evo2max REAL,
            runalyze_vdot REAL,
            runalyze_marathon_shape REAL,
            updated_at TEXT DEFAULT (datetime('now')),
            UNIQUE(date, source)
        );

        CREATE INDEX IF NOT EXISTS idx_daily_fitness_date
            ON daily_fitness(date);

        CREATE TABLE IF NOT EXISTS planned_workouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            workout_type TEXT NOT NULL CHECK(workout_type IN ('easy', 'tempo', 'interval', 'long', 'rest')),
            distance_km REAL,
            target_pace_min INTEGER,
            target_pace_max INTEGER,
            target_hr_zone INTEGER,
            description TEXT,
            rationale TEXT,
            completed INTEGER NOT NULL DEFAULT 0,
            matched_activity_id INTEGER REFERENCES activities(id),
            source TEXT DEFAULT 'manual',
            ai_model TEXT,
            garmin_workout_id TEXT
        );

        CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            race_date TEXT,
            distance_km REAL NOT NULL,
            target_time_sec INTEGER,
            target_pace_sec_km INTEGER,
            status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'completed', 'cancelled')),
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
    """)


def migrate_db(conn: sqlite3.Connection) -> None:
    """기존 DB에 새 테이블/컬럼을 안전하게 추가.

    이미 존재하는 컬럼이나 테이블은 건너뛴다.
    """
    # daily_fitness 테이블 (IF NOT EXISTS이므로 안전)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS daily_fitness (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            source TEXT NOT NULL,
            ctl REAL,
            atl REAL,
            tsb REAL,
            ramp_rate REAL,
            garmin_vo2max REAL,
            runalyze_evo2max REAL,
            runalyze_vdot REAL,
            runalyze_marathon_shape REAL,
            updated_at TEXT DEFAULT (datetime('now')),
            UNIQUE(date, source)
        );
        CREATE INDEX IF NOT EXISTS idx_daily_fitness_date
            ON daily_fitness(date);
    """)

    # planned_workouts 새 컬럼 (SQLite ALTER TABLE은 IF NOT EXISTS 미지원 → try/except)
    new_columns = [
        "ALTER TABLE planned_workouts ADD COLUMN source TEXT DEFAULT 'manual'",
        "ALTER TABLE planned_workouts ADD COLUMN ai_model TEXT",
        "ALTER TABLE planned_workouts ADD COLUMN garmin_workout_id TEXT",
    ]
    for stmt in new_columns:
        try:
            conn.execute(stmt)
        except sqlite3.OperationalError:
            pass  # 이미 존재하는 컬럼

    conn.commit()


def init_db() -> Path:
    """DB 초기화: 테이블 생성, 마이그레이션, WAL 모드 설정. DB 경로 반환."""
    db_path = get_db_path()
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        create_tables(conn)
        migrate_db(conn)
    return db_path


def main() -> None:
    """CLI 진입점."""
    db_path = init_db()
    print(f"DB 초기화 완료: {db_path}")

    with sqlite3.connect(db_path) as conn:
        tables = [
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
        ]
    print(f"테이블: {', '.join(tables)}")


if __name__ == "__main__":
    main()
