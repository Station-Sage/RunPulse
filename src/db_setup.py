"""RunPulse v0.3 데이터베이스 스키마 — 전면 재작성.

5-Layer 아키텍처:
  Layer 0: source_payloads         — 외부 API 응답 원문 (절대 삭제 안 함)
  Layer 1: activity_summaries      — 통합 활동 요약 (38 컬럼)
           daily_wellness           — 일별 웰니스 core (15 컬럼)
  Layer 2: metric_store            — 모든 메트릭 통합 EAV (16 컬럼)
           (daily_fitness 삭제됨 — ADR-005: ctl/atl/tsb/ramp_rate/vo2max → metric_store)
  Layer 3: activity_streams        — 시계열 GPS/HR/Pace
           activity_laps            — 랩/스플릿
           activity_best_efforts    — 베스트 에포트
           activity_exercise_sets   — 근력/운동 세트 (Garmin)
  Layer 4: gear, weather_cache, sync_jobs, v_canonical_activities

마이그레이션:
  v0.2 → v0.3은 schema reset (SCHEMA_VERSION=10). 기존 데이터는
  source_payloads에 보존되어 있으므로 reprocess로 재구축 가능.
  v12: calories/normalized_power/suffer_score/training_effect_aerobic/
       training_effect_anaerobic/training_load → metric_store 이동.
  v19: chat_messages.evidence_json — Coach 답변 근거 저장.
"""

import logging
import re
import sqlite3
from pathlib import Path

log = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_USER = "default"
SCHEMA_VERSION = 22  # v0.3.12: 마일스톤 재계산 종류 분리 (db_schema_v22) — v21: 예측 스냅샷, v20: 예측 리뉴얼 컬럼·race_results


# ─────────────────────────────────────────────────────────────────────────────
# DB Path
# ─────────────────────────────────────────────────────────────────────────────

def get_db_path(user_id: str | None = None, *, create: bool = True) -> Path:
    """사용자별 running.db 경로 반환.

    create=False 는 읽기 전용 소비자(MCP 서버 등)용 — 오타 난 user_id로 빈 디렉터리가
    생기지 않도록 디렉터리를 만들지 않는다.
    """
    uid = user_id or DEFAULT_USER
    user_dir = _PROJECT_ROOT / "data" / "users" / uid
    if create:
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

    -- ── 파워 (2) ──
    avg_power                   REAL,
    max_power                   REAL,

    -- ── 고도 (2) ──
    elevation_gain              REAL,
    elevation_loss              REAL,

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

    -- ── 훈련 (1) ──
    workout_label               TEXT,

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

