# DESIGN-GARMIN-VO2MAX-PRECISE — Garmin VO2max 소수점 값 저장·백필

- 상태: 설계 초안 (2026-10-10). 구현 전 사용자 확인 필요(§7)
- BACKLOG: `[GARMIN-VO2MAX-PRECISE]`
- 범위: Garmin 정밀 VO2max(소수 1자리)를 일별 메트릭으로 저장하는 것, 과거 구간 백필, 기존 소비처를 "정밀값 우선, 정수 폴백"으로 바꾸는 것
- 범위 밖: UI 표시 형식(product 영역), 사이클링 VO2max(`cycling` 키, 현재 null), `training_status_day` ATL/CTL 파서 결함(§1.4, 별도 항목으로 제안)

---

## 1. 현재 상태 (2026-10-10 읽기 전용 조회)

### 1.1 저장 경로
| 경로 | 저장 위치 | 값 | 실제 데이터 |
|------|-----------|----|-------------|
| 활동 목록 `vO2MaxValue` (`garmin_extractor.py:124`, `garmin_v2_mappings.py:77,180,261`, ZIP `garmin_backfill.py:21`) | metric_store `activity` / `vo2max_activity` / garmin | 정수 | 261건, 2025-05-20~2026-10-09 |
| `get_training_status(date)` → `training_status_day` payload (`garmin_daily_extensions.py:26`) | source_payloads만 저장. VO2max는 파싱 안 함 | `mostRecentVO2Max.generic.vo2MaxPreciseValue` | 10건, 2026-05-02~05-11 |
| user_summary `vo2MaxValue` → `extract_fitness` → `save_daily_fitness` (`garmin_wellness_sync.py:154`) | metric_store `daily` / `vo2max` / garmin | 정수 | **0건**. user_summary payload에 해당 키가 없어 실행되지 않는 코드 |

- `vo2max` daily MetricDef는 이미 등록돼 있음(`metric_defs_misc.py:53`, "일별 VO2Max 추정치 (Garmin wellness)"). 행은 0건.
- `_upsert_vo2max()`(`garmin_helpers.py:23`)는 정의돼 있지만 호출하는 곳이 없음.

### 1.2 training_status_day가 10건뿐인 이유
`sync_daily_extensions()`는 CLI 경로(`src/sync.py` → `sync_garmin`)에서만 호출된다. 웹 백그라운드 동기화(`bg_sync.py:329`)는 `sync_activities`와 `sync_wellness`만 부른다. 그래서 2026-05 CLI 실행분만 남아 있다. 이 엔드포인트는 날짜 1개에 호출 1회가 필요하다(`/metrics-service/metrics/trainingstatus/aggregated/{date}`). 날짜별 백필 수단으로는 비효율적이다.

### 1.3 백필 API 확인 (실측, GET 5회)
`garminconnect.Garmin.get_max_metrics_range(start, end)` → `/metrics-service/metrics/maxmet/daily/{start}/{end}`

| 구간 | 응답 | 값이 있는 날 |
|------|------|-------------|
| 2026-09-01~2026-10-10 | list | 20일 (09-03 51.7 … 10-05 53.7, 10-09 53.9) |
| 2025-10-11~2026-10-10 (365일) | list | 162일 |
| 2024-10-11~2025-10-10 | list | 97일 (첫 값 2025-05-20 48.1, 2025-10-09 54.4) |
| 2023-10-11~2024-10-10 | 빈 list | 0 |

- 요소 형식: `{"userId", "generic": {"calendarDate", "vo2MaxPreciseValue", "vo2MaxValue", "fitnessAge", "maxMetCategory"}, "cycling", "heatAltitudeAcclimation"}`
- 365일 구간을 호출 1회로 받을 수 있다. 전체 이력(2025-05-20~)은 **호출 2회**로 끝난다.
- 응답에는 Garmin이 값을 갱신한 날만 들어 있다(희소). `vo2MaxValue`는 정밀값을 반올림한 값이다(53.7→54.0, 53.0→53.0).
- `training_status_day`의 `mostRecentVO2Max`는 "그 날짜 기준 가장 최근 측정"이라서 `generic.calendarDate`가 요청 날짜와 다를 수 있다. maxmet은 측정일에 값이 정확히 붙는다. 그래서 **maxmet을 원천으로 쓴다.**

