
# Phase 4 상세 설계 — Metrics Engine 재구축

## 4-0. Phase 4의 목표

`activity_summaries`(Layer 1)와 `metric_store`(Layer 2, 소스 데이터)의 데이터를 입력으로, RunPulse 자체 메트릭을 계산해 `metric_store`에 `provider=runpulse:*`로 저장한다.

핵심 원칙:
- 모든 calculator는 `metric_store`에서 읽고 `metric_store`에 쓴다 (동일 테이블, provider만 다름)
- 의존성 그래프를 자동 해소한다 (TRIMP → ATL/CTL → ACWR → CIRS 순서)
- 데이터 부족 시 `None` 반환, `confidence` 필드로 신뢰도 표시
- 재계산 용이: `provider LIKE 'runpulse%'` 행만 삭제 후 재실행

---

## 4-1. CalcContext API

Calculator는 raw SQL 직접 사용 금지 (ADR-009). `CalcContext` API만 사용.

| 메서드 | 시그니처 | 설명 |
|--------|----------|------|
| `activity` | property | 현재 활동의 activity_summaries 행 (prefetch-first) |
| `get_metric` | `(metric_name, provider=None, scope_type=None, scope_id=None)` | 현재 scope의 primary 메트릭 numeric 값 |
| `get_metric_json` | `(metric_name, provider=None)` | 현재 scope의 메트릭 JSON 값 |
| `get_metric_text` | `(metric_name)` | 현재 scope의 메트릭 text 값 |
| `get_wellness` | `(date=None)` | 특정 날짜의 daily_wellness (prefetch-first) |
| `get_streams` | `(activity_id=None)` | 활동의 스트림 데이터 (activity_streams) |
| `get_laps` | `(activity_id=None)` | 활동의 랩 데이터 (activity_laps) |
| `get_activities_in_range` | `(days, activity_type=None)` | 과거 N일간 활동 목록 (v_canonical_activities) |
| `get_activity_metric` | `(activity_id, metric_name)` | 특정 활동의 메트릭 numeric 값 (prefetch-first) |
| `get_activity_metric_text` | `(activity_id, metric_name)` | 특정 활동의 메트릭 text 값 |
| `get_daily_metric_series` | `(metric_name, days, provider=None)` | 과거 N일간 일별 메트릭 시계열 `[(date, value), ...]` |
| `get_daily_load` | `(date_str)` | 특정 날짜의 TRIMP 합산 (prefetch-first, PMC/LSI/Monotony용) |
| `get_activity_metric_series` | `(metric_name, days, activity_type=None, include_json=False)` | 과거 N일간 activity-scope 메트릭 시계열 |
| `get_wellness_series` | `(days, fields=None)` | 과거 N일간 daily_wellness 시계열 |
| `update_metric_cache` | `(metric_name, provider, numeric, text, json_val)` | 후속 calculator용 캐시 업데이트 (engine 내부용) |

> **변경 이력**: 초기 설계 대비 ADR-009 도입 후 prefetch-first 구조로 전환. `get_activity_metric_text`, `get_activity_metric_series`, `get_wellness_series`, `get_daily_load`, `get_laps`, `update_metric_cache` 신규 추가.

---

## 4-2. MetricCalculator 인터페이스

`src/metrics/base.py: MetricCalculator` (추상 클래스)

| 속성/메서드 | 타입 | 설명 |
|-------------|------|------|
| `name` | `str` | 메트릭 이름 (metric_store key) |
| `category` | `str` | rp_* 카테고리 (예: rp_load) |
| `scope_type` | `str` | `"activity"` 또는 `"daily"` |
| `produces` | `list[str]` | 이 calculator가 생성하는 메트릭 이름 목록 |
| `requires` | `list[str]` | 선행 필요 메트릭 이름 목록 (의존성 그래프용) |
| `needs_streams` | `bool` | 스트림 데이터 필요 여부 |
| `compute(ctx)` | `→ list[CalcResult]` | 계산 실행 (추상 메서드) |

`CalcResult` 필드: `name`, `numeric_value`, `text_value`, `json_value`, `confidence`, `provider`

`ConfidenceBuilder`: `utrs`, `cirs` 등 복합 메트릭의 신뢰도 점수 계산 헬퍼.

