"""SQLite 데이터베이스 초기화 및 스키마 생성/마이그레이션.

마이그레이션 전략:
- PRAGMA user_version 으로 스키마 버전 추적
- 버전별 마이그레이션 함수 (_migrate_to_vN) 순차 실행
- 새 테이블: CREATE TABLE IF NOT EXISTS (기존 방식 유지)
- 새 컬럼: ALTER TABLE ADD COLUMN (user_version 기반 감지)
- 마이그레이션 실행 시 schema_meta.needs_resync = 1 설정
"""

import logging
import sqlite3
from pathlib import Path

log = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 기본 사용자 ID (싱글유저 하위호환)
DEFAULT_USER = "default"


def get_db_path(user_id: str | None = None) -> Path:
    """사용자별 running.db 경로 반환.

    - user_id=None 또는 "default": data/users/default/running.db
    - user_id="alice": data/users/alice/running.db
    """
    uid = user_id or DEFAULT_USER
    user_dir = _PROJECT_ROOT / "data" / "users" / uid
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir / "running.db"


def create_tables(conn: sqlite3.Connection) -> None:
    """7개 테이블 생성 (IF NOT EXISTS)."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS activity_summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL CHECK(source IN ('garmin', 'strava', 'intervals', 'runalyze')),
            source_id TEXT NOT NULL,
            name TEXT,
            activity_type TEXT NOT NULL DEFAULT 'running',
            sport_type TEXT,
            start_time TEXT NOT NULL,
            distance_km REAL,
            duration_sec INTEGER,
            moving_time_sec INTEGER,
            elapsed_time_sec INTEGER,
            avg_pace_sec_km INTEGER,
            avg_hr INTEGER,
            max_hr INTEGER,
            avg_cadence INTEGER,
            max_cadence INTEGER,
            elevation_gain REAL,
            elevation_loss REAL,
            min_elevation REAL,
            max_elevation REAL,
            max_vertical_speed REAL,
            calories INTEGER,
            bmr_calories INTEGER,
            description TEXT,
            avg_speed_ms REAL,
            max_speed_ms REAL,
            avg_grade_adjusted_speed REAL,
            avg_power REAL,
            max_power REAL,
            normalized_power REAL,
            avg_stride_length_cm REAL,
            avg_vertical_oscillation_cm REAL,
            avg_vertical_ratio_percent REAL,
            avg_ground_contact_time_ms INTEGER,
            avg_ground_contact_balance REAL,
            avg_double_cadence REAL,
            avg_fractional_cadence REAL,
            max_fractional_cadence REAL,
            aerobic_training_effect REAL,
            anaerobic_training_effect REAL,
            training_load REAL,
            vo2max_activity REAL,
            workout_label TEXT,
            steps INTEGER,
            lap_count INTEGER,
            start_lat REAL,
            start_lon REAL,
            end_lat REAL,
            end_lon REAL,
            min_lat REAL,
            max_lat REAL,
            min_lon REAL,
            max_lon REAL,
            avg_temperature REAL,
            min_temperature REAL,
            max_temperature REAL,
            body_battery_diff INTEGER,
            device_id TEXT,
            favorite INTEGER,
            water_estimated_ml INTEGER,
            moderate_intensity_min INTEGER,
            vigorous_intensity_min INTEGER,
            avg_hr_gap REAL,
            max_double_cadence REAL,
            export_filename TEXT,
            -- Strava specific
            suffer_score INTEGER,
            kudos_count INTEGER,
            achievement_count INTEGER,
            pr_count INTEGER,
            strava_gear_id TEXT,
            workout_type INTEGER,
            trainer INTEGER,
            commute INTEGER,
            -- intervals.icu specific
            icu_training_load REAL,
            icu_trimp REAL,
            icu_hrss REAL,
            icu_intensity REAL,
            icu_atl REAL,
            icu_ctl REAL,
            icu_tsb REAL,
            icu_gap REAL,
            icu_decoupling REAL,
            icu_efficiency_factor REAL,
            -- cross-service training quality metrics
            session_rpe REAL,
            strain_score REAL,
            polarization_index REAL,
            perceived_exertion REAL,
            event_type TEXT,
            matched_group_id TEXT,
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

        -- v0.3: AI 채팅 메시지 히스토리
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
            content TEXT NOT NULL,
            chip_id TEXT,
            ai_model TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        -- v0.2: 활동별 랩 스플릿 데이터 (DARP 페이스 전략, 분할 분석)
        CREATE TABLE IF NOT EXISTS activity_laps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            activity_id INTEGER NOT NULL REFERENCES activity_summaries(id) ON DELETE CASCADE,
            source TEXT NOT NULL,
            lap_index INTEGER NOT NULL,
            split_type TEXT,
            start_time TEXT,
            distance_km REAL,
            duration_sec INTEGER,
            moving_time_sec INTEGER,
            elapsed_time_sec INTEGER,
            avg_pace_sec_km INTEGER,
            avg_hr INTEGER,
            max_hr INTEGER,
            avg_cadence INTEGER,
            max_cadence INTEGER,
            elevation_gain REAL,
            total_ascent REAL,
            total_descent REAL,
            avg_speed_ms REAL,
            avg_moving_speed_ms REAL,
            max_speed_ms REAL,
            avg_power REAL,
            max_power REAL,
            normalized_power REAL,
            total_calories INTEGER,
            avg_temperature REAL,
            avg_stride_length_cm REAL,
            avg_vertical_oscillation_cm REAL,
            avg_vertical_ratio_pct REAL,
            avg_ground_contact_time_ms INTEGER,
            avg_grade_adjusted_speed_ms REAL,
            start_lat REAL,
            start_lon REAL,
            end_lat REAL,
            end_lon REAL,
            start_elevation REAL,
            UNIQUE(activity_id, source, lap_index)
        );
        CREATE INDEX IF NOT EXISTS idx_activity_laps_activity
            ON activity_laps(activity_id);

        -- v0.2: GPS/time-series 스트림 데이터
        CREATE TABLE IF NOT EXISTS activity_streams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            activity_id INTEGER NOT NULL REFERENCES activity_summaries(id) ON DELETE CASCADE,
            source TEXT NOT NULL,
            stream_type TEXT NOT NULL,
            data_json TEXT NOT NULL,
            original_size INTEGER,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(activity_id, source, stream_type)
        );
        CREATE INDEX IF NOT EXISTS idx_activity_streams_activity
            ON activity_streams(activity_id, source);

        -- v0.2: 베스트 에포트 (1K, 5K, 10K, 하프, 마라톤 등)
        CREATE TABLE IF NOT EXISTS activity_best_efforts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            activity_id INTEGER NOT NULL REFERENCES activity_summaries(id) ON DELETE CASCADE,
            source TEXT NOT NULL,
            name TEXT NOT NULL,
            distance_m REAL,
            elapsed_sec INTEGER,
            moving_sec INTEGER,
            start_index INTEGER,
            end_index INTEGER,
            pr_rank INTEGER,
            UNIQUE(activity_id, source, name)
        );
        CREATE INDEX IF NOT EXISTS idx_activity_best_efforts_activity
            ON activity_best_efforts(activity_id);

        -- v0.2: 선수 프로필 (소스별)
        CREATE TABLE IF NOT EXISTS athlete_profile (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL UNIQUE,
            source_athlete_id TEXT,
            firstname TEXT,
            lastname TEXT,
            city TEXT,
            country TEXT,
            sex TEXT,
            weight_kg REAL,
            birthday TEXT,
            ftp INTEGER,
            lthr INTEGER,
            vo2max REAL,
            profile_json TEXT,
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        -- v0.2: 누적 운동 통계 스냅샷 (날짜별)
        CREATE TABLE IF NOT EXISTS athlete_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            snapshot_date TEXT NOT NULL,
            all_run_count INTEGER,
            all_run_distance_km REAL,
            all_run_elapsed_sec INTEGER,
            all_run_elevation_m REAL,
            ytd_run_count INTEGER,
            ytd_run_distance_km REAL,
            ytd_run_elapsed_sec INTEGER,
            recent_run_count INTEGER,
            recent_run_distance_km REAL,
            stats_json TEXT,
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(source, snapshot_date)
        );
        CREATE INDEX IF NOT EXISTS idx_athlete_stats_date
            ON athlete_stats(source, snapshot_date DESC);

        -- v0.2: 기어 (신발, 자전거 등)
        CREATE TABLE IF NOT EXISTS gear (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            source_gear_id TEXT NOT NULL,
            name TEXT,
            brand TEXT,
            model TEXT,
            distance_m REAL,
            retired INTEGER DEFAULT 0,
            gear_type TEXT DEFAULT 'shoes',
            gear_json TEXT,
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(source, source_gear_id)
        );
        CREATE INDEX IF NOT EXISTS idx_gear_source
            ON gear(source, source_gear_id);

        -- v0.2: 운동 세트 (근력/수영/인터벌 등)
        CREATE TABLE IF NOT EXISTS activity_exercise_sets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            activity_id INTEGER NOT NULL REFERENCES activity_summaries(id) ON DELETE CASCADE,
            source TEXT NOT NULL,
            set_index INTEGER NOT NULL,
            exercise_name TEXT,
            exercise_category TEXT,
            set_type TEXT,
            reps INTEGER,
            weight_kg REAL,
            duration_sec INTEGER,
            distance_m REAL,
            UNIQUE(activity_id, source, set_index)
        );
        CREATE INDEX IF NOT EXISTS idx_activity_exercise_sets_activity
            ON activity_exercise_sets(activity_id);

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

        -- v3: 사용자 훈련 환경 설정 (싱글유저, id=1 고정)
        CREATE TABLE IF NOT EXISTS user_training_prefs (
            id                 INTEGER PRIMARY KEY DEFAULT 1 CHECK(id = 1),
            -- 정기 휴식 요일 비트마스크: bit0=월(1), bit1=화(2), ..., bit6=일(64)
            rest_weekdays_mask INTEGER NOT NULL DEFAULT 0,
            -- 일회성 차단 날짜 JSON 배열 ["2026-04-05", ...]
            blocked_dates      TEXT    NOT NULL DEFAULT '[]',
            -- 인터벌 기본 반복 거리(m): 자유 입력 (200~2000, 320 같은 비표준 포함)
            interval_rep_m     INTEGER NOT NULL DEFAULT 1000,
            -- 주간 최대 Q-day 수 (0=자동)
            max_q_days         INTEGER NOT NULL DEFAULT 0,
            updated_at         TEXT
        );

        -- v3: 훈련 세션 성과 기록 (ML 학습 데이터)
        -- 계획 vs 실제 비교 + 훈련 당시 컨디션 스냅샷
        CREATE TABLE IF NOT EXISTS session_outcomes (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            planned_id      INTEGER REFERENCES planned_workouts(id),
            activity_id     INTEGER REFERENCES activity_summaries(id),
            date            TEXT NOT NULL,
            -- 달성률 (Buchheit & Laursen 2013: 세션 볼륨 목표 대비)
            planned_dist_km REAL,
            actual_dist_km  REAL,
            dist_ratio      REAL,           -- actual/planned, 1.0=100%
            -- 페이스 편차 (Daniels 처방 대비)
            planned_pace    INTEGER,        -- sec/km
            actual_pace     INTEGER,        -- sec/km
            pace_delta_pct  REAL,           -- (actual-planned)/planned
            -- 심박 존 분포 (Seiler 2010 3존 기준)
            hr_z1_pct       REAL,           -- VT1 이하 비율
            hr_z2_pct       REAL,           -- VT1~VT2
            hr_z3_pct       REAL,           -- VT2 이상
            target_zone     INTEGER,        -- 계획 HR zone (1~5)
            actual_avg_hr   INTEGER,
            hr_delta        INTEGER,        -- actual_hr - target_hr
            -- 훈련 품질 (Friel 2012: decoupling 5% 기준)
            decoupling_pct  REAL,
            trimp           REAL,
            -- 컨디션 스냅샷 (훈련 시점 — ML 피처)
            crs_at_session  REAL,           -- 복합 준비도 점수
            tsb_at_session  REAL,           -- Coggan 2003
            hrv_at_session  REAL,           -- Plews 2013
            bb_at_session   INTEGER,        -- Body Battery
            acwr_at_session REAL,           -- Gabbett 2016
            -- ML 타겟 레이블
            outcome_label   TEXT CHECK(outcome_label IN (
                'on_target','overperformed','underperformed','skipped','modified'
            )),
            computed_at     TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_session_outcomes_date
            ON session_outcomes(date DESC);
        CREATE UNIQUE INDEX IF NOT EXISTS idx_session_outcomes_planned_id
            ON session_outcomes(planned_id);
        CREATE INDEX IF NOT EXISTS idx_session_outcomes_activity
            ON session_outcomes(activity_id);
    """)