### 1.4 관찰된 부수 결함 (이번 범위 밖)
`sync_daily_training_status`는 최상위 `acuteTrainingLoadDTO`/`trainingStatus`를 찾는다. 그런데 실제 payload의 최상위 키는 `mostRecentTrainingStatus`, `mostRecentTrainingLoadBalance`, `mostRecentVO2Max`, `heatAltitudeAcclimationDTO`다. 그래서 ATL/CTL을 저장하지 못한다. 별도 BUGS 항목으로 등록할 것을 제안한다.

---

## 2. 제안 설계

### 2.1 메트릭 이름·저장 위치 (결정 D1, 추천: 기존 `vo2max` daily 재사용)
```
metric_store
  scope_type = 'daily'
  scope_id   = generic.calendarDate (YYYY-MM-DD, Garmin 로컬 날짜)
  metric_name= 'vo2max'
  provider   = 'garmin'
  category   = 'capacity'
  numeric_value = vo2MaxPreciseValue (예: 53.9)
  raw_name   = 'vo2MaxPreciseValue'
  json_value = {"int": vo2MaxValue, "max_met_category": maxMetCategory}  -- 선택
```
- `daily_detail_metrics` 테이블은 없다. 일별 상세값도 metric_store `daily`에 저장된다(`_upsert_daily_detail_metric`도 같은 방식). 새 테이블과 DDL 변경은 필요 없고 SCHEMA_VERSION도 그대로 둔다.
- 저장은 측정일에만 한다(희소 저장, 앞 값 채우기 없음). 특정 날짜의 "현재 값"은 읽는 쪽이 `scope_id <= 날짜` 조건의 마지막 값으로 구한다(§2.4).
- MetricDef 설명만 고친다: `"일별 VO2Max 추정치 (Garmin maxmet 정밀값, 소수 1자리, 측정일만)"`. aliases는 `{"garmin": "vo2MaxPreciseValue"}`로 둔다.
- 이렇게 하면 이미 daily `vo2max`를 읽는 소비처 5곳(`views_report_loaders.py:51`, `chat_context_rich.py:176`, `chat_context_builders.py:30,156`, `ai_context_legacy.py:61`, MCP `tool_exec_context.py:97` get_fitness)이 코드 변경 없이 바로 값을 받는다.

### 2.2 수집 모듈 (새 파일, 300줄 규칙 준수)
`garmin_extractor.py`가 이미 687줄이다. 그래서 `garmin_lap_fields.py`처럼 별도 모듈로 분리한다.

```python
# src/sync/extractors/garmin_maxmet_fields.py
def extract_vo2max_daily(extractor, items: list[dict]) -> dict[str, list[MetricRecord]]:
    """maxmet/daily 응답 → {date: [MetricRecord('vo2max', precise, raw_name=...)]}.
    generic이 없거나 precise와 정수 값이 모두 None이면 건너뜀. precise가 없으면 정수 값으로 폴백."""
    # extractor._metric("vo2max", ..., raw_name="vo2MaxPreciseValue") 사용 → 정합성 검사 #10/#11 대상

# src/sync/garmin_maxmet_sync.py
def sync_vo2max_range(conn, client, start: str, end: str, *, limiter=None) -> int:
    """get_max_metrics_range 1회(구간 ≤ 365일) → 날짜별 raw 저장 + metric 저장 + resolve_primaries.
    반환: 저장한 측정일 수. 429는 RateLimiter.handle_rate_limit()로 넘김. 실패 시 sync를 중단하지 않음."""
def backfill_vo2max(conn, client, start: str, end: str, *, sleep=3.0) -> dict:
    """365일 창으로 나눠 sync_vo2max_range 반복. 창 사이 sleep, 429면 중단하고 다음 시작일 반환."""
```
- raw 저장: `_store_raw_payload(conn, "maxmet_day", calendarDate, item)`. 날짜 1개 = 행 1개이고 payload_hash로 멱등이다. 구간 전체를 담은 한 덩어리(`*_range`)로 저장하지 않고 날짜별로 나눈다. 그래야 reprocess(ADR-012)가 날짜 단위로 다시 만들 수 있다.
- 정기 동기화 연결: `bg_sync`의 Garmin 배치가 끝나면 `sync_vo2max_range(win_from, win_to)`를 **창마다 1회** 호출한다. CLI `sync_garmin`에도 같은 함수를 넣는다. `extract_fitness`의 user_summary 기반 vo2max 경로(실행되지 않는 코드)와 `_upsert_vo2max`는 삭제한다(결정 D4).

