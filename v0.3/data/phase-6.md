# Phase 6 — Initial Data Load & Validation

> **브랜치**: `renew/data-architecture`
> **선행 조건**: Phase 1–5 완료 (Schema v11, 4 Extractors, Sync Pipeline, 32 Calculators, Service Layer)
> **작성일**: 2026-04-07

---

## 1. 목표

빈 DB에 모든 역사 데이터를 적재하고, 파이프라인 전체(Layer 0 → 1 → 2 → Dedup → Metric Engine → Primary Resolution)가
정상 동작하는지 자동 검증한다. Phase 6 완료 시 RunPulse는 **실사용 가능 상태**가 된다.

Phase 6a(데이터 적재)와 Phase 6b(검증 & 도구)로 분리하여 순차 진행한다.

---

## 2. Phase 6a — 데이터 적재

### 2-1. 실행 순서 (9 Steps)

| Step | 작업 | 대상 테이블 | 기존 모듈 재활용 | 신규 구현 |
|------|------|------------|-----------------|----------|
| 1 | Garmin Bulk Export ZIP 로드 | source_payloads → activity_summaries, metric_store | garmin_extractor, `_helpers.save_*` | `garmin_bulk_loader.py` |
| 2 | Garmin API 보충 sync | 동일 | garmin_activity_sync.sync() | — |
| 3 | Garmin Wellness sync | daily_wellness, metric_store | garmin_wellness_sync.sync() | — |
| 4 | Strava 전체 sync | source_payloads → activity_summaries, metric_store, streams, best_efforts | strava_activity_sync.sync() | — |
| 5 | Intervals 전체 sync + wellness | activity_summaries, metric_store | intervals_activity_sync.sync(), sync_wellness() | — |
| 6 | Runalyze 전체 sync | activity_summaries, metric_store | runalyze_activity_sync.sync() | — |
| 7 | Dedup | activity_summaries.matched_group_id | dedup.run() | — |
| 8 | Metric Engine 전체 재계산 | metric_store | engine.recompute_all() | days 파라미터 확장 필요 |
| 9 | Primary Resolution | metric_store.is_primary | metric_priority.resolve_all_primaries() | — |

### 2-2. 신규 모듈: GarminBulkLoader

**위치**: `src/sync/garmin_bulk_loader.py`

**역할**: Garmin 계정의 Bulk Export ZIP(JSON 파일만)을 파싱하여 기존 파이프라인에 투입.

**설계 판단**:

- ZIP 안의 JSON 파일만 처리한다. FIT/GPX 파싱은 Phase 6 범위에서 제외한다(디버깅 비용 대비 가치 낮음, JSON으로 충분).
- `source_payloads`에 upsert 후, 기존 `garmin_extractor`로 추출 → `_helpers.save_*` 로 저장하는 흐름을 그대로 탄다.
- `reprocess.py`의 `_reprocess_activity_summaries` 패턴을 참고하되, ZIP → source_payloads 적재 단계가 추가되는 것이 차이.

**핵심 결정 사항**:

- ZIP 내 파일명 패턴: Garmin Export는 `{activityId}_summarizedActivities.json` 형태. 이 파일에서 `entity_id`를 추출한다.
- JSON 파일에 detail/streams가 별도 파일로 존재하면 각각 `activity_detail`, `activity_streams` entity_type으로 저장.
- payload_hash로 중복 방지. 이미 존재하는 payload는 skip.

**반환값**: 로드 결과(total, loaded, skipped, errors) — 기존 `SyncResult`와 유사한 형태.

**테스트**: `tests/test_bulk_loader.py` — 단일 JSON, 복수 JSON, 중복 skip, 잘못된 JSON 처리.

### 2-3. CLI 확장: initial-load 서브커맨드

**위치**: `src/sync_cli.py`에 `initial-load` 서브커맨드 추가

**역할**: Steps 1–9를 순차 실행하는 단일 진입점.

**플래그**:

| 플래그 | 설명 | 기본값 |
|--------|------|--------|
| `--zip-path` | Garmin Bulk Export ZIP 경로 | 필수 (Step 1 실행 시) |
| `--garmin-days` | Garmin API 보충 범위 (일) | 30 |
| `--strava-days` | Strava sync 범위 | 730 |
| `--intervals-days` | Intervals sync 범위 | 730 |
| `--runalyze-days` | Runalyze sync 범위 | 730 |
| `--include-streams` | 스트림 데이터 포함 | False |
| `--recompute-days` | engine.recompute_all의 days 파라미터 | 730 |
| `--steps` | 실행할 step 번호(예: `1,2,3,7,8,9`) | `1,2,3,4,5,6,7,8,9` |
| `--dry-run` | DB 변경 없이 시뮬레이션 | False |

