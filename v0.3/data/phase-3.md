# Phase 3 상세 설계 — Sync Orchestrator

> 소스: [src/sync/](src/sync/) | 의존: phase-2.md (Extractor), phase-1.md (db_helpers)
> Orchestrator는 **배관공(plumber)**입니다. 비즈니스 로직은 Extractor에, DB 유틸은 db_helpers에, 메트릭 정규화는 registry에 위임합니다. Orchestrator는 이것들을 올바른 순서로 연결하고, 실패 시 안전하게 처리하는 역할만 합니다.

---

## 3-1. 전체 Sync 흐름도

```
orchestrator.full_sync(sources=["garmin","strava","intervals","runalyze"], days=7)
│
├─ garmin_activity_sync.sync(conn, days=7)
│   └─ for each activity:
│       ├─ [1] API: fetch activity list
│       ├─ [2] source_payloads UPSERT (entity_type='activity_summary')
│       ├─ [3] extractor.extract_activity_core(raw) → core_dict
│       ├─ [4] upsert_activity(conn, core_dict) → activity_id
│       ├─ [5] API: fetch activity detail
│       ├─ [6] source_payloads UPSERT (entity_type='activity_detail')
│       ├─ [7] extractor.extract_activity_metrics(summary, detail) → metrics[]
│       ├─ [8] upsert_metrics_batch(conn, 'activity', activity_id, source, metrics)
│       ├─ [9] extractor.extract_activity_laps(detail) → laps[]
│       ├─ [10] upsert_laps_batch(conn, activity_id, laps)
│       ├─ [11] (선택) API: fetch streams → upsert_streams_batch
│       ├─ [12] resolve_all_primaries(conn, 'activity', activity_id)
│       └─ [13] COMMIT (per activity)
│
├─ garmin_wellness_sync.sync(conn, days=7)
│   └─ for each date:
│       ├─ API: fetch sleep, hrv, stress, body_battery, user_summary, training_readiness
│       ├─ source_payloads UPSERT (각 entity_type별)
│       ├─ extractor.extract_wellness_core(date, **payloads) → upsert_daily_wellness
│       ├─ extractor.extract_wellness_metrics(date, **payloads) → upsert_metrics_batch('daily')
│       ├─ extractor.extract_fitness(date, raw) → upsert_daily_fitness  [Phase 5에서 제거]
│       └─ COMMIT (per date)
│
├─ strava_activity_sync / intervals_activity_sync / runalyze_activity_sync
│   └─ (같은 패턴, 소스별 API 호출)
│
├─ dedup.run(conn)
│   └─ matched_group_id 할당
│
└─ SyncResult 집계 반환
```

---

## 3-2. 공통 인터페이스

**소스**: [src/sync/sync_result.py](src/sync/sync_result.py)

### SyncResult 필드

| 필드 | 타입 | 설명 |
|------|------|------|
| source | str | 'garmin' \| 'strava' \| 'intervals' \| 'runalyze' |
| job_type | str | 'activity' \| 'wellness' \| 'streams' |
| status | str | 'success' \| 'partial' \| 'failed' \| 'skipped' |
| total_items | int | 처리 대상 수 |
| synced_count | int | 성공 수 |
| skipped_count | int | 변경 없어 스킵한 수 (hash 동일) |
| error_count | int | 실패 수 |
| api_calls | int | API 호출 횟수 |
| errors | list | [(entity_id, error_msg), ...] |
| retry_after | str? | rate-limit 시 재시도 시각 |

`merge(other)`: 두 결과 합산 (partial sync 이어하기).

---

## 3-3. Rate-Limit 관리

**소스**: [src/sync/rate_limiter.py](src/sync/rate_limiter.py)

### 소스별 Rate Policy

| 소스 | per_request_sleep | backoff_base | 제한 |
|------|------------------|-------------|------|
| garmin | 2.0s | 120s (2→4→8분) | — |
| strava | 0.5s | 60s | daily=2000, window=200/15min |
| intervals | 0.3s | 30s | — |
| runalyze | 1.0s | 60s | — |

429 수신 시: backoff_base × backoff_multiplier^n 지수 백오프, max_retries 초과 시 partial status로 안전 종료.

---