---

## 4-3. Calculator 인벤토리 (32개)

### Activity-scope (8개)

| 클래스 | name | produces | requires | category |
|--------|------|----------|----------|----------|
| `TRIMPCalculator` | trimp | trimp | — | rp_load |
| `RelativeEffortCalculator` | relative_effort | relative_effort | — | rp_load |
| `WLEICalculator` | wlei | wlei | trimp | rp_load |
| `HRSSCalculator` | hrss | hrss | trimp | rp_load |
| `AerobicDecouplingCalculator` | aerobic_decoupling_rp | aerobic_decoupling_rp | — | rp_efficiency |
| `EfficiencyFactorCalculator` | efficiency_factor_rp | efficiency_factor_rp | — | rp_efficiency |
| `GAPCalculator` | gap_rp | gap_rp | — | rp_performance |
| `VDOTCalculator` | runpulse_vdot | runpulse_vdot | — | rp_performance |
| `FEARPCalculator` | fearp | fearp | — | rp_performance |
| `WorkoutClassifier` | workout_type | workout_type | — | rp_classification |

### Daily-scope (22개)

| 클래스 | name | produces | requires | category |
|--------|------|----------|----------|----------|
| `PMCCalculator` | ctl | ctl, atl, tsb, ramp_rate | trimp | rp_load |
| `ACWRCalculator` | acwr | acwr | ctl, atl | rp_load |
| `LSICalculator` | lsi | lsi | trimp | rp_load |
| `MonotonyStrainCalculator` | monotony | monotony, training_strain | trimp | rp_load |
| `RTTICalculator` | rtti | rtti | ctl, atl | rp_load |
| `UTRSCalculator` | utrs | utrs | tsb | rp_readiness |
| `CRSCalculator` | crs | crs | acwr, tsb, cirs | rp_readiness |
| `CIRSCalculator` | cirs | cirs | acwr, lsi, ctl | rp_risk |
| `DICalculator` | di | di | — | rp_endurance |
| `DARPCalculator` | darp | darp_5k, darp_10k, darp_half, darp_marathon | runpulse_vdot | rp_prediction |
| `TIDSCalculator` | tids | tids | workout_type | rp_distribution |
| `RMRCalculator` | rmr | rmr | tsb | rp_recovery |
| `ADTICalculator` | adti | adti | ctl | rp_trend |
| `TEROICalculator` | teroi | teroi | ctl, trimp | rp_trend |
| `TPDICalculator` | tpdi | tpdi | fearp | rp_trend |
| `RECCalculator` | rec | rec | efficiency_factor_rp, aerobic_decoupling_rp | rp_efficiency |
| `CriticalPowerCalculator` | critical_power | critical_power | power_curve | rp_performance |
| `SAPICalculator` | sapi | sapi | fearp | rp_performance |
| `RRICalculator` | rri | rri | runpulse_vdot, ctl, di | rp_performance |
| `EFTPCalculator` | eftp | eftp | runpulse_vdot | rp_performance |
| `VDOTAdjCalculator` | vdot_adj | vdot_adj | runpulse_vdot | rp_performance |
| `MarathonShapeCalculator` | marathon_shape | marathon_shape | runpulse_vdot | rp_performance |

---

## 4-4. Engine 실행 모델

**파일**: `src/metrics/engine.py`

### 실행 흐름

```
recompute_recent(conn, days)
  └─ activity-scope:
       1. _topological_sort(activity_calculators)
       2. 각 activity 대상 순서대로 compute()
       3. metric_store에 upsert (provider='runpulse:formula_v1')
  └─ daily-scope:
       1. _topological_sort(daily_calculators)
       2. 각 date 대상 순서대로 compute()
       3. metric_store에 upsert
```

### Prefetch 전략

engine이 CalcContext 생성 시 prefetch:
- `_prefetched_activities`: `{activity_id: row_dict}`
- `_prefetched_metrics`: `{(scope_type, scope_id, metric_name): row}`
- `_prefetched_wellness`: `{date: wellness_dict}`
- `_prefetched_daily_loads`: `{date: trimp_sum}`

