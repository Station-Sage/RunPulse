# RunPulse 데이터 아키텍처 v0.3.1

> 이 문서는 **전체 지도 + 설계 원칙 + ADR**만 다룹니다.
> DDL 상세 → `phase-1.md` | Extractor 상세 → `phase-2.md` | 메트릭/컬럼 전체 목록 → `data_master.md` (자동 생성)

---

## Part 1: 설계 원점

### RunPulse는 어떤 앱인가

RunPulse는 단순한 러닝 로그 앱이 아닙니다. 여러 플랫폼에 흩어진 러닝 데이터를 **하나의 통합된 뷰**로 보여주고, 그 위에서 **기존 앱이 제공하지 못하는 깊은 분석**을 하고, **AI가 코칭**하고, **ML이 패턴을 발견**하는 플랫폼입니다.

**사용자가 활동 상세 페이지를 열었을 때 보고 싶은 것:**

> "오늘 10km를 52분에 뛰었다. 평균 심박 155, 최대 178. 케이던스 172. Garmin이 말하는 Training Effect는 3.2, VO2Max 52. Intervals가 계산한 TRIMP은 85, Efficiency Factor 1.67. Strava의 Relative Effort는 78. 날씨는 22도, 습도 65%. RunPulse가 종합 분석한 FEARP는 5:08/km, CIRS 32점, DARP 하프 1시간 42분."

이 경험을 제공하려면 **활동 하나에 대해 50개 이상의 지표가 통합**되어야 합니다.

### 데이터 모델이 풀어야 할 5가지 문제

1. **같은 활동, 소스마다 다른 값** — 대표값 + 소스별 원본 접근
2. **같은 개념, 소스마다 다른 이름/단위** — 정규 이름(canonical name) 통일
3. **같은 메트릭, 출처가 여러 개** — provider 필드로 구분, is_primary로 대표값 결정
4. **메트릭은 시간이 지나면서 진화** — 재처리(reprocess) 파이프라인
5. **종합 운동앱으로 확장** — 고정 컬럼 + EAV 하이브리드

---

## Part 2: 아키텍처 개요

### 핵심 통찰 — "Fat Summary + Metric Store" 하이브리드

**activity_summaries는 "두꺼운 core"로 유지합니다.** 대시보드에서 "최근 30일 거리/시간/페이스/심박 추세"를 볼 때 EAV를 매번 pivot하면 느립니다. 자주 조회하는 핵심 수치는 컬럼으로 둡니다.

기준:

> **센서가 직접 측정했거나, 단순 산술로 파생된 값** → `activity_summaries` 컬럼
> **알고리즘/모델이 적용된 계산 결과** → `metric_store` (EAV)

### 저장 계층 — 5 Layer

| Layer | 구성 | 역할 |
|-------|------|------|
| 0 | source_payloads | 외부 API 응답 원문 (절대 삭제 안 함) |
| 1 | activity_summaries, daily_wellness | 통합 요약 (센서 측정값 + 메타) |
| 2 | metric_store | 모든 메트릭 단일 저장소 (소스 + RunPulse + ML) |
| 3 | activity_streams, activity_laps, activity_best_efforts | 시계열/구조화 데이터 |
| 4 | gear, weather_cache, sync_jobs, 앱 테이블들 | 참조/캐시/운영/앱 기능 |

### 테이블 목록 (15 테이블 + 1 뷰)

