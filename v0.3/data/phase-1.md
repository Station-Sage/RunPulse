# Phase 1 상세 설계 — 스키마 & 기반 인프라

> DDL 전문과 설계 결정 사유를 기록합니다.
> 메트릭/컬럼 전체 배정표 → `data_master.md` (자동 생성) | 아키텍처 개요 → `architecture.md`

---

## 1-1. 테이블별 DDL

### `source_payloads` — API 원문 보존 (Layer 0)

외부 API 응답 원문을 100% 보존합니다. Extractor 수정 시 API 재호출 없이 재추출 가능.

**설계 결정**: INSERT OR REPLACE로 최신 raw만 유지. payload_hash로 변경 감지.

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

11컬럼.

---

### `activity_summaries` — 통합 활동 요약 (Layer 1)

센서 측정값과 메타데이터만 저장합니다. 알고리즘 산출물은 metric_store로.

**컬럼 포함 기준**:
- 센서 직접 측정값 또는 단순 산술 파생값
- 활동 목록/필터/정렬에서 직접 사용되는 값

**단위 suffix 원칙**: 컬럼명 끝에 SI 기본 단위를 suffix로 명시한다. 단위 변환은 UI 표시 시점에서만 수행한다. → 상세 규칙은 `architecture.md` ADR-012 참조.

**metric_store로 이동 완료 (Phase 5-G)**: calories, normalized_power, suffer_score, training_effect_aerobic, training_effect_anaerobic, training_load. Extractor에서 extract_activity_metrics() 경로로 저장.

CREATE TABLE IF NOT EXISTS activity_summaries (
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
    duration_sec                REAL,
    moving_time_sec             REAL,
    elapsed_time_sec            REAL,

    -- ── 속도/페이스 (3) ──
    avg_speed_ms                REAL,
    max_speed_ms                REAL,
    avg_pace_sec_km             REAL,

    -- ── 심박 (2) ──
    avg_hr                      REAL,
    max_hr                      REAL,

    -- ── 케이던스 (2) ──
    avg_cadence                 REAL,
    max_cadence                 REAL,

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

    -- ── 메타 (4) ──
    description                 TEXT,
    event_type                  TEXT,
    device_name                 TEXT,
    gear_id                     INTEGER,
    source_url                  TEXT,

    -- ── 관리 (2) ──
    created_at                  TEXT DEFAULT (datetime('now')),
    updated_at                  TEXT DEFAULT (datetime('now')),

    UNIQUE(source, source_id)
);

38컬럼. calories/normalized_power/suffer_score/training_effect_aerobic/training_effect_anaerobic/training_load → metric_store 이동 완료 (Phase 5-G, v12).

---

### `daily_wellness` — 일별 웰니스 요약 (Layer 1)

대시보드 "오늘의 상태" 카드에 직접 표시되는 핵심 건강 지표만 포함합니다. sleep 상세, stress 상세, training readiness 상세, SpO2, 호흡수 등은 metric_store(scope_type='daily')로.

**설계 결정**: source 컬럼 없음. 하루 한 행. 주 소스 Garmin이 먼저 채우고, 다른 소스는 NULL fill only merge. 소스별 원본값은 metric_store에 보존.

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

16컬럼.

---

### `daily_fitness` — 삭제 (→ metric_store 흡수)

> **ADR-005**: v0.3.1에서 삭제. ctl, atl, tsb, ramp_rate는 metric_store(scope=daily, category=load)로, vo2max는 metric_store(scope=daily, category=capacity)로 이동. UNIQUE(date, source) 구조가 metric_store의 provider 체계와 동일하여 중복 테이블 불필요.

기존 DDL (참조용, 삭제 대상):

-- DEPRECATED: v0.3.1에서 삭제. metric_store로 마이그레이션.
-- CREATE TABLE IF NOT EXISTS daily_fitness (
--     id          INTEGER PRIMARY KEY AUTOINCREMENT,
--     date        TEXT NOT NULL,
--     source      TEXT NOT NULL,
--     ctl         REAL,
--     atl         REAL,
--     tsb         REAL,
--     ramp_rate   REAL,
--     vo2max      REAL,
--     created_at  TEXT DEFAULT (datetime('now')),
--     updated_at  TEXT DEFAULT (datetime('now')),
--     UNIQUE(date, source)
-- );

---

### `metric_store` — 통합 메트릭 저장소 (Layer 2)

모든 알고리즘 산출물, 존 분포, 소스 파생값을 행 단위(EAV)로 저장합니다. provider로 출처 구분, is_primary로 대표값 결정.

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