Calculator 실행 후 `update_metric_cache()`로 캐시 갱신 → 후속 calculator가 즉시 참조 가능.

### ComputeResult 필드

| 필드 | 설명 |
|------|------|
| `succeeded` | 성공 건수 |
| `failed` | 실패 건수 |
| `skipped` | 건너뜀 건수 (데이터 부족) |
| `errors` | `[(calculator_name, error_msg), ...]` |

### Dirty Tracking

- `needs_streams=True`인 calculator만 `get_streams()` 호출
- `recompute_all()`: 전체 재계산
- `clear_runpulse_metrics()`: `provider LIKE 'runpulse%'` 행 삭제

---

## 4-5. SEMANTIC_GROUPS (13개)

`src/utils/metric_groups.py: SEMANTIC_GROUPS`

| key | display_name | primary member (runpulse) | 비교 소스 |
|-----|--------------|---------------------------|-----------|
| trimp | TRIMP | trimp | intervals |
| training_load | 훈련 부하 | hrss, wlei, rtti | garmin, intervals, strava |
| training_trend | 훈련 트렌드 | teroi, tpdi, adti | — |
| readiness | 훈련 준비도 | crs, utrs | garmin |
| recovery | 회복 상태 | rmr | garmin (body_battery) |
| relative_effort | 상대적 노력도 | relative_effort | strava, intervals |
| decoupling | 유산소 분리 | aerobic_decoupling_rp | intervals |
| running_efficiency | 러닝 효율성 | rec, efficiency_factor_rp | intervals |
| vo2max | VO2Max | runpulse_vdot | garmin, runalyze |
| vdot | VDOT | runpulse_vdot, vdot_adj | garmin, runalyze |
| race_prediction | 레이스 예측 | darp_5k/10k/half/marathon, rri, marathon_shape | — |
| threshold_power | 임계 파워/페이스 | critical_power, eftp | intervals |
| seasonal_performance | 환경별 성과 | sapi, fearp | — |

---

## 4-6. 파일 구조

```
src/metrics/
├── __init__.py         # 패키지 진입점
├── base.py             # MetricCalculator, CalcContext, CalcResult, ConfidenceBuilder
├── engine.py           # MetricsEngine, ALL_CALCULATORS, _topological_sort
├── cli.py              # recompute CLI 진입점
├── reprocess.py        # reprocess_metrics() (phase 3 통합)
│
├── trimp.py            # TRIMPCalculator
├── hrss.py             # HRSSCalculator
├── relative_effort.py  # RelativeEffortCalculator
├── wlei.py             # WLEICalculator
├── decoupling.py       # AerobicDecouplingCalculator
├── efficiency.py       # EfficiencyFactorCalculator
├── gap.py              # GAPCalculator
├── vdot.py             # VDOTCalculator
├── fearp.py            # FEARPCalculator
├── classifier.py       # WorkoutClassifier
│
├── pmc.py              # PMCCalculator
├── acwr.py             # ACWRCalculator
├── lsi.py              # LSICalculator
├── monotony.py         # MonotonyStrainCalculator
├── rtti.py             # RTTICalculator
├── utrs.py             # UTRSCalculator
├── crs.py              # CRSCalculator
├── cirs.py             # CIRSCalculator
├── di.py               # DICalculator
├── darp.py             # DARPCalculator
├── tids.py             # TIDSCalculator
├── rmr.py              # RMRCalculator
├── adti.py             # ADTICalculator
├── teroi.py            # TEROICalculator
├── tpdi.py             # TPDICalculator
├── rec.py              # RECCalculator
├── critical_power.py   # CriticalPowerCalculator
├── sapi.py             # SAPICalculator
├── rri.py              # RRICalculator
├── eftp.py             # EFTPCalculator
├── vdot_adj.py         # VDOTAdjCalculator
└── marathon_shape.py   # MarathonShapeCalculator
```

관련 유틸:
- `src/utils/metric_groups.py` — SEMANTIC_GROUPS 정의
- `src/utils/metric_registry.py` — METRIC_REGISTRY (SSOT)

---

## 4-7. 테스트 전략

