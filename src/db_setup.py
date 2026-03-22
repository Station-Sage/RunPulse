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
            -- v0.2: 위치·날씨·FEARP 계산에 필요
            start_lat REAL,
            start_lon REAL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_activity_summaries_source
            ON activity_summaries(source, source_id);

        CREATE INDEX IF NOT EXISTS idx_activity_summaries_start_time
            ON activity_summaries(start_time);
        CREATE INDEX IF NOT EXISTS idx_activity_summaries_group
            ON activity_summaries(matched_group_id);
        CREATE INDEX IF NOT EXISTS idx_activity_summaries_group_time
            ON activity_summaries(matched_group_id, start_time DESC);


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
        CREATE INDEX IF NOT EXISTS idx_activity_detail_metrics_activity_source
            ON activity_detail_metrics(activity_id, source);

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
            workout_type TEXT NOT NULL CHECK(workout_type IN ('easy', 'tempo', 'interval', 'long', 'rest', 'recovery', 'race')),
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

        -- v0.2: 활동별 랩 스플릿 데이터 (DARP 페이스 전략, 분할 분석)
        CREATE TABLE IF NOT EXISTS activity_laps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            activity_id INTEGER NOT NULL REFERENCES activity_summaries(id) ON DELETE CASCADE,
            source TEXT NOT NULL,
            lap_index INTEGER NOT NULL,
            start_time TEXT,
            distance_km REAL,
            duration_sec INTEGER,
            avg_pace_sec_km INTEGER,
            avg_hr INTEGER,
            max_hr INTEGER,
            avg_cadence INTEGER,
            elevation_gain REAL,
            avg_power REAL,
            UNIQUE(activity_id, source, lap_index)
        );
        CREATE INDEX IF NOT EXISTS idx_activity_laps_activity
            ON activity_laps(activity_id);

        -- 분석용 정규화 뷰: 동일 활동 그룹에서 소스 우선순위(garmin>strava>intervals>runalyze)로
        -- 대표 1행만 반환. 중복 집계 방지. 분석 쿼리에서 activity_summaries 대신 이 뷰 사용.
        -- LEFT JOIN 패턴: 같은 그룹에서 우선순위가 더 높은(또는 같은 우선순위면 id 더 작은) 행이
        -- 존재하지 않는 행만 선택 → 상관 서브쿼리 없이 동일 결과.
        CREATE VIEW IF NOT EXISTS v_canonical_activities AS
        SELECT a.*
        FROM activity_summaries a
        LEFT JOIN activity_summaries b
            ON  b.matched_group_id = a.matched_group_id
            AND b.matched_group_id IS NOT NULL
            AND (
                CASE b.source WHEN 'garmin' THEN 1 WHEN 'strava' THEN 2
                              WHEN 'intervals' THEN 3 WHEN 'runalyze' THEN 4 ELSE 5 END
                < CASE a.source WHEN 'garmin' THEN 1 WHEN 'strava' THEN 2
                                WHEN 'intervals' THEN 3 WHEN 'runalyze' THEN 4 ELSE 5 END
                OR (
                    CASE b.source WHEN 'garmin' THEN 1 WHEN 'strava' THEN 2
                                  WHEN 'intervals' THEN 3 WHEN 'runalyze' THEN 4 ELSE 5 END
                    = CASE a.source WHEN 'garmin' THEN 1 WHEN 'strava' THEN 2
                                    WHEN 'intervals' THEN 3 WHEN 'runalyze' THEN 4 ELSE 5 END
                    AND b.id < a.id
                )
            )
        WHERE b.id IS NULL;

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

        -- v0.2: RunPulse 계산 메트릭 저장 (UTRS, CIRS, LSI, FEARP 등)
        -- activity_id NULL = 일별 범위, NOT NULL = 활동 범위
        CREATE TABLE IF NOT EXISTS computed_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            activity_id INTEGER REFERENCES activity_summaries(id),
            metric_name TEXT NOT NULL,
            metric_value REAL,
            metric_json TEXT,
            computed_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(date, activity_id, metric_name)
        );
        CREATE INDEX IF NOT EXISTS idx_computed_metrics_date
            ON computed_metrics(date);
        CREATE INDEX IF NOT EXISTS idx_computed_metrics_activity
            ON computed_metrics(activity_id, metric_name);

        -- v0.2: 날씨 데이터 캐시 (Open-Meteo, 무료)
        CREATE TABLE IF NOT EXISTS weather_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            hour INTEGER NOT NULL DEFAULT 12,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            temp_c REAL,
            feels_like_c REAL,
            humidity_pct INTEGER,
            wind_speed_ms REAL,
            precipitation_mm REAL,
            cloudcover_pct INTEGER,
            fetched_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(date, hour, latitude, longitude)
        );
        CREATE INDEX IF NOT EXISTS idx_weather_data_date
            ON weather_data(date, latitude, longitude);
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
        "ALTER TABLE activity_summaries ADD COLUMN workout_label TEXT",
        # v0.2: FEARP 날씨 조회용 위치
        "ALTER TABLE activity_summaries ADD COLUMN start_lat REAL",
        "ALTER TABLE activity_summaries ADD COLUMN start_lon REAL",
    ]:
        try:
            conn.execute(stmt)
        except sqlite3.OperationalError:
            pass  # 이미 존재

    # v_canonical_activities 뷰: 구 버전(상관 서브쿼리) 교체 → LEFT JOIN 패턴
    # DROP 후 재생성해야 구 버전이 남지 않는다.
    conn.executescript("""
        DROP VIEW IF EXISTS v_canonical_activities;
        CREATE VIEW IF NOT EXISTS v_canonical_activities AS
        SELECT a.*
        FROM activity_summaries a
        LEFT JOIN activity_summaries b
            ON  b.matched_group_id = a.matched_group_id
            AND b.matched_group_id IS NOT NULL
            AND (
                CASE b.source WHEN 'garmin' THEN 1 WHEN 'strava' THEN 2
                              WHEN 'intervals' THEN 3 WHEN 'runalyze' THEN 4 ELSE 5 END
                < CASE a.source WHEN 'garmin' THEN 1 WHEN 'strava' THEN 2
                                WHEN 'intervals' THEN 3 WHEN 'runalyze' THEN 4 ELSE 5 END
                OR (
                    CASE b.source WHEN 'garmin' THEN 1 WHEN 'strava' THEN 2
                                  WHEN 'intervals' THEN 3 WHEN 'runalyze' THEN 4 ELSE 5 END
                    = CASE a.source WHEN 'garmin' THEN 1 WHEN 'strava' THEN 2
                                    WHEN 'intervals' THEN 3 WHEN 'runalyze' THEN 4 ELSE 5 END
                    AND b.id < a.id
                )
            )
        WHERE b.id IS NULL;
    """)

    # 누락 인덱스 추가 (기존 DB 대응)
    for stmt in [
        "CREATE INDEX IF NOT EXISTS idx_activity_detail_metrics_activity_source ON activity_detail_metrics(activity_id, source)",
        "CREATE INDEX IF NOT EXISTS idx_activity_summaries_group_time ON activity_summaries(matched_group_id, start_time DESC)",
    ]:
        try:
            conn.execute(stmt)
        except sqlite3.OperationalError:
            pass

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

    # v0.2 신규 테이블 (IF NOT EXISTS이므로 안전)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS activity_laps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            activity_id INTEGER NOT NULL REFERENCES activity_summaries(id) ON DELETE CASCADE,
            source TEXT NOT NULL,
            lap_index INTEGER NOT NULL,
            start_time TEXT,
            distance_km REAL,
            duration_sec INTEGER,
            avg_pace_sec_km INTEGER,
            avg_hr INTEGER,
            max_hr INTEGER,
            avg_cadence INTEGER,
            elevation_gain REAL,
            avg_power REAL,
            UNIQUE(activity_id, source, lap_index)
        );
        CREATE INDEX IF NOT EXISTS idx_activity_laps_activity
            ON activity_laps(activity_id);

        CREATE TABLE IF NOT EXISTS computed_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            activity_id INTEGER REFERENCES activity_summaries(id),
            metric_name TEXT NOT NULL,
            metric_value REAL,
            metric_json TEXT,
            computed_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(date, activity_id, metric_name)
        );
        CREATE INDEX IF NOT EXISTS idx_computed_metrics_date
            ON computed_metrics(date);
        CREATE INDEX IF NOT EXISTS idx_computed_metrics_activity
            ON computed_metrics(activity_id, metric_name);

        CREATE TABLE IF NOT EXISTS weather_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            hour INTEGER NOT NULL DEFAULT 12,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            temp_c REAL,
            feels_like_c REAL,
            humidity_pct INTEGER,
            wind_speed_ms REAL,
            precipitation_mm REAL,
            cloudcover_pct INTEGER,
            fetched_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(date, hour, latitude, longitude)
        );
        CREATE INDEX IF NOT EXISTS idx_weather_data_date
            ON weather_data(date, latitude, longitude);
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