CREATE INDEX IF NOT EXISTS idx_metric_scope ON metric_store(scope_type, scope_id);
CREATE INDEX IF NOT EXISTS idx_metric_name ON metric_store(metric_name);
CREATE INDEX IF NOT EXISTS idx_metric_primary ON metric_store(scope_type, scope_id, is_primary);
CREATE INDEX IF NOT EXISTS idx_metric_category ON metric_store(category);

17컬럼.

---

### `activity_streams` — 시계열 데이터 (Layer 3)

GPS, 심박, 페이스 등 초 단위 시계열. MetricDef 대상 아님, DDL로만 관리.

CREATE TABLE IF NOT EXISTS activity_streams (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    activity_id     INTEGER NOT NULL,
    source          TEXT NOT NULL,
    elapsed_sec     INTEGER NOT NULL,
    latitude        REAL,
    longitude       REAL,
    altitude_m      REAL,
    heart_rate      INTEGER,
    cadence         INTEGER,
    power_watts     INTEGER,
    speed_ms        REAL,
    pace_sec_km     REAL,
    distance_m      REAL,
    temperature_c   REAL,
    grade_pct       REAL,
    FOREIGN KEY (activity_id) REFERENCES activity_summaries(id)
);

CREATE INDEX IF NOT EXISTS idx_streams_activity ON activity_streams(activity_id, elapsed_sec);

15컬럼.

---

### `activity_laps` — 랩/스플릿 (Layer 3)

CREATE TABLE IF NOT EXISTS activity_laps (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    activity_id     INTEGER NOT NULL,
    source          TEXT NOT NULL,
    lap_index       INTEGER NOT NULL,
    start_time      TEXT,
    duration_sec    REAL,
    distance_m      REAL,
    avg_speed_ms    REAL,
    max_speed_ms    REAL,
    avg_hr          REAL,
    max_hr          REAL,
    avg_cadence     REAL,
    avg_power       REAL,
    elevation_gain  REAL,
    avg_pace_sec_km REAL,
    lap_trigger     TEXT,
    intensity       TEXT,
    FOREIGN KEY (activity_id) REFERENCES activity_summaries(id)
);

CREATE INDEX IF NOT EXISTS idx_laps_activity ON activity_laps(activity_id);

17컬럼.

---

### `activity_best_efforts` — 베스트 에포트 (Layer 3)

CREATE TABLE IF NOT EXISTS activity_best_efforts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    activity_id     INTEGER NOT NULL,
    source          TEXT NOT NULL,
    name            TEXT NOT NULL,
    distance_m      REAL,
    elapsed_sec     REAL,
    moving_sec      REAL,
    start_index     INTEGER,
    end_index       INTEGER,
    pr_rank         INTEGER,
    FOREIGN KEY (activity_id) REFERENCES activity_summaries(id)
);

CREATE INDEX IF NOT EXISTS idx_best_activity ON activity_best_efforts(activity_id);

10컬럼.

---

### `gear` — 장비 (Layer 4)

CREATE TABLE IF NOT EXISTS gear (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    source              TEXT NOT NULL,
    source_gear_id      TEXT NOT NULL,
    name                TEXT,
    brand               TEXT,
    model               TEXT,
    gear_type           TEXT,
    total_distance_m    REAL,
    status              TEXT DEFAULT 'active',
    created_at          TEXT DEFAULT (datetime('now')),
    updated_at          TEXT DEFAULT (datetime('now')),
    UNIQUE(source, source_gear_id)
);

11컬럼. activity_summaries.gear_id와 FK 관계의 참조 테이블.

---

### `weather_cache` — 날씨 캐시 (Layer 4)

open_meteo API 호출 결과를 캐시합니다. Calculator(FEARP, WLEI 등)가 직접 조회하는 독립 캐시. metric_store의 weather 메트릭(원본 API 제공)과는 별개.

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

15컬럼. latitude/longitude는 Python 단에서 소수점 2자리로 rounding 후 저장 (~1.1km 해상도).

---


### `sync_jobs` — 동기화 작업 관리 (Layer 4)

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

13컬럼.

---

### `v_canonical_activities` — 대표 활동 뷰

동일 활동 그룹 중 garmin > intervals > strava > runalyze 우선순위로 대표 1건 선택.

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
                   END,
                   id
           ) AS rn
    FROM activity_summaries
)
SELECT * FROM grouped WHERE rn = 1;

---

### 기타 기존 테이블 처리

