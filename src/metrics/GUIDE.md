# src/metrics/ GUIDE — v0.3 Metrics Engine

## 아키텍처 개요

v0.3 메트릭 엔진은 **MetricCalculator ABC 기반 플러그인 아키텍처**입니다.
모든 calculator는 `CalcContext` API를 통해 데이터에 접근하고, `metric_store`에 `provider=runpulse:formula_v1`로 저장합니다.

    activity_summaries (Layer 1) ─┐
    metric_store (Layer 2, 소스) ──┼→ CalcContext → Calculator.compute() → CalcResult
    daily_wellness (Layer 1) ─────┘                      ↓
                                              engine._save_results()
                                                         ↓
                                              metric_store (Layer 2, runpulse)
                                                         ↓
                                              resolve_for_scope() → is_primary 결정

## 핵심 설계 원칙

1. **metric_store 단일 저장소**: 소스 메트릭과 RunPulse 메트릭이 같은 테이블에 공존, provider로 구분
2. **의존성 자동 해소**: requires/produces 선언 → topological sort → 올바른 실행 순서
3. **데이터 부족 시 빈 리스트 반환**: 에러 아닌 graceful skip, confidence로 신뢰도 표시
4. **재계산 용이**: `provider LIKE 'runpulse%'` 삭제 후 재실행
5. **is_primary 자동 결정**: upsert_metric → resolve_primary 호출 (metric_priority.py 우선순위)
6. **CalcContext API 전용 데이터 접근**: Calculator 내부에서 raw SQL 사용 금지 (ADR-009)
7. **Calculator = 순수 함수**: A/B 테스트, Mock 테스트를 위해 입력만 바꿔서 실행 가능

## CalcContext API (13개)

Calculator가 데이터에 접근할 수 있는 유일한 경로입니다.

| 메서드 | 반환 | 용도 |
|--------|------|------|
| `activity` | `dict` | 현재 activity의 activity_summaries 데이터 |
| `get_metric(name)` | `float \| None` | 현재 scope의 primary numeric_value |
| `get_metric_json(name)` | `str \| None` | 현재 scope의 primary json_value |
| `get_metric_text(name)` | `str \| None` | 현재 scope의 primary text_value |
| `get_wellness()` | `dict` | 현재 날짜의 daily_wellness 데이터 |
| `get_streams()` | `dict[str, list]` | activity의 time-series 데이터 |
| `get_laps()` | `list[dict]` | activity의 랩 데이터 |
| `get_activities_in_range(days, activity_type?)` | `list[dict]` | 날짜 범위 내 활동 목록 |
| `get_activity_metric(activity_id, name)` | `float \| None` | 특정 activity의 metric numeric_value |
| `get_activity_metric_text(activity_id, name)` | `str \| None` | 특정 activity의 metric text_value |
| `get_daily_metric_series(name, days)` | `list[dict]` | daily-scope metric 시계열 |
| `get_daily_load(date_str)` | `float` | 특정 날짜의 TRIMP 합산 (prefetch 지원) |
| `get_activity_metric_series(name, days, activity_type?, include_json?)` | `list[dict]` | activity-scope metric 시계열 (JOIN 포함) |
| `get_wellness_series(days, fields?)` | `list[dict]` | daily_wellness 히스토리 |

### Prefetch 지원

`engine.py`가 배치 실행 시 다음을 미리 로드합니다:
- `_prefetched_activity_data` — activity_summaries 전체
- `_prefetched_metrics` — 해당 scope의 metric_store
- `_prefetched_wellness_map` — daily_wellness (daily-scope용)
- `_prefetched_daily_loads` — 날짜별 TRIMP 합산 (PMC/LSI/Monotony용)

## 진입점

| 방법 | 명령 |
|------|------|
| CLI | `python3 -m src.metrics.cli status` |
| CLI | `python3 -m src.metrics.cli recompute --days 7` |
| CLI | `python3 -m src.metrics.cli recompute-single --metric trimp --days 30` |
| Python | `from src.metrics.engine import run_activity_metrics, run_daily_metrics` |
| Sync 연동 | `from src.sync.integration import compute_metrics_after_sync` |