### 2.3 is_primary
daily `vo2max`의 provider는 지금 garmin 하나뿐이라 `resolve_for_scope`가 그대로 garmin을 고른다. 나중에 intervals나 runalyze가 같은 이름으로 들어오면 metric_priority를 따른다.

### 2.4 읽기 헬퍼 (Calculator 밖, 서비스·분석 계층)
```python
# src/utils/vo2max_source.py
def garmin_vo2max_asof(conn, as_of: str | None = None) -> tuple[float | None, str]:
    """(값, 출처). 1) daily vo2max/garmin 중 scope_id <= as_of의 최신값 → ('precise')
    2) 없으면 vo2max_activity/garmin 중 활동 날짜 <= as_of의 최신값 → ('activity_int')
    3) 없으면 (None, 'none'). 반환값은 round(1)."""
def garmin_vo2max_weekly_last(conn, wk_start: str, wk_end: str) -> float | None:
    """주 구간 안의 마지막 정밀값. 없으면 기존 _fitness_last_from_activity_metrics 정수값으로 폴백."""
```
- 정밀값이 너무 오래됐을 때의 기준은 결정 D3에서 정한다. 추천은 as_of 기준 30일보다 오래되면 활동 정수값을 쓰지 않고 정밀값을 그대로 쓰는 것이다. 정밀값과 정수값은 같은 Garmin 추정이고 정수값은 반올림일 뿐이라서, 날짜가 같거나 더 최신일 때만 정수값이 의미가 있다. 그래서 두 값의 날짜를 비교해서 더 최신인 쪽을 쓴다. 날짜가 같으면 정밀값을 쓴다.
- Calculator(ADR-009)가 필요해지면 `ctx.get_daily_metric_series("vo2max", days, provider="garmin")`의 마지막 값을 쓴다. 지금은 vo2max를 소비하는 Calculator가 없다(`src/metrics/` grep 결과 0건).

---

## 3. 소비처 변경 (정밀값 우선, 정수값 폴백)

| # | 위치 | 현재 | 변경 |
|---|------|------|------|
| C1 | `analysis/race_readiness.py:239` | 최신 `vo2max_activity` → runalyze `effective_vo2max` | `garmin_vo2max_asof(conn)` → 그다음 runalyze 폴백. 출력 `vo2max`는 소수값 |
| C2 | `analysis/trends.py:167` `fitness_trend` | 주간 마지막 활동 정수값 | `garmin_vo2max_weekly_last` (정밀값, 없으면 정수값) |
| C3 | `analysis/activity_deep.py:415` `fitness_ctx["garmin_vo2max"]` | rowid 기준 전역 최신 활동값(활동 날짜와 무관한 결함) | `garmin_vo2max_asof(conn, act_date)` |
| C4 | `web/views_activity_g2_performance.py:131` | `garmin.get("vo2max")`(그 활동의 정수값) 우선 | `fitness_ctx["garmin_vo2max"]`(as-of 정밀값) 우선, 활동 정수값은 폴백 |
| C5 | `utils/metric_groups.py:40` SEMANTIC_GROUPS `vo2max` | activity 멤버 2개 | `("vo2max", "garmin")` 멤버 추가(결정 D2) |
| C6 | `utils/provider_matrix_rows.py:87` | `vo2max_activity` activity | garmin 칸을 `("vo2max","garmin","daily")`로 바꿀지는 결정 D2 |
| C7 | 예측 엔진(`src/metrics/prediction/*`, `prediction_compare_service`) | VO2max 입력 없음(VDOT·Garmin 예측 사용) | 변경 없음. 문구 확인만 |
| C8 | daily `vo2max` 기존 소비처 5곳(§2.1) | 데이터 0건 | 코드 변경 없음. 값이 생기는지 회귀 확인 |
| C9 | `frontend/src/lib/metrics.ts:61` 활동 KEY_METRIC_NAMES | `vo2max_activity` | 백엔드만 바꿈. 표시 방식은 product-architect에 넘김 |

---

