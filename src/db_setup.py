"""RunPulse v0.3 데이터베이스 스키마 — 전면 재작성.

5-Layer 아키텍처:
  Layer 0: source_payloads         — 외부 API 응답 원문 (절대 삭제 안 함)
  Layer 1: activity_summaries      — 통합 활동 요약 (46 컬럼)
           daily_wellness           — 일별 웰니스 core (15 컬럼)
           daily_fitness            — 일별 피트니스 모델 (9 컬럼)
  Layer 2: metric_store            — 모든 메트릭 통합 EAV (16 컬럼)
  Layer 3: activity_streams        — 시계열 GPS/HR/Pace
           activity_laps            — 랩/스플릿
           activity_best_efforts    — 베스트 에포트
  Layer 4: gear, weather_cache, sync_jobs, v_canonical_activities

마이그레이션:
  v0.2 → v0.3은 schema reset (SCHEMA_VERSION=10). 기존 데이터는
  source_payloads에 보존되어 있으므로 reprocess로 재구축 가능.
"""

import logging
import sqlite3
from pathlib import Path

log = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_USER = "default"
SCHEMA_VERSION = 10  # v0.3 시작점. v0.2는 4까지 사용.


# ─────────────────────────────────────────────────────────────────────────────
# DB Path
# ─────────────────────────────────────────────────────────────────────────────

def get_db_path(user_id: str | None = None) -> Path:
    """사용자별 running.db 경로 반환."""
    uid = user_id or DEFAULT_USER
    user_dir = _PROJECT_ROOT / "data" / "users" / uid
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir / "running.db"


# ─────────────────────────────────────────────────────────────────────────────
# DDL — 12개 테이블 + 1 뷰
# ─────────────────────────────────────────────────────────────────────────────

_DDL_SOURCE_PAYLOADS = """
CREATE TABLE IF NOT EXISTS source_payloads (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source          TEXT NOT NULL,
    entity_type     TEXT NOT NULL,
    entity_id       TEXT,
    entity_date     TEXT,
    activity_id     INTEGER,
    payload         TEXT NOT NULL,
    payload_hash    TEXT,
    endpoint        TEXT,
    parser_version  TEXT DEFAULT '1.0',
    fetched_at      TEXT DEFAULT (datetime('now')),
    UNIQUE(source, entity_type, entity_id)
);
"""

_DDL_ACTIVITY_SUMMARIES = """
CREATE TABLE IF NOT EXISTS activity_summaries (
    -- ── 식별 (4) ──
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    source                      TEXT NOT NULL,
    source_id                   TEXT NOT NULL,
    matched_group_id            TEXT,

    -- ── 기본 정보 (3) ──
    name                        TEXT,
    activity_type               TEXT NOT NULL DEFAULT 'running',
    start_time                  TEXT NOT NULL,

    -- ── 거리/시간 (4) ──
    distance_m                  REAL,
    duration_sec                INTEGER,
    moving_time_sec             INTEGER,
    elapsed_time_sec            INTEGER,

    -- ── 속도/페이스 (3) ──
    avg_speed_ms                REAL,
    max_speed_ms                REAL,
    avg_pace_sec_km             REAL,

    -- ── 심박 (2) ──
    avg_hr                      INTEGER,
    max_hr                      INTEGER,

    -- ── 케이던스 (2) ──
    avg_cadence                 INTEGER,
    max_cadence                 INTEGER,

    -- ── 파워 (3) ──
    avg_power                   REAL,
    max_power                   REAL,
    normalized_power            REAL,

    -- ── 고도 (2) ──
    elevation_gain              REAL,
    elevation_loss              REAL,

    -- ── 에너지 (1) ──
    calories                    INTEGER,

    -- ── 훈련 효과/부하 (4) ──
    training_effect_aerobic     REAL,
    training_effect_anaerobic   REAL,
    training_load               REAL,
    suffer_score                INTEGER,

    -- ── 러닝 다이내믹스 (4) ──
    avg_ground_contact_time_ms  REAL,
    avg_stride_length_cm        REAL,
    avg_vertical_oscillation_cm REAL,
    avg_vertical_ratio_pct      REAL,

    -- ── 위치 (4) ──
    start_lat                   REAL,
    start_lon                   REAL,
    end_lat                     REAL,
    end_lon                     REAL,

    -- ── 환경 (1) ──
    avg_temperature             REAL,

    -- ── 메타 (5) ──
    description                 TEXT,
    event_type                  TEXT,
    device_name                 TEXT,
    gear_id                     TEXT,
    source_url                  TEXT,

    -- ── 관리 (2) ──
    created_at                  TEXT DEFAULT (datetime('now')),
    updated_at                  TEXT DEFAULT (datetime('now')),

    UNIQUE(source, source_id)
);
"""