## 3-4. Raw Payload 저장

**소스**: [src/sync/raw_store.py](src/sync/raw_store.py)

`upsert_raw_payload(conn, source, entity_type, entity_id, payload, ...) → bool`

payload_hash(SHA-256)로 변경 감지. 동일 hash이면 False 반환(스킵). 변경 시 `ON CONFLICT DO UPDATE`로 덮어쓰기. entity_type 목록: `activity_summary`, `activity_detail`, `activity_streams`, `wellness_sleep`, `wellness_hrv`, `wellness_stress`, `wellness_body_battery`, `wellness_user_summary`, `wellness_training_readiness`, `wellness_race_predictions`, `wellness_fitness`.

> **Intervals 전용**: `wellness_day`(activity_sync에서 저장), `wellness`(wellness_sync에서 저장) — Intervals API가 단일 엔드포인트로 응답하므로 Garmin처럼 분리되지 않음.

---

## 3-5. Extractor → DB 어댑터

**소스**: [src/sync/_helpers.py](src/sync/_helpers.py) — 설계 대비 추가된 레이어

Orchestrator와 db_helpers 사이의 얇은 어댑터. Extractor 반환값을 db_helpers 호출로 변환합니다.

| 함수 | 역할 |
|------|------|
| save_activity_core(conn, core_dict, source) → int | upsert_activity + activity_id 반환 |
| save_metrics(conn, scope_type, scope_id, source, metrics) | upsert_metrics_batch + resolve_primaries |
| save_laps(conn, activity_id, laps) | upsert_laps_batch |
| save_streams(conn, activity_id, rows) | upsert_streams_batch |
| save_wellness_core(conn, date, core_dict) | upsert_daily_wellness |
| save_daily_fitness(conn, date, source, fitness) | upsert_daily_fitness |
| resolve_primaries(conn, scope_type, scope_id) | resolve_all_primaries |

---

## 3-6. 소스별 Sync 모듈

### 공통 패턴

각 `*_activity_sync.py`는 `sync(conn, days=N) → SyncResult`를 구현합니다. API 클라이언트는 모듈 외부에서 주입받거나 내부에서 생성합니다.

**소스**: [src/sync/garmin_activity_sync.py](src/sync/garmin_activity_sync.py) · [strava_activity_sync.py](src/sync/strava_activity_sync.py) · [intervals_activity_sync.py](src/sync/intervals_activity_sync.py) · [runalyze_activity_sync.py](src/sync/runalyze_activity_sync.py)

### 소스별 특이사항

**Garmin**: 활동 목록 API(summary)와 활동 상세 API(detail) 2단계 호출. detail API에서 HR/Power zone, weather, splits 추출. Wellness는 date별로 6개 엔드포인트 분리 호출([garmin_wellness_sync.py](src/sync/garmin_wellness_sync.py)).

**Strava**: streams는 선택적(활동당 별도 호출). detail이 summary를 보강하므로 `detail_raw or summary_raw`로 처리. best_efforts는 detail_raw에서 추출.

**Intervals**: 활동 API 응답에 wellness 데이터(CTL/ATL/TSB/HRV)가 포함됨. activity_sync에서 extract_wellness_core/extract_fitness도 함께 처리. wellness 전용 sync는 [intervals_wellness_sync.py](src/sync/intervals_wellness_sync.py)에 별도 존재.

**Runalyze**: export JSON 형식. `s` 필드가 duration(초), `kcal`이 calories. distance는 미터 또는 km 혼용(extractor에서 처리).

### 추가 파일 (설계 대비 확장)

| 파일 | 역할 |
|------|------|
| garmin_auth.py / strava_auth.py / intervals_auth.py | OAuth 토큰 관리 |
| garmin_helpers.py | Garmin 전용 헬퍼 (vo2max 저장 등) |
| garmin_daily_extensions.py | 일별 ATL/CTL 등 확장 |
| garmin_athlete_extensions.py / garmin_api_extensions.py | 선수 프로필, API 확장 |
| garmin_v2_mappings.py | Garmin API v2 필드 매핑 |
| garmin_backfill.py | 과거 데이터 일괄 적재 |
| intervals_athlete_sync.py / strava_athlete_sync.py | 선수 프로필 sync |
| integration.py | 통합 테스트 유틸리티 |