# ── 스키마 버전 관리 ───────────────────────────────────────────────────────
# 새 마이그레이션 추가 시: SCHEMA_VERSION 증가 + _migrate_to_vN 함수 작성
SCHEMA_VERSION = 4  # display: 3.1


def _get_user_version(conn: sqlite3.Connection) -> int:
    """현재 DB의 user_version 반환."""
    row = conn.execute("PRAGMA user_version").fetchone()
    return int(row[0]) if row else 0


def _set_user_version(conn: sqlite3.Connection, version: int) -> None:
    """DB user_version 설정."""
    conn.execute(f"PRAGMA user_version = {int(version)}")


def _get_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    """테이블의 현재 컬럼명 집합 반환."""
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {row[1] for row in rows}


def _add_column_if_missing(
    conn: sqlite3.Connection,
    table: str,
    column: str,
    typedef: str,
) -> bool:
    """컬럼이 없으면 ALTER TABLE ADD COLUMN 실행. 추가했으면 True."""
    existing = _get_columns(conn, table)
    if column in existing:
        return False
    conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {typedef}")
    log.info("ALTER TABLE %s ADD COLUMN %s %s", table, column, typedef)
    return True


def _ensure_schema_meta(conn: sqlite3.Connection) -> None:
    """schema_meta 테이블 생성 (1행짜리 메타 테이블)."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_meta (
            id INTEGER PRIMARY KEY CHECK(id = 1),
            schema_version INTEGER NOT NULL DEFAULT 0,
            needs_resync INTEGER NOT NULL DEFAULT 0,
            migrated_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        INSERT OR IGNORE INTO schema_meta (id, schema_version, needs_resync)
        VALUES (1, 0, 0)
    """)


