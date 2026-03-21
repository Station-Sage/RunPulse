"""SQLite 데이터베이스 초기화 및 스키마 생성."""

import sqlite3
from pathlib import Path


def get_db_path() -> Path:
    """프로젝트 루트의 running.db 경로 반환."""
    return Path(__file__).resolve().parent.parent / "running.db"


def create_tables(conn: sqlite3.Connection) -> None:
    """7개 테이블 생성 (IF NOT EXISTS)."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS activity_summaries (
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

        CREATE UNIQUE INDEX IF NOT EXISTS idx_activity_summaries_source
            ON activity_summaries(source, source_id);

        CREATE INDEX IF NOT EXISTS idx_activity_summaries_start_time
            ON activity_summaries(start_time);
        CREATE INDEX IF NOT EXISTS idx_activity_summaries_group
            ON activity_summaries(matched_group_id);


        CREATE TABLE IF NOT EXISTS raw_source_payloads (
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

        CREATE INDEX IF NOT EXISTS idx_raw_source_payloads_lookup
            ON raw_source_payloads(source, entity_type, entity_id);

        CREATE TABLE IF NOT EXISTS activity_detail_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            activity_id INTEGER NOT NULL REFERENCES activity_summaries(id),
            source TEXT NOT NULL,
            metric_name TEXT NOT NULL,
            metric_value REAL,
            metric_json TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_activity_detail_metrics_activity
            ON activity_detail_metrics(activity_id);

        CREATE TABLE IF NOT EXISTS daily_wellness (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            source TEXT NOT NULL,
            sleep_score REAL,
            sleep_hours REAL,
            hrv_value REAL,
            hrv_sdnn REAL,
            resting_hr INTEGER,
            avg_sleeping_hr REAL,
            body_battery INTEGER,
            stress_avg INTEGER,
            readiness_score REAL,
            fatigue REAL,
            mood REAL,
            motivation REAL,
            steps INTEGER,
            weight_kg REAL
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

        CREATE TABLE IF NOT EXISTS daily_detail_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            source TEXT NOT NULL,
            metric_name TEXT NOT NULL,
            metric_value REAL,
            metric_json TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(date, source, metric_name)
        );

        CREATE INDEX IF NOT EXISTS idx_daily_detail_metrics_lookup
            ON daily_detail_metrics(date, source);

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
            matched_activity_id INTEGER REFERENCES activity_summaries(id),
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

        CREATE TABLE IF NOT EXISTS sync_jobs (
            id TEXT PRIMARY KEY,
            service TEXT NOT NULL,
            from_date TEXT NOT NULL,
            to_date TEXT NOT NULL,
            window_days INTEGER NOT NULL,
            current_from TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            completed_days INTEGER NOT NULL DEFAULT 0,
            total_days INTEGER NOT NULL,
            synced_count INTEGER NOT NULL DEFAULT 0,
            req_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            retry_after TEXT,
            last_error TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_sync_jobs_service
            ON sync_jobs(service, created_at);
    """)


def migrate_db(conn: sqlite3.Connection) -> None:
    """기존 DB에 새 테이블/컬럼을 안전하게 추가.

    이미 존재하는 컬럼이나 테이블은 건너뛴다.
    """
    existing_tables = {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }

    rename_statements = [
        ("activities", "activity_summaries"),
        ("source_payloads", "raw_source_payloads"),
        ("source_metrics", "activity_detail_metrics"),
    ]
    for old_name, new_name in rename_statements:
        if old_name in existing_tables and new_name not in existing_tables:
            conn.execute(f"ALTER TABLE {old_name} RENAME TO {new_name}")

    # rename 이후 테이블 목록 다시 읽기
    existing_tables = {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }

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

        CREATE TABLE IF NOT EXISTS daily_detail_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            source TEXT NOT NULL,
            metric_name TEXT NOT NULL,
            metric_value REAL,
            metric_json TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(date, source, metric_name)
        );
        CREATE INDEX IF NOT EXISTS idx_daily_detail_metrics_lookup
            ON daily_detail_metrics(date, source);
    """)

    # daily_wellness 새 컬럼 (SQLite ALTER TABLE은 IF NOT EXISTS 미지원 → try/except)
    daily_wellness_columns = [
        "ALTER TABLE daily_wellness ADD COLUMN hrv_sdnn REAL",
        "ALTER TABLE daily_wellness ADD COLUMN avg_sleeping_hr REAL",
        "ALTER TABLE daily_wellness ADD COLUMN fatigue REAL",
        "ALTER TABLE daily_wellness ADD COLUMN mood REAL",
        "ALTER TABLE daily_wellness ADD COLUMN motivation REAL",
        "ALTER TABLE daily_wellness ADD COLUMN steps INTEGER",
        "ALTER TABLE daily_wellness ADD COLUMN weight_kg REAL",
    ]
    for stmt in daily_wellness_columns:
        try:
            conn.execute(stmt)
        except sqlite3.OperationalError:
            pass  # 이미 존재하는 컬럼

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

    # activity_summaries 새 컬럼
    for stmt in [
        "ALTER TABLE activity_summaries ADD COLUMN avg_power REAL",
        "ALTER TABLE activity_summaries ADD COLUMN export_filename TEXT",
    ]:
        try:
            conn.execute(stmt)
        except sqlite3.OperationalError:
            pass  # 이미 존재

    # shoes 테이블 (Strava export)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS shoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL DEFAULT 'strava',
            brand TEXT,
            model TEXT,
            name TEXT,
            default_sport_types TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(source, brand, model)
        );
    """)

    # sync_jobs 테이블 (IF NOT EXISTS이므로 안전)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS sync_jobs (
            id TEXT PRIMARY KEY,
            service TEXT NOT NULL,
            from_date TEXT NOT NULL,
            to_date TEXT NOT NULL,
            window_days INTEGER NOT NULL,
            current_from TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            completed_days INTEGER NOT NULL DEFAULT 0,
            total_days INTEGER NOT NULL,
            synced_count INTEGER NOT NULL DEFAULT 0,
            req_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            retry_after TEXT,
            last_error TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_sync_jobs_service
            ON sync_jobs(service, created_at);
    """)

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
