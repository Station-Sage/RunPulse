
# RunPulse v0.3 데이터 아키텍처 — Phase별 구현 계획서

## Phase 진행 현황

| Phase | 상태 | 완료일 | 비고 |
|-------|------|--------|------|
| Phase 1 – Schema & Base Infrastructure | ✅ 완료 | 2026-04-03 | 64 tests all pass |
| Phase 2 – Extractors | ✅ 완료 | 2026-04-03 | 11/11 DoD 충족, 7 test files, 83+ tests |
| Phase 3 – Sync Orchestrators | ✅ 완료 | 2026-04-03 | 600 tests, DoD 11/11 충족 |
| Phase 4 – Metric Engine | ✅ 완료 | 2026-04-03 | 19 calculators, engine, 46 tests |
| Phase 5 – Consumer Migration | 🔲 대기 | - | - |
| Phase 6 – Full Data Load | 🔲 대기 | - | - |
| Phase 7 – Future Extensions | 🔲 대기 | - | - |

## 전체 구조 리캡

앞서 합의한 5-Layer 아키텍처를 기반으로 합니다.

**Layer 0** — `source_payloads` (raw JSON 100% 보존)
**Layer 1** — Core tables (`activity_summaries` ~45 cols, `daily_wellness`, `daily_fitness`)
**Layer 2** — `metric_store` (EAV, provider 추적, 모든 scope 통합)
**Layer 3** — Time-series (`activity_streams`, `activity_laps`, `activity_best_efforts`)
**Layer 4** — Materialized / support (`gear`, `weather_cache`, `sync_jobs`, `computed_views`)

핵심 설계 원칙: "provider" 필드로 소스 데이터와 RunPulse 계산값을 동일 테이블에 공존시키되, 출처·버전·우선순위를 완벽히 추적.

---

## Phase 1: 스키마 & 기반 인프라 (예상 2–3일)

### 1-1. `db_setup.py` 전면 재작성

기존 80+ 컬럼의 `activity_summaries`와 15+ 테이블을 정리합니다.

**`source_payloads`** — 변경 없음. 기존 스키마 유지. raw JSON 100% 보존 원칙 강화. `UNIQUE(source, entity_type, entity_id)` 유지하되, 동일 entity의 버전 변경 추적을 위해 `payload_hash`를 활용한 변경 감지 로직 추가.

**`activity_summaries`** — 기존 ~16 INSERT 컬럼에서 ~45 컬럼으로 확장. 모든 소스에서 한 개라도 제공하는 "UI에서 빈번히 조회되는" 필드를 포함합니다. 여기서 핵심 판단 기준은 "3개 소스 공통"이 아니라 "러닝 분석에 필수적이고 리스트/필터/정렬에 쓰이는가"입니다. 따라서 `training_load`, `vo2max_activity`, `suffer_score`, `avg_stride_length_cm`, `avg_vertical_oscillation_mm`, `avg_ground_contact_time_ms`, `avg_temperature` 등 소스 1개에서만 오더라도 중요하면 포함합니다. NULL 허용으로 소스 미제공 시 자연스럽게 처리.

**`metric_store`** — v4 핵심 테이블. 스키마:

```
id INTEGER PRIMARY KEY,
scope_type TEXT NOT NULL,        -- 'activity' | 'daily' | 'weekly' | 'monthly' | 'athlete'
scope_id TEXT NOT NULL,          -- activity_id or 'YYYY-MM-DD' or 'YYYY-Www' or 'athlete'
metric_name TEXT NOT NULL,       -- canonical name (from metric_registry)
category TEXT NOT NULL,          -- 'hr_zone', 'power', 'training_load', 'rp_readiness' ...
provider TEXT NOT NULL,          -- 'garmin' | 'strava' | 'intervals' | 'runalyze' | 'rp_formula' | 'rp_ml' | 'rp_rule' | 'user'
numeric_value REAL,
text_value TEXT,
json_value TEXT,                 -- JSON for complex structures (zone arrays, radar data)
unit TEXT,
algorithm_version TEXT,          -- e.g., 'utrs_v1.2', 'garmin_api_2026q1'
confidence REAL,                 -- 0.0–1.0, for ML outputs or uncertain calculations
raw_name TEXT,                   -- original field name from source (e.g., 'icu_efficiency_factor')
parent_metric_id INTEGER,        -- FK to self, for derivative tracking
is_primary INTEGER DEFAULT 0,    -- resolved display priority
created_at TEXT DEFAULT (datetime('now')),
updated_at TEXT DEFAULT (datetime('now'))
```

`UNIQUE(scope_type, scope_id, metric_name, provider)` — 같은 메트릭을 여러 provider가 각각 저장. `is_primary`로 UI에 보여줄 값을 결정.

**기존 `activity_detail_metrics`, `daily_detail_metrics`, `daily_fitness`, `computed_metrics`를 모두 `metric_store`로 통합.** `daily_wellness`는 Core 테이블로 유지 (sleep, HRV 등 매일 필수 조회).