def _set_needs_resync(conn: sqlite3.Connection, value: bool = True) -> None:
    """재동기화 필요 플래그 설정."""
    _ensure_schema_meta(conn)
    conn.execute(
        "UPDATE schema_meta SET needs_resync = ?, migrated_at = datetime('now') WHERE id = 1",
        (1 if value else 0,),
    )


def get_needs_resync(conn: sqlite3.Connection) -> bool:
    """재동기화 필요 여부 반환."""
    _ensure_schema_meta(conn)
    row = conn.execute("SELECT needs_resync FROM schema_meta WHERE id = 1").fetchone()
    return bool(row and row[0])


def clear_needs_resync(conn: sqlite3.Connection) -> None:
    """재동기화 플래그 해제 (동기화 완료 후 호출)."""
    _ensure_schema_meta(conn)
    conn.execute("UPDATE schema_meta SET needs_resync = 0 WHERE id = 1")


# ── 버전별 마이그레이션 ─────────────────────────────────────────────────────

# activity_summaries 전체 컬럼 목록 (v1 기준)
_V1_ACTIVITY_SUMMARIES_COLUMNS: list[tuple[str, str]] = [
    # v0.1 이후 추가된 컬럼들
    ("start_lat", "REAL"),
    ("start_lon", "REAL"),
    ("end_lat", "REAL"),
    ("end_lon", "REAL"),
    ("min_lat", "REAL"),
    ("max_lat", "REAL"),
    ("min_lon", "REAL"),
    ("max_lon", "REAL"),
    ("avg_temperature", "REAL"),
    ("min_temperature", "REAL"),
    ("max_temperature", "REAL"),
    ("body_battery_diff", "INTEGER"),
    ("device_id", "TEXT"),
    ("favorite", "INTEGER"),
    ("water_estimated_ml", "INTEGER"),
    ("moderate_intensity_min", "INTEGER"),
    ("vigorous_intensity_min", "INTEGER"),
    ("avg_hr_gap", "REAL"),
    ("max_double_cadence", "REAL"),
    ("export_filename", "TEXT"),
    ("suffer_score", "INTEGER"),
    ("kudos_count", "INTEGER"),
    ("achievement_count", "INTEGER"),
    ("pr_count", "INTEGER"),
    ("strava_gear_id", "TEXT"),
    ("workout_type", "INTEGER"),
    ("trainer", "INTEGER"),
    ("commute", "INTEGER"),
    ("icu_training_load", "REAL"),
    ("icu_trimp", "REAL"),
    ("icu_hrss", "REAL"),
    ("icu_intensity", "REAL"),
    ("icu_atl", "REAL"),
    ("icu_ctl", "REAL"),
    ("icu_tsb", "REAL"),
    ("icu_gap", "REAL"),
    ("icu_decoupling", "REAL"),
    ("icu_efficiency_factor", "REAL"),
    ("session_rpe", "REAL"),
    ("strain_score", "REAL"),
    ("polarization_index", "REAL"),
    ("perceived_exertion", "REAL"),
    ("event_type", "TEXT"),
    ("matched_group_id", "TEXT"),
]

