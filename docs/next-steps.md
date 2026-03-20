# RunPulse Next Steps

최종 업데이트: 2026-03-20

## 현재 상태

`dev` 브랜치에는 다음 작업이 반영되어 있다.

- Phase 1 기반 구축
- Phase 2 데이터 수집
- Phase 3 분석/리포트/CLI
- Intervals follow-up polish
  - `interval_summary` 리포트 노출 및 포맷 개선
  - wellness 확장 필드 저장/표시 보강
  - `/payloads` 필터 및 `/payloads/view` drill-down
- Phase 4 훈련 계획 및 목표
  - goal CRUD
  - weekly planner
  - daily adjuster
  - `plan.py` CLI
- integration validation 통합 및 검증
  - `python -m pytest -q` → 263 passed
  - `analyze.py today/full` smoke 통과
  - `plan.py --help` smoke 통과
  - web workbench smoke 통과

## 현재 브랜치 전략

장기 유지 브랜치:
- `main`
- `dev`

설계/메모는 별도 장기 브랜치보다 문서로 유지하는 방향을 우선한다.

새 기능/후속 작업은 항상 `dev`에서 새 브랜치를 생성해 진행한다.

기본 흐름:

    git checkout dev
    git pull --ff-only origin dev
    git checkout -b <new-branch-name>

## 남은 큰 작업 축

### 1. Integration validation 후속
- cross-source fixture 수집
- parser fixture 테스트 추가
- `tests/fixtures/` 구조 정리
- import_history regression 설계
- dedup false positive / false negative 사례 정리

### 2. Phase 4-1 AI 코치 기반
- `src/ai/ai_context.py`
- `src/ai/ai_schema.py`
- `src/ai/ai_parser.py`
- `src/ai/briefing.py`
- `src/ai/suggestions.py`
- `src/ai/prompt_templates/`

### 3. Phase 4-2 Workout / Garmin calendar
- `src/workout/workout_builder.py`
- `src/workout/garmin_calendar.py`
- `src/workout/workout_export.py`

### 4. Phase 5 웹 대시보드 확장
- 대시보드 탭
- AI 코치 탭
- 훈련 계획 탭
- 설정 탭
- 모바일 반응형 / 다크 모드

### 5. 문서 구조 재편
- 긴 문서 분리
- roadmap / todo / usage 역할 정리
- validation 문서 슬림화
- 실행 메모와 계획 문서 분리

## 추천 우선순위

### 1순위: `feature/integration-fixtures`
목표:
- cross-source fixture 기반 검증 강화
- parser 안정성 보강
- validation 후속 자동화 기반 마련

첫 슬라이스 제안:
- `tests/fixtures/` 디렉터리 구조 생성
- Intervals / Garmin / Strava / Runalyze fixture 배치 기준 문서화
- parser fixture 테스트 스캐폴딩 추가

### 2순위: `feature/phase4-ai-coach-foundation`
목표:
- 분석/리포트/훈련계획 결과를 AI 코치 흐름으로 연결

첫 슬라이스 제안:
- `ai_context.py`
- `briefing.py`
- 최소 prompt template
- 테스트 가능한 순수 함수 중심으로 시작

### 3순위: `chore/docs-restructure`
목표:
- 장문 문서 정리
- 중복/역할 혼재 해소

### 4순위: `feature/phase5-dashboard-foundation`
목표:
- 기존 workbench를 실제 대시보드 방향으로 확장

## 추천 운영 원칙

- 작은 vertical slice 단위로 진행
- 새 기능은 항상 새 브랜치
- validation 결과는 문서와 테스트로 남긴다
- 실데이터 sanity check와 fixture test를 분리한다
- 설계는 브랜치보다 문서로 보존한다
