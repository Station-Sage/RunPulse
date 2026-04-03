# CHANGELOG — RunPulse v0.3 Data Architecture

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