# daily_wellness 추가 컬럼 (v0.2에서 추가된 것)
_V1_DAILY_WELLNESS_COLUMNS: list[tuple[str, str]] = [
    ("steps", "INTEGER"),
    ("weight_kg", "REAL"),
]

# planned_workouts 추가 컬럼 (v0.2 훈련 이행 추적)
_V1_PLANNED_WORKOUTS_COLUMNS: list[tuple[str, str]] = [
    ("skip_reason", "TEXT"),
    ("updated_at", "TEXT"),  # ALTER TABLE은 non-constant default 불가
]

# v3 추가 컬럼
_V3_PLANNED_WORKOUTS_COLUMNS: list[tuple[str, str]] = [
    # 인터벌 처방 JSON: {"rep_m":320,"sets":10,"rest_sec":94,"recovery_pace":330}
    ("interval_prescription", "TEXT"),
]

_V3_GOALS_COLUMNS: list[tuple[str, str]] = [
    # 표준 거리 레이블: '1.5k'|'3k'|'5k'|'10k'|'half'|'full'|'custom'
    ("distance_label", "TEXT"),
]

_V4_GOALS_COLUMNS: list[tuple[str, str]] = [
    # Wizard: 사용자 목표 주간 km
    ("weekly_km_target", "REAL"),
    # Wizard: 사용자 선택 훈련 기간 (주)
    ("plan_weeks", "INTEGER"),
]

