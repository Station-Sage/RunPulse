### Phase 4 – 포팅 메트릭 테스트 (2026-04-03)
- tests/test_daniels_table.py: 12 tests (훈련 페이스, 레이스 예측, T-pace 변환)
- tests/test_porting_activity.py: 10 tests (RelativeEffort, WLEI)
- tests/test_porting_daily.py: 25 tests (TEROI, REC, RTTI, CP, RRI, EFTP, VDOTAdj, MarathonShape, CRS, TPDI, SAPI)
- 전체 테스트: 755 passed, 0 failed

# CHANGELOG — RunPulse v0.3 Data Architecture
## [Phase 4 추가] v0.2→v0.3 메트릭 포팅 완료 — 2026-04-03

### Added (13 calculators + 1 utility)
- `src/utils/daniels_table.py` — VDOT 룩업 테이블 (페이스/레이스/볼륨, 보간/역산)
- `src/metrics/relative_effort.py` — 심박존 노력도 (Strava 방식, activity-scope)
- `src/metrics/wlei.py` — 날씨 가중 노력 지수 (activity-scope)
- `src/metrics/teroi.py` — 훈련 효과 ROI (CTL증가/TRIMP 비율)
- `src/metrics/tpdi.py` — 실내/실외 FEARP 격차 지수
- `src/metrics/rec.py` — 통합 러닝 효율성 (EF+Decoupling)
- `src/metrics/rtti.py` — 달리기 내성 지수 (ATL/CTL×wellness)
- `src/metrics/critical_power.py` — CP/W' 임계 파워 (2파라미터 회귀)
- `src/metrics/sapi.py` — 계절 성과 비교 (기온 구간별 FEARP)
- `src/metrics/rri.py` — 레이스 준비도 종합 지수
- `src/metrics/eftp.py` — 역치 페이스 추정 (Daniels T-pace)
- `src/metrics/vdot_adj.py` — VDOT 보정 (역치런/HR회귀)
- `src/metrics/marathon_shape.py` — 마라톤 훈련 완성도
- `src/metrics/crs.py` — 복합 훈련 준비도 (5-gate 필터 + CRS 점수)

### Changed
- `src/metrics/engine.py` — ALL_CALCULATORS 19→32개 확장
- `tests/test_phase4_dod.py` — 32 calculators 대응
- `tests/test_round4.py` — ranges 형식 검증 수정

### Verified
- v0.2 메트릭 14개 전부 v0.3 MetricCalculator 형식으로 포팅 완료
- 전체 708 tests passed, 0 failed

## [Phase 4] Metrics Engine 완료 — 2026-04-03

### Added
- `src/metrics/base.py` — MetricCalculator ABC, CalcResult, CalcContext (prefetch & cache), ConfidenceBuilder
- `src/metrics/trimp.py` — TRIMP (Banister 1991)
- `src/metrics/hrss.py` — HRSS (LTHR 정규화)
- `src/metrics/decoupling.py` — Aerobic Decoupling (needs_streams=True)
- `src/metrics/gap.py` — Grade Adjusted Pace (Minetti 2002, needs_streams=True)
- `src/metrics/classifier.py` — Workout Type Classifier (json_value)
- `src/metrics/vdot.py` — VDOT (Jack Daniels)
- `src/metrics/efficiency.py` — Efficiency Factor
- `src/metrics/fearp.py` — FEARP (환경 보정 + confidence)
- `src/metrics/pmc.py` — ATL/CTL/TSB/Ramp Rate (EMA decay)
- `src/metrics/acwr.py` — ACWR (Acute:Chronic Workload Ratio)
- `src/metrics/lsi.py` — Load Spike Index
- `src/metrics/monotony.py` — Monotony & Training Strain
- `src/metrics/utrs.py` — UTRS (Unified Training Readiness Score, confidence)
- `src/metrics/cirs.py` — CIRS (Composite Injury Risk Score, confidence)
- `src/metrics/di.py` — Durability Index
- `src/metrics/darp.py` — DARP (Dynamic Adjusted Race Predictor)
- `src/metrics/tids.py` — TIDS (Training Intensity Distribution, json_value)
- `src/metrics/rmr.py` — RMR (Runner Maturity Radar, json_value)
- `src/metrics/adti.py` — ADTI (Aerobic Decoupling Trend Index)
- `src/metrics/engine.py` — Topological sort engine, ComputeResult, prefetch, dirty tracking
- `src/metrics/reprocess.py` — Layer 0→1/2 재구축 로직
- `src/metrics/cli.py` — CLI (status, recompute, recompute-all, recompute-single, clear)
- `src/utils/metric_groups.py` — 7개 semantic group + helper functions
- `src/sync/integration.py` — Phase 3→4 통합 (compute_metrics_after_sync)
- `tests/helpers/mock_context.py` — MockCalcContext (DB-less unit testing)
- 10개 테스트 파일, 108개 테스트:
  - `tests/test_trimp_calc.py` — TRIMP/HRSS 단위 테스트
  - `tests/test_activity_calcs.py` — Decoupling/GAP/Classifier/VDOT/EF 테스트
  - `tests/test_daily_calcs.py` — PMC/ACWR/LSI/Monotony 테스트
  - `tests/test_daily2_calcs.py` — UTRS/CIRS/FEARP/RMR/ADTI 테스트
  - `tests/test_engine.py` — Engine topological sort + 통합 테스트
  - `tests/test_phase4_dod.py` — DoD 11항목 검증 (15 tests)
  - `tests/test_round2.py` — ComputeResult/dirty tracking/integration 테스트
  - `tests/test_mock_calcs.py` — MockCalcContext 기반 단위 테스트
  - `tests/test_metric_naming.py` — 메트릭 이름 충돌 검증
  - `tests/test_round4.py` — 메타데이터/semantic grouping/CLI 테스트
  - `tests/test_phase4_spec.py` — 설계서 4-6 누락 케이스 (9 tests)

### Changed
- 19개 calculator에 UI 메타데이터 추가 (display_name, description, unit, ranges, format_type)
- `src/metrics/engine.py` — 중복 코드 제거, _failed 키 반환 추가

### Verified
- Phase 4 DoD 11개 조건 전체 충족
- Phase 4-6 테스트 계획 전체 구현
- 보강 항목 12/12 전부 완료
- 전체 108 tests passed, 0 failed (0.94s)

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
