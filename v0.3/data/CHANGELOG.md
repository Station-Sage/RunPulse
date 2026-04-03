# CHANGELOG — RunPulse v0.3 Data Architecture
## [Phase 3] Sync Orchestrators 완료 — 2026-04-03

### Added
- `src/sync/sync_result.py` — SyncResult dataclass (merge, rate_limited, to_sync_job_dict)
- `src/sync/rate_limiter.py` — 소스별 rate-limit 정책 (garmin 2s, strava 0.5s, intervals 0.3s, runalyze 1s)
- `src/sync/raw_store.py` — payload_hash 기반 변경 감지 wrapper
- `src/sync/_helpers.py` — Extractor → DB adapter
- `src/sync/garmin_activity_sync.py` — Garmin activity sync orchestrator
- `src/sync/garmin_wellness_sync.py` — Garmin wellness sync (6 endpoints)
- `src/sync/strava_activity_sync.py` — Strava OAuth + detail + streams
- `src/sync/intervals_activity_sync.py` — Intervals.icu activity + wellness
- `src/sync/runalyze_activity_sync.py` — Runalyze basic sync
- `src/sync/dedup.py` — 5분/3% cross-source 중복 매칭
- `src/sync/orchestrator.py` — full_sync 통합 진입점 + sync_jobs 기록
- `src/sync/reprocess.py` — Layer 0 → Layer 1/2 재구축 (API 호출 없음)
- `src/sync_cli.py` — CLI 진입점 (sync / reprocess 명령)
- 12개 테스트 파일, 74개 신규 테스트

### Changed
- `src/sync/__init__.py` — v0.2 import 제거, v0.3 orchestrator 진입점으로 교체
- `src/sync/garmin.py`, `strava.py`, `intervals.py` — v0.2 sync 함수 import 제거
- `src/sync/extractors/strava_extractor.py` — start_date_local fallback 추가
- 6개 sync 모듈 datetime.utcnow() → datetime.now(timezone.utc) 경고 제거

### Removed
- v0.2 전용 테스트 52개 파일 삭제 (v0.3 스키마 비호환)

### Verified
- Phase 3 DoD 11개 조건 전체 충족
- 전체 600 tests passed, 0 failed


## [Phase 2] Extractors 완료 - 2026-04-03

### Added
- `src/sync/extractors/` 패키지 (base.py, garmin_extractor.py, strava_extractor.py, intervals_extractor.py, runalyze_extractor.py)
- `src/sync/extractors/__init__.py` — `EXTRACTORS` dict, `get_extractor()` 팩토리 함수
- `src/utils/activity_types.py` — 5개 운동 유형 정규화 모듈
- 7개 fixture JSON 파일 (tests/fixtures/api/)
- 7개 테스트 파일 — 총 83+ 테스트 케이스

### Changed
- Strava `normalized_power`: `extract_activity_metrics` → `extract_activity_core`로 이동 (이중 저장 금지 원칙)

### Verified
- Phase 2 DoD 11개 조건 전체 충족
- Phase 1 테스트 회귀 없음 (64 tests still pass)
- Cross-extractor 일관성 테스트 통과

## [Phase 1] - 2026-04-03

### Added
- **Schema v10**: 12 pipeline tables + 5 app tables + 1 canonical view (`v_canonical_activities`)
  - `source_payloads`, `activity_summaries` (46 cols), `daily_wellness`, `daily_fitness`
  - `metric_store` (EAV, UNIQUE on scope_type/scope_id/metric_name/provider)
  - `activity_streams`, `activity_laps`, `activity_best_efforts`
  - `gear`, `weather_cache`, `sync_jobs`
- **metric_registry.py**: 80+ 메트릭 정의, alias map, canonicalize/lookup API
- **metric_priority.py**: provider 우선순위 (user > rp:ml > rp:formula > rp:rule > garmin > intervals > strava > runalyze)
- **db_helpers.py**: 전 레이어 CRUD 유틸리티 (upsert, batch, merge)
- **test_phase1_schema.py**: 64 test cases (schema, constraints, migration, real DB, performance)

### Changed
- `db_setup.py` 전면 재작성 (SCHEMA_VERSION 4 → 10)
- `conftest.py` fixture 확장 (in-memory + real DB copy)

### Design Decisions
- `weather_cache` UNIQUE 제약에서 SQLite 함수 사용 불가 → Python rounding으로 전환
- Index 생성을 동적 `_safe_create_indexes()`로 변경 (v0.2 호환)
- distance는 meters(SI), speed는 m/s, pace는 sec/km 저장