_V4_SCHEMA_META_COLUMNS: list[tuple[str, str]] = [
    # 사람이 읽을 수 있는 버전 표시 (예: '3.1')
    ("display_version", "TEXT"),
]

_V4_TRAINING_PREFS_COLUMNS: list[tuple[str, str]] = [
    # 롱런 요일 마스크 (비트 플래그, 0=일 ~ 6=토). 0이면 플래너가 자동 선택
    ("long_run_weekday_mask", "INTEGER DEFAULT 0"),
]


def _migrate_to_v1(conn: sqlite3.Connection) -> bool:
    """v0 → v1: 모든 v0.2 컬럼/테이블 보장.

    Returns: True if any changes were made.
    """
    changed = False

    # 1) 기존 테이블에 누락 컬럼 추가 (CREATE TABLE/VIEW 보다 먼저!)
    #    VIEW가 컬럼을 참조하므로 컬럼 보강이 선행되어야 함
    existing_tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }

    if "activity_summaries" in existing_tables:
        for col, typedef in _V1_ACTIVITY_SUMMARIES_COLUMNS:
            if _add_column_if_missing(conn, "activity_summaries", col, typedef):
                changed = True

    if "daily_wellness" in existing_tables:
        for col, typedef in _V1_DAILY_WELLNESS_COLUMNS:
            if _add_column_if_missing(conn, "daily_wellness", col, typedef):
                changed = True

    if "planned_workouts" in existing_tables:
        for col, typedef in _V1_PLANNED_WORKOUTS_COLUMNS:
            if _add_column_if_missing(conn, "planned_workouts", col, typedef):
                changed = True

    # 2) 신규 테이블/뷰/인덱스 생성 (IF NOT EXISTS)
    create_tables(conn)
    tables_after = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    new_tables = tables_after - existing_tables
    if new_tables:
        log.info("신규 테이블 생성: %s", ", ".join(sorted(new_tables)))
        changed = True

    return changed


def _migrate_to_v2(conn: sqlite3.Connection) -> bool:
    """v1 → v2: planned_workouts 훈련 이행 추적 컬럼 추가.

    - skip_reason TEXT: 건너뜀 사유
    - updated_at TEXT: 마지막 수정 시각

    Returns: True if any changes were made.
    """
    changed = False
    existing_tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    if "planned_workouts" in existing_tables:
        for col, typedef in _V1_PLANNED_WORKOUTS_COLUMNS:
            if _add_column_if_missing(conn, "planned_workouts", col, typedef):
                changed = True
    return changed