**추가 테이블 정리:**

| 테이블 | 상태 | 비고 |
|--------|------|------|
| `activity_streams` | 유지 | time-series 전용 |
| `activity_laps` | 유지 | 구조화된 랩 데이터 |
| `activity_best_efforts` | 유지 | PR 추적 |
| `gear` | 유지 | 신발 관리 |
| `weather_cache` | 유지 | Open-Meteo 캐시 |
| `sync_jobs` | 유지 | 동기화 이력 |
| `goals`, `planned_workouts` | 유지 | 훈련 계획 |
| `chat_messages` | 유지 | AI 코칭 이력 |
| `athlete_profile` | 유지 | 사용자 프로필 |

### 1-2. `metric_registry.py` — 메트릭 이름 사전

모든 메트릭의 정규 이름, 카테고리, 단위, 설명, 소스별 원본 이름 매핑을 한 곳에 정의합니다.

```python
REGISTRY = {
    "hr_zone_1_sec": {
        "category": "hr_zone",
        "unit": "seconds",
        "description": "Time in HR Zone 1",
        "aliases": {
            "garmin": "heartRateZones[0].secsInZone",
            "strava": "hr_zone_time_1",
            "intervals": "icu_hr_zone_times[0]",
        }
    },
    "training_load": {
        "category": "training_load",
        "unit": "score",
        "description": "Session training load (TRIMP-based or proprietary)",
        "aliases": {
            "garmin": "activityTrainingLoad",
            "intervals": "icu_training_load",
            "strava": None,  # not provided
        }
    },
    # ... 전체 ~120 항목
}
```

`canonicalize(source, raw_name) → canonical_name` 함수 제공. 매핑에 없으면 `raw_name` 그대로 저장하되 `_unmapped` 카테고리로 분류 → 추후 매핑 추가 시 재처리.

### 1-3. `metric_priority.py` — Provider 우선순위 & Primary 해소

```python
PROVIDER_PRIORITY = [
    "user",           # 사용자 직접 입력/수정 (최우선)
    "rp_ml",          # RunPulse ML 모델 출력
    "rp_ab_winner",   # A/B 테스트 승리 알고리즘
    "rp_formula",     # RunPulse 자체 공식 계산
    "rp_rule",        # RunPulse 규칙 기반
    "garmin",         # 소스 데이터
    "intervals",
    "strava",
    "runalyze",
]
```

`resolve_primary(conn, scope_type, scope_id, metric_name)` — 해당 메트릭의 모든 provider 행을 조회, 우선순위에 따라 `is_primary=1`을 한 행에만 설정.

**A/B 테스트 시나리오**: UTRS를 `rp_formula` (v1.0, 가중치 기반)와 `rp_ml` (v1.0, 회귀 모델)로 동시 계산하여 저장. `algorithm_version`으로 구분. UI에서는 `is_primary=1`인 값만 표시. 관리자 설정에서 어떤 provider를 primary로 할지 전환 가능.

### 1-4. `db_helpers.py` — CRUD 유틸리티

`upsert_activity_summary(conn, data_dict)` — dict → INSERT OR REPLACE
`upsert_metric(conn, scope_type, scope_id, metric_name, provider, value, ...)` — metric_store INSERT OR REPLACE on UNIQUE constraint
`get_primary_metric(conn, scope_type, scope_id, metric_name) → value`
`get_metrics_by_category(conn, scope_type, scope_id, category) → list`
`get_metric_history(conn, metric_name, provider=None, date_range=None) → list` — 시계열 조회

### 1-5. 마이그레이션 전략

기존 DB를 완전히 드롭하고 새로 시작 (데이터가 이미 날아갔으므로). `db_setup.py`에서 `PRAGMA user_version`을 10으로 설정하여 v4 시작점 명시. 향후 마이그레이션은 v10 이후부터 적용.

### Phase 1 산출물

| 파일 | 설명 |
|------|------|
| `src/db_setup.py` | 13개 테이블 DDL, WAL 모드, 인덱스 |
| `src/utils/metric_registry.py` | ~120 메트릭 정의 & 소스 별칭 |
| `src/utils/metric_priority.py` | Provider 우선순위 & resolve 로직 |
| `src/utils/db_helpers.py` | upsert, query 유틸리티 |
| `tests/test_db_setup.py` | 테이블 생성 & 마이그레이션 테스트 |
| `tests/test_metric_registry.py` | canonicalize 매핑 테스트 |
| `tests/test_metric_priority.py` | 우선순위 해소 테스트 |

---

## Phase 2: Extractor 모듈 구현 (예상 3–4일)

### 설계 원칙

Extractor는 **순수 함수**입니다. `raw_json → (core_dict, list[metric_dict])`. DB 접근 없음, side-effect 없음. 따라서 단위 테스트가 매우 쉽습니다.