| 기존 테이블 | v0.3 처리 | 사유 |
|------------|----------|------|
| activity_detail_metrics | → metric_store 흡수 | EAV 통합 |
| daily_detail_metrics | → metric_store 흡수 | EAV 통합 |
| computed_metrics | → metric_store 흡수 | provider로 구분 |
| athlete_profile | → metric_store(scope='athlete') | 소수 메트릭 |
| athlete_stats | → metric_store(scope='athlete') | 소수 메트릭 |
| activity_exercise_sets | → metric_store(json_value) | ADR-011 참조 |

앱 기능 테이블(chat_messages, goals, planned_workouts, user_training_prefs, session_outcomes)은 데이터 파이프라인과 무관하므로 기존 DDL 그대로 유지.

---

## 1-2. 전체 테이블 요약

**파이프라인 테이블 (10개)**

| # | 테이블 | Layer | 컬럼 | 예상 행 |
|---|--------|-------|------|---------|
| 1 | source_payloads | 0 | 11 | ~3,000 |
| 2 | activity_summaries | 1 | 32* | ~600 |
| 3 | daily_wellness | 1 | 16 | ~1,500 |
| 4 | metric_store | 2 | 17 | ~55,000 |
| 5 | activity_streams | 3 | 15 | ~500,000 |
| 6 | activity_laps | 3 | 17 | ~5,000 |
| 7 | activity_best_efforts | 3 | 10 | ~2,000 |
| 8 | gear | 4 | 11 | ~20 |
| 9 | weather_cache | 4 | 15 | ~1,000 |
| 10 | sync_jobs | 4 | 13 | ~200 |

*activity_summaries는 38컬럼. calories/normalized_power/suffer_score/training_effect_aerobic/training_effect_anaerobic/training_load → metric_store 이동 완료 (Phase 5-G, v12).

**앱 기능 테이블 (5개)**

| # | 테이블 | 비고 |
|---|--------|------|
| 11 | chat_messages | AI 코칭 이력 |
| 12 | goals | 훈련 목표 |
| 13 | planned_workouts | 훈련 계획 |
| 14 | user_training_prefs | 사용자 설정 |
| 15 | session_outcomes | AI 세션 결과 |

**총 15개 테이블 + 1개 뷰** (v0.3.1, daily_fitness 삭제 반영).

---

## 1-3. `metric_registry.py` — 구현 설계

SSOT 파일. 모든 컬럼과 메트릭의 정의를 MetricDef dataclass로 관리합니다.

**v0.3.1 변경사항**: storage 필드 추가 (activity_summary / wellness / metric). Layer 1 컬럼도 MetricDef로 등록. 카테고리 16개 도메인 체계 적용.

| 항목 | 값 |
|------|-----|
| 전체 MetricDef | 184 |
| storage=activity_summary | 32 |
| storage=wellness | 12 |
| storage=metric | 140 |
| 카테고리 | 16 |

하나의 파일로 유지합니다. 카테고리별 주석 섹션으로 구분. alias 검색은 모듈 로드 시 _ALIAS_MAP을 빌드하여 O(1) 조회. 미등록 메트릭은 category='_unmapped'으로 저장 후 주기적으로 확인.

> 카테고리 목록, 메트릭 상세 → `data_master.md`

---

## 1-4. `metric_priority.py` — 구현 설계

is_primary 결정 로직을 담당합니다.

**소스 우선순위**: garmin(1) > intervals(2) > strava(3) > runalyze(4).

**규칙**:
- RunPulse 계산 메트릭 (provider가 'runpulse'로 시작) → 항상 is_primary=1
- 소스 메트릭 → 동일 (scope_type, scope_id, metric_name) 내에서 가장 높은 우선순위 소스가 is_primary=1
- 새 메트릭 upsert 시 같은 그룹의 is_primary를 재계산

**공개 API**: resolve_primary(conn, scope_type, scope_id, metric_name), get_source_priority(source) → int.

---

## 1-5. `db_helpers.py` — 구현 설계

upsert 함수들의 인터페이스입니다.

**activity_summaries 관련**:
- upsert_activity_summary(conn, source, source_id, data: dict) → int (activity_id)
- get_activity(conn, activity_id) → dict
- get_activities_in_range(conn, start_date, end_date) → list[dict]

**daily_wellness 관련**:
- upsert_daily_wellness(conn, date, data: dict) — NULL fill only merge

**metric_store 관련**:
- upsert_metric(conn, scope_type, scope_id, provider, metric_name, category, value, unit) — UPSERT + is_primary 재계산
- get_primary_metrics(conn, scope_type, scope_id) → list[dict]
- get_all_providers_for_metric(conn, scope_type, scope_id, metric_name) → list[dict]
- get_metric_time_series(conn, metric_name, provider, start_date, end_date) → list[dict]