## 파일 구조

### 인프라 (5개)
| 파일 | 역할 |
|------|------|
| `base.py` | MetricCalculator ABC, CalcResult, CalcContext (13 API + prefetch), ConfidenceBuilder |
| `engine.py` | ALL_CALCULATORS 등록 (32개), topological sort, prefetch, 배치 실행, _save_results |
| `reprocess.py` | metric_store 기반 재처리 |
| `cli.py` | CLI 진입점 (status, recompute, recompute-single, clear) |
| `__init__.py` | 패키지 초기화 |

### Activity-Scope Calculators (10개)
| 파일 | name | 설명 | category |
|------|------|------|----------|
| `trimp.py` | trimp | Banister TRIMPexp | rp_load |
| `hrss.py` | hrss | HR Stress Score (LTHR 기반) | rp_load |
| `decoupling.py` | aerobic_decoupling_rp | 유산소 분리 (%) | rp_efficiency |
| `gap.py` | gap_rp | 경사 보정 페이스 | rp_performance |
| `vdot.py` | runpulse_vdot | Jack Daniels VDOT | rp_performance |
| `classifier.py` | workout_type | 운동 유형 자동 분류 | rp_classification |
| `efficiency.py` | efficiency_factor_rp | 효율 계수 (EF) | rp_efficiency |
| `fearp.py` | fearp | 환경 보정 페이스 (날씨+경사) | rp_performance |
| `relative_effort.py` | relative_effort | 심박존 기반 노력도 | rp_load |
| `wlei.py` | wlei | 날씨 가중 노력 지수 | rp_load |

### Daily-Scope Calculators — 1차 (4개, 활동 메트릭 집계)
| 파일 | name | 설명 | category |
|------|------|------|----------|
| `pmc.py` | ctl | ATL/CTL/TSB/Ramp Rate (PMC) | rp_load |
| `acwr.py` | acwr | 급성:만성 부하 비율 | rp_load |
| `lsi.py` | lsi | 부하 급증 지수 | rp_load |
| `monotony.py` | monotony | 단조로움 + 스트레인 | rp_load |

### Daily-Scope Calculators — 2차 (8개, RunPulse 고유)
| 파일 | name | 설명 | category |
|------|------|------|----------|
| `utrs.py` | utrs | 통합 훈련 준비도 (ConfidenceBuilder) | rp_readiness |
| `cirs.py` | cirs | 복합 부상 위험 (ConfidenceBuilder) | rp_risk |
| `di.py` | di | 내구성 지수 | rp_endurance |
| `darp.py` | darp | 레이스 예측 (VDOT+DI) | rp_prediction |
| `tids.py` | tids | 훈련 강도 분포 | rp_distribution |
| `rmr.py` | rmr | 회복 준비도 레이더 | rp_recovery |
| `adti.py` | adti | 유산소 분리 추세 | rp_trend |
| `crs.py` | crs | 복합 준비도 게이트 (5-gate) | rp_readiness |

### Daily-Scope Calculators — 3차 (10개, v0.2 포팅)
| 파일 | name | 설명 | category |
|------|------|------|----------|
| `teroi.py` | teroi | 훈련 효과 ROI | rp_trend |
| `tpdi.py` | tpdi | 실내/실외 격차 | rp_trend |
| `rec.py` | rec | 통합 러닝 효율성 | rp_efficiency |
| `rtti.py` | rtti | 달리기 내성 지수 | rp_load |
| `critical_power.py` | critical_power | CP/W' 임계 파워 | rp_performance |
| `eftp.py` | eftp | 역치 페이스 추정 | rp_performance |
| `sapi.py` | sapi | 계절 성과 비교 | rp_performance |
| `rri.py` | rri | 레이스 준비도 | rp_performance |
| `vdot_adj.py` | vdot_adj | VDOT 보정 | rp_performance |
| `marathon_shape.py` | marathon_shape | 마라톤 훈련 완성도 | rp_performance |

