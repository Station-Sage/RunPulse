# 데이터 모델 재구성 계획

## 목적

이 문서는 외부 데이터 수집 파이프라인에서 사용하는 현재 데이터 모델의 역할을 다시 정리하고, 이후 스키마 확장과 이름 체계 개선 방향을 정의하기 위한 계획 문서다.

현재 Garmin alignment 작업을 진행하면서 다음 문제가 더 분명해졌다.

- raw payload 저장은 `source_payloads`로 방향이 잡혔다.
- activity 단위 source-specific metric은 `source_metrics`에 저장되고 있다.
- 하지만 day 단위 wellness/source-specific metric을 저장할 적절한 구조가 부족하다.
- 일부 테이블 이름은 현재 역할을 정확히 드러내지 못한다.
- core summary와 source-specific detail의 경계가 점점 중요해지고 있다.

이 문서는 위 문제를 정리하고, 다음 단계 rework의 범위를 명확히 하기 위해 작성한다.

---

## 현재 테이블 역할

### `source_payloads`
외부 소스에서 받은 raw payload를 저장하는 테이블이다.

역할:
- API 응답 원문 보존
- import 원문 보존
- parser 개선 후 재처리 가능성 확보
- 디버깅과 fixture 추출의 기준점 제공

현재 판단:
- 역할은 비교적 명확하다.
- 향후 entity metadata 확장 여지는 있지만 기본 방향은 적절하다.

---

### `activities`
활동(activity)의 공통 핵심 요약 정보를 저장하는 테이블이다.

역할:
- 소스 공통 activity summary
- UI / 비교 / 기본 분석의 기반
- source-agnostic query 지원

현재 판단:
- core table 역할이 명확하다.
- source-specific field를 과도하게 넣지 않는 원칙을 유지해야 한다.

---

### `source_metrics`
현재는 activity 단위 source-specific metric을 저장하는 역할을 하고 있다.

실제 역할:
- Garmin activity metric
- Intervals activity metric
- 기타 활동 단위 세부 지표

문제:
- 이름만 보면 “모든 source metric 저장소”처럼 보이지만,
  실제로는 `activity_id` 기반이라 activity-level metric 저장소에 가깝다.
- day-level source-specific metric을 담을 수 없다.
- 이름과 역할 사이에 간극이 있다.

현재 판단:
- 당장 rename하기보다 역할을 명확히 문서화하는 것이 우선이다.
- 이후 `activity_source_metrics`로의 rename 가능성은 별도 검토 대상이다.

---

### `daily_wellness`
일별 wellness 핵심 요약 정보를 저장하는 테이블이다.

역할:
- sleep / hrv / resting_hr / body_battery / stress_avg 등
- 앱 전반에서 공통으로 사용할 수 있는 daily summary 제공

문제:
- source-specific daily detail을 계속 이 테이블에만 넣기 시작하면 경계가 흐려진다.
- Garmin/Intervals/Runalyze 별 세부 daily metric을 모두 여기에 수용하기는 어렵다.

현재 판단:
- core daily summary 테이블로 유지하는 것이 맞다.
- source-specific daily detail은 별도 구조가 필요하다.

---

### `daily_fitness`
일별 fitness model / training state 성격의 요약 값을 저장하는 테이블이다.

역할:
- ctl / atl / tsb / ramp_rate
- vo2max / vdot / marathon shape 등 일부 일별 상태값

현재 판단:
- daily training model summary 역할로 유지하는 것이 적절하다.
- wellness detail 저장소로 확장하는 방향은 피해야 한다.

---

## 현재 문제 요약

### 1. activity-level / day-level metric 저장 구조가 비대칭이다
- activity-level은 `source_metrics`가 있다.
- day-level은 source-specific metric 저장소가 없다.

### 2. core summary와 source-specific detail의 경계가 모호해질 위험이 있다
- `daily_wellness`에 너무 많은 소스 특화 필드를 넣기 시작하면 core table 역할이 흐려진다.

### 3. 이름이 역할을 완전히 설명하지 못한다
- 특히 `source_metrics`는 현재 실제 역할보다 이름이 더 넓다.

