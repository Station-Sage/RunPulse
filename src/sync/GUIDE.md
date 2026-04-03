# src/sync/ GUIDE — v0.3 Sync Orchestrator

## 아키텍처 개요

v0.3에서 sync 모듈은 **5-Layer 파이프라인**의 Layer 0 → Layer 1/2 데이터 흐름을 담당합니다.

    API 호출 → raw_store (Layer 0) → extractor → DB helpers (Layer 1/2)
                                         ↓
                                 SyncResult 반환 → sync_jobs 기록

## 진입점

| 방법 | 명령 |
|------|------|
| CLI (sync) | `python3 src/sync_cli.py sync --source garmin --days 7` |
| CLI (reprocess) | `python3 src/sync_cli.py reprocess --source garmin` |
| Python | `from src.sync.orchestrator import full_sync` |

## 파일 구조

### Core (8개)
| 파일 | 역할 |
|------|------|
| `orchestrator.py` | full_sync() — 전체 sync 통합 진입점, sync_jobs 기록, dedup 실행 |
| `sync_result.py` | SyncResult dataclass — status/counts/errors/retry_after 통합 |
| `rate_limiter.py` | 소스별 rate-limit 정책 + 429 exponential backoff |
| `raw_store.py` | payload_hash 기반 변경 감지 (skip-unchanged) |
| `_helpers.py` | Extractor → DB adapter (save_activity_core, save_metrics 등) |
| `dedup.py` | 5분/3% cross-source 중복 매칭 |
| `reprocess.py` | Layer 0 raw payload → Layer 1/2 재구축 (API 호출 없음) |
| `integration.py` | sync 완료 후 metric engine 자동 실행 (compute_metrics_after_sync) |

### Extractors (6개)
| 파일 | 역할 |
|------|------|
| `extractors/__init__.py` | 패키지 init |
| `extractors/base.py` | BaseExtractor ABC — extract_activity_core/metrics/laps/streams/wellness |
| `extractors/garmin_extractor.py` | Garmin JSON → 정규화 (HR zones, weather, power curve 포함) |
| `extractors/strava_extractor.py` | Strava JSON → 정규화 (weather, best_efforts 포함) |
| `extractors/intervals_extractor.py` | Intervals.icu JSON → 정규화 (HR zones, power curve 포함) |
| `extractors/runalyze_extractor.py` | Runalyze JSON → 정규화 |

### Source Orchestrators (5개)
| 파일 | 소스 | 기능 |
|------|------|------|
| `garmin_activity_sync.py` | Garmin | 활동 목록/상세/스트림 sync |
| `garmin_wellness_sync.py` | Garmin | 6개 wellness endpoint (sleep/HRV/BB/stress/summary/readiness) |
| `strava_activity_sync.py` | Strava | OAuth + 활동 목록/상세/스트림/laps/best_efforts |
| `intervals_activity_sync.py` | Intervals.icu | 활동 + wellness sync |
| `runalyze_activity_sync.py` | Runalyze | 활동 목록 sync |

### Legacy Wrappers (4개) — v0.2 호환용, web layer 참조
| 파일 | 역할 |
|------|------|
| `garmin.py` | check_garmin_connection() + daily/athlete extensions |
| `strava.py` | check_strava_connection() re-export |
| `intervals.py` | check_intervals_connection() re-export |
| `runalyze.py` | (미사용, 향후 정리 대상) |

### 지원 모듈
| 파일 | 역할 |
|------|------|
| `garmin_auth.py` | Garmin 토큰 인증 |
| `garmin_helpers.py` | Garmin 공통 헬퍼 |
| `garmin_v2_mappings.py` | ZIP/detail 필드 매핑 |
| `garmin_backfill.py` | 기존 활동 보강 |
| `garmin_api_extensions.py` | streams/gear/exercise_sets |
| `garmin_athlete_extensions.py` | profile/stats/personal_records |
| `garmin_daily_extensions.py` | race_predictions/training_status 등 |
| `strava_auth.py` | OAuth2 토큰 관리 |
| `strava_activity_sync.py` | (위 orchestrator와 동일) |
| `strava_athlete_sync.py` | 선수 프로필/통계/기어 |
| `intervals_auth.py` | Intervals.icu 인증 |
| `intervals_athlete_sync.py` | 선수 프로필/통계 |
| `intervals_wellness_sync.py` | (intervals_activity_sync.py에 통합) |

## Rate Limit 정책

| 소스 | 요청 간격 | 최대 재시도 | Backoff 기본값 | 일일 한도 |
|------|----------|-----------|--------------|----------|
| Garmin | 2초 | 3회 | 120초 | - |
| Strava | 0.5초 | 3회 | 60초 | 2000 (15분당 200) |
| Intervals | 0.3초 | 2회 | 30초 | - |
| Runalyze | 1초 | 2회 | 60초 | - |

## Sync 흐름 (예: Garmin Activity)

1. API에서 활동 목록 조회 (days 기간)
2. 각 활동에 대해:
   - raw_store.upsert_raw_payload() → 변경 감지
   - 변경 없으면 skip
   - extractor.extract_activity_core() → activity_summaries upsert
   - API에서 상세 조회 → raw payload 저장
   - extractor.extract_activity_metrics() → metric_store upsert
   - extractor.extract_laps() → activity_laps upsert
   - (옵션) streams 조회 → activity_streams upsert
3. resolve_primaries() — `metric_priority.resolve_for_scope()` 호출하여 provider 우선순위 기반 is_primary 플래그 설정
4. `integration.compute_metrics_after_sync()` — synced activity IDs와 affected dates를 metric engine에 전달:
   - `engine.compute_for_activities(conn, activity_ids)` → activity-scope 메트릭 계산
   - `engine.compute_for_dates(conn, dates)` → daily-scope 메트릭 계산
5. SyncResult 반환

## Reprocess 흐름

API 호출 없이 Layer 0 (source_payloads)에서 Layer 1/2를 재구축:

1. clear_first=True면 derived 테이블 초기화
2. activity_summary payload → extract_activity_core → upsert
3. activity_detail payload → extract_metrics + laps → upsert
4. activity_streams payload → extract_streams → upsert
5. wellness payload → extract_wellness_core + metrics → upsert
6. dedup.run() 실행

## 테스트

| 파일 | 테스트 수 | 범위 |
|------|----------|------|
| test_sync_result.py | 5 | SyncResult merge/rate_limited/to_sync_job |
| test_rate_limiter.py | 5 | 정책 로딩/window 제한/429 backoff |
| test_raw_store.py | 5 | payload upsert/hash 변경 감지 |
| test_db_helpers_batch.py | 8 | laps/streams/best_efforts batch upsert |
| test_dedup.py | 6 | 5분/3% 매칭 규칙 |
| test_garmin_activity_sync.py | 7 | Garmin activity sync mock |
| test_garmin_wellness_sync.py | 6 | Garmin wellness 6 endpoint mock |
| test_strava_sync.py | 5 | Strava OAuth + detail mock |
| test_intervals_sync.py | 7 | Intervals activity + wellness mock |
| test_runalyze_sync.py | 5 | Runalyze basic sync mock |
| test_orchestrator.py | 5 | full_sync + dedup + sync_jobs |
| test_reprocess.py | 10 | reprocess rebuild/preserve/dedup |
| **합계** | **74** | |