## 4. 백필 절차
1. 백업: `running.db.bak-YYYYMMDD-pre-vo2max-precise` (운영 DB에 쓰기 전에 반드시)
2. 컨테이너에서 실행: `docker exec runpulse-runpulse-1 sh -c 'cd /app && PYTHONPATH=. python3 scripts/backfill_garmin_vo2max.py --user pansongit@gmail.com --start 2023-10-01 --dry-run'` → 날짜 수와 최소·최대값을 확인한 뒤 `--dry-run` 없이 다시 실행
3. 시작일 기본값: 그 사용자의 가장 이른 garmin 활동 날짜(2023-10-29). 빈 창은 호출 1회로 끝난다. 예상 호출 수는 3회
4. 429 대응: `RateLimiter("garmin")`을 그대로 쓴다. 창 사이에 3초 쉬고, 429가 나면 `handle_rate_limit()` 백오프를 1회 거친다. 다시 429가 나면 `set_retry_after`를 기록하고 처리한 마지막 창의 다음 시작일을 출력한 뒤 종료한다(재실행해도 멱등)
5. 검증: 행 수 약 260(97+162 근처), 2026-10-09 = 53.9, 2026 5월 최대값 = 54.3 근처, 정수값과의 차이 |round(precise) − vo2MaxValue| = 0
6. 문서: `gen_metric_dictionary.py`, `check_docs.py`, `check_data_consistency.py --db …`

---

## 5. 테스트 계획
| 파일 | 내용 | 예상 수 |
|------|------|---------|
| `tests/test_garmin_maxmet_fields.py` | 정상 list → 날짜별 레코드, precise 없을 때 정수값 폴백, generic None·빈 list, 잘못된 값(문자열/None) 무시 | 5 |
| `tests/test_garmin_maxmet_sync.py` | 가짜 client로 저장과 `maxmet_day` raw 확인, 재실행 멱등(행 수 그대로), 365일 창 분할, 429 → 중단과 재개 시작일 반환, 예외 시 0 반환(sync 계속) | 6 |
| `tests/test_vo2max_source.py` | 정밀값 우선, 정수값 폴백, as_of 경계(당일 포함), 날짜가 같으면 정밀값, 둘 다 없으면 None | 5 |
| 기존 회귀: race_readiness·trends·activity_deep·report_loaders 테스트 | 정밀값이 있는 fixture에서 소수값 노출, 정밀값이 없는 fixture에서 기존 정수값 유지 | +4 |
| `check_data_consistency` #10/#11 | `vo2max`가 등록된 이름이고 category가 `capacity`인지 | 자동 |

합계 약 20개. 실제 Garmin을 호출하는 테스트는 없다(가짜 client만 사용).

---

## 6. 작업 분해
| ID | 작업 | 산출 | 의존 |
|----|------|------|------|
| T1 | `garmin_maxmet_fields.extract_vo2max_daily`와 테스트 | 새 파일 2개 | — |
| T2 | `garmin_maxmet_sync.sync_vo2max_range`/`backfill_vo2max`와 테스트 | 새 파일 2개 | T1 |
| T3 | MetricDef `vo2max` 설명·alias 수정, `gen_metric_dictionary.py` 실행 | `metric_defs_misc.py`, `metric_dictionary.md` | T1 |
| T4 | 정기 동기화 연결: bg_sync Garmin 배치와 CLI `sync_garmin`. user_summary vo2max 경로와 `_upsert_vo2max` 삭제 | `bg_sync.py`, `garmin.py`, `garmin_wellness_sync.py`, `garmin_extractor.py`, `garmin_helpers.py` | T2 |
| T5 | `src/utils/vo2max_source.py`와 테스트 | 새 파일 2개 | T3 |
| T6 | 소비처 C1~C4 교체와 회귀 테스트 | 분석 3개 + 뷰 1개 | T5 |
| T7 | SEMANTIC_GROUPS·provider matrix(C5/C6), 결정 D2 반영 | 2개 파일 | T3, D2 |
| T8 | `scripts/backfill_garmin_vo2max.py`(dry-run 기본, 백업 확인) → 사용자 승인 후 운영 백필 실행 | 스크립트, 실행 로그 | T2, T4 |
| T9 | ADR 기록(D1~D4), `check_docs`, `check_data_consistency`, BACKLOG·DONE 갱신. §1.4 결함은 BUGS에 등록 | 문서 | 전체 |