| Layer | 테이블 | 역할 | 컬럼 | 예상 행 |
|-------|--------|------|------|---------|
| 0 | source_payloads | API 원문 보존 | 11 | ~3,000 |
| 1 | activity_summaries | 통합 활동 요약 | 38 | ~600 |
| 1 | daily_wellness | 일별 웰니스 요약 | 16 | ~1,500 |
| 2 | metric_store | 메트릭 통합 저장소 | 17 | ~55,000 |
| 3 | activity_streams | 시계열 GPS/HR/Pace | 15 | ~500,000 |
| 3 | activity_laps | 랩/스플릿 | 17 | ~5,000 |
| 3 | activity_best_efforts | 베스트 에포트 | 10 | ~2,000 |
| 4 | gear | 장비 참조 | 11 | ~20 |
| 4 | weather_cache | 날씨 캐시 (open_meteo) | 15 | ~1,000 |
| 4 | sync_jobs | 동기화 관리 | 13 | ~200 |
| 4 | chat_messages | AI 채팅 이력 | — | ~500 |
| 4 | goals | 사용자 목표 | — | ~10 |
| 4 | planned_workouts | 훈련 계획 | — | ~100 |
| 4 | user_training_prefs | 훈련 설정 | — | ~5 |
| 4 | session_outcomes | 세션 결과 | — | ~300 |
| — | v_canonical_activities | 대표 활동 뷰 | — | (view) |

> 컬럼 상세, 제약조건 → `phase-1.md` / 컬럼·메트릭 전체 배정표 → `data_master.md` (자동 생성)

### 핵심 설계 원칙

**P1: metric_store는 Single Source of Truth.** 동일 메트릭이 여러 소스에서 올 때 metric_store에서 provider별로 저장하고 is_primary로 대표값을 결정합니다.

**P2: metric_name은 질문을 반영합니다.** "TRIMP이 얼마야?" → metric_name = `trimp`. 같은 개념이면 같은 이름, provider로 출처 구분.

**P3: 기본 데이터와 메트릭은 구분합니다.** 센서 측정값/단순 산술 → activity_summaries. 알고리즘 산출물 → metric_store.

**P4: provider로 출처를 구분합니다.** garmin, strava, intervals, runalyze, runpulse:formula_v1, runpulse:ml_v1 등.

**P5: 재처리는 API 재호출 없이 가능합니다.** Layer 0 원문에서 Layer 1+2 재추출, Layer 1+2에서 RunPulse 메트릭 재계산.

### weather 데이터 흐름

weather 데이터는 두 경로로 들어옵니다. **경로 1**: Garmin/Strava/Intervals API → extractor → metric_store (category=weather, provider=garmin/strava/...). **경로 2**: open_meteo API → weather_cache (보충/계산용 캐시). weather_cache는 Calculator(FEARP, WLEI 등)가 직접 조회하는 독립 캐시입니다. metric_store로의 자동 파이프라인은 없습니다.

---

## Part 3: 데이터 분류 체계

### SSOT: src/utils/metric_registry.py

모든 컬럼과 메트릭의 정의는 MetricDef dataclass로 관리됩니다. 필드: name(정규 이름), category(도메인), storage(저장 위치), unit(단위), description(설명), scope(범위), aliases(소스별 원본 필드명). 이 파일이 데이터 정의의 Single Source of Truth입니다.

### storage — 어디에 저장되는가

| storage | 테이블 | 성격 |
|---------|--------|------|
| activity_summary | activity_summaries 컬럼 | 센서 측정값 + 메타 |
| wellness | daily_wellness 컬럼 | 일별 웰니스 기초 데이터 |
| metric | metric_store 행 | 알고리즘 산출물, 존 분포, 소스 파생값 |

Layer 3(streams, laps, best_efforts)은 채널 단위 시계열이므로 MetricDef 대상이 아닙니다. DDL로만 관리합니다.

### scope — 어떤 단위에 대한 값인가

| scope | 의미 | 예시 |
|-------|------|------|
| activity | 개별 활동 | avg_hr, trimp, weather_temp_c |
| daily | 하루 | sleep_score, ctl, stress_high_duration_sec |
| weekly | 주간 | di, tids, rmr |
| athlete | 선수 고정 속성 | max_hr_setting, ftp_setting |

### category — 16개 도메인