### 2-1. `src/sync/extractors/base.py`

```python
@dataclass
class CoreActivity:
    """activity_summaries에 들어갈 dict"""
    fields: dict

@dataclass
class MetricRecord:
    """metric_store에 들어갈 한 행"""
    metric_name: str
    category: str
    provider: str
    numeric_value: float | None
    text_value: str | None
    json_value: dict | None
    unit: str | None
    raw_name: str | None
    algorithm_version: str | None
```

`BaseExtractor` ABC: `extract_activity(raw_json) → (CoreActivity, list[MetricRecord])`, `extract_wellness(raw_json) → (dict, list[MetricRecord])`, `extract_fitness(raw_json) → list[MetricRecord]`

### 2-2. `garmin_extractor.py`

가장 데이터가 풍부한 소스. Garmin API 응답 JSON에서 추출할 항목:

**Core (activity_summaries로):**
source, source_id, activity_type (정규화), name, start_time, start_time_local, timezone_offset, distance_m, duration_sec, moving_time_sec, elapsed_time_sec, avg_hr, max_hr, avg_cadence, max_cadence, avg_speed_ms, max_speed_ms, avg_pace_sec_km, best_pace_sec_km, avg_power, max_power, normalized_power, calories, elevation_gain, elevation_loss, avg_stride_length_cm, avg_vertical_oscillation_mm, avg_ground_contact_time_ms, avg_vertical_ratio, training_effect_aerobic, training_effect_anaerobic, training_load, vo2max_activity, avg_temperature, start_lat, start_lon, description

**Metrics (metric_store로, provider='garmin'):**
hr_zone_1_sec ~ hr_zone_5_sec, training_stress_score, intensity_factor, avg_respiration_rate, avg_stress_level, lactate_threshold_hr, lactate_threshold_speed, performance_condition, endurance_score, body_battery_change, avg_spo2, min_spo2 등. 여기에 Garmin이 제공하는 모든 "세컨더리" 데이터를 빠짐없이 추출.

**핵심 포인트**: Garmin API 응답에 있는데 `activity_summaries` 45 컬럼에 없는 필드는 전부 `metric_store`로 갑니다. 어떤 데이터도 버리지 않습니다.

### 2-3. `strava_extractor.py`

**Core**: source, source_id, name, activity_type, start_time, distance_m, duration_sec, moving_time_sec, elapsed_time_sec, avg_hr, max_hr, avg_cadence, avg_speed_ms, max_speed_ms, avg_power, max_power, calories, elevation_gain, avg_temperature, start_lat, start_lon, description, suffer_score

**Metrics**: achievement_count, kudos_count, pr_count, segment_efforts (json), weighted_avg_watts, device_watts (boolean), has_heartrate, average_temp, embed_token 등.

**Streams** (별도 처리 — Phase 3): time, distance, heartrate, velocity_smooth, cadence, altitude, grade_smooth, watts, temp → `activity_streams`

### 2-4. `intervals_extractor.py`

**Core**: source, source_id, name, activity_type, start_time, distance_m, duration_sec, moving_time_sec, avg_hr, max_hr, avg_cadence, max_cadence, avg_speed_ms, max_speed_ms, avg_power, max_power, normalized_power, calories, elevation_gain, elevation_loss, training_load, description

**Metrics**: icu_training_load, trimp, icu_efficiency_factor, icu_ftp, icu_w_prime, icu_power_hr_z2, icu_power_hr_z4, decoupling, icu_hr_zone_times (JSON array), icu_power_zone_times (JSON array), gap (grade adjusted pace), icu_rpe, icu_feel, icu_atl, icu_ctl, variability_index, pace_variation 등.

### 2-5. `runalyze_extractor.py`

**Core**: source, source_id, name, activity_type, start_time, distance_m, duration_sec, avg_hr, max_hr, avg_cadence, elevation_gain, calories

**Metrics**: effective_vo2max, race_prediction_5k ~ marathon, trimp, rpe, cadence_ground_contact_balance, vertical_oscillation, power (if available), temperature_avg 등.

### 2-6. Wellness/Fitness Extractors

각 소스별로 wellness와 fitness 데이터에 대한 extractor도 구현합니다.

**`garmin_wellness_extractor.py`**: sleep_score, sleep_duration_sec, deep_sleep_sec, light_sleep_sec, rem_sleep_sec, awake_sec, avg_spo2, min_spo2, avg_stress, max_stress, body_battery_high, body_battery_low, resting_hr, hrv_status, hrv_sdnn, hrv_rmssd, steps, intensity_minutes, floors_climbed, respiration_rate 등. Core `daily_wellness`에는 주요 6~8개, 나머지는 `metric_store(scope_type='daily')`.

**`intervals_wellness_extractor.py`**: ctl, atl, tsb, hrv_sdnn, avg_sleeping_hr, weight_kg, fatigue, mood, motivation, steps, rpe 등.

### 2-7. 매핑 실패 처리