---

## 3-7. `dedup.py` — 중복 매칭

**소스**: [src/sync/dedup.py](src/sync/dedup.py)

### 매칭 알고리즘

```
TIME_TOLERANCE_MINUTES = 5
DISTANCE_TOLERANCE_PCT = 3.0
```

서로 다른 source의 활동이 `start_time 5분 이내 + distance_m 3% 이내`이면 동일 활동으로 판정. `matched_group_id`(UUID)를 공유 활동에 할당. `v_canonical_activities` 뷰가 이 group_id로 대표 1건(garmin > intervals > strava > runalyze)을 선택.

`run(conn) → int`: 전체 매칭 재실행. matched_group_id를 모두 초기화 후 재계산.

---

## 3-8. `reprocess.py` — Layer 0 → Layer 1/2 재구축

**소스**: [src/sync/reprocess.py](src/sync/reprocess.py)

architecture.md Part 6의 **재처리 경로 1**을 구현합니다 (Extractor 수정 후 실행).

내부 함수 분리 (설계 단일 함수 → 6개 구현):

| 함수 | 역할 |
|------|------|
| `_clear_derived_data(conn)` | activity_summaries / metric_store / daily_wellness 초기화 |
| `_reprocess_activity_summaries(conn)` | entity_type='activity_summary' payload → extract_activity_core |
| `_reprocess_activity_details(conn)` | entity_type='activity_detail' → extract_activity_metrics |
| `_reprocess_activity_streams(conn)` | entity_type='activity_streams' → extract_activity_streams |
| `_reprocess_best_efforts(conn)` | best_efforts → insert_best_efforts |
| `_reprocess_wellness(conn)` | entity_type='wellness_*' → extract_wellness_core/metrics |

공개 API: `reprocess_all(conn)` — 순서대로 6개 함수 실행. source_payloads는 보존.

---

## 3-9. db_helpers 추가분 (Phase 3)

**소스**: [src/utils/db_helpers.py](src/utils/db_helpers.py)

| 함수 | 역할 |
|------|------|
| upsert_metrics_batch(conn, scope_type, scope_id, source, metrics) | MetricRecord 리스트 일괄 upsert |
| upsert_laps_batch(conn, activity_id, laps) | activity_laps 배치 INSERT |
| upsert_streams_batch(conn, activity_id, rows) | activity_streams 전체 교체 (DELETE+INSERT) |
| upsert_best_efforts_batch(conn, activity_id, efforts) | activity_best_efforts 배치 |
| record_sync_job(conn, result) | sync_jobs 테이블에 SyncResult 기록 |

streams는 전체 교체 전략 (기존 DELETE 후 INSERT) — 부분 업데이트보다 단순하고 안전.

---

## 3-10. CLI

**소스**: [src/sync_cli.py](src/sync_cli.py) (설계 `src/sync.py`에서 이름 변경 — sync/ 패키지와 충돌 방지)

```
python3 src/sync_cli.py sync --source garmin --days 7
python3 src/sync_cli.py sync --source all --days 30
python3 src/sync_cli.py reprocess
```

---

## 3-11. 파일 구조

    src/sync/
    ├── __init__.py
    ├── orchestrator.py          # full_sync() 통합 진입점
    ├── sync_result.py           # SyncResult dataclass
    ├── rate_limiter.py          # 소스별 rate-limit 정책
    ├── raw_store.py             # source_payloads UPSERT (hash 기반)
    ├── _helpers.py              # Extractor → DB 어댑터
    ├── dedup.py                 # cross-source 중복 매칭
    ├── reprocess.py             # Layer 0 → Layer 1/2 재구축
    ├── garmin_activity_sync.py
    ├── garmin_wellness_sync.py
    ├── garmin_auth.py / garmin_helpers.py / garmin_v2_mappings.py
    ├── garmin_daily_extensions.py / garmin_athlete_extensions.py
    ├── garmin_api_extensions.py / garmin_backfill.py
    ├── strava_activity_sync.py / strava_auth.py / strava_athlete_sync.py
    ├── intervals_activity_sync.py / intervals_wellness_sync.py
    ├── intervals_auth.py / intervals_athlete_sync.py
    ├── runalyze_activity_sync.py / runalyze.py
    ├── integration.py
    └── extractors/              # Phase 2

    src/sync_cli.py              # CLI 진입점