| category | 설명 |
|----------|------|
| hr | 심박 |
| power | 파워 |
| pace | 페이스 |
| running_dynamics | 러닝 다이내믹스 |
| volume | 운동량 |
| load | 부하 |
| efficiency | 효율성 |
| capacity | 체력/역량 |
| prediction | 예측 |
| sleep | 수면 |
| stress | 스트레스 |
| readiness | 준비도 |
| weather | 날씨/환경 |
| body | 신체 |
| meta | 메타/분류 |
| athlete | 선수 설정 |

> 카테고리별 메트릭 목록, scope×category 교차표, storage×category 교차표 → `data_master.md`

### 검증 체계

| 스크립트 | 역할 |
|----------|------|
| scripts/check_docs.py | 문서 간 정합성 (컬럼 수, 테이블 수, 용어) |
| scripts/check_data_consistency.py | SSOT ↔ DDL ↔ DB ↔ 문서 교차 검증 (9개 항목) |
| scripts/gen_data_master.py | SSOT에서 data_master.md 자동 생성 |
| scripts/gen_metric_dictionary.py | Calculator 메트릭 사전 생성 |

---

## Part 4: ETL 파이프라인

### Extractor 패턴

Extractor는 **DB를 모르는 순수 함수**입니다. JSON을 받아서 dict/list를 반환합니다.

| 메서드 | 반환 | 저장 대상 |
|--------|------|-----------|
| extract_activity_core() | dict | activity_summaries |
| extract_activity_metrics() | list[MetricRecord] | metric_store |
| extract_wellness_core() | dict | daily_wellness |
| extract_wellness_metrics() | list[MetricRecord] | metric_store |
| extract_streams() | list[dict] | activity_streams |
| extract_laps() | list[dict] | activity_laps |

### is_primary 결정

소스 우선순위: garmin > intervals > strava > runalyze. RunPulse 계산 메트릭은 항상 primary. 동일 metric_name + 동일 scope_id에서 가장 높은 우선순위 소스가 is_primary=1.

> Extractor 구현 상세 → `phase-2.md`

---

## Part 5: 전체 데이터 흐름 다이어그램

| 단계 | 구성요소 | 입력 | 출력 |
|------|----------|------|------|
| 1 | Garmin/Strava/Intervals/Runalyze API | 외부 호출 | raw JSON |
| 2 | Layer 0: source_payloads | raw JSON | 원문 100% 보존 |
| 3 | Extractors (순수 함수) | raw JSON | core_dict + metrics_list |
| 4 | Layer 1: activity_summaries, daily_wellness | core_dict | 센서 측정값 저장 |
| 5 | Layer 2: metric_store | metrics_list | provider별 메트릭 저장 |
| 6 | Metrics Engine (src/metrics/) | Layer 1 + Layer 2(소스) | Layer 2(RunPulse), provider=runpulse:formula_v1 |
| 7 | UI / AI Coach / Reports | Layer 1 (목록/필터) + metric_store (상세) | is_primary=1 기본 표시, provider별 비교 뷰 |

### CalcContext API (Metrics Engine)

Calculator는 **순수 함수**입니다. DB 직접 접근 없이 CalcContext를 통해서만 데이터를 읽습니다.

주요 메서드: activity(), get_metric(), get_metric_json(), get_metric_text(), get_wellness(), get_streams(), get_laps(), get_activities_in_range(), get_activity_metric(), get_activity_metric_text().

시맨틱 그룹(13개)으로 Calculator를 묶어 의존성 순서대로 실행합니다.

> CalcContext 상세, 시맨틱 그룹 목록 → `phase-4.md`

---

## Part 6: 재처리(Reprocess) & Backfill 전략

두 가지 독립적인 재처리 경로가 있습니다. 둘 다 외부 API를 호출하지 않습니다.