_DDL_DAILY_WELLNESS = """
CREATE TABLE IF NOT EXISTS daily_wellness (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    date                TEXT NOT NULL UNIQUE,

    -- ── 수면 (3) ──
    sleep_score         INTEGER,
    sleep_duration_sec  INTEGER,
    sleep_start_time    TEXT,

    -- ── 심박변이도 (3) ──
    hrv_weekly_avg      REAL,
    hrv_last_night      REAL,
    resting_hr          INTEGER,

    -- ── 회복/에너지 (2) ──
    body_battery_high   INTEGER,
    body_battery_low    INTEGER,

    -- ── 스트레스 (1) ──
    avg_stress          INTEGER,

    -- ── 활동량 (2) ──
    steps               INTEGER,
    active_calories     INTEGER,

    -- ── 체성분 (1) ──
    weight_kg           REAL,

    -- ── 관리 (2) ──
    created_at          TEXT DEFAULT (datetime('now')),
    updated_at          TEXT DEFAULT (datetime('now'))
);
"""

_DDL_DAILY_FITNESS = """
CREATE TABLE IF NOT EXISTS daily_fitness (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    date                TEXT NOT NULL,
    source              TEXT NOT NULL,

    ctl                 REAL,
    atl                 REAL,
    tsb                 REAL,
    ramp_rate           REAL,
    vo2max              REAL,

    created_at          TEXT DEFAULT (datetime('now')),
    updated_at          TEXT DEFAULT (datetime('now')),

    UNIQUE(date, source)
);
"""

_DDL_METRIC_STORE = """
CREATE TABLE IF NOT EXISTS metric_store (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    scope_type          TEXT NOT NULL,
    scope_id            TEXT NOT NULL,
    metric_name         TEXT NOT NULL,
    category            TEXT,
    provider            TEXT NOT NULL,
    numeric_value       REAL,
    text_value          TEXT,
    json_value          TEXT,
    algorithm_version   TEXT DEFAULT '1.0',
    confidence          REAL,
    raw_name            TEXT,
    parent_metric_id    INTEGER,
    is_primary          BOOLEAN DEFAULT 0,
    created_at          TEXT DEFAULT (datetime('now')),
    updated_at          TEXT DEFAULT (datetime('now')),
    UNIQUE(scope_type, scope_id, metric_name, provider)
);
"""

_DDL_ACTIVITY_STREAMS = """
CREATE TABLE IF NOT EXISTS activity_streams (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    activity_id     INTEGER NOT NULL,
    source          TEXT NOT NULL,
    elapsed_sec     INTEGER NOT NULL,
    distance_m      REAL,
    heart_rate      INTEGER,
    cadence         INTEGER,
    power_watts     REAL,
    altitude_m      REAL,
    speed_ms        REAL,
    latitude        REAL,
    longitude       REAL,
    grade_pct       REAL,
    temperature_c   REAL,
    created_at      TEXT DEFAULT (datetime('now')),
    UNIQUE(activity_id, source, elapsed_sec)
);
"""

_DDL_ACTIVITY_LAPS = """
CREATE TABLE IF NOT EXISTS activity_laps (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    activity_id     INTEGER NOT NULL,
    source          TEXT NOT NULL,
    lap_index       INTEGER NOT NULL,
    start_time      TEXT,
    duration_sec    REAL,
    distance_m      REAL,
    avg_hr          INTEGER,
    max_hr          INTEGER,
    avg_pace_sec_km REAL,
    avg_cadence     REAL,
    avg_power       REAL,
    max_power       REAL,
    elevation_gain  REAL,
    calories        INTEGER,
    lap_trigger     TEXT,
    created_at      TEXT DEFAULT (datetime('now')),
    UNIQUE(activity_id, source, lap_index)
);
"""

_DDL_ACTIVITY_BEST_EFFORTS = """
CREATE TABLE IF NOT EXISTS activity_best_efforts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    activity_id     INTEGER NOT NULL,
    source          TEXT NOT NULL,
    effort_name     TEXT NOT NULL,
    elapsed_sec     REAL,
    distance_m      REAL,
    start_index     INTEGER,
    end_index       INTEGER,
    pr_rank         INTEGER,
    created_at      TEXT DEFAULT (datetime('now')),
    UNIQUE(activity_id, source, effort_name)
);
"""