---

## 3-12. 테스트 전략

| 테스트 파일 | 검증 대상 |
|------------|---------|
| test_sync_result.py | SyncResult 필드, merge() |
| test_rate_limiter.py | 소스별 policy, 429 backoff |
| test_raw_store.py | hash 비교, UPSERT |
| test_db_helpers_batch.py | laps/streams/metrics batch upsert |
| test_dedup.py | 5분/3% 매칭, group_id 할당 |
| test_garmin_activity_sync.py | mock API, core→metrics 흐름 |
| test_garmin_wellness_sync.py | 6개 payload 통합 |
| test_strava_sync.py / test_intervals_sync.py / test_runalyze_sync.py | 소스별 mock |
| test_orchestrator.py | full_sync 흐름 |
| test_reprocess.py | Layer 0→1/2 재구축 |

---

## 3-13. 완료 기준 (DoD)

| # | 완료 기준 | 상태 |
|---|----------|------|
| 1 | sync --source garmin 정상 동작 | ✅ |
| 2 | sync --source strava 정상 동작 | ✅ |
| 3 | sync --source intervals 정상 동작 | ✅ |
| 4 | reprocess Layer 0→1/2 재구축 | ✅ |
| 5 | source_payloads 행 수 ≥ activity_summaries | ✅ |
| 6 | 활동당 metric_store 메트릭 최소 5개 | ✅ |
| 7 | metric_store 전 행에 16-domain category 설정 | ✅ (phase-2 extractor 수정으로 완전 해소) |
| 8 | (scope, scope_id, metric_name) 당 is_primary=1 정확히 1개 | ✅ |
| 9 | Dedup cross-source 매칭 (전체 초기화 후 재계산) | ✅ (2026-04-07 incremental 버그 수정) |
| 10 | 429 시 partial status 안전 종료 | ✅ |
| 11 | 전체 테스트 통과 | ✅ (795 passed, 2026-04-07) |

**Phase 3 완료일: 2026-04-03 / 코드 정합성 수정: 2026-04-07**

---

## 3-14. 구현 결과 & 설계 대비 변경 로그

**이름 변경**:
- `_calculate_retry_after()` → `_retry_after()` (간소화)
- `_sync_streams()` → `_fetch_and_save_streams()` (역할 명확화)
- `run_dedup()` → `run()` (dedup 모듈명 중복 제거)
- `src/sync.py` → `src/sync_cli.py` (패키지 충돌 방지)

**구조 확장**:
- `reprocess_all()` 단일 → 6개 내부 함수 분리 (명확성)
- `_helpers.py` 추가 — Extractor→DB 어댑터 레이어 (설계에 미포함)
- 테스트: 설계 5개 → 실제 12개 파일, 74개 테스트

**버그 수정** (설계 외):
- `strava_extractor.py`: `start_date` → `start_date_local` fallback 추가
- 6개 sync 모듈: `datetime.utcnow()` → `datetime.now(timezone.utc)` (Python 3.12)
- `intervals_activity_sync.py`: wellness extractor 키워드 `wellness_day` → `wellness` 수정

**Phase 3 코드 정합성 수정** (2026-04-07):
- `dedup.run()`: incremental 방식 → 설계대로 전체 초기화 후 재계산 (C 소스 추가 시 기존 A↔B 그룹에 합류 불가 버그 수정)
- Garmin wellness entity_type: `sleep_day`/`hrv_day`/`body_battery_day`/`stress_day`/`user_summary_day`/`training_readiness` → `wellness_sleep`/`wellness_hrv`/`wellness_body_battery`/`wellness_stress`/`wellness_user_summary`/`wellness_training_readiness` (설계 spec 통일)
- 동일 rename 반영: `garmin_extractor.py`, `reprocess.py`, `tests/fixtures/wellness_minimal.json`, `test_reprocess.py`, `test_garmin_wellness_sync.py`
- M-6 (category 구버전 잔존): phase-2 extractor 수정으로 해소 (check_data_consistency.py Check 10/11/12 전부 통과)