### 유틸리티
| 파일 | 역할 |
|------|------|
| `src/utils/daniels_table.py` | Daniels VDOT 룩업 (훈련 페이스, 레이스 예측, 볼륨) |
| `src/utils/metric_priority.py` | provider 우선순위 → is_primary 결정 |
| `src/utils/metric_registry.py` | MetricDef 등록, 이름 정규화, CATEGORY_LABELS |
| `src/utils/metric_groups.py` | 시맨틱 그룹 (13개 그룹), get_group_for_metric() |

## Calculator 메타데이터 (UI 힌트)

모든 calculator는 다음 속성을 선언합니다:

| 속성 | 설명 | 예시 |
|------|------|------|
| display_name | UI 표시 이름 | "TRIMP (Banister)" |
| description | 설명 텍스트 | "심박 기반 훈련 부하 점수" |
| unit | 단위 | "AU", "sec/km", "%", "W" |
| ranges | 범위 ([low, high] 리스트) | {"easy": [0, 50], "hard": [200, 350]} |
| higher_is_better | 방향성 | True / False / None |
| format_type | UI 포맷 | "number", "pace", "json" |
| decimal_places | 소수점 | 0, 1, 2 |

## 의존성 그래프 (주요)

    trimp ──→ pmc(ctl/atl/tsb) ──→ acwr ──→ cirs ──→ crs
                │                    │         │
                ├→ lsi               │         └→ rri
                ├→ monotony          │
                └→ rtti              └→ utrs ──→ crs
    
    runpulse_vdot ──→ eftp
                  ──→ vdot_adj ──→ marathon_shape
                  ──→ darp
                  ──→ rri
    
    fearp ──→ sapi
          ──→ tpdi
    
    efficiency_factor_rp ──→ rec
    aerobic_decoupling_rp ──→ rec
                          ──→ adti

## 시맨틱 그룹 (13개)

| 그룹 | display_name | 멤버 |
|------|-------------|------|
| training_load | 훈련 부하 | training_load_score, training_load, suffer_score, hrss, wlei, rtti |
| training_strain | 훈련 스트레인 | monotony, training_strain, lsi |
| heart_rate | 심박 | resting_hr, max_hr, avg_hr, hrv_rmssd |
| efficiency | 효율성 | icu_efficiency_factor, efficiency_factor_rp, aerobic_decoupling_rp, rec |
| race_prediction | 레이스 예측 | darp, race_prediction_marathon, rri |
| readiness | 준비도 | utrs, cirs, crs |
| pmc | PMC | ctl, atl, tsb, acwr, ramp_rate |
| body_composition | 신체 조성 | weight_kg, bmi, body_fat_pct |
| sleep | 수면 | sleep_score, deep_sleep_sec, rem_sleep_sec |
| vo2max | VO2Max | runpulse_vdot, vo2max_activity, effective_vo2max |
| vdot | VDOT | runpulse_vdot, vdot_adj, vo2max_activity, effective_vo2max |
| training_trend | 훈련 트렌드 | teroi, tpdi, adti |
| seasonal_performance | 환경별 성과 | sapi, fearp |

## 규칙

1. **데이터 없으면 빈 리스트 반환** — 에러 발생 금지, UI에서 "데이터 수집 중" 표시
2. 모든 저장은 `engine._save_results() → upsert_metric()` 경로 사용
3. `confidence`는 모든 메트릭에 설정 (1.0=완전, 0.8=추정값 포함, 0.6=부분 데이터)
4. `ranges`는 반드시 `[low, high]` 리스트 형식 (ADR-007)
5. `provider = "runpulse:formula_v1"` 통일
6. `category`는 `rp_` 접두사 (metric_registry.py CATEGORY_LABELS와 일치, ADR-008)
7. **Calculator 내 raw SQL 금지** — 반드시 CalcContext API 사용 (ADR-009)
8. 복합 메트릭(UTRS, CIRS)은 `ConfidenceBuilder` 사용 권장

