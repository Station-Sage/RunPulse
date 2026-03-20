# RunPulse Integration Validation Plan

최종 업데이트: 2026-03-20

## 목적

실제 export 데이터와 API 샘플을 사용해 RunPulse의 데이터 수집, 중복 매칭, 분석 출력이 현실적인 입력에서도 정상 동작하는지 검증한다.

이 문서는 단위 테스트를 보완하는 실제 데이터 기반 검증 계획을 정의한다.

## 왜 필요한가

현재 테스트 스위트는 기능 단위의 정확성 검증에는 유효하지만, 다음 항목은 실제 데이터로 별도 확인이 필요하다.

- Garmin / Strava export 파일 구조 차이
- API 응답의 누락 필드, null 값, 포맷 변화
- dedup false positive / false negative
- 실제 활동 데이터에서의 주간/월간 분석 sanity
- race readiness 의 sufficient / insufficient_data 판정 현실성

## 범위

### 포함
- `src/import_history.py` 기반 과거 데이터 일괄 임포트 검증
- `src/sync/garmin.py`
- `src/sync/strava.py`
- `src/sync/intervals.py`
- `src/sync/runalyze.py`
- `src/utils/dedup.py`
- `src/analysis/report.py`
- `src/analysis/race_readiness.py`
- `src/analyze.py` 출력 sanity 확인

### 제외
- 웹 UI 연동 플로우
- OAuth 팝업 / 브라우저 인증 UX
- 대시보드 렌더링
- 운영 배포 자동화
- cron / background scheduler

## 검증 원칙

1. 실제 개인정보가 포함된 원본 export 파일은 repo에 커밋하지 않는다.
2. 자동화 테스트에는 익명화된 fixture만 포함한다.
3. 실데이터 수동 검증과 fixture 기반 테스트를 분리한다.
4. import → dedup → analyze 전체 흐름을 한 번 이상 실제로 점검한다.
5. 분석 결과는 “오류가 없다”보다 “현실적으로 말이 되는지”까지 확인한다.

## 준비할 데이터

### 1. 로컬 개인 데이터
repo 외부 또는 gitignore 경로에서만 사용한다.

권장 위치:
- `data/history/`
- `data/samples/private/`

예시:
- Garmin export ZIP에서 풀어낸 FIT 파일
- Strava archive ZIP에서 풀어낸 GPX/FIT/TCX 파일
- Intervals API 응답 JSON 샘플
- Runalyze API 응답 JSON 샘플

### 2. 익명화 fixture 데이터
repo에 포함 가능한 최소 샘플.

권장 위치:
- `tests/fixtures/history/garmin/`
- `tests/fixtures/history/strava/`
- `tests/fixtures/api/garmin/`
- `tests/fixtures/api/strava/`
- `tests/fixtures/api/intervals/`
- `tests/fixtures/api/runalyze/`

## 최소 샘플 구성

다음 케이스를 가능하면 모두 확보한다.

- easy run
- long run
- tempo 또는 interval run
- 심박 누락 활동
- duplicate candidate
- Strava stream 포함 활동
- wellness / fitness 데이터 2~4주치
- 레이스 직전 taper 구간 데이터
- 데이터가 부족한 초기 구간 샘플

## 익명화 원칙

다음 항목은 제거 또는 치환한다.

- athlete id
- email
- token / refresh token / api key
- description 내 개인식별정보
- GPS 원본 좌표
- 외부 서비스 원본 source_id 그대로 노출되는 값

허용 예외:
- 날짜는 추세 검증에 필요하면 유지 가능
- 필요 시 전체 날짜를 동일 오프셋으로 이동
- 파일명은 `sample_run_01.fit` 같은 일반 이름 사용

## 검증 단계

## Phase A. import_history 검증

목표:
- 실제 export 파일이 파싱 가능한지 확인
- 주요 activity 필드가 정상 저장되는지 확인
- 재실행 시 중복 삽입 문제가 과도하지 않은지 확인

체크리스트:
- FIT / GPX / TCX 파싱 성공
- `activity_type`, `start_time`, `distance_km`, `duration_sec` 저장 확인
- 일부 비정상 파일이 있어도 전체 import가 과도하게 실패하지 않는지 확인
- import 후 `analyze.py full` 이 정상 동작하는지 확인

## Phase B. dedup 검증

목표:
- 동일 활동이 적절히 하나의 그룹으로 묶이는지 확인
- 과매칭 / 미매칭 사례를 수집한다

핵심 기준:
- start_time 차이 5분 이내
- distance 차이 3% 이내

점검 포인트:
- Garmin / Strava 동일 러닝이 같은 matched_group_id를 가지는가
- 같은 날 다른 러닝이 잘못 하나로 합쳐지지 않는가
- 주간 거리 합계가 비정상적으로 증가하지 않는가

## Phase C. sync parser 검증

목표:
- 외부 API 응답 구조 변화에 현재 파서가 견디는지 확인
- 누락 필드 / null 값 / 타입 차이에 대한 복원력을 확인

점검 대상:
- Garmin 활동 / wellness / vo2max
- Strava activity detail / streams / best efforts
- Intervals daily fitness / activity metrics
- Runalyze evo2max / vdot / marathon shape / race prediction

체크리스트:
- 날짜 파싱 일관성
- source_metrics key naming 일관성
- daily_wellness / daily_fitness upsert 정상 동작
- 선택 필드 누락 시 crash 없이 진행
- 에러 메시지가 디버깅 가능한 수준인지 확인