**설계 판단**:

- `--steps` 플래그로 특정 단계만 재실행 가능. Strava rate limit(100/15min, 1000/day)으로 Step 4가 중단될 경우, Step 4만 재실행하면 payload_hash로 이미 로드된 건 skip된다.
- 각 Step 완료 후 `sync_jobs`에 기록. 중단 시 마지막 성공 Step 확인 가능.

**테스트**: `tests/test_initial_load_cli.py` — argparse 파싱, step 순서, dry-run 동작.

### 2-4. engine.recompute_all 수정

**문제**: 현재 `recompute_all(days=90)`이 기본값. 2년치 데이터 적재 시 90일로는 부족.

**변경**: CLI에서 전달되는 `--recompute-days` 값을 `recompute_all(days=N)`으로 넘긴다. 코드 변경은 호출부뿐이며 `engine.py` 자체는 이미 days 파라미터를 받는 구조.

**실행 시간 예측**: 600개 활동 × 32 calculators + 730일 × 24 daily calculators ≈ 수분 내 (SQLite, 로컬). Prefetch가 이미 구현되어 있으므로 병목은 낮다.

### 2-5. Strava Rate Limit 전략

기존 `rate_limiter.py`의 `RATE_POLICIES["strava"]` (window_limit=200/900s, daily_limit=2000) 활용.

**추가 고려**: 2년치 전체 sync 시 활동 수 × API 호출(목록 + 상세 + 스트림) = 약 600 × 3 = 1,800 호출. 1일 리밋(2,000) 내 처리 가능하지만, streams 포함 시 초과 가능. 이 경우 `--steps 4`로 다음날 재실행하면 payload_hash diff로 이어서 진행된다.

### 2-6. 파일 변경 목록

| 파일 | 변경 유형 | 내용 |
|------|----------|------|
| `src/sync/garmin_bulk_loader.py` | 신규 | GarminBulkLoader 클래스 |
| `src/sync_cli.py` | 수정 | initial-load 서브커맨드 추가 |
| `tests/test_bulk_loader.py` | 신규 | BulkLoader 단위 테스트 |
| `tests/test_initial_load_cli.py` | 신규 | CLI 통합 테스트 |

### 2-7. DoD (Phase 6a)

1. `python -m src.sync_cli initial-load --zip-path ... --steps 1,2,3,4,5,6,7,8,9` 에러 없이 완료
2. `source_payloads` 행 수 > 0 (4개 소스 모두)
3. `activity_summaries` 행 수가 예상 범위 내
4. `dedup.run()` 완료, `matched_group_id` 그룹 존재
5. `metric_store`에 RunPulse provider 행 존재
6. `resolve_all_primaries()` 완료, 중복 primary 없음
7. 기존 pytest 전체 pass + 신규 테스트 pass

### 2-8. 예상 공수: ~12h

| 작업 | 시간 |
|------|------|
| GarminBulkLoader 구현 | 3h |
| CLI initial-load 서브커맨드 | 2h |
| BulkLoader 테스트 | 2h |
| CLI 테스트 | 1.5h |
| 실제 데이터 적재 실행 | 2.5h |
| 디버그/수정 | 1h |

---

## 3. Phase 6b — 검증 & 도구

### 3-1. Validation Suite

**위치**: `src/validation/` 패키지

**목적**: 적재된 데이터의 정합성을 12개 자동 체크로 검증. FAIL이 하나라도 있으면 Phase 6 미완료.

**12개 체크 항목**:

| # | 체크명 | 판정 기준 | FAIL 조건 |
|---|--------|----------|----------|
| 1 | row_counts | source_payloads, activity_summaries, metric_store 각각 > 0 | 어느 하나라도 0 |
| 2 | source_distribution | 4개 소스 모두 activity_summaries에 존재 | 어느 소스 누락 |
| 3 | unmapped_metric_ratio | metric_store에서 category=NULL인 비율 < 5% | ≥ 10% |
| 4 | metric_density | 활동당 평균 metric 수 ≥ 5 | < 3 |
| 5 | primary_uniqueness | (scope_type, scope_id, metric_name)별 is_primary=1이 0~1개 | 2개 이상 존재 |
| 6 | provider_distribution | RunPulse provider 메트릭이 존재 | RunPulse 메트릭 0건 |
| 7 | dedup_consistency | matched_group_id 내 동일 소스 중복 없음 | 동일 소스 2건 이상 |
| 8 | data_quality | distance_m, duration_sec에 음수/극단값(마라톤 > 100km 등) 없음 | 극단값 존재 |
| 9 | wellness_coverage | daily_wellness 행이 최근 30일 중 ≥ 20일 | < 15일 |
| 10 | fitness_continuity | metric_store에 ctl/atl/tsb가 연속 존재 | 7일 이상 연속 gap |
| 11 | referential_integrity | activity_streams/laps의 activity_id가 activity_summaries에 모두 존재 | 고아 레코드 존재 |
| 12 | engine_coverage | 32개 calculator의 produces 메트릭 중 metric_store에 존재하는 비율 ≥ 80% | < 50% |

