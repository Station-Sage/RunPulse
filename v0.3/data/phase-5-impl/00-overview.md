# Phase 5 Overview — Consumer Service Layer

> Phase 5 목표: 새 스키마(activity_summaries + metric_store + daily tables)에서
> 데이터를 읽는 서비스 레이어를 구축한다.
> 기존 뷰(69개)는 마이그레이션하지 않는다. Phase 7에서 새 UI가 서비스 레이어를 호출한다.

## 현재 상태 (Phase 4 완료 시점)

| 항목 | 값 |
|------|-----|
| Schema Version | 10 |
| activity_summaries | 44 컬럼, distance_m (SI) |
| daily_wellness | 15 컬럼 |
| daily_fitness | 9 컬럼 (date + source UNIQUE) |
| metric_store | 16 컬럼, EAV |
| Calculator classes | 31 (39 metric_names produces) |
| Calculator categories | 11 (rp_*) |
| Semantic groups | 13 |
| METRIC_REGISTRY entries | ~142 |
| Tests | ~791 |
| metric_store consumer code | 0 (서비스 레이어 없음) |

## 선행 작업 (Phase 5 시작 전)

### P5-PRE-1: metric_registry.py category 수정

Calculator 코드의 category를 정답으로, registry를 맞춘다.

| metric_name | registry 현재 | 수정 후 |
|---|---|---|
| trimp | training_load | rp_load |
| hrss | training_load | rp_load |
| ctl | pmc | rp_load |
| atl | pmc | rp_load |
| tsb | pmc | rp_load |
| ramp_rate | pmc | rp_load |
| adti | rp_efficiency | rp_trend |
| di | rp_performance | rp_endurance |
| rmr | rp_performance | rp_recovery |

### P5-PRE-2: metric_registry.py 누락 등록

| metric_name | category | unit | description | scope |
|---|---|---|---|---|
| darp_5k | rp_prediction | sec | DARP 5K 예측 | daily |
| darp_10k | rp_prediction | sec | DARP 10K 예측 | daily |
| darp_half | rp_prediction | sec | DARP 하프 예측 | daily |
| darp_marathon | rp_prediction | sec | DARP 마라톤 예측 | daily |
| workout_type | rp_classification | (없음) | 규칙 기반 운동 분류 | activity |
| training_strain | rp_load | (없음) | 훈련 스트레인 | daily |

### P5-PRE-3: gen_metric_dictionary.py 재실행

registry 수정 후 dictionary 재생성하여 일관성 확인.

    python3 scripts/gen_metric_dictionary.py

### 선행 작업 DoD

- [ ] registry의 모든 rp_* calculator metric이 calculator 코드와 category 일치
- [ ] darp_5k~darp_marathon, workout_type, training_strain이 registry에 등록됨
- [ ] gen_metric_dictionary.py 실행 시 에러 없음
- [ ] 기존 테스트 전체 통과 (pytest)

## Phase 5 산출물

| # | 파일 | 설명 | 상세 설계 |
|---|------|------|----------|
| 1 | src/services/activity_service.py | 활동 데이터 조회 | 01-service-layer.md |
| 2 | src/services/dashboard_service.py | 대시보드/PMC 데이터 | 01-service-layer.md |
| 3 | src/services/wellness_service.py | 웰니스 상세/추세 | 01-service-layer.md |
| 4 | src/ai/ai_context.py | AI 코칭 context builder | 02-ai-context.md |
| 5 | src/web/template_helpers.py | 단위변환, badge, color | 03-template-helpers.md |
| 6 | tests/test_activity_service.py | 서비스 테스트 | 04-tests.md |
| 7 | tests/test_dashboard_service.py | 서비스 테스트 | 04-tests.md |
| 8 | tests/test_wellness_service.py | 서비스 테스트 | 04-tests.md |
| 9 | tests/test_ai_context.py | AI context 테스트 | 04-tests.md |
| 10 | tests/test_template_helpers.py | 헬퍼 테스트 | 04-tests.md |

## 만들지 않는 것

- 기존 69개 뷰 파일 마이그레이션
- computed_metrics 호환 뷰
- 구 컬럼 매핑 테이블

## 데이터 소스 지도

서비스 레이어가 읽는 테이블과 용도:

| 테이블 | 서비스 | 용도 |
|--------|--------|------|
| v_canonical_activities | activity | 목록, 필터, 정렬 |
| activity_summaries | activity | 상세 core, 소스 비교 |
| metric_store (scope=activity, is_primary=1) | activity | 상세 메트릭 |
| metric_store (scope=activity, 전체) | activity | 소스별 비교 |
| metric_store (scope=daily, is_primary=1) | dashboard, wellness | 일별 메트릭 |
| daily_wellness | dashboard, wellness | 오늘 상태, 추세 |
| daily_fitness | dashboard | 소스별 PMC 비교 (Garmin/Intervals) |
| activity_streams | activity | 차트, 분석 |
| activity_laps | activity | 랩 테이블 |
| activity_best_efforts | activity | PR 표시 |
| gear | activity | 신발 정보 |
| sync_jobs | dashboard | 동기화 상태 |

참고: RunPulse PMC(ctl/atl/tsb)는 metric_store에 저장됨 (daily_fitness 아님).
daily_fitness는 소스가 제공하는 PMC/VO2Max 원본 저장용.

## 작업 순서

1. 선행 작업 (P5-PRE-1~3)
2. src/services/activity_service.py
3. src/services/dashboard_service.py
4. src/services/wellness_service.py
5. src/web/template_helpers.py
6. src/ai/ai_context.py
7. 테스트 전체
8. 전체 DoD 검증

## 참조 문서

- 이 디렉토리의 01~04 설계서
- v0.3/data/metric_dictionary.md (범위 해석, 의존성)
- src/utils/metric_registry.py (단위, 설명, aliases)
- src/utils/metric_groups.py (13 semantic groups)
- src/utils/db_helpers.py (읽기 함수 시그니처)
