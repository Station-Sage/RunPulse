# 외부 데이터 수집(Ingestion) 전략

## 목적

이 문서는 Intervals.icu, Garmin, Strava, Runalyze 같은 외부 소스에서 활동(activity) 및 웰니스(wellness) 데이터를 수집할 때 적용할 공통 전략을 정의한다.

목표는 다음과 같다.

- 실제 API 응답이 문서와 다르거나 더 많은 필드를 포함하더라도 안정적으로 대응한다.
- 파서(parser)와 스키마(schema)를 점진적으로 개선할 수 있도록 한다.
- 소스별 구현 차이를 흡수하면서도 공통된 저장 원칙을 유지한다.
- 나중에 분석(analyze)에서 필요해지는 필드를 다시 살릴 수 있도록 원본(raw)을 보존한다.
- fixture 기반 회귀 테스트를 만들기 쉬운 구조를 마련한다.

---

## 핵심 원칙: 먼저 원본(raw)을 저장하고, 그 다음 필요한 값을 추출한다

외부 소스의 데이터는 다음 순서를 기본 원칙으로 삼는다.

1. 가능한 한 원본 payload 전체를 저장한다.
2. 애플리케이션에서 공통으로 사용하는 핵심 필드만 정규화(normalize)해서 저장한다.
3. 소스별 특화 지표나 분석용 값은 별도의 유연한 저장소에 저장한다.
4. 파서가 바뀌더라도 raw payload 기준으로 재처리(reprocess)할 수 있어야 한다.

이 원칙을 따르면 다음과 같은 문제가 줄어든다.

- API 문서에 없는 필드를 나중에 발견하는 경우
- 같은 의미인데 소스마다 필드명이 다른 경우
- 초기에는 필요 없어 보였지만 나중에 분석에 필요한 경우
- 파서 버그 수정 후 예전 데이터를 다시 적재해야 하는 경우

---

## 저장 계층(Storage Layers)

### 1. Raw payload 저장 계층

외부 API에서 받은 응답 원문은 정규화 이전 또는 정규화와 함께 별도로 저장한다.

이 계층은 “현재 무엇을 분석에 쓰는가”와 무관하게, **외부 소스에서 실제로 무엇을 받았는가**를 보존하는 역할을 한다.

예시:

- Intervals activity list item
- Intervals wellness day
- Garmin activity summary
- Garmin activity detail
- Garmin sleep / HRV / stress / body battery / resting HR 응답
- Strava activity summary / detail / streams
- Runalyze activity / health 관련 payload

원칙:

- 원본 구조를 가능한 한 훼손하지 않는다.
- 필요한 값만 뽑아 저장하더라도 raw 자체는 남긴다.
- 이후 parser 개선이나 backfill 시 raw를 기준으로 다시 처리할 수 있어야 한다.

권장 메타데이터 예시:

- `source`
- `entity_type`
- `entity_id`
- `entity_date`
- `payload_json`
- `payload_hash`
- `endpoint`
- `fetched_at`
- `parser_version`
- `parse_status`
- `error_message`

현재의 `source_payloads` 테이블은 이 raw-ingestion ledger 역할의 중심으로 사용하고, 필요 시 컬럼을 확장한다.

---

### 2. Normalized core tables

정규화된 핵심 테이블은 앱 전반에서 넓게 쓰이고, 소스가 달라도 의미가 비교적 안정적인 필드만 담는다.

예시:

- `activities`
- `daily_wellness`
- `daily_fitness`
- `planned_workouts`
- `goals`

이 테이블은 다음 목적을 위해 존재한다.

- UI 표시
- 공통 분석 로직
- 리포트 생성
- 소스 비종속(source-agnostic) 조회

주의할 점은, 외부 소스에서 발견되는 모든 필드를 여기에 억지로 넣지 않는 것이다.  
소스별 특수 필드까지 모두 core schema로 끌어오면 스키마 변경이 잦아지고 유지보수가 어려워진다.

---

### 3. Source-specific extracted metrics 계층

공통 core schema에 넣기에는 너무 소스 특화적이거나, 아직 안정성이 확인되지 않은 값은 `source_metrics` 같은 별도 계층에 저장한다.

예시:

- `icu_training_load`
- `icu_intensity`
- `icu_hrss`
- `steps`
- `avg_stress_level`
- `body_battery_max`
- `avg_overnight_hrv`
- `training_effect_aerobic`
- `training_effect_anaerobic`
- `time_in_hr_zone_1`
- `time_in_power_zone_3`

이 계층의 목적은 다음과 같다.

- 분석 실험을 빠르게 진행한다.
- 소스 특화 리포트를 만든다.
- 새로 발견된 필드를 곧바로 활용해 본다.
- core table의 schema churn을 줄인다.

가능하다면 값 타입도 분리해 두는 것이 좋다.

예:

- numeric value
- text value
- JSON value

---

## 파서(Parser) 설계 원칙

파서는 “원본 저장”과 “정규화 추출”을 개념적으로 분리하는 방향으로 설계한다.

권장 흐름:

1. 외부 소스에서 payload를 가져온다.
2. raw payload를 저장한다.
3. payload를 파싱해서 normalized field를 만든다.
4. `activities`, `daily_wellness`, `daily_fitness` 같은 core table에 쓴다.
5. `source_metrics`에 소스 특화 지표를 쓴다.