T1~T7은 한 브랜치(`feat/garmin-vo2max-precise`)에서 진행한다. T8은 운영 DB 쓰기라 따로 승인을 받는다.

---

## 7. 결정 필요 사항 (추천안 포함)
- **D1 메트릭 이름**: (a, 추천) 기존 daily `vo2max`를 재사용한다. 이미 등록돼 있고, 읽는 곳 5곳이 바로 살아나고, 이름이 늘지 않는다. (b) 새 이름 `vo2max_precise`. 출처 구분은 분명하지만 등록·사전·소비처를 모두 새로 맞춰야 하고, 같은 개념이 이름 두 개로 갈라진다.
- **D2 비교 그룹·매트릭스 칸**: (a, 추천) SEMANTIC_GROUPS에 daily 멤버를 추가하고, 매트릭스 garmin 칸을 daily `vo2max`로 바꾼다(정밀값). activity `vo2max_activity`는 활동 단위 기록으로 유지한다. (b) 그대로 둔다.
- **D3 정밀값 신선도**: (a, 추천) 정밀값과 활동 정수값 중 측정일이 더 최신인 쪽을 쓰고, 같으면 정밀값을 쓴다. 나이 제한은 두지 않는다(정수값도 같은 추정이기 때문). (b) 정밀값이 30일보다 오래되면 "오래됨" 플래그를 붙인다(표시 여부는 product 결정).
- **D4 실행되지 않는 코드 정리**: (a, 추천) user_summary `vo2MaxValue` 경로와 `_upsert_vo2max`를 삭제한다. 두 번째 쓰기 경로가 생기는 것을 막기 위해서다. (b) 그대로 둔다.
- **D5 training_status_day 수집**: (a, 추천) 이번 범위에서는 손대지 않는다. maxmet이 VO2max를 대체한다. ATL/CTL 파서 결함(§1.4)은 따로 처리한다. (b) bg_sync에 일별 확장 전체를 연결한다. 날짜마다 호출이 5회 이상 늘어서 429 위험이 커진다.

---

## 8. 위험
| 위험 | 영향 | 완화 |
|------|------|------|
| maxmet 응답 형식이 바뀌거나 365일 상한이 바뀜 | 백필이 비거나 실패 | 창 크기를 상수로 두고 실패 시 절반으로 다시 시도. 응답 형식은 테스트 fixture로 고정 |
| 희소 저장이라 "그날 값"을 조회하면 None | 오늘 화면 등에서 값 없음 | 모든 소비는 as-of 헬퍼를 거치게 한다. `scope_id=당일` 직접 조회는 금지(C3의 기존 `_ms_daily` 방식 주의) |
| 정밀값과 정수값이 섞여 차트가 계단 모양 | 추세 해석이 왜곡됨 | 주간 추세(C2)는 정밀값이 있는 주에는 정밀값만 쓰고, 출처를 응답에 함께 담는다 |
| 운영 백필 중 429 | 일부 구간만 채워짐 | 멱등 재실행, 재개 시작일 출력, retry_after 기록 |
| `calendarDate`가 Garmin 로컬 날짜임 | 활동 as-of 비교에서 하루 어긋날 수 있음 | 활동 날짜도 로컬 `start_time[:10]` 기준(현재 저장 방식과 같음) |

---

## 9. Definition of Done
1. maxmet 기반 daily `vo2max`(garmin)가 정기 동기화 창마다 갱신되고 raw `maxmet_day`가 저장된다
2. 운영 백필 후 행 약 260건, 2026-10-09 = 53.9
3. C1~C4가 정밀값을 우선 쓰고, 정밀값이 없는 fixture에서는 기존 정수값 동작을 유지한다
4. §5 테스트 전체와 기존 `pytest tests/`가 통과한다
5. `gen_metric_dictionary.py`, `check_docs.py`, `check_data_consistency.py`에서 🔴 0건
6. ADR(D1~D5) 기록, BACKLOG 항목이 DONE으로 이동, §1.4 결함이 BUGS에 등록됨

## 10. 구현 기록
- T1~T7 구현 완료(수집·동기화 연결·D4 정리·`vo2max_source`·소비처 C1~C3·그룹/매트릭스). C4 는 C3 의 fitness_ctx 를 그대로 사용. T8 백필은 사용자 승인 대기.