**Layer 3 관련**:
- insert_streams(conn, activity_id, source, records: list[dict])
- insert_laps(conn, activity_id, source, records: list[dict])
- insert_best_efforts(conn, activity_id, source, records: list[dict])

> 구현 상세는 소스 코드 참조: `src/utils/db_helpers.py`

---

## 1-6. 스키마 버전 관리

PRAGMA user_version으로 관리. db_setup.py 실행 시 현재 버전을 확인하고, 필요 시 마이그레이션 실행.

| 버전 | 변경 내용 |
|------|----------|
| 10 | v0.3 초기 스키마 (16 테이블 + 1 뷰) |
| 11 | v0.3.1 — daily_fitness 삭제 (ADR-005: ctl/atl/tsb/vo2max → metric_store) |
| 12 | v0.3.2 — activity_summaries 6컬럼 → metric_store 이동 (calories/normalized_power/suffer_score/training_effect_aerobic/training_effect_anaerobic/training_load) |

---

## 1-7. Phase 1 테스트 계획

| 테스트 파일 | 검증 대상 |
|------------|----------|
| tests/test_db_setup.py | 테이블 생성, 컬럼 수, 제약조건, 인덱스, 뷰 |
| tests/test_metric_registry.py | MetricDef 정의, canonicalize(), alias 충돌, 카테고리 완전성 |
| tests/test_metric_priority.py | is_primary 결정 로직, 소스 우선순위 |
| tests/test_db_helpers.py | upsert, merge, get 함수들 |

검증 스크립트:
- scripts/check_data_consistency.py — SSOT ↔ DDL ↔ DB 교차 검증 (12개 항목)
- scripts/gen_data_master.py — data_master.md 자동 생성

---

## 1-8. Phase 1 작업 순서 & 파일 목록

| 순서 | 파일 | 설명 |
|------|------|------|
| 1 | src/db_setup.py | 전면 재작성 (15 테이블 + 1 뷰) |
| 2 | src/utils/metric_registry.py | SSOT (184 MetricDef) |
| 3 | src/utils/metric_priority.py | is_primary 로직 |
| 4 | src/utils/db_helpers.py | upsert 함수들 |
| 5 | tests/test_*.py | 단위 테스트 |
| 6 | scripts/check_data_consistency.py | 정합성 검증 |
| 7 | scripts/gen_data_master.py | 마스터 시트 생성 |

---

## 1-9. Phase 1 완료 기준 (Definition of Done)

| # | 완료 기준 | 상태 |
|---|----------|------|
| 1 | python src/db_setup.py 실행 시 빈 DB 정상 생성 | ✅ |
| 2 | 15개 테이블 + 1개 뷰 존재 | ✅ (daily_fitness 삭제 완료 v11) |
| 3 | activity_summaries 38컬럼 확인 | ✅ (Phase 5-G 이후 38컬럼, v12) |
| 4 | metric_registry.py에 194 MetricDef, alias 충돌 없음 | ✅ |
| 5 | canonicalize() 테스트 통과 | ✅ |
| 6 | resolve_primary() 테스트 통과 | ✅ |
| 7 | upsert/get 함수 테스트 통과 | ✅ |
| 8 | check_data_consistency.py 🔴 0건 | ✅ |

---

## 구현 결과 (Implementation Result)

### 완료일: 2026-04-03 (v0.3.0), 2026-04-06 (v0.3.1 설계 갱신)

### v0.3.1 설계 변경사항
- daily_fitness 테이블 삭제 → metric_store 흡수 (ADR-005)
- MetricDef에 storage 필드 추가 (ADR-007)
- 카테고리 39개 → 16개 도메인 재설계 (ADR-006)
- activity_summaries 6개 메트릭 컬럼 제거 예정 표시
- 테이블 수 16 → 15 + 1뷰
- check_data_consistency.py, gen_data_master.py 추가

### v0.3.2 설계 변경사항 (Phase 5-G, 2026-04-07)
- activity_summaries 6컬럼 → metric_store 이동 (SCHEMA_VERSION=12)
- calories/normalized_power/suffer_score/training_effect_aerobic/training_effect_anaerobic/training_load
- MetricDef 194개 (신규 4개 추가)

### 테스트 결과
Phase 1 기본 테스트 전체 통과 (883 tests). v0.3.2 Phase 5-G 완료 반영.

---
