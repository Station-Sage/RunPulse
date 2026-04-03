# CHANGELOG — RunPulse v0.3 Data Architecture

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