**경로 1: reprocess_all()** — Extractor 로직을 수정한 후 실행. Layer 0(raw)에서 Layer 1 + Layer 2를 전체 재추출합니다. source_payloads를 순회하면서 get_extractor(source)로 extractor를 가져오고, entity_type에 따라 extract_activity_core/extract_activity_metrics/extract_wellness_metrics를 호출하여 upsert합니다.

**경로 2: recompute_runpulse_metrics()** — Metrics Engine 알고리즘을 수정한 후 실행. Layer 1 + Layer 2(소스 메트릭)에서 RunPulse 결과를 전체 재계산합니다. 날짜 범위를 지정하거나 전체 범위를 자동 감지합니다.

이 구조의 핵심 가치: Extractor 수정과 Calculator 수정이 서로 독립적입니다. Extractor를 고치면 경로 1만, Calculator를 고치면 경로 2만 실행하면 됩니다.

> 구현 상세 → `phase-3.md`

---

## Part 7: 미래 확장 시나리오 검증

### 시나리오 1: 새 소스 추가 (예: Apple Health)

새 extractor 파일 작성 + metric_priority.py에 우선순위 추가. 기존 테이블/메트릭 구조 변경 없음. metric_store의 provider 필드로 자연스럽게 통합.

### 시나리오 2: 새 스포츠 추가 (예: 사이클링)

activity_summaries.activity_type으로 구분. 러닝 전용 컬럼(avg_ground_contact_time_ms 등)은 NULL. 사이클 전용 메트릭(normalized_power, tss 등)은 metric_store에 추가. activity_summaries 스키마 변경 불필요.

### 시나리오 3: ML 모델 결과 저장

provider=runpulse:ml_v1으로 metric_store에 저장. 기존 formula 결과와 공존. is_primary 로직으로 어떤 결과를 기본 표시할지 결정.

### 시나리오 4: 메트릭 알고리즘 버전업

provider를 runpulse:formula_v1 → runpulse:formula_v2로 변경. 구 버전 결과 보존 가능. recompute_runpulse_metrics()로 전체 재계산.

### 시나리오 5: 근력 운동 확장

activity_exercise_sets는 v0.3에서 metric_store(json_value)로 흡수. 단, 본격 지원 시 세트×반복×무게의 구조화된 쿼리를 위해 별도 테이블 복원을 검토. (→ ADR-011)

---

## Part 8: ADR (Architecture Decision Records)

### ADR-001: Fat Summary + Metric Store 하이브리드

센서 측정값은 activity_summaries 컬럼, 알고리즘 산출물은 metric_store EAV. 성능과 확장성의 균형.

### ADR-002: provider 체계

동일 메트릭의 다중 출처를 provider 필드로 구분. is_primary로 대표값 자동 결정.

### ADR-003: 재처리 2경로 분리

Extractor 재추출(경로 1)과 Calculator 재계산(경로 2)을 독립적으로 실행 가능.

### ADR-004: Layer 0 원문 보존

source_payloads에 API 응답 원문을 100% 보존. Extractor 수정 시 API 재호출 없이 재추출 가능.

### ADR-005: daily_fitness 테이블 삭제

ctl, atl, tsb, ramp_rate, vo2max를 metric_store로 이동. daily_fitness의 UNIQUE(date, source) 구조가 metric_store와 동일하여 중복. 테이블 수 16 → 15.

### ADR-006: 카테고리 재설계 (v0.3.1)

기존 39개 카테고리(hr_zone, power_zone, rp_load 등)를 16개 도메인 카테고리로 통합. rp_ prefix 제거, provider 필드로 출처 구분. dynamics → running_dynamics 통합, fitness → capacity 개명.

### ADR-007: MetricDef에 storage 필드 추가

activity_summaries 컬럼과 daily_wellness 컬럼도 MetricDef로 등록하여 SSOT 일원화. storage 값: activity_summary, wellness, metric.

### ADR-008: Layer 3 MetricDef 제외

activity_streams, activity_laps, activity_best_efforts는 채널 단위 시계열로 개별 메트릭화 부적합. DDL로만 관리.