_DDL_GEAR = """
CREATE TABLE IF NOT EXISTS gear (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    source              TEXT NOT NULL,
    source_gear_id      TEXT NOT NULL,
    name                TEXT,
    brand               TEXT,
    model               TEXT,
    gear_type           TEXT DEFAULT 'shoes',
    total_distance_m    REAL DEFAULT 0,
    status              TEXT DEFAULT 'active',
    created_at          TEXT DEFAULT (datetime('now')),
    updated_at          TEXT DEFAULT (datetime('now')),
    UNIQUE(source, source_gear_id)
);
"""

_DDL_WEATHER_CACHE = """
CREATE TABLE IF NOT EXISTS weather_cache (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    date                TEXT NOT NULL,
    hour                INTEGER DEFAULT 12,
    latitude            REAL NOT NULL,
    longitude           REAL NOT NULL,
    source              TEXT NOT NULL DEFAULT 'open_meteo',
    temp_c              REAL,
    humidity_pct        INTEGER,
    dew_point_c         REAL,
    wind_speed_ms       REAL,
    wind_direction_deg  INTEGER,
    pressure_hpa        REAL,
    cloud_cover_pct     INTEGER,
    condition_text      TEXT,
    fetched_at          TEXT DEFAULT (datetime('now')),
    UNIQUE(date, hour, latitude, longitude, source)
);
"""

_DDL_SYNC_JOBS = """
CREATE TABLE IF NOT EXISTS sync_jobs (
    id              TEXT PRIMARY KEY,
    source          TEXT NOT NULL,
    job_type        TEXT NOT NULL DEFAULT 'activity',
    from_date       TEXT,
    to_date         TEXT,
    status          TEXT DEFAULT 'pending',
    total_items     INTEGER,
    completed_items INTEGER DEFAULT 0,
    error_count     INTEGER DEFAULT 0,
    last_error      TEXT,
    retry_after     TEXT,
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
);
"""

# ── 앱 기능 테이블 (기존 유지) ──

_DDL_APP_TABLES = """
CREATE TABLE IF NOT EXISTS chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    chip_id TEXT,
    ai_model TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    race_date TEXT,
    distance_km REAL NOT NULL,
    target_time_sec INTEGER,
    target_pace_sec_km INTEGER,
    status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'completed', 'cancelled')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    distance_label TEXT,
    weekly_km_target REAL,
    plan_weeks INTEGER
);

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
    matched_activity_id INTEGER,
    source TEXT DEFAULT 'manual',
    ai_model TEXT,
    garmin_workout_id TEXT,
    skip_reason TEXT,
    updated_at TEXT,
    interval_prescription TEXT
);

CREATE TABLE IF NOT EXISTS user_training_prefs (
    id                 INTEGER PRIMARY KEY DEFAULT 1 CHECK(id = 1),
    rest_weekdays_mask INTEGER NOT NULL DEFAULT 0,
    blocked_dates      TEXT    NOT NULL DEFAULT '[]',
    interval_rep_m     INTEGER NOT NULL DEFAULT 1000,
    max_q_days         INTEGER NOT NULL DEFAULT 0,
    long_run_weekday_mask INTEGER DEFAULT 0,
    updated_at         TEXT
);

CREATE TABLE IF NOT EXISTS session_outcomes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    planned_id      INTEGER,
    activity_id     INTEGER,
    date            TEXT NOT NULL,
    planned_dist_km REAL,
    actual_dist_km  REAL,
    dist_ratio      REAL,
    planned_pace    INTEGER,
    actual_pace     INTEGER,
    pace_delta_pct  REAL,
    hr_z1_pct       REAL,
    hr_z2_pct       REAL,
    hr_z3_pct       REAL,
    target_zone     INTEGER,
    actual_avg_hr   INTEGER,
    hr_delta        INTEGER,
    decoupling_pct  REAL,
    trimp           REAL,
    crs_at_session  REAL,
    tsb_at_session  REAL,
    hrv_at_session  REAL,
    bb_at_session   INTEGER,
    acwr_at_session REAL,
    outcome_label   TEXT CHECK(outcome_label IN (
        'on_target','overperformed','underperformed','skipped','modified'
    )),
    computed_at     TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_session_outcomes_date ON session_outcomes(date DESC);
"""

# ── View ──