각 체크는 `(name, status, expected, actual, message)` 튜플을 반환한다. status는 PASS / WARN / FAIL.

- WARN: 정상 운영에 문제 없지만 개선 필요 (예: wellness_coverage 15~19일)
- FAIL: 파이프라인 결함. 원인 파악 후 수정 필수.

**설계 판단**:

- Validator는 순수 읽기 전용. DB를 변경하지 않는다.
- 기대값(expected_activity_count 등)은 CLI 인자 또는 config로 받을 수 있지만, 기본값은 "0보다 큼" 수준의 loose check. 정확한 기대값은 사용자가 지정.

### 3-2. Validator CLI

**실행**: `python -m src.validation`

**플래그**:

| 플래그 | 설명 |
|--------|------|
| `--db-path` | DB 경로 (기본: get_db_path()) |
| `--json` | 결과를 JSON으로 출력 |
| `--expected-activities` | 기대 활동 수 (옵션) |
| `--sources` | 기대 소스 목록 (기본: garmin,strava,intervals,runalyze) |

**출력 형식**:

```
═══════════════════════════════════════════════
RunPulse Data Validation Report
═══════════════════════════════════════════════
✅ row_counts          PASS  (sp=2847, as=612, ms=18340)
✅ source_distribution PASS  (4/4 sources)
⚠️ wellness_coverage   WARN  (18/30 days — expected ≥20)
...
═══════════════════════════════════════════════
Result: 10 PASS, 2 WARN, 0 FAIL
═══════════════════════════════════════════════
```

exit code: 0(FAIL 없음), 1(FAIL 있음).

### 3-3. DB Status Dashboard

**위치**: `src/utils/db_status.py`

**역할**: 빠른 상태 확인용. Validator보다 가벼운 요약 정보.

**출력 항목**: 각 테이블 행 수, 소스별 활동 수, 최근 sync_job 시각, primary violation 수, schema version.

**실행**: `python -m src.utils.db_status`

### 3-4. Snapshot Script

**위치**: `scripts/snapshot.sh`

**역할**: 적재 완료 후 DB를 VACUUM → gzip 백업.

**출력**: `data/backups/runpulse_initial_YYYYMMDD.db.gz`

### 3-5. 파일 변경 목록

| 파일 | 변경 유형 | 내용 |
|------|----------|------|
| `src/validation/__init__.py` | 신규 | 패키지 초기화 |
| `src/validation/validator.py` | 신규 | DataValidator 클래스, 12개 체크 |
| `src/validation/__main__.py` | 신규 | CLI 진입점 |
| `src/utils/db_status.py` | 신규 | 상태 대시보드 |
| `scripts/snapshot.sh` | 신규 | DB 백업 스크립트 |
| `tests/test_validator.py` | 신규 | 검증기 테스트 |

### 3-6. DoD (Phase 6b)

1. `python -m src.validation` 실행 시 0 FAIL
2. WARN 항목은 BACKLOG.md에 문서화
3. `python -m src.utils.db_status` 정상 출력
4. `scripts/snapshot.sh` 실행 후 백업 파일 생성 확인
5. 신규 + 기존 pytest 전체 pass

### 3-7. 예상 공수: ~10h

| 작업 | 시간 |
|------|------|
| DataValidator 12개 체크 구현 | 4h |
| Validator CLI | 0.5h |
| DB Status Dashboard | 1h |
| Snapshot Script | 0.5h |
| 테스트 작성 | 2h |
| 실제 검증 실행 + 수정 | 2h |

---

## 4. 전체 완료 기준 (Phase 6 DoD)

