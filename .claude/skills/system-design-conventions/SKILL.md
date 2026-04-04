---
name: system-design-conventions
description: >
  RunPulse 시스템/데이터 설계 규칙과 빠른 확인 레시피.
  system-architect 에이전트에 프리로드된다.
user-invocable: false
---

# RunPulse 시스템 설계 규칙

## 핵심 수치 빠른 확인 (파일 전체를 읽지 말고 이 명령어 사용)

```bash
# Calculator 수 + 목록
grep -c "Calculator()" src/metrics/engine.py
sed -n '/^ALL_CALCULATORS/,/^]/p' src/metrics/engine.py

# CalcContext API 목록
grep "def get_\|def update_\|def add_" src/metrics/base.py

# 테이블 수 + 목록
grep "CREATE TABLE" src/db_setup.py

# SCHEMA_VERSION
grep "SCHEMA_VERSION" src/db_setup.py

# metric_store 스키마 상세
grep -A15 "CREATE TABLE IF NOT EXISTS metric_store" src/db_setup.py

# SEMANTIC_GROUPS 키 목록
python3 -c "from src.utils.metric_groups import SEMANTIC_GROUPS; print(list(SEMANTIC_GROUPS.keys()))"

# MetricDef 등록 수
grep -c "MetricDef(" src/utils/metric_registry.py
```

## 데이터 모델 원칙

1. **metric_store 단일 저장소**: 소스 메트릭과 RunPulse 메트릭이 같은 테이블에 공존.
   provider 컬럼으로 구분 (garmin, strava, intervals, runalyze, runpulse:formula_v1).

2. **is_primary 자동 결정**: metric_priority.py의 우선순위에 따라
   같은 metric_name에 대해 대표값 하나를 선택.

3. **scope_type 구분**: activity (활동별), daily (일별), weekly (주별).

4. **확장성 설계**: 새 스포츠 추가 시 activity_summaries에 컬럼 추가가 아니라
   metric_store에 새 metric_name으로 저장.

## CalcContext API (ADR-009)

Calculator는 CalcContext의 API만 사용하여 데이터에 접근한다.
ctx.conn.execute() 같은 raw SQL은 절대 금지.

## 테이블 구조

Pipeline 테이블 11개:
source_payloads, activity_summaries, daily_wellness, daily_fitness,
metric_store, activity_streams, activity_laps, activity_best_efforts,
gear, weather_cache, sync_jobs

App 테이블 5개:
chat_messages, goals, planned_workouts, user_training_prefs, session_outcomes

## Phase 문서 템플릿

새 Phase 문서 작성 시 아래 섹션을 반드시 포함:

1. Phase N 목표 — 이 Phase가 달성해야 할 것
2. 상세 설계 — 코드 블럭 포함 (DDL, API, 클래스 정의)
3. 테스트 계획 — 테스트 파일명, 예상 테스트 수
4. Definition of Done (DoD) — 번호 매긴 완료 조건
5. 구현 기록 — 완료일, 실제 테스트 수, 변경 파일 목록

## 설계 변경 시 체크리스트

새 테이블 추가 시:
- db_setup.py에 CREATE TABLE 추가
- 해당 phase-*.md에 DDL 기록
- phase_summary.md 테이블 수 업데이트
- architecture.md 테이블 목록 업데이트

새 Calculator 추가 시:
- src/metrics/ 에 파일 생성
- engine.py ALL_CALCULATORS에 등록
- metric_registry.py에 MetricDef 추가
- gen_metric_dictionary.py 실행
- test 파일 생성