Extractor가 원본 JSON에서 `metric_registry`에 없는 필드를 발견하면:

1. `metric_name`을 `{source}__{raw_field_name}` 형식으로 저장 (예: `garmin__newMetric2026`)
2. `category`를 `_unmapped`로 설정
3. 로그에 WARNING 출력: `"Unmapped Garmin field: newMetric2026"`
4. 향후 `metric_registry`에 추가하면 `reprocess`로 이름 정규화

이 방식으로 API 스키마가 변경되거나 새 필드가 추가되어도 **데이터를 절대 놓치지 않습니다**.

### Phase 2 산출물

| 파일 | 설명 |
|------|------|
| `src/sync/extractors/__init__.py` | 패키지 |
| `src/sync/extractors/base.py` | 기본 클래스 & 데이터 구조 |
| `src/sync/extractors/garmin_extractor.py` | Garmin activity + wellness |
| `src/sync/extractors/strava_extractor.py` | Strava activity |
| `src/sync/extractors/intervals_extractor.py` | Intervals activity + wellness |
| `src/sync/extractors/runalyze_extractor.py` | Runalyze activity |
| `tests/fixtures/garmin_activity_sample.json` | 익명화된 Garmin 응답 |
| `tests/fixtures/strava_activity_sample.json` | 익명화된 Strava 응답 |
| `tests/fixtures/intervals_activity_sample.json` | 익명화된 Intervals 응답 |
| `tests/test_garmin_extractor.py` | 필드 매핑 검증 |
| `tests/test_strava_extractor.py` | 필드 매핑 검증 |
| `tests/test_intervals_extractor.py` | 필드 매핑 검증 |

---

### Phase 2 구현 결과 (2026-04-03)

**산출물:**

| 파일 | 설명 |
|------|------|
| `src/sync/extractors/__init__.py` | 패키지 + `EXTRACTORS` dict + `get_extractor()` 팩토리 |
| `src/sync/extractors/base.py` | `MetricRecord` dataclass + `BaseExtractor` ABC |
| `src/sync/extractors/garmin_extractor.py` | Garmin activity core/metrics/laps + wellness core/metrics + fitness |
| `src/sync/extractors/strava_extractor.py` | Strava activity core/metrics + streams + best efforts |
| `src/sync/extractors/intervals_extractor.py` | Intervals.icu activity core/metrics + wellness + fitness |
| `src/sync/extractors/runalyze_extractor.py` | Runalyze activity core/metrics + fitness |
| `src/utils/activity_types.py` | 5개 운동 유형 정규화 (running, cycling, swimming, walking, strength) |
| `tests/test_extractor_base.py` | BaseExtractor 헬퍼 단위 테스트 |
| `tests/test_garmin_extractor.py` | Garmin 추출 검증 (core, metrics, laps, wellness, fitness) |
| `tests/test_strava_extractor.py` | Strava 추출 검증 (core, metrics, streams, best efforts) |
| `tests/test_intervals_extractor.py` | Intervals 추출 검증 (core, metrics, wellness, fitness) |
| `tests/test_runalyze_extractor.py` | Runalyze 추출 검증 (core, metrics, fitness) |
| `tests/test_activity_types.py` | 활동 유형 정규화 검증 |
| `tests/test_extractors_cross.py` | 4개 extractor 교차 일관성 테스트 |
| `tests/fixtures/api/garmin/` | activity_summary_minimal.json, activity_detail_minimal.json, wellness_minimal.json |
| `tests/fixtures/api/strava/` | activity_minimal.json |
| `tests/fixtures/api/intervals/` | activity_minimal.json, wellness_minimal.json |
| `tests/fixtures/api/runalyze/` | activity_minimal.json |

**설계 대비 변경 사항:**

1. **`normalized_power` 이중 저장 제거** — 설계서(phase-2.md)에서 Strava의 `weighted_average_watts`를 `extract_activity_metrics`에서 `normalized_power`로 매핑했으나, `normalized_power`는 `activity_summaries` 컬럼이므로 이중 저장 금지 원칙에 위배. `extract_activity_core`로 이동하여 해결.
2. **`get_extractor()` 팩토리 함수 추가** — 설계서에는 `EXTRACTORS` dict만 정의했으나, DoD 조건 2에서 `get_extractor("garmin")` 함수 동작을 요구하여 `__init__.py`에 팩토리 함수 추가. case-insensitive 처리 및 미지원 소스 에러 포함.
3. **`test_extractors_cross.py` 신규 작성** — 설계서 Phase 2 산출물에 없었으나 DoD 조건 10, 11에서 cross-extractor 일관성 테스트를 요구하여 추가.

**완료 기준 (11/11):**