## 새 메트릭 추가 체크리스트

1. `src/metrics/<name>.py` 생성 — MetricCalculator 서브클래스
2. name, provider, scope_type, category, requires, produces, UI 메타데이터 설정
3. `compute()` 구현 — **CalcContext API만 사용**, 데이터 부족 시 `return []`
4. `engine.py`에 import + ALL_CALCULATORS 등록
5. `src/utils/metric_registry.py`에 MetricDef 추가
6. `src/utils/metric_groups.py`에 시맨틱 그룹 추가 (해당 시)
7. `tests/test_<name>.py` 독립 테스트 파일 작성 (DB 기반 + Mock 기반)
8. 이 GUIDE.md 파일맵에 추가

## 테스트 (74개 파일, 791 passed)

### Metrics 전용 테스트 (27개 파일)
| 파일 | 테스트 수 | 범위 |
|------|----------|------|
| test_trimp_calc.py | 6 | TRIMP, HRSS |
| test_activity_calcs.py | 12 | Decoupling, GAP, Classifier, VDOT, EF |
| test_daily_calcs.py | 10 | PMC, ACWR, LSI, Monotony |
| test_daily2_calcs.py | 10 | FEARP, RMR, ADTI |
| test_pmc.py | 4 | PMC (CTL 증가, TSB 음수) |
| test_utrs.py | 6 | UTRS (전체 입력, 부분, confidence) |
| test_cirs.py | 5 | CIRS (high/optimal ACWR, confidence) |
| test_relative_effort.py | 8 | RelativeEffort (DB + Mock) |
| test_wlei.py | 6 | WLEI (날씨 가중) |
| test_teroi.py | 3 | TEROI |
| test_tpdi.py | 3 | TPDI (실내/실외) |
| test_rec.py | 3 | REC (EF + Decoupling) |
| test_rtti.py | 6 | RTTI (DB + Mock) |
| test_critical_power.py | 3 | Critical Power |
| test_eftp.py | 3 | eFTP |
| test_sapi.py | 3 | SAPI (계절 성과) |
| test_rri.py | 6 | RRI (DB + Mock) |
| test_vdot_adj.py | 3 | VDOT 보정 |
| test_marathon_shape.py | 3 | 마라톤 완성도 |
| test_crs.py | 6 | CRS (5-gate) |
| test_engine.py | 9 | Topological sort, prefetch, 배치 |
| test_phase4_dod.py | 12 | DoD 11항목 |
| test_phase4_spec.py | 9 | 설계서 시나리오 |
| test_round2.py | 5 | 보강 2차 |
| test_round4.py | 11 | 메타데이터, 그룹, CLI |
| test_mock_calcs.py | 14 | MockCalcContext (TRIMP, HRSS, EF, VDOT, ConfidenceBuilder) |
| test_metric_naming.py | 5 | 이름 충돌 방지 |
| test_daniels_table.py | 12 | VDOT 룩업 |

---

## 메트릭 사전 (Metric Dictionary)

`v0.3/data/metric_dictionary.md`는 32개 메트릭의 정의, 해석, 범위를 정리한 공식 사전입니다.
UI 툴팁, AI 코칭 프롬프트, 사용자 도움말의 원본(single source of truth)입니다.

**이 파일을 직접 수정하지 마세요.** Calculator 메타데이터에서 자동 생성됩니다.

재생성 방법:

python scripts/gen_metric_dictionary.py

동기화 검증:
python scripts/check_docs.py # 전체 문서 정합성 검사 python -m pytest tests/test_doc_sync.py # CI 검증


calculator를 추가/변경하면 `test_doc_sync.py`가 자동으로 불일치를 감지합니다.