1. `initial-load` CLI가 9개 Step 모두 에러 없이 완료
2. `DataValidator.run_all()` 결과 0 FAIL
3. 4개 소스 모두 `source_payloads`에 raw JSON 보존
4. `activity_summaries` 컬럼이 Extractor 출력과 일치
5. 32개 calculator의 메트릭이 `metric_store`에 존재
6. `(scope_type, scope_id, metric_name)`별 is_primary=1이 정확히 0 또는 1개
7. `matched_group_id` 그룹 내 동일 소스 중복 없음
8. 전체 pytest suite (기존 + Phase 6 신규) pass
9. DB 스냅샷 생성: `runpulse_initial_YYYYMMDD.db.gz`

---

## 5. 범위 외 (Out of Scope)

| 항목 | 사유 | 이관 |
|------|------|------|
| v3→v4 마이그레이션 스크립트 | YAGNI — 현재 v0.2 데이터가 운영 중이지 않음 | 필요 시 별도 태스크 |
| FIT/GPX 파일 파서 | JSON으로 충분, 디버깅 비용 높음 | Phase 6.5 또는 LATER |
| 성능 벤치마크 테스트 | 현 단계에서 불필요 | Phase 7 |

---

## 6. 진행 순서

```
Phase 6a                          Phase 6b
───────                          ───────
1. GarminBulkLoader 구현          5. DataValidator 구현
2. CLI initial-load 추가          6. Validator CLI + Dashboard
3. 테스트 작성                     7. 테스트 작성
4. 실제 데이터 적재 실행            8. 검증 실행, WARN/FAIL 수정
                                  9. Snapshot 생성, 문서 업데이트
```

Phase 6a DoD 통과 후 Phase 6b 착수.

---

## 7. 기존 모듈 의존성 맵

Phase 6에서 새로 만드는 것과 기존에 있는 것의 관계를 명확히 한다.

```
[신규] garmin_bulk_loader.py
  ├─ 사용: raw_store.upsert_raw_payload()
  ├─ 사용: extractors.get_extractor("garmin")
  ├─ 사용: _helpers.save_activity_core(), save_metrics(), save_laps()
  └─ 사용: _helpers.resolve_primaries()

[신규] sync_cli.py > initial-load
  ├─ 호출: garmin_bulk_loader.GarminBulkLoader.load()
  ├─ 호출: garmin_activity_sync.sync()
  ├─ 호출: garmin_wellness_sync.sync()
  ├─ 호출: strava_activity_sync.sync()
  ├─ 호출: intervals_activity_sync.sync() + sync_wellness()
  ├─ 호출: runalyze_activity_sync.sync()
  ├─ 호출: dedup.run()
  ├─ 호출: engine.recompute_all()
  └─ 호출: metric_priority.resolve_all_primaries()

[신규] validation/validator.py
  ├─ 읽기: source_payloads, activity_summaries, metric_store
  ├─ 읽기: daily_wellness, activity_streams, activity_laps
  └─ 읽기: sync_jobs
```

---

## 8. CLAUDE.md 업데이트 사항

Phase 6 완료 시 CLAUDE.md Level 3에 `v0.3/data/phase-6.md` 추가.
BACKLOG.md의 NEXT에서 Phase 6 항목을 NOW로 이동 (작업 시작 시).

---

## 9. 설계 판단 근거 (ADR 참조)

| 결정 | 근거 |
|------|------|
| ZIP 내 JSON만 처리 | FIT 파서(fitparse)는 의존성 추가 + 엣지 케이스 다수. Garmin JSON이 이미 활동 요약 + 메트릭 포함 |
| Strava 재시작 전략 | payload_hash diff가 이미 구현되어 있으므로 별도 checkpoint 불필요 |
| recompute_all days 확장 | engine.py가 이미 days 파라미터 지원. 호출부만 변경 |
| Validator를 별도 패키지로 분리 | 운영 도구이며 핵심 파이프라인과 결합도를 낮춘다 |
| Phase 5-G(6컬럼 제거)는 선행 처리 | BACKLOG에 기록됨. Phase 6 시작 전 또는 동시에 처리 |
```

---

이 설계서의 특징:

1. **코드 스니펫 없음** — 목표, 결정, 의존성만 기술. Claude Code가 읽는 토큰을 최소화하면서 구현 방향은 명확히 전달.
2. **기존 모듈 재활용 명시** — 9개 Step 중 신규 구현은 GarminBulkLoader 1개뿐. 나머지는 기존 코드 호출.
3. **Phase 5-G 선행 조건 언급** — BACKLOG의 미완료 항목을 인지하고 있음.
4. **Strava rate limit 대응** — `--steps` 플래그로 중단/재개 가능하다는 점을 설계 수준에서 해결.
5. **engine.recompute_all의 days 문제** — 코드 변경 없이 호출부 인자만 바꾸면 된다는 판단 포함.