| # | 조건 | 검증 방법 |
|---|------|-----------|
| 1 | 4개 extractor가 BaseExtractor 상속 | `TestCrossExtractorConsistency` |
| 2 | `get_extractor("garmin")` 팩토리 정상 동작 | `TestGetExtractorFactory` (4 tests) |
| 3 | `extract_activity_core()` 필수 4 key 반환 | `TestCoreKeysConsistency` |
| 4 | core dict key가 `activity_summaries` 컬럼명 일치 | `TestCoreKeysConsistency.test_valid_core_keys` |
| 5 | metric_name이 core 컬럼명과 비중복 | `TestMetricNoDuplicateWithCore` (4 sources) |
| 6 | 모든 MetricRecord에 category 설정 | `TestAllMetricsHaveCategory` |
| 7 | distance_m 미터 단위 통일 | `TestDistanceUnit` |
| 8 | `_seconds()` 밀리초/초 자동 판별 | `TestSecondsHelper` (6 cases) |
| 9 | fixture 기반 단위 테스트 전체 통과 | 4 extractor test files |
| 10 | Cross-extractor 일관성 테스트 통과 | `TestCrossExtractorConsistency` (8 checks) |
| 11 | 전체 pytest 통과 | Phase 1 (64) + Phase 2 (83+) all green |

## Phase 3: Sync Orchestrator 재작성 (예상 3–4일)

### 3-1. 새로운 Sync 흐름

```
API call
  → raw JSON
  → source_payloads INSERT (Layer 0)
  → extractor.extract_activity(raw)
    → CoreActivity → activity_summaries UPSERT (Layer 1)
    → list[MetricRecord] → metric_store UPSERT (Layer 2)
  → extractor.extract_streams(raw) [if available]
    → activity_streams INSERT (Layer 3)
  → resolve_primary() for affected metrics
  → commit
```

### 3-2. `garmin_activity_sync.py` 재작성

기존 `garmin.py`의 `sync_activities()`는 ~400줄에 추출 로직이 인라인으로 들어가 있습니다. 이를 분리합니다.

**Orchestrator 책임**: API 호출, 인증, rate-limit 처리, raw 저장, extractor 호출, DB 저장 위임, 에러 핸들링, sync_jobs 기록.

**Extractor 책임**: JSON → dict 변환만. DB 무관.

Rate-limit 전략은 기존 exponential backoff를 유지하되, 429 발생 시 현재까지의 데이터를 즉시 커밋하고 sync_jobs에 `status='partial'`로 기록. 다음 sync에서 이어서 진행.

### 3-3. `strava_activity_sync.py`

Strava는 2-step: 먼저 activity list → 각 activity의 상세 + streams 별도 호출. Streams는 용량이 크므로 별도 함수 `_sync_activity_streams()`로 분리. 200 req/15min 제한 준수.

### 3-4. `intervals_activity_sync.py`

Intervals.icu는 비교적 관대한 rate limit. Activity list + detail을 한 번에 가져올 수 있는 bulk endpoint 활용. Wellness 데이터도 여기서 함께 sync.

### 3-5. `runalyze_activity_sync.py`

가장 제한적인 API. 기본 activity 데이터 + VO2Max 전용 비공식 endpoint 활용.

### 3-6. `wellness_sync.py` (통합)

각 소스의 wellness/daily 데이터를 통합 sync하는 orchestrator. Garmin (sleep, HRV, body battery, stress), Intervals (wellness endpoint), Runalyze (없으면 skip). 결과는 `daily_wellness` (Core) + `metric_store(scope_type='daily')`.

### 3-7. `src/sync/orchestrator.py` — 통합 sync 진입점

```python
def full_sync(conn, sources, days=7):
    """모든 소스를 순차적으로 sync"""
    for source in sources:
        sync_activities(conn, source, days)
        sync_wellness(conn, source, days)
    recompute_metrics(conn, days)  # Phase 4
    resolve_all_primaries(conn)
```

### 3-8. Dedup 재설계

기존 5분/3% 규칙 유지. 하지만 dedup 결과를 `metric_store`에 영향을 주지 않도록 분리. `activity_summaries`에 `matched_group_id`만 설정. `metric_store`에서는 각 소스별 메트릭이 독립적으로 존재하며, UI에서 그룹 내 "best available" 값을 보여줌.

### Phase 3 산출물

| 파일 | 설명 |
|------|------|
| `src/sync/garmin_activity_sync.py` | Garmin sync orchestrator |
| `src/sync/strava_activity_sync.py` | Strava sync orchestrator |
| `src/sync/intervals_activity_sync.py` | Intervals sync orchestrator |
| `src/sync/runalyze_activity_sync.py` | Runalyze sync orchestrator |
| `src/sync/wellness_sync.py` | Daily wellness 통합 sync |
| `src/sync/orchestrator.py` | 진입점 |
| `src/utils/dedup.py` | 리팩토링된 dedup |
| `tests/test_garmin_sync.py` | mock API + DB 검증 |
| `tests/test_dedup.py` | 중복 판정 테스트 |

---

## Phase 4: Metric Engine 재구축 (예상 4–5일)