### ADR-009: Calculator = 순수 함수

DB 직접 접근 금지. CalcContext API를 통해서만 데이터 읽기. 테스트 용이성과 재현성 보장.

### ADR-010: canonical 뷰 우선순위

v_canonical_activities 뷰에서 동일 활동 그룹 중 garmin > intervals > strava > runalyze 순으로 대표 1건 선택.

### ADR-011: activity_exercise_sets 처리

v0.2의 activity_exercise_sets는 v0.3에서 metric_store(json_value)로 흡수. 근력 운동 본격 지원 시 세트×반복×무게 구조화 쿼리를 위해 별도 테이블 복원 검토.

### ADR-012: 컬럼/메트릭 이름 단위 suffix 원칙

내부 저장값은 SI 기본 단위로 통일하고, 컬럼명 끝에 단위를 suffix로 명시한다. 이유: Garmin·Strava·Intervals 모두 m·sec·m/s 단위로 제공하므로 변환 손실이 없고, suffix로 단위를 명확히 하면 UI 변환 코드에서 실수를 줄일 수 있다. 단위 변환은 UI 표시 시점에서만 수행한다.

| suffix | 의미 | 예시 |
|--------|------|------|
| `_m` | 미터 | `distance_m`, `altitude_m` |
| `_sec` | 초 | `duration_sec`, `elapsed_sec` |
| `_ms` | 밀리초 또는 m/s(속도) | `avg_ground_contact_time_ms`, `avg_speed_ms` |
| `_sec_km` | 초/km (페이스) | `avg_pace_sec_km` |
| `_pct` | 퍼센트 | `avg_vertical_ratio_pct`, `cloud_cover_pct` |
| `_deg` | 도(angle) | `wind_direction_deg` |
| `_c` | 섭씨 | `weather_temp_c`, `dew_point_c` |
| `_kg` | 킬로그램 | `weight_kg` |
| `_cm` | 센티미터 | `avg_stride_length_cm` |

단위가 자명하거나 무차원인 컬럼(avg_hr, avg_cadence, sleep_score 등)은 suffix 생략.

---

## Part 9: 구현 로드맵

### 미래 확장 메트릭 (미구현)

Garmin API에서 제공하지만 아직 extractor에 미구현: skin_temp, fitness_age, hill_score, heat_acclimation_pct, altitude_acclimation, training_status, training_status_feedback, avg_sleep_stress, avg_spo2_sleep, training_readiness_acute_load_factor, race_shape.

### Phase 1 — 기반

db_setup.py 전면 재작성 (15 테이블 + 1 뷰), metric_registry.py 작성 (SSOT, 184 MetricDef), metric_priority.py 작성 (is_primary 로직), db_helpers.py 작성 (upsert 함수들).

### Phase 2 — Extractors

garmin_extractor.py, strava_extractor.py, intervals_extractor.py, runalyze_extractor.py. Extractor 단위 테스트 (fixture 기반).

### Phase 3 — Sync 재작성

garmin_activity_sync.py, garmin_wellness_sync.py, strava_activity_sync.py, intervals_activity_sync.py 전면 재작성. reprocess.py 구현.

### Phase 4 — Metrics Engine 구현 + 포팅

workout_classifier.py → metric_store 직접 조회. 나머지 metrics/*.py → 정규 이름 기반 조회. engine.py → metric_store에 provider=runpulse:formula_v1로 저장.

### Phase 5 — 서비스 레이어 + UI 적응

activity_summaries에서 메트릭 6개 제거 → metric_store 이동. 4개 extractor 수정. db_helpers.py upsert 수정. src/services/ 서비스 레이어 구현. src/web/ 뷰 수정.

### Phase 6 — 초기 적재 & 검증

전체 sync 실행. Reprocess 테스트. Computed metrics 전체 계산. Sanity check.