_DDL_ACTIVITY_EXERCISE_SETS = """
CREATE TABLE IF NOT EXISTS activity_exercise_sets (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    activity_id       INTEGER NOT NULL,
    source            TEXT NOT NULL,
    set_index         INTEGER NOT NULL,
    exercise_name     TEXT,
    exercise_category TEXT,
    set_type          TEXT,
    reps              INTEGER,
    weight_kg         REAL,
    duration_sec      REAL,
    distance_m        REAL,
    created_at        TEXT DEFAULT (datetime('now')),
    UNIQUE(activity_id, source, set_index)
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

_DDL_ATHLETE_PROFILE = """
CREATE TABLE IF NOT EXISTS athlete_profile (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    source              TEXT NOT NULL UNIQUE,
    source_athlete_id   TEXT,
    firstname           TEXT,
    lastname            TEXT,
    city                TEXT,
    country             TEXT,
    sex                 TEXT,
    weight_kg           REAL,
    ftp                 INTEGER,
    lthr                INTEGER,
    vo2max              REAL,
    profile_json        TEXT,
    updated_at          TEXT DEFAULT (datetime('now'))
);
"""

_DDL_ATHLETE_STATS = """
CREATE TABLE IF NOT EXISTS athlete_stats (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    source                  TEXT NOT NULL,
    snapshot_date           TEXT NOT NULL,
    -- Strava / Intervals (run-scoped totals)
    all_run_count           INTEGER,
    all_run_distance_km     REAL,
    all_run_elapsed_sec     INTEGER,
    all_run_elevation_m     REAL,
    ytd_run_count           INTEGER,
    ytd_run_distance_km     REAL,
    ytd_run_elapsed_sec     INTEGER,
    recent_run_count        INTEGER,
    recent_run_distance_km  REAL,
    -- Garmin (generic totals)
    total_distance_km       REAL,
    total_elevation_m       REAL,
    total_moving_sec        INTEGER,
    total_activities        INTEGER,
    biggest_distance_km     REAL,
    stats_json              TEXT,
    updated_at              TEXT DEFAULT (datetime('now')),
    UNIQUE(source, snapshot_date)
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

_DDL_ACTIVITY_GROUPS = """
CREATE TABLE IF NOT EXISTS activity_groups (
    group_id        TEXT PRIMARY KEY,
    primary_source  TEXT NOT NULL,
    activity_date   TEXT NOT NULL,
    distance_m      REAL,
    member_count    INTEGER DEFAULT 1,
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
);
"""

_DDL_MILESTONES = """
CREATE TABLE IF NOT EXISTS milestones (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    type        TEXT NOT NULL,
    date        TEXT NOT NULL,
    title       TEXT NOT NULL,
    detail      TEXT,
    activity_id INTEGER,
    metric_name TEXT,
    old_value   REAL,
    new_value   REAL,
    created_at  TEXT DEFAULT (datetime('now')),
    UNIQUE(type, date, title)
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
    thread_id INTEGER,
    evidence_json TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS chat_threads (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT,
    created_at  TEXT DEFAULT (datetime('now')),
    updated_at  TEXT DEFAULT (datetime('now'))
);
-- idx_chat_thread는 여기 두지 않는다: chat_messages는 기존 테이블이라 thread_id가
-- 아직 없는 상태로 create_tables()만 단독 호출될 수 있음(migrate_db 없이) — 대신
-- _safe_create_indexes()의 컬럼 존재 확인 헬퍼로 안전하게 생성한다.

-- D3 (Phase 7): 사용자 체크인 + AI 피드백. 06-data-layer-extensions.md ADR 기준,
-- activity_id는 FK 제약 없음(이 스키마 전체 관례 일치 — REFERENCES 쓰는 테이블 없음,
-- PRAGMA foreign_keys=ON 상태에서 활동 재처리 시 참조 무결성 위반 위험 회피).
CREATE TABLE IF NOT EXISTS user_inputs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    input_date      TEXT NOT NULL,
    input_type      TEXT NOT NULL,
    fatigue         INTEGER,
    pain            TEXT,
    mood            INTEGER,
    note            TEXT,
    activity_id     INTEGER,
    created_at      TEXT DEFAULT (datetime('now')),
    UNIQUE(input_date, input_type)
);
CREATE INDEX IF NOT EXISTS idx_ui_date ON user_inputs(input_date);
CREATE INDEX IF NOT EXISTS idx_ui_type ON user_inputs(input_date, input_type);

CREATE TABLE IF NOT EXISTS ai_feedback (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id       INTEGER NOT NULL,
    message_id      INTEGER NOT NULL,
    rating          INTEGER,
    thumbs          TEXT,
    comment         TEXT,
    created_at      TEXT DEFAULT (datetime('now')),
    UNIQUE(thread_id, message_id)
);
CREATE INDEX IF NOT EXISTS idx_af_thread ON ai_feedback(thread_id);

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
    "activity_groups",
    "milestones",
    "daily_wellness",
    "metric_store",
    "activity_streams",
    "activity_laps",
    "activity_best_efforts",
    "activity_exercise_sets",
    "gear",
    "athlete_profile",
    "athlete_stats",
    "weather_cache",
    "sync_jobs",
]

APP_TABLES = [
    "chat_messages",
    "goals",
    "planned_workouts",
    "user_training_prefs",
    "session_outcomes",
    "chat_threads",
    "user_inputs",
    "ai_feedback",
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

    # activity_exercise_sets
    _idx(conn, "activity_exercise_sets", "activity_id",
         "CREATE INDEX IF NOT EXISTS idx_exercise_sets_activity ON activity_exercise_sets(activity_id, source)")

    # sync_jobs
    _idx(conn, "sync_jobs", "source",
         "CREATE INDEX IF NOT EXISTS idx_sync_jobs_source ON sync_jobs(source, created_at)")

    # activity_groups (D2)
    _idx(conn, "activity_groups", "activity_date",
         "CREATE INDEX IF NOT EXISTS idx_ag_date ON activity_groups(activity_date)")

    # milestones
    _idx(conn, "milestones", "date",
         "CREATE INDEX IF NOT EXISTS idx_milestones_date ON milestones(date DESC)")

    # chat_messages.thread_id (D3) — 기존 테이블에 추가되는 컬럼이라 컬럼 존재 확인 필요
    _idx(conn, "chat_messages", "thread_id",
         "CREATE INDEX IF NOT EXISTS idx_chat_thread ON chat_messages(thread_id)")


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
    """v0.3 스키마: 14 파이프라인 테이블 + 8 앱 테이블 + 1 뷰 생성."""
    for ddl in [
        _DDL_SOURCE_PAYLOADS,
        _DDL_ACTIVITY_SUMMARIES,
        _DDL_ACTIVITY_GROUPS,
        _DDL_MILESTONES,
        _DDL_DAILY_WELLNESS,
        _DDL_METRIC_STORE,
        _DDL_ACTIVITY_STREAMS,
        _DDL_ACTIVITY_LAPS,
        _DDL_ACTIVITY_BEST_EFFORTS,
        _DDL_ACTIVITY_EXERCISE_SETS,
        _DDL_GEAR,
        _DDL_ATHLETE_PROFILE,
        _DDL_ATHLETE_STATS,
        _DDL_WEATHER_CACHE,
        _DDL_SYNC_JOBS,
        _DDL_APP_TABLES,
    ]:
        conn.executescript(ddl)

    # View
    _ensure_canonical_view(conn)

    # Indexes (컬럼 존재 확인 후 안전 생성)
    _safe_create_indexes(conn)

    # v20: 예측 리뉴얼 컬럼·race_results (멱등)
    from src.db_schema_v20 import ensure_v20
    ensure_v20(conn)
    # v21: 예측 스냅샷(P7-PRED-63)
    from src.db_schema_v21 import ensure_v21
    ensure_v21(conn)
    # v22: 마일스톤 provider·재계산 종류(A/B)
    from src.db_schema_v22 import ensure_v22
    ensure_v22(conn)

    conn.commit()


def _view_body(sql: str) -> str:
    """CREATE VIEW 문에서 첫 `AS` 뒤 SELECT 본문만 공백 정규화해 반환 (정의 비교용).

    sqlite_master.sql은 `IF NOT EXISTS`가 빠진 채 저장돼 DDL 원문과 직접 비교할 수 없다.
    """
    m = re.search(r"\bAS\b", sql, re.IGNORECASE)
    body = sql[m.end():] if m else sql
    return re.sub(r"\s+", " ", body).strip().rstrip(";").strip()


def _ensure_canonical_view(conn: sqlite3.Connection) -> None:
    """v_canonical_activities를 정의가 바뀐 경우에만 DROP+CREATE 한다 (원자적).

    app.py의 before_request가 매 요청마다 migrate_db → create_tables를 부르는데, 그때마다
    뷰를 DROP하면 병렬 요청(SPA는 화면 하나에 API를 4~5개 동시에 부른다)이 뷰가 없는
    찰나에 `no such table: v_canonical_activities`로 500이 났다 — 2026-09-24 합성 데이터
    부하 테스트로 재현(동시 400건 중 73건). 정의가 같으면 아무 DDL도 실행하지 않고,
    바뀐 경우엔 DROP·CREATE를 한 트랜잭션에 묶어 다른 연결이 중간 상태를 보지 못하게 한다.
    """
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'view' AND name = 'v_canonical_activities'"
    ).fetchone()
    if row and row[0] and _view_body(row[0]) == _view_body(_DDL_CANONICAL_VIEW):
        return
    conn.executescript(
        "BEGIN IMMEDIATE;\nDROP VIEW IF EXISTS v_canonical_activities;\n"
        + _DDL_CANONICAL_VIEW
        + "\nCOMMIT;"
    )

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
    """v0.2(≤4) → v0.3(≤10) → v0.3.1(=11) → v0.3.2(=12) → v0.3.3(=13) → v0.3.4(=14) 마이그레이션.

    전략: 기존 테이블은 건드리지 않고, 새 테이블만 추가.
    v11: daily_fitness 삭제 (ADR-005 — ctl/atl/tsb/ramp_rate/vo2max → metric_store).
    v12: activity_summaries 6컬럼 → metric_store 이동.
         calories/normalized_power/suffer_score/training_effect_aerobic/
         training_effect_anaerobic/training_load — DROP COLUMN.
    v13: activity_summaries.distance_km → distance_m 컬럼명 수정 (SQLite 3.25+ RENAME COLUMN).
    v14: activity_streams / activity_best_efforts elapsed_sec 컬럼 누락 시 테이블 재생성.
    v15: activity_summaries.workout_label TEXT 컬럼 추가.
    v16: chat_messages.thread_id 컬럼 추가 (D3 — user_inputs/ai_feedback/chat_threads는
         신규 테이블이라 create_tables()의 CREATE TABLE IF NOT EXISTS만으로 충분).
    v17: activity_groups 마스터 테이블 신설 (D2 — CREATE TABLE IF NOT EXISTS만으로 충분).
    v18: milestones 테이블 신설 — CREATE TABLE IF NOT EXISTS만으로 충분.
    v19: chat_messages.evidence_json 추가 (Coach 답변 근거).
    v22: milestones.provider 추가 + 재계산 종류 분리(create_tables 안의 ensure_v22 가 멱등 처리).
    """
    current = _get_user_version(conn)

    if current >= SCHEMA_VERSION:
        # 이미 최신. 테이블만 보장.
        create_tables(conn)
        return False

    log.info("스키마 마이그레이션: v%d → v%d", current, SCHEMA_VERSION)

    # v11: daily_fitness 삭제
    if current < 11:
        conn.execute("DROP TABLE IF EXISTS daily_fitness")

    # v12: activity_summaries 6컬럼 DROP (SQLite 3.35+ 필요)
    if current < 12:
        _drop_cols = (
            "calories", "normalized_power", "suffer_score",
            "training_effect_aerobic", "training_effect_anaerobic", "training_load",
        )
        for col in _drop_cols:
            try:
                conn.execute(f"ALTER TABLE activity_summaries DROP COLUMN {col}")
            except Exception:
                pass  # 이미 없거나 SQLite 버전 미지원 — 무시

    # v13: activity_summaries.distance_km → distance_m (DDL 기준 정렬)
    if current < 13:
        existing_cols = {
            r[1] for r in conn.execute("PRAGMA table_info(activity_summaries)").fetchall()
        }
        if "distance_km" in existing_cols and "distance_m" not in existing_cols:
            try:
                conn.execute(
                    "ALTER TABLE activity_summaries RENAME COLUMN distance_km TO distance_m"
                )
            except Exception as exc:
                log.warning("distance_km → distance_m 컬럼 변환 실패 (SQLite 3.25+ 필요): %s", exc)

    # v14: activity_streams / activity_best_efforts — elapsed_sec 컬럼 보장
    # 두 테이블은 재동기화로 복원 가능하므로, 컬럼 누락 시 DROP → 재생성
    if current < 14:
        for tbl in ("activity_streams", "activity_best_efforts"):
            existing = {
                r[1] for r in conn.execute(f"PRAGMA table_info({tbl})").fetchall()
            }
            if existing and "elapsed_sec" not in existing:
                log.info("v14 마이그레이션: %s elapsed_sec 누락 → 테이블 재생성", tbl)
                conn.execute(f"DROP TABLE IF EXISTS {tbl}")

    # v15: activity_summaries.workout_label 추가
    if current < 15:
        existing = {r[1] for r in conn.execute("PRAGMA table_info(activity_summaries)").fetchall()}
        if "workout_label" not in existing:
            conn.execute("ALTER TABLE activity_summaries ADD COLUMN workout_label TEXT")

    # v16: chat_messages.thread_id 추가 (D3 — Coach 스레드 지원)
    if current < 16:
        existing = {r[1] for r in conn.execute("PRAGMA table_info(chat_messages)").fetchall()}
        if existing and "thread_id" not in existing:
            conn.execute("ALTER TABLE chat_messages ADD COLUMN thread_id INTEGER")

    # v19: chat_messages.evidence_json 추가 (Coach 답변 근거)
    if current < 19:
        existing = {r[1] for r in conn.execute("PRAGMA table_info(chat_messages)").fetchall()}
        if existing and "evidence_json" not in existing:
            conn.execute("ALTER TABLE chat_messages ADD COLUMN evidence_json TEXT")

    # 새 테이블 생성 (IF NOT EXISTS이므로 기존 테이블 무시) — v20 컬럼은 create_tables 안에서 보장
    create_tables(conn)

    _set_user_version(conn, SCHEMA_VERSION)
    conn.commit()

    log.info("스키마 마이그레이션 완료: v%d", SCHEMA_VERSION)
    return True


# ─────────────────────────────────────────────────────────────────────────────
# Init
# ─────────────────────────────────────────────────────────────────────────────

def get_needs_resync(conn: sqlite3.Connection) -> bool:
    """동기화가 필요한지 확인. 활동 데이터가 없으면 True."""
    row = conn.execute("SELECT COUNT(*) FROM activity_summaries").fetchone()
    return (row[0] if row else 0) == 0


def clear_needs_resync(conn: sqlite3.Connection) -> None:
    """재동기화 플래그 해제. get_needs_resync()는 활동 수 기반이므로 no-op."""
    pass


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