### 4-1. 설계 철학 변경

기존: `computed_metrics` 테이블에 계산 결과를 별도 저장.
신규: `metric_store`에 `provider='rp_formula'` 또는 `provider='rp_ml'`로 저장. 소스 메트릭과 동일 테이블에 공존.

**이점**: 같은 메트릭 이름에 대해 "Garmin이 계산한 training_load"와 "RunPulse가 계산한 training_load"가 나란히 존재. `is_primary`로 어떤 값을 보여줄지 결정. 사용자가 "Garmin 값 vs RunPulse 값" 비교 UI를 만들기도 쉬움.

### 4-2. Metric Calculator 인터페이스

```python
class MetricCalculator(ABC):
    name: str                    # canonical metric name
    provider: str = "rp_formula" # or "rp_ml", "rp_rule"
    algorithm_version: str       # e.g., "v1.0"
    scope_type: str              # "activity" or "daily" or "weekly"
    required_inputs: list[str]   # 필요한 선행 메트릭/컬럼 목록
    
    @abstractmethod
    def compute(self, context: MetricContext) -> MetricRecord | None:
        ...
```

`MetricContext`는 해당 scope의 activity_summaries 데이터, 관련 metric_store 값, 날짜 범위의 히스토리 등을 lazy-load로 제공.

### 4-3. 1차 메트릭 (소스 데이터 기반 계산)

이들은 소스에서 직접 제공하지 않지만, 소스 데이터로부터 계산 가능한 메트릭입니다.

**Activity-scope:**
- `trimp` — Banister 공식. provider: rp_formula. Garmin/Intervals도 자체 TRIMP을 제공하므로, 3개 값이 공존.
- `hrss` — TRIMP 기반 HR Stress Score.
- `running_tss` (rTSS) — Normalized Grade Pace vs FTP.
- `gap` (Grade Adjusted Pace) — altitude stream 기반. Intervals도 제공하므로 비교 가능.
- `aerobic_decoupling` — 전반/후반 pace:HR ratio.
- `efficiency_factor` — NGP / avg_HR.
- `vdot` — Jack Daniels 공식.
- `variability_index` — NP / avg_pace.
- `workout_type_classification` — 규칙 기반 분류 (easy, tempo, interval, long, race).

**Daily-scope:**
- `atl`, `ctl`, `tsb` — PMC 계산. Intervals도 제공하므로 비교 가능.
- `monotony`, `training_strain` — 7일 TRIMP 기반.
- `acwr` — Acute:Chronic Workload Ratio.
- `lsi` (Load Spike Index) — 당일 부하 / 21일 평균.

### 4-4. 2차 메트릭 (RunPulse 고유)

이들이 차별화 포인트입니다.

**UTRS (Unified Training Readiness Score)** — provider: rp_formula, version: v1.0.
- 입력: body_battery (garmin), tsb (rp_formula 또는 intervals), sleep_score (garmin), hrv_ratio (garmin 또는 intervals), stress (garmin).
- 가중치: body_battery×0.30, TSB×0.25, sleep×0.20, HRV×0.15, stress×0.10.
- `confidence` 필드: 입력 5개 중 몇 개가 실제 존재하는지에 비례 (예: 3/5 = 0.6).

**CIRS (Composite Injury Risk Score)** — provider: rp_formula.
- 입력: ACWR, LSI, consecutive training days, fatigue (CTL-TSB).
- 가중치: ACWR×0.4, LSI×0.3, consecutive×0.2, fatigue×0.1.

**FEARP (Field-Equivalent Adjusted Running Pace)** — provider: rp_formula.
- 입력: actual pace, temperature (weather_cache), humidity, altitude, grade (stream).
- 곱셈 보정 팩터.

**DI (Durability Index)** — provider: rp_formula.
- 입력: 90분 이상 세션의 전반/후반 pace drop.
- NULL 조건: 최근 8주 내 90분+ 세션 3개 미만.

**DARP (Dynamic Adjusted Race Predictor)** — provider: rp_formula.
- 입력: VDOT, DI penalty, Race Shape, EF bonus.

**RMR (Runner Maturity Radar)** — provider: rp_formula.
- 6축: aerobic capacity, threshold intensity, endurance, movement efficiency, recovery, economy.
- json_value로 저장.

**TIDS (Training Intensity Distribution Score)** — provider: rp_formula.
- 입력: HR zone 시간 비율.
- 80/20, Polarized, Pyramid 모델 대비 편차.

**ADTI (Aerobic Decoupling Trend Index)** — provider: rp_formula.
- 주간 decoupling 값의 선형 회귀 기울기.

### 4-5. A/B 테스트 프레임워크

동일 메트릭에 대해 2개 알고리즘을 병렬 실행:

```python
# UTRS v1.0 (가중 평균)
utrs_v1 = UTRSv1Calculator()  # provider="rp_formula", version="utrs_v1.0"

# UTRS v2.0 (XGBoost, 향후)
utrs_v2 = UTRSv2Calculator()  # provider="rp_ml", version="utrs_v2.0"
```

