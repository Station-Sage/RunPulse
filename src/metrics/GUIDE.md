# src/metrics/ GUIDE — v0.3 Metrics Engine

## 아키텍처 개요

v0.3 메트릭 엔진은 **MetricCalculator ABC 기반 플러그인 아키텍처**입니다.
모든 calculator는 `metric_store`에서 읽고 `metric_store`에 `provider=runpulse:formula_v1`로 저장합니다.

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

## 진입점

| 방법 | 명령 |
|------|------|
| CLI | `python3 -m src.metrics.cli status` |
| CLI | `python3 -m src.metrics.cli recompute --days 7` |
| Python | `from src.metrics.engine import run_activity_metrics, run_daily_metrics` |
| Sync 연동 | `from src.sync.integration import compute_metrics_after_sync` |

## 파일 구조

### 인프라 (5개)
| 파일 | 역할 |
|------|------|
| `base.py` | MetricCalculator ABC, CalcResult, CalcContext, ConfidenceBuilder |
| `engine.py` | ALL_CALCULATORS 등록, topological sort, prefetch, 배치 실행, _save_results |
| `reprocess.py` | metric_store 기반 재처리 |
| `cli.py` | CLI 진입점 (status, recompute) |
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
| `utrs.py` | utrs | 통합 훈련 준비도 | rp_readiness |
| `cirs.py` | cirs | 복합 부상 위험 | rp_risk |
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
| `src/utils/metric_groups.py` | 시맨틱 그룹 (소스 비교 뷰 지원, 11개 그룹) |

## Calculator 메타데이터 (UI 힌트)

모든 calculator는 다음 속성을 선언합니다:

| 속성 | 설명 | 예시 |
|------|------|------|
| display_name | UI 표시 이름 | "TRIMP (Banister)" |
| description | 설명 텍스트 | "심박 기반 훈련 부하 점수" |
| unit | 단위 | "AU", "sec/km", "%", "W" |
| ranges | 범위 | {"easy": [0, 50], "hard": [200, 350]} |
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

## 규칙

1. **데이터 없으면 빈 리스트 반환** — 에러 발생 금지, UI에서 "데이터 수집 중" 표시
2. 모든 저장은 `engine._save_results() → upsert_metric()` 경로 사용
3. `confidence`는 모든 메트릭에 설정 (1.0=완전, 0.8=추정값 포함, 0.6=부분 데이터)
4. `ranges`는 반드시 `[low, high]` 리스트 형식
5. `provider = "runpulse:formula_v1"` 통일
6. `category`는 `rp_` 접두사 (metric_registry.py CATEGORY_LABELS와 일치)

## 새 메트릭 추가 체크리스트

1. `src/metrics/<name>.py` 생성 — MetricCalculator 서브클래스
2. name, provider, scope_type, category, requires, produces, UI 메타데이터 설정
3. `compute()` 구현 (데이터 부족 시 `return []`)
4. `engine.py`에 import + ALL_CALCULATORS 등록
5. `src/utils/metric_registry.py`에 MetricDef 추가
6. `src/utils/metric_groups.py`에 시맨틱 그룹 추가 (해당 시)
7. 테스트 작성
8. 이 GUIDE.md 파일맵에 추가

## 테스트

| 파일 | 테스트 수 | 범위 |
|------|----------|------|
| test_trimp_calc.py | 6 | TRIMP, HRSS 기본 계산 |
| test_activity_calcs.py | 12 | Activity-scope 7개 calculator |
| test_daily_calcs.py | 10 | Daily-scope 1차 (PMC, ACWR, LSI, Monotony) |
| test_daily2_calcs.py | 12 | Daily-scope 2차 (UTRS, CIRS, DI, DARP, TIDS, RMR, ADTI) |
| test_engine.py | 8 | Topological sort, prefetch, batch 실행 |
| test_phase4_dod.py | 12 | DoD 11항목 검증 |
| test_phase4_spec.py | 9 | 설계서 테스트 케이스 6건 |
| test_round2.py | 5 | 2차 보강 검증 |
| test_round4.py | 11 | 메타데이터, 그룹, CLI |
| test_mock_calcs.py | 6 | MockCalcContext DB-less 테스트 |
| test_metric_naming.py | 5 | 이름 충돌 방지 검증 |
| test_daniels_table.py | 12 | VDOT 룩업, T-pace, 레이스 예측 |
| test_porting_activity.py | 10 | RelativeEffort, WLEI |
| test_porting_daily.py | 25 | 포팅 메트릭 11개 |
| **합계** | **143** | |