### 4. 향후 소스 확장 시 중복 설계가 반복될 수 있다
- Garmin에서 드러난 문제는 Intervals / Runalyze / Strava에서도 다시 나타날 가능성이 높다.

---

## 이번 rework의 목표

이번 rework 브랜치의 목표는 다음과 같다.

1. 현재 테이블 역할을 명확히 정의한다.
2. day-level source-specific metric 저장 구조를 설계한다.
3. additive change를 우선 적용해 현재 기능을 깨지 않도록 한다.
4. 필요한 경우 새 테이블을 추가하되, 대규모 rename은 분리해서 다룬다.
5. Garmin과 Intervals에서 재사용 가능한 공통 방향을 만든다.

---

## 설계 원칙

### 1. raw는 계속 보존한다
raw payload 보존 전략은 유지한다.

### 2. core table은 보수적으로 유지한다
`activities`, `daily_wellness`, `daily_fitness`는 공통적으로 자주 쓰는 요약만 담는다.

### 3. source-specific detail은 별도 계층으로 분리한다
activity/day 수준 모두 source-specific metric은 별도 계층으로 저장하는 방향을 우선 검토한다.

### 4. rename보다 additive change를 먼저 한다
기존 쿼리와 테스트 영향도를 줄이기 위해,
가능한 경우 새 구조를 먼저 추가하고 이후 rename 여부를 검토한다.

### 5. 점진적으로 적용한다
한 번에 전체 소스에 강제 적용하지 않고,
Garmin / Intervals 같은 우선 소스부터 순차 적용한다.

---

## 우선 검토 대상

### 후보 1. `daily_source_metrics` 테이블 추가
의도:
- day-level source-specific metric 저장
- Garmin wellness detail
- Intervals daily custom wellness field
- 향후 Runalyze daily health metric 수용

예상 역할:
- core daily summary 밖의 source-specific metric 저장소
- numeric / json 형태 지원 가능

현재 판단:
- 가장 유력한 1차 additive change 후보

---

### 후보 2. `source_metrics` 역할 문서화
의도:
- 현재는 사실상 activity-level metric 저장소임을 명시
- immediate rename 없이 혼동을 줄임

현재 판단:
- 이번 브랜치에서 문서/코드 주석 수준으로 먼저 명확히 할 수 있다.

---

### 후보 3. 향후 rename 검토
대상 예시:
- `source_metrics` → `activity_source_metrics`

현재 판단:
- 의미는 더 명확해지지만 영향 범위가 넓다.
- 이번 브랜치에서는 바로 수행하지 않고 후속 단계로 검토하는 편이 안전하다.

---

## 1차 구현 방향(초안)

1. `daily_source_metrics` 추가 여부를 확정한다.
2. `src/db_setup.py`에 additive schema change 형태로 반영한다.
3. Garmin wellness detail 일부를 새 구조에 저장할지 검토한다.
4. Intervals daily metric에도 같은 구조를 적용할 수 있는지 확인한다.
5. rename은 보류하고, 문서/주석으로 역할을 먼저 정리한다.

---

## 이번 브랜치에서 하지 않을 것

- 광범위한 테이블 rename
- 기존 analysis query 전면 수정
- 모든 source를 한 번에 재구성
- raw/core/source-specific 경계를 한 번에 완전히 고정하려는 시도

---

## 기대 효과

이 rework가 끝나면 다음이 더 쉬워진다.

- daily wellness detail 확장
- source별 세부 metric 저장 일관성 확보
- Garmin 이후 Strava / Runalyze 확장 시 구조 재사용
- naming/schema cleanup의 다음 단계 분리
- 분석 레이어에서 activity/day metric 활용 범위 확대

---

## 요약

이번 rework의 핵심은 다음과 같다.

- raw payload 보존 전략은 유지한다.
- core summary table은 보수적으로 유지한다.
- source-specific metric 저장 구조를 activity/day 수준으로 더 명확히 나눈다.
- rename은 서두르지 않고 additive change를 우선한다.
- Garmin alignment에서 드러난 구조 문제를 공통 설계로 정리한다.