둘 다 `metric_store`에 저장. `metric_priority`에서 현재 어떤 provider를 primary로 할지 설정. 시간이 지나면 v2의 예측 정확도가 높아지면 primary를 전환.

### 4-6. Metric Engine (`src/metrics/engine.py`)

```python
def recompute_recent(conn, days=7):
    """최근 N일 데이터에 대해 모든 metric calculator 실행"""
    calculators = [
        # 1차 (의존성 없음 또는 소스 데이터만 필요)
        TRIMPCalculator(), HRSSCalculator(), GAPCalculator(),
        AerobicDecouplingCalculator(), EfficiencyFactorCalculator(),
        VDOTCalculator(), WorkoutClassifier(),
        
        # 1차 daily
        ATLCTLTSBCalculator(), MonotonyCalculator(), ACWRCalculator(), LSICalculator(),
        
        # 2차 (1차 결과 필요)
        UTRSCalculator(), CIRSCalculator(), FEARPCalculator(),
        DICalculator(), DARPCalculator(), RMRCalculator(),
        TIDSCalculator(), ADTICalculator(),
    ]
    
    # Topological sort by required_inputs
    ordered = topological_sort(calculators)
    
    for calc in ordered:
        for target in get_targets(conn, calc.scope_type, days):
            context = build_context(conn, calc, target)
            result = calc.compute(context)
            if result:
                upsert_metric(conn, ...)
    
    resolve_all_primaries(conn)
```

의존성 그래프를 기반으로 실행 순서를 자동 결정. 순환 의존 방지.

### 4-7. Reprocess 유틸리티

```python
def reprocess_all(conn):
    """Layer 0 raw payload에서 Layer 1, 2를 완전 재구축"""
    # 1. activity_summaries, metric_store(provider in sources) 전부 DELETE
    # 2. source_payloads에서 모든 raw JSON 읽기
    # 3. extractor로 재추출 → Layer 1, 2 INSERT
    # 4. recompute_recent(conn, days=9999) → Layer 2 RunPulse 메트릭 재계산
    # 5. resolve_all_primaries()
```

이 기능 덕분에 extractor 로직을 개선할 때마다 API를 다시 호출하지 않고도 모든 데이터를 재처리할 수 있습니다.

### Phase 4 산출물

| 파일 | 설명 |
|------|------|
| `src/metrics/engine.py` | 메트릭 엔진 (topological execution) |
| `src/metrics/base.py` | MetricCalculator ABC, MetricContext |
| `src/metrics/trimp.py` | TRIMP / HRSS |
| `src/metrics/gap.py` | Grade Adjusted Pace |
| `src/metrics/pmc.py` | ATL / CTL / TSB |
| `src/metrics/acwr.py` | Acute:Chronic Workload Ratio |
| `src/metrics/lsi.py` | Load Spike Index |
| `src/metrics/utrs.py` | Unified Training Readiness Score |
| `src/metrics/cirs.py` | Composite Injury Risk Score |
| `src/metrics/fearp.py` | Field-Equivalent Adjusted Pace |
| `src/metrics/di.py` | Durability Index |
| `src/metrics/darp.py` | Dynamic Adjusted Race Predictor |
| `src/metrics/rmr.py` | Runner Maturity Radar |
| `src/metrics/tids.py` | Training Intensity Distribution |
| `src/metrics/adti.py` | Aerobic Decoupling Trend |
| `src/metrics/classifier.py` | Workout type classification |
| `src/metrics/reprocess.py` | Raw → Layer 1/2 재구축 |
| `tests/test_trimp.py` | 계산 정확도 테스트 |
| `tests/test_utrs.py` | 가중치, confidence 테스트 |
| `tests/test_engine.py` | topological sort, 전체 흐름 |

---

## Phase 5: Consumer 코드 마이그레이션 (예상 2–3일)

### 5-1. Analysis 모듈

기존 `src/analysis/` 모듈들이 직접 DB 쿼리를 하던 것을 `metric_store` 기반으로 전환. `get_primary_metric()`을 통해 조회.

### 5-2. AI Context 생성

`src/ai/ai_context.py` — LLM에 보낼 컨텍스트를 `metric_store`에서 카테고리별로 조회하여 구성. Provider 정보도 포함하여 AI가 "이 값은 Garmin 제공, 이 값은 RunPulse 계산"을 인지하도록.

### 5-3. Web UI Views

대시보드, 활동 목록, 상세 페이지 등에서 `activity_summaries` JOIN `metric_store`로 데이터 조회. 특히 활동 상세에서 "소스별 값 비교" 뷰 추가 가능.

### 5-4. Training Planner

`src/training/planner.py` — UTRS, CIRS 등을 `metric_store`에서 조회하여 훈련 강도 조절.

---