| 파일 | 대상 |
|------|------|
| `tests/metrics/test_trimp.py` | TRIMPCalculator |
| `tests/metrics/test_hrss.py` | HRSSCalculator |
| `tests/metrics/test_pmc.py` | PMCCalculator (ctl/atl/tsb) |
| `tests/metrics/test_acwr.py` | ACWRCalculator |
| `tests/metrics/test_cirs.py` | CIRSCalculator |
| `tests/metrics/test_utrs.py` | UTRSCalculator |
| `tests/metrics/test_vdot.py` | VDOTCalculator |
| `tests/metrics/test_darp.py` | DARPCalculator |
| `tests/metrics/test_classifier.py` | WorkoutClassifier |
| `tests/metrics/test_relative_effort.py` | RelativeEffortCalculator |
| `tests/metrics/test_wlei.py` | WLEICalculator |
| `tests/metrics/test_teroi.py` | TEROICalculator |
| `tests/metrics/test_tpdi.py` | TPDICalculator |
| `tests/metrics/test_rec.py` | RECCalculator |
| `tests/metrics/test_rtti.py` | RTTICalculator |
| `tests/metrics/test_critical_power.py` | CriticalPowerCalculator |
| `tests/metrics/test_eftp.py` | EFTPCalculator |
| `tests/metrics/test_sapi.py` | SAPICalculator |
| `tests/metrics/test_rri.py` | RRICalculator |
| `tests/metrics/test_vdot_adj.py` | VDOTAdjCalculator |
| `tests/metrics/test_marathon_shape.py` | MarathonShapeCalculator |
| `tests/metrics/test_crs.py` | CRSCalculator |
| `tests/metrics/test_engine.py` | MetricsEngine 통합 |

공통 패턴: MockCalcContext (DB-less) 사용. 각 파일에 mock 포함.

---

## 4-8. DoD

| # | 완료 기준 | 상태 |
|---|----------|------|
| 1 | ALL_CALCULATORS에 32개 calculator 등록 | ✅ |
| 2 | `_topological_sort()` 의존성 순서 해소 (TRIMP → PMC → ACWR → CIRS) | ✅ |
| 3 | `recompute_recent(conn, days=7)` 에러 없이 완료 | ✅ |
| 4 | metric_store에 `provider LIKE 'runpulse%'` 행 존재 | ✅ |
| 5 | 각 activity에 최소 TRIMP, workout_type, efficiency_factor 3개 이상 | ✅ |
| 6 | 각 date에 최소 CTL, ATL, TSB, UTRS 4개 이상 | ✅ |
| 7 | `clear_runpulse_metrics()` 후 `recompute_all()` 동일 결과 재현 | ✅ |
| 8 | 소스 메트릭은 `clear_runpulse_metrics()` 영향 없음 | ✅ |
| 9 | confidence 필드가 복합 메트릭(utrs, cirs)에 설정됨 | ✅ |
| 10 | json_value가 구조화 메트릭에 설정됨 | ✅ |
| 11 | 독립 테스트 파일 전체 통과 (791 passed, 0 failed) | ✅ |

보강 항목: Prefetch/ADR-009, needs_streams, ComputeResult 에러 추적, Dirty Tracking, MockCalcContext, ConfidenceBuilder, Calculator 메타데이터(7속성), Semantic Grouping(13그룹), 메트릭 이름 충돌 검증, 재계산 CLI 세분화, Daily Prefetch 상세, Phase 3-4 통합(integration.py) — 전체 ✅

---

## 4-9. 변경 이력

| 날짜 | 변경 내용 |
|------|----------|
| 2026-04-04 | Phase 4 구현 완료. 32 calculators, 791 tests passed |
| 2026-04-04 | ADR-009 도입 — Calculator 내부 raw SQL 금지, CalcContext API 전용 |
| 2026-04-04 | CalcContext API 6개 추가 (get_activity_metric_text, get_activity_metric_series, get_wellness_series, get_daily_load, get_laps, update_metric_cache) |
| 2026-04-04 | ConfidenceBuilder 추가 |
| 2026-04-04 | SEMANTIC_GROUPS 13개 정의 (metric_groups.py) |
| 2026-04-06 | phase-4.md 경량화 재작성 (3531줄 → 코드블록 제거, 매핑테이블 형식) |

---