def _migrate_to_v3(conn: sqlite3.Connection) -> bool:
    """v2 → v3: 훈련 엔진 v2 스키마.

    신규 테이블:
    - user_training_prefs: 사용자 훈련 환경 설정 (휴식 요일, 인터벌 설정)
    - session_outcomes: 훈련 세션 성과 기록 (ML 학습 데이터)

    기존 테이블 컬럼 추가:
    - planned_workouts.interval_prescription: 인터벌 처방 JSON
    - goals.distance_label: 표준 거리 레이블

    Returns: True if any changes were made.
    """
    changed = False
    existing_tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }

    # 기존 테이블에 컬럼 추가
    if "planned_workouts" in existing_tables:
        for col, typedef in _V3_PLANNED_WORKOUTS_COLUMNS:
            if _add_column_if_missing(conn, "planned_workouts", col, typedef):
                changed = True

    if "goals" in existing_tables:
        for col, typedef in _V3_GOALS_COLUMNS:
            if _add_column_if_missing(conn, "goals", col, typedef):
                changed = True

    # 신규 테이블 생성 (user_training_prefs, session_outcomes)
    create_tables(conn)
    tables_after = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    new_tables = tables_after - existing_tables
    if new_tables:
        log.info("신규 테이블 생성 (v3): %s", ", ".join(sorted(new_tables)))
        changed = True

    return changed


def _migrate_to_v4(conn: sqlite3.Connection) -> bool:
    """v3 → v4: 훈련탭 UX 재설계 (display_version='3.1').

    신규 컬럼:
    - schema_meta.display_version TEXT: 사람이 읽을 수 있는 버전 문자열
    - goals.weekly_km_target REAL: 사용자 목표 주간 km
    - goals.plan_weeks INTEGER: 사용자 선택 훈련 기간 (주)
    - user_training_prefs.long_run_weekday_mask INTEGER: 롱런 요일 설정

    Returns: True if any changes were made.
    """
    changed = False
    existing_tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }

    # schema_meta에 display_version 컬럼 추가
    if "schema_meta" in existing_tables:
        for col, typedef in _V4_SCHEMA_META_COLUMNS:
            if _add_column_if_missing(conn, "schema_meta", col, typedef):
                changed = True
        conn.execute(
            "UPDATE schema_meta SET display_version = '3.1' WHERE id = 1"
        )

    # goals에 Wizard 컬럼 추가
    if "goals" in existing_tables:
        for col, typedef in _V4_GOALS_COLUMNS:
            if _add_column_if_missing(conn, "goals", col, typedef):
                changed = True

    # user_training_prefs에 롱런 요일 컬럼 추가
    if "user_training_prefs" in existing_tables:
        for col, typedef in _V4_TRAINING_PREFS_COLUMNS:
            if _add_column_if_missing(conn, "user_training_prefs", col, typedef):
                changed = True

    return changed


# 마이그레이션 함수 레지스트리: {target_version: migrate_fn}
_MIGRATIONS: dict[int, callable] = {
    1: _migrate_to_v1,
    2: _migrate_to_v2,
    3: _migrate_to_v3,
    4: _migrate_to_v4,
}


def migrate_db(conn: sqlite3.Connection) -> bool:
    """DB 스키마를 최신 버전으로 마이그레이션.

    Returns: True if any migration was applied.
    """
    _ensure_schema_meta(conn)

    current = _get_user_version(conn)
    if current >= SCHEMA_VERSION:
        # 최신 버전이면 테이블만 보장하고 종료
        create_tables(conn)
        return False

    any_changed = False
    for target_ver in range(current + 1, SCHEMA_VERSION + 1):
        migrate_fn = _MIGRATIONS.get(target_ver)
        if migrate_fn is None:
            log.warning("마이그레이션 함수 없음: v%d", target_ver)
            continue
        log.info("마이그레이션 실행: v%d → v%d", target_ver - 1, target_ver)
        changed = migrate_fn(conn)
        if changed:
            any_changed = True
        _set_user_version(conn, target_ver)

    if any_changed:
        _set_needs_resync(conn, True)
        log.info("스키마 업데이트 완료 (v%d → v%d), 재동기화 필요", current, SCHEMA_VERSION)

    # schema_meta에도 버전 기록
    conn.execute(
        "UPDATE schema_meta SET schema_version = ?, migrated_at = datetime('now') WHERE id = 1",
        (SCHEMA_VERSION,),
    )
    conn.commit()
    return any_changed


def init_db(user_id: str | None = None) -> Path:
    """DB 초기화: 테이블 생성 + 마이그레이션 + WAL 모드 설정. DB 경로 반환."""
    dbp = get_db_path(user_id)
    with sqlite3.connect(dbp) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        create_tables(conn)
        migrate_db(conn)
    return dbp


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
        ver = _get_user_version(conn)
        resync = get_needs_resync(conn)
    print(f"스키마 버전: v{ver}")
    print(f"테이블: {', '.join(tables)}")
    if resync:
        print("⚠️ 재동기화가 필요합니다. 전체 동기화를 실행하세요.")


if __name__ == "__main__":
    main()