## Phase 6: Full Sync & Validation (예상 2일)

### 6-1. 초기 데이터 로드

1. Garmin ZIP export → `import_history.py` (리팩토링) → Layer 0 저장 → Extractor → Layer 1/2
2. 각 소스 API full sync (전체 기간)
3. Wellness full sync
4. `recompute_recent(conn, days=9999)` — 전체 메트릭 계산
5. `resolve_all_primaries()` 실행

### 6-2. Sanity Checks

```python
def run_sanity_checks(conn):
    # 1. source_payloads row count >= activity_summaries row count
    # 2. metric_store에 _unmapped 카테고리 비율 < 5%
    # 3. 각 activity에 최소 10개 이상 metric 존재
    # 4. UTRS가 계산된 날짜 수 >= daily_wellness 날짜 수 × 0.8
    # 5. 중복 그룹 내 거리 차이 < 3%
    # 6. is_primary=1인 행이 (scope, metric) 당 정확히 1개
    # 7. Provider 분포 통계 출력
```

### 6-3. 회귀 테스트

기존 263 pytest를 새 스키마에 맞게 수정하여 통과 확인. Fixture 기반 테스트 보강.

---

## Phase 7: 향후 확장 준비 (Phase 6 이후)

이 아키텍처가 지원하는 미래 시나리오들:

**멀티 스포츠 확장**: `activity_summaries`에 `sport` 컬럼 추가 (running, cycling, swimming, strength). `metric_store`의 `category`에 `swimming_stroke`, `cycling_power` 등 추가. Extractor만 새로 작성하면 됨.

**ML 파이프라인**: `provider='rp_ml'`로 모델 결과를 `metric_store`에 저장. `algorithm_version`으로 모델 버전 추적. `confidence`로 예측 신뢰도. `parent_metric_id`로 입력 메트릭 추적 (lineage).

**사용자 피드백 루프**: 사용자가 "오늘 컨디션 8/10"을 입력하면 `provider='user'`, `metric_name='perceived_readiness'`로 저장. 이 값이 UTRS ML 모델의 학습 데이터가 됨.

**새로운 메트릭 발굴**: `metric_registry`에 새 항목 추가 → Calculator 작성 → `engine.py`에 등록. 스키마 변경 불필요.

**외부 데이터 통합**: 날씨 (이미 `weather_cache`), 고도, 코스 난이도, 대회 결과 등도 `metric_store(scope_type='activity', category='environment')`로 저장 가능.

---

## 전체 타임라인 요약

| Phase | 내용 | 예상 기간 | 의존성 |
|-------|------|-----------|--------|
| 1 | 스키마 + 기반 인프라 | 2–3일 | 없음 |
| 2 | Extractor 모듈 | 3–4일 | Phase 1 |
| 3 | Sync Orchestrator | 3–4일 | Phase 1, 2 |
| 4 | Metric Engine | 4–5일 | Phase 1, 2 |
| 5 | Consumer 마이그레이션 | 2–3일 | Phase 3, 4 |
| 6 | Full Sync & Validation | 2일 | Phase 3, 4, 5 |

총 **16–21일** (하루 평균 2–3시간 기준).

---

## 핵심 설계 결정 요약

**Q: activity_summaries를 왜 45 컬럼으로 유지하나?**
→ "러닝 분석에 필수적이고 리스트/필터/정렬에 쓰이는" 필드를 와이드 테이블에 두면 `SELECT * FROM activity_summaries WHERE ...` 한 번으로 목록 뷰에 필요한 모든 데이터를 가져옵니다. EAV만으로 목록 뷰를 만들면 JOIN이 폭발합니다. 하지만 45개 이상은 넣지 않고, 나머지는 전부 `metric_store`로.

**Q: metric_store에서 소스 데이터와 RunPulse 계산을 어떻게 구분하나?**
→ `provider` 필드. `garmin`, `strava` 등은 소스 데이터. `rp_formula`, `rp_ml`, `rp_rule`은 RunPulse 계산. `is_primary`로 현재 UI에 보여줄 값 결정. 같은 `metric_name`에 대해 여러 provider 행이 공존.

**Q: A/B 테스트는 어떻게?**
→ `algorithm_version`으로 구분. 예: `utrs_v1.0` (가중 평균)과 `utrs_v2.0` (ML)이 동시 존재. `metric_priority` 설정으로 어느 쪽이 primary인지 제어.

**Q: 새 메트릭 추가 시 스키마 변경 필요?**
→ 없음. `metric_registry`에 등록하고 Calculator 작성만 하면 됨.

---

이 계획에 대해 피드백 부탁드립니다. 특히 다음 사항들을 확인해 주세요:

- `activity_summaries` 45 컬럼의 범위가 적절한지 (더 넓히거나 줄여야 할 부분)
- `metric_store` 단일 테이블 통합이 성능/관리 측면에서 괜찮은지
- Phase 우선순위나 기간 조정이 필요한지