## Phase D. 분석 sanity check

목표:
- 분석 결과가 실행만 되는 수준이 아니라 실제로도 납득 가능한지 확인한다

실행 대상:
- `python src/analyze.py today`
- `python src/analyze.py week`
- `python src/analyze.py month`
- `python src/analyze.py full`
- `python src/analyze.py race --date 2026-06-01 --distance 42.195`
- `python src/analyze.py full --json`
- `python src/analyze.py today --ai-context`

확인 항목:
- 헤더/섹션이 비정상적으로 비어 있지 않은가
- 거리/시간/페이스 값이 터무니없는 수치를 출력하지 않는가
- race readiness 가 과도하게 낙관적/비관적이지 않은가
- insufficient_data 판정이 실제 데이터 양과 맞는가
- AI context 문자열이 누락 없이 생성되는가

## 우선순위

1. import_history + dedup 실제 검증
2. analyze / report / race_readiness sanity 확인
3. API 응답 fixture 축적
4. parser fixture 기반 자동 테스트 추가
5. dedup 기준 보정 여부 검토

## 산출물

이 검증 단계에서 최종적으로 남겨야 할 것:

- 익명화 가능한 fixture 후보 목록
- false positive / false negative 사례 목록
- parser 취약 필드 목록
- race readiness 기준 조정 필요 사항
- integration test 추가 후보 목록

## 후속 작업 TODO

- `tests/fixtures/` 구조 생성
- parser fixture 테스트 추가
- import_history 실제 export 회귀 테스트 설계
- dedup 기준 보정 여부 검토
- insufficient_data 기준 실데이터 기반 재보정

## 실행 메모

실제 검증은 다음 순서로 진행한다.

1. 개인 export 데이터로 수동 검증
2. 반복적으로 등장하는 케이스를 익명화 fixture로 축소
3. fixture 기반 테스트로 일부 자동화
4. 이후 필요하면 검증 스크립트 자동화 추가


## 2026-03-20 Intervals.icu follow-up 검증 메모

실데이터 기준으로 다음 사항을 추가 확인했다.

- `source_payloads`에 Intervals activity / wellness raw payload가 저장됨
- Intervals activity metric 정규화 항목이 확장됨
  - `trimp`, `strain_score`, `icu_efficiency_factor`, `decoupling`
  - `hr_load`, `pace_load`, `power_load`, `session_rpe`
  - `average_stride`, `icu_lap_count`
  - `icu_zone_times`, `icu_hr_zone_times`, `pace_zone_times`, `gap_zone_times`
  - `interval_summary`, `stream_types`
- `activity_type` 필터를 넓혀 `run`, `virtualrun`, `treadmill`,
  `highintensityintervaltraining`도 분석 대상에 포함
- `analyze.py today` / `report.py`에서 Intervals efficiency 및 zone 데이터 노출 확인
- `interval_summary`가 pace split 부재 시에도 읽을 수 있는 형태로 리포트에 표시됨
- `/payloads` 및 `/payloads/view` workbench 경로로 raw payload와 연관 `source_metrics`
  drill-down 확인 가능
- `/payloads`에서 `source`, `entity_type`, `activity_id`, `limit` 필터 지원
- Intervals wellness 확장 필드 저장 컬럼 추가
  - `hrv_sdnn`, `avg_sleeping_hr`, `fatigue`, `mood`, `motivation`, `steps`, `weight_kg`
- 현재 실데이터에서는 `steps`가 raw payload에 안정적으로 존재하며, `weight`는 일부 날짜에만 존재
- 일부 확장 wellness 값은 `daily_wellness`에 비어 있을 수 있어, 리포트에서는 raw payload fallback으로 표시 가능하게 보완함

최신 sanity 예시(2026-03-19 activity):
- 거리: 4.768 km
- 시간: 26m 27s
- 평균 페이스: 5:33
- 평균 심박: 154
- Intervals Training Load: 35.0
- EF: 1.6753
- Decoupling: 0.35
- zone 분포:
  - Z1 회복 8.8% (138s)
  - Z2 유산소 27.4% (432s)
  - Z3 템포 45.8% (722s)
  - Z4 역치 14.5% (228s)
  - Z5 VO2Max 3.6% (56s)
- interval summary:
  - 1회 2m17s 261W
  - 2회 7m07s 254W
- wellness 참고:
  - 걸음 수 13195

## 2026-03-20 integration-validation 통합 결과

`feature/integration-validation` 브랜치에 다음 작업을 통합했다.

- `feature/intervals-analysis-polish`
  - Intervals `interval_summary` 리포트 노출/포맷 개선
  - wellness 확장 필드 저장 및 report visibility 보강
  - `/payloads` 필터 및 `/payloads/view` drill-down 추가
- `feature/phase4-ai-coach`
  - 목표 CRUD, 주간 계획 생성, 당일 조정, `plan.py` CLI 추가
- 통합 후 hotfix
  - `get_active_goal()`이 최신 active goal을 안정적으로 선택하도록 정렬 기준 보강
  - `ORDER BY created_at DESC, id DESC`

검증 결과:
- `python -m py_compile ...` 통과
- `python -m pytest -q` → 263 passed
- `python src/analyze.py today` / `full` 정상
- `python src/plan.py --help` 정상
- `/`, `/db`, `/sync-status`, `/payloads`, `/payloads/view` smoke 확인

다음 단계:
- `feature/integration-validation` → `dev` PR 생성
- 남은 roadmap / phase 미구현 기능은 새 브랜치에서 진행