_DDL_CANONICAL_VIEW = """
CREATE VIEW IF NOT EXISTS v_canonical_activities AS
WITH grouped AS (
    SELECT *,
           ROW_NUMBER() OVER (
               PARTITION BY COALESCE(matched_group_id, 'solo_' || id)
               ORDER BY
                   CASE source
                       WHEN 'garmin' THEN 1
                       WHEN 'intervals' THEN 2
                       WHEN 'strava' THEN 3
                       WHEN 'runalyze' THEN 4
                       ELSE 5
                   END,
                   id
           ) AS rn
    FROM activity_summaries
)
SELECT * FROM grouped WHERE rn = 1;
"""


# ─────────────────────────────────────────────────────────────────────────────
# Table Creation
# ─────────────────────────────────────────────────────────────────────────────

# 파이프라인 테이블 이름 목록 (검증용)
PIPELINE_TABLES = [
    "source_payloads",
    "activity_summaries",
    "daily_wellness",
    "daily_fitness",
    "metric_store",
    "activity_streams",
    "activity_laps",
    "activity_best_efforts",
    "gear",
    "weather_cache",
    "sync_jobs",
]

APP_TABLES = [
    "chat_messages",
    "goals",
    "planned_workouts",
    "user_training_prefs",
    "session_outcomes",
]

ALL_TABLES = PIPELINE_TABLES + APP_TABLES


def _safe_create_indexes(conn: sqlite3.Connection) -> None:
    """모든 인덱스를 컬럼 존재 여부를 확인하고 안전하게 생성."""
    _idx = _create_index_if_column_exists

    # source_payloads
    _idx(conn, "source_payloads", "source",
         "CREATE INDEX IF NOT EXISTS idx_sp_source_entity ON source_payloads(source, entity_type, entity_id)")
    _idx(conn, "source_payloads", "activity_id",
         "CREATE INDEX IF NOT EXISTS idx_sp_activity ON source_payloads(activity_id)")
    _idx(conn, "source_payloads", "entity_date",
         "CREATE INDEX IF NOT EXISTS idx_sp_entity_date ON source_payloads(entity_date)")

    # activity_summaries
    _idx(conn, "activity_summaries", "activity_type",
         "CREATE INDEX IF NOT EXISTS idx_as_activity_type ON activity_summaries(activity_type)")
    _idx(conn, "activity_summaries", "start_time",
         "CREATE INDEX IF NOT EXISTS idx_as_start_time ON activity_summaries(start_time)")
    _idx(conn, "activity_summaries", "source",
         "CREATE INDEX IF NOT EXISTS idx_as_source ON activity_summaries(source)")
    _idx(conn, "activity_summaries", "matched_group_id",
         "CREATE INDEX IF NOT EXISTS idx_as_matched_group ON activity_summaries(matched_group_id)")
    _idx(conn, "activity_summaries", "gear_id",
         "CREATE INDEX IF NOT EXISTS idx_as_gear ON activity_summaries(gear_id)")

    # daily_fitness
    _idx(conn, "daily_fitness", "date",
         "CREATE INDEX IF NOT EXISTS idx_df_date ON daily_fitness(date)")

    # metric_store
    _idx(conn, "metric_store", "scope_type",
         "CREATE INDEX IF NOT EXISTS idx_ms_scope ON metric_store(scope_type, scope_id)")
    _idx(conn, "metric_store", "metric_name",
         "CREATE INDEX IF NOT EXISTS idx_ms_name ON metric_store(metric_name)")
    _idx(conn, "metric_store", "provider",
         "CREATE INDEX IF NOT EXISTS idx_ms_provider ON metric_store(provider)")
    _idx(conn, "metric_store", "category",
         "CREATE INDEX IF NOT EXISTS idx_ms_category ON metric_store(category)")
    _idx(conn, "metric_store", "is_primary",
         "CREATE INDEX IF NOT EXISTS idx_ms_primary ON metric_store(scope_type, scope_id, metric_name) WHERE is_primary = 1")
    _idx(conn, "metric_store", "category",
         "CREATE INDEX IF NOT EXISTS idx_ms_scope_category ON metric_store(scope_type, scope_id, category)")

    # activity_streams
    _idx(conn, "activity_streams", "activity_id",
         "CREATE INDEX IF NOT EXISTS idx_streams_activity ON activity_streams(activity_id, source)")

    # activity_laps
    _idx(conn, "activity_laps", "activity_id",
         "CREATE INDEX IF NOT EXISTS idx_laps_activity ON activity_laps(activity_id)")

    # activity_best_efforts
    _idx(conn, "activity_best_efforts", "activity_id",
         "CREATE INDEX IF NOT EXISTS idx_best_efforts_activity ON activity_best_efforts(activity_id)")

    # sync_jobs
    _idx(conn, "sync_jobs", "source",
         "CREATE INDEX IF NOT EXISTS idx_sync_jobs_source ON sync_jobs(source, created_at)")