이렇게 분리하면 다음이 쉬워진다.

- 파싱 로직 단위 테스트
- raw 기준 재처리(backfill)
- source별 디버깅
- fixture 기반 회귀 테스트
- API 재호출 없이 parser 개선 반영

---

## Parser versioning과 재처리(reprocessing)

외부 payload 구조는 바뀔 수 있고, parser도 실데이터를 보면서 계속 개선된다.

따라서 raw payload를 저장할 때, 가능하면 parser version 또는 parse status를 함께 관리하는 것이 좋다.

목적:

- 어떤 payload가 오래된 parser로 처리되었는지 파악
- 어떤 payload가 parsing에 실패했는지 기록
- metric 확장 후 어떤 범위를 재처리할지 판단

원칙적으로는 가능한 한 **외부 API를 다시 호출하기보다 raw payload에서 재처리하는 구조**를 우선한다.

---

## 소스별 적용 전략

### Intervals.icu

Intervals는 현재 방향과 가장 가까운 구현을 이미 가지고 있다.

현재 상태 요약:

- raw payload 저장이 이미 존재한다.
- normalized 데이터 추출이 이루어지고 있다.
- analysis 쪽에서도 `source_metrics`를 활용하고 있다.

따라서 Intervals는 처음부터 다시 설계하기보다는, 공통 전략 기준으로 정리(alignment)하는 것이 적절하다.

권장 후속 작업:

- raw payload의 `entity_type` 구분 명확화
- `parser_version` 추적 추가
- activity / wellness 저장 흐름 일관화
- 필요 시 selective reprocessing 지원

### Garmin

Garmin은 개선된 설계를 처음부터 적용하기 가장 적합한 대상이다.

이유:

- 실제 payload discovery가 진행 중이다.
- 현재 normalized model보다 실제 응답이 훨씬 넓다.
- activity summary와 detail 구조가 다르다.
- wellness 관련 endpoint가 여러 개로 나뉘어 있다.

권장 raw entity_type 예시:

- `activity_summary`
- `activity_detail`
- `sleep_day`
- `hrv_day`
- `stress_day`
- `body_battery_day`
- `rhr_day`

Garmin은 우선 raw-first 구조를 적용한 뒤, 앱에서 당장 필요한 필드만 제한적으로 normalized extraction 하는 방식이 적절하다.

### Strava

Strava도 실제 API 응답 확인 이후 같은 구조를 따른다.

예상 raw entity_type 예시:

- `activity_summary`
- `activity_detail`
- `activity_streams`
- `activity_laps`

### Runalyze

Runalyze도 실제 API 또는 bulk import 결과를 확인한 후 같은 모델을 적용한다.

Runalyze의 특수 지표는 우선 `source_metrics`에 저장하고, 여러 기능에서 공통적으로 필요한 경우에만 core schema 반영을 검토한다.

---

## 스키마 확장 원칙(Schema Evolution Policy)

새 필드를 발견했을 때는 다음 순서를 우선한다.

1. raw payload를 보존한다.
2. 그 필드가 아래 중 어디에 속하는지 판단한다.
   - core normalized data
   - source-specific metric
   - 아직 저장 불필요
3. 여러 기능에서 반복적으로 필요하고 의미가 안정적일 때만 core schema 변경을 고려한다.

이 원칙은 특정 소스 하나의 초기 샘플에 데이터베이스가 과적합(overfit)되는 것을 막는다.

---

## Fixture 전략

fixture는 discovery를 대체하는 것이 아니라, discovery 결과를 고정해 회귀(regression)를 막기 위한 수단이다.

권장 순서:

1. 실제 API 또는 import payload를 확인한다.
2. 민감정보를 제거(sanitize)한다.
3. 대표 샘플을 `tests/fixtures/...` 아래에 저장한다.
4. fixture 기반 smoke test / regression test / edge-case test를 만든다.

의미:

- Intervals fixture는 이미 가치가 있다.
- Garmin fixture는 실제 payload discovery 이후 만드는 것이 맞다.
- Strava / Runalyze fixture도 실제 응답 확인 후 만드는 것이 맞다.

---

## 구현 우선순위

현재 권장 순서는 다음과 같다.

1. 진행 중인 validation / integration 브랜치에서 실패 테스트가 있으면 먼저 안정화한다.
2. 이 문서로 ingestion 전략을 고정한다.
3. Garmin에 개선된 raw-first 설계를 처음 적용한다.
4. 실제 payload와 테스트로 패턴을 검증한다.
5. Intervals를 공통 설계 기준으로 정리한다.
6. 이후 Strava, Runalyze로 확장한다.

---

## 요약

권장 아키텍처는 다음과 같다.

- 외부 소스의 raw payload는 가능한 한 보존한다.
- 앱 공통 기능에 필요한 값만 신중하게 normalize 한다.
- 소스 특화 지표는 `source_metrics` 같은 유연한 저장 계층으로 분리한다.
- parser는 계속 진화할 것을 전제로 한다.
- 재처리는 외부 API 재호출보다 raw payload 기반 backfill을 우선한다.

이 구조는 데이터 손실을 줄이고, 스키마 변경 비용을 낮추며, 실제 외부 payload를 확인하면서 시스템을 점진적으로 발전시키는 데 가장 적합하다.