def _create_index_if_column_exists(
    conn: sqlite3.Connection, table: str, column: str, ddl: str
) -> None:
    """테이블이 존재하고 해당 컬럼이 있을 때만 인덱스 생성."""
    try:
        cols = {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    except Exception:
        return
    if not cols:  # 테이블 자체가 없음
        return
    if column in cols:
        conn.execute(ddl)


def create_tables(conn: sqlite3.Connection) -> None:
    """v0.3 스키마: 12 파이프라인 테이블 + 5 앱 테이블 + 1 뷰 생성."""
    for ddl in [
        _DDL_SOURCE_PAYLOADS,
        _DDL_ACTIVITY_SUMMARIES,
        _DDL_DAILY_WELLNESS,
        _DDL_DAILY_FITNESS,
        _DDL_METRIC_STORE,
        _DDL_ACTIVITY_STREAMS,
        _DDL_ACTIVITY_LAPS,
        _DDL_ACTIVITY_BEST_EFFORTS,
        _DDL_GEAR,
        _DDL_WEATHER_CACHE,
        _DDL_SYNC_JOBS,
        _DDL_APP_TABLES,
    ]:
        conn.executescript(ddl)

    # View
    conn.execute("DROP VIEW IF EXISTS v_canonical_activities")
    conn.executescript(_DDL_CANONICAL_VIEW)

    # Indexes (컬럼 존재 확인 후 안전 생성)
    _safe_create_indexes(conn)

    conn.commit()

# ─────────────────────────────────────────────────────────────────────────────
# Schema Version Management
# ─────────────────────────────────────────────────────────────────────────────

def _get_user_version(conn: sqlite3.Connection) -> int:
    row = conn.execute("PRAGMA user_version").fetchone()
    return int(row[0]) if row else 0


def _set_user_version(conn: sqlite3.Connection, version: int) -> None:
    conn.execute(f"PRAGMA user_version = {int(version)}")


def _get_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    """테이블의 컬럼명 집합."""
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {row[1] for row in rows}


def _get_existing_tables(conn: sqlite3.Connection) -> set[str]:
    """현재 DB의 테이블명 집합."""
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    return {row[0] for row in rows}


def migrate_db(conn: sqlite3.Connection) -> bool:
    """v0.2(≤4) → v0.3(=10) 마이그레이션.

    전략: 기존 테이블은 건드리지 않고, 새 테이블만 추가합니다.
    기존 데이터는 Phase 6의 migration 스크립트(v3_to_v4.py)에서 변환합니다.
    """
    current = _get_user_version(conn)

    if current >= SCHEMA_VERSION:
        # 이미 최신. 테이블만 보장.
        create_tables(conn)
        return False

    log.info("스키마 마이그레이션: v%d → v%d", current, SCHEMA_VERSION)

    # 새 테이블 생성 (IF NOT EXISTS이므로 기존 테이블 무시)
    create_tables(conn)

    _set_user_version(conn, SCHEMA_VERSION)
    conn.commit()

    log.info("스키마 마이그레이션 완료: v%d", SCHEMA_VERSION)
    return True


# ─────────────────────────────────────────────────────────────────────────────
# Init
# ─────────────────────────────────────────────────────────────────────────────

def init_db(user_id: str | None = None) -> Path:
    """DB 초기화: 테이블 생성 + 마이그레이션 + WAL 모드. DB 경로 반환."""
    dbp = get_db_path(user_id)
    with sqlite3.connect(dbp) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        create_tables(conn)
        migrate_db(conn)
    return dbp


def get_connection(user_id: str | None = None) -> sqlite3.Connection:
    """DB 연결 반환. Row factory 설정 포함."""
    dbp = get_db_path(user_id)
    conn = sqlite3.connect(dbp)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def main() -> None:
    """CLI 진입점."""
    db_path = init_db()
    print(f"DB 초기화 완료: {db_path}")

    with sqlite3.connect(db_path) as conn:
        tables = sorted(
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
        )
        views = sorted(
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='view'"
            ).fetchall()
        )
        ver = _get_user_version(conn)

    print(f"스키마 버전: v{ver}")
    print(f"테이블 ({len(tables)}): {', '.join(tables)}")
    print(f"뷰 ({len(views)}): {', '.join(views)}")


if __name__ == "__main__":
    main()
