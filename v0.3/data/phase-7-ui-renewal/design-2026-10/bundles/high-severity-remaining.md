# 설계: 상 심각도 잔여 7건 (T-01, M-01, M-03, M-04, D-01, D-03, C-01)

- 상태: 결정 확정(2026-10-11, HSR-1~10), 구현 전 — T-01 실데이터 확인 남음. 범위 제외: P-01~P-08(훈련 계획 묶음), T-03/M-02(`data-freshness.md`), T-05/A-01(`non-running-activities.md`)
- 변경 이력: 2026-10-11 원인 검증 반영 — T-01 근본 원인·설계안·단계 재작성(v2 경로 매칭 존재 확인, 실데이터 확인 항목 추가)
- 변경 이력: 2026-10-11 설계서 동기화 — `decisions-table.md` HSR-1~6 결정을 설계안·변경 파일·단계·검증·호환성에 반영
- 변경 이력: 2026-10-11 HSR-7 반영 — M-03 floor 를 지표별로 `MetricDef` 에 정의(전역 floor 아님). 결정 섹션 축약
- 변경 이력: 2026-10-11 2차 동기화 — HSR-8(모든 지표 floor, 원단위 절댓값 + 누락 검증)·HSR-9(동기화된 건 = 신규 활동 수) 반영, §7 해소 항목 축약
- 변경 이력: 2026-10-11 3차 동기화 — HSR-10(두 소스 같은 활동은 canonical 1건으로 신규 집계) 반영: 집계 위치를 동기화 오케스트레이터로 옮기고 소스별 `sync_activities` 수정 제거
- 변경 이력: 2026-10-11 5차 동기화 — V1-1 정정·V1-2(v1 일몰 = UI·라우트 일몰): 4차에서 지운 `_auto_match_after_sync` 호환성 서술을 grep 사실(v1 라우트 전용, v2 는 `bg_sync`)로 복원, §7-5 해소
- 관련 ADR: ADR-009(Calculator raw SQL 금지 — 본 설계는 Calculator 무변경), ADR-020(판정·등급은 서버 SSOT)
- 묶음: **G1 "같은 수치를 여러 곳에서 각자 계산"**(M-03, M-04, D-03) / **G2 "매칭 실행 여부가 보이지 않음"**(T-01) / 단독: M-01, D-01, C-01

## 1. 근본 원인
- **T-01** (G2) `week_compliance.outcome_label`은 `matched_activity_id`가 없으면 과거일을 `missed`로 판정한다(같은 주 "31.1/47.9km 완료"는 `v_canonical_activities` 합산이라 매칭과 무관 → 모순). 정정: v2 동기화(`sync_trigger_service`/`sync_range_service` → `BgSyncThread._run_batches`)도 완료 직후 `bg_sync.py:277-290`에서 최근 4주 `match_week_activities`를 실행한다(c9e4b23, 10-10 추가). 매칭 호출이 없는 것은 `src/sync.py` CLI뿐이다. 합성 DB 재현 결과 T-01 패턴(5일 전부 missed, 0/5)은 "매칭 미실행"일 때만 나오고, 매칭이 실행되면 P-06 패턴(2/5)이 된다. 미실행 후보는 3가지이며 지금은 하나로 확정할 수 없다(§4 실데이터 확인): ① 사본 DB의 마지막 동기화가 c9e4b23 이전이거나 CLI로 실행됨 ② 조기 return(garmin 로그인 실패 135-138, stop/pause 158-168·187, 소스 오류 200-210, 429 213-222, 배치 오류+0건 237-244)으로 매칭 블록에 도달하지 못함 ③ 매칭 예외가 `except: pass`(289-290)에 흔적 없이 삼켜짐. 확정된 부수 원인: 거리 비율 상한 `MAX_RATIO=1.6`(`match_select.py:10,40-41`)으로 10/8·10/9가 탈락하고, 이지 페이스 판정이 볼륨보다 먼저 실행되어(`week_compliance.py:69-72`) 10/6·10/7이 "강도 어긋남"이 된다. 잠재 결함(재현됨, 이번 데이터 해당 여부 불명): `_effective` 순위(48-52)가 미매칭 외부 계획을 매칭된 planner 행보다 우선해 missed로 만든다.
- **M-01** `story_service.py:153~192` 주 분기가 월 분기 지역변수 `prev_year`를 참조(→ UnboundLocalError 500). 같은 분기가 `prev_date.year`(달력 연도)와 `isocalendar()[1]`(ISO 주)를 섞어, 연말(예: 2027-01-01은 2026-W53)에 잘못된 범위·링크를 만든다. 기간 파싱/이전/다음 계산이 함수 안에 흩어져 있는 것이 원인.
- **M-03** (G1) 변화율 계산이 3곳에 따로 있다: 서버 `metrics_browser_service._change`(목록, 14일 창)·`get_metric_trend`의 `change_pct = (cur-first)/first`(부호 있는 분모), 프론트 `trendChart.periodChange`(`/abs(first)`)·`changeLabel`(30일 창). 분모 부호 처리 차이가 API↔UI 부호 반전(ramp_rate, skin_temp 등)을, 0 근처·부호 교차 기준(TSB, REC)이 수백~수천 %를 만든다. 근본적으로 "이 지표에 %가 의미 있는가(비율 척도인가)"라는 메타데이터가 없다.
- **M-04** (G1) `get_metric_trend` 219행 `peak = max(value)`로 방향성을 무시. 같은 함수가 이미 `HIGHER_IS_BETTER` 기반 `best/worst`를 계산하지만 상세 페이지는 `trend.peak`만 렌더한다. `higher_is_better=None`(예측·중립)은 "피크" 개념 자체가 없다.
- **D-01** `frontend/src/routes/data/{export,settings,settings/ai}/+page.svelte`에 `{base}` 없는 절대 경로 6건. 재발 방지 장치(정적 검사)가 없다.
- **D-03** (G1) 개요 타일은 `data_service.py:66`의 소스별 `activity_summaries` 원시 행 합(중복 포함 1,427), sync-state는 `v_canonical_activities` 중 running만(488), 중복 그룹 전체는 약 626. "활동 수" 정의가 서비스마다 다르다.
- **C-01** `coach/[threadId]/+page.svelte:220` 사용자 말풍선에 `whitespace-pre-wrap`·`overflow-wrap:anywhere`·`min-w-0`이 없어 무공백 문자열이 flex 컨테이너를 밀어내고 입력 줄바꿈이 합쳐진다.

## 2. 설계안
- **T-01 (A: 관측 가능성 우선, 이동 없음)** 매칭 위치는 유지(`bg_sync` 완료 후). 공용 후처리로 옮기는 기존 안은 "v2에 없음"이라는 전제가 틀려 철회한다.
  ① `bg_sync` 매칭 블록을 `src/training/match_hooks.py`(신규) `run_post_sync_match(conn, weeks=4) -> {weeks, matched, error}`로 추출한다. `except: pass` 대신 `update_job(last_error=...)`과 로그를 남기고 결과를 `sync_jobs.result_json.match`에 기록한다(실패해도 동기화는 계속).
  ② 조기 return(HSR-5): 이번 실행에서 **동기화된 건이 1건 이상이면 매칭을 실행**하고, 0건이면 실행하지 않고 `result_json.match={"skipped":"<사유>"}`를 기록한다(로그인 실패는 자연히 0건 → skip). "동기화된 건"(HSR-9)은 **이번 실행에서 새로 생긴 활동 수만** 센다 — 소스별 합계·기존 활동 갱신은 제외. 같은 활동이 두 소스에서 처음 들어오면 **canonical 1건**으로 센다(HSR-10). 집계 위치는 소스가 아니라 **동기화 오케스트레이터**(`bg_sync` 배치 종료 지점·CLI `src/sync.py`)이며, 실행 시작 전과 모든 소스 수신·중복 그룹화 후의 `activity_counts(conn).canonical_total`(D-03 헬퍼) 차이를 신규 수로 쓴다(음수는 0). 소스별 `sync_activities` 반환값은 바꾸지 않는다. 결과는 `counts_json.new_activities` 로 기록하고 조건 판정에 쓴다. 일부 누락 상태의 매칭은 다음 동기화의 4주 재매칭으로 갱신된다.
  ③ CLI `src/sync.py`도 같은 함수를 호출한다(실제로 빠진 유일한 경로).
  ④ "매칭 미실행" 표시(HSR-6): 스트립에서 missed 와 **구분하지 않는다**. 관측은 로그·`result_json.match`로만. 실데이터 확인 결과 원인 ①이면 `unverified` 표시안((b))을 재검토한다.
  ⑤ 거리 비율 상한(HSR-1): `match_select`에서 **같은 날 후보가 1개면 비율 상한을 무시**, 후보가 여럿이면 `MAX_RATIO=1.6` 유지. `coach-plan-bundle.md`의 판정 순서(PLN-6)·`_effective` 순위(PLN-10)와 단일 결정이며 그 두 항목은 그 설계서 R3에서 처리한다.
  - 기각: B(읽기 시점 즉석 매칭) — 저장 상태와 화면이 갈라짐.
- **M-01** `src/services/story_period.py`(신규, ~60줄) 값 객체 `Period(kind, key, start, end)` + `parse(key)`, `prev()`, `next()`. 주는 `date.fromisocalendar`/`isocalendar().year`만 사용(달력 연도 혼용 금지), 잘못된 키는 `ValueError` → 라우트 400. `story_service`는 `Period`만 소비(분기 제거).
- **M-03 (A)** 서버 SSOT `src/services/metric_change.py`(신규, ~70줄) `compute_change(points, slug, window) -> {abs, pct|None, pct_suppressed: reason|None, window_days, direction: better|worse|neutral|None}`. 규칙: ① 분모는 `abs(base)` 단일 정의, ② `pct`는 지표가 비율 척도이고 `abs(base) >= floor`일 때만, 아니면 `pct=None`+사유(`interval_scale`/`near_zero_base`), ③ direction은 `HIGHER_IS_BETTER`로 서버가 판정. `floor`는 **지표별 값**(HSR-7)으로 `MetricDef`에 `scale`과 함께 정의하며 전역 공통 floor는 두지 않는다. HSR-8: floor 는 **지표 원단위 절댓값**(비율·정규화 값이 아닌 그 지표의 저장 단위 값, 예: skin_temp 는 °C)이고 **비율 척도 여부와 무관하게 모든 지표에 값을 채운다**(비율 척도가 아닌 지표는 ②에서 `interval_scale` 로 먼저 걸러지므로 floor 는 판정에 쓰이지 않지만 값은 둔다). 필드는 기본값 없는 필수 정보로 다루고, 신규 지표 누락은 아래 검증이 막는다. `_change`와 `get_metric_trend`가 이 함수를 호출, 프론트 `periodChange`/`changeLabel`의 % 계산 제거(렌더만). 척도·floor 메타는 **`MetricDef.scale` + 지표별 floor 필드**(HSR-2·HSR-7, `src/utils/metric_def.py`, SSOT)로 두고 `gen_metric_dictionary`·`check_docs`·`check_data_consistency`를 함께 수정한다. 누락 방지(HSR-8): `check_data_consistency` 에 "모든 MetricDef 에 scale·floor 존재, floor ≥ 0 숫자" 검사를 추가하고, 같은 조건을 레지스트리 전체를 순회하는 단위 테스트(`tests/test_metric_def_floor.py`)로도 강제해 신규 지표가 floor 없이 추가되면 CI 에서 실패한다. 사전(`metric_dictionary.md`)에 floor·단위를 출력한다.
  - 기각: B(프론트 임계값 숨김) — ADR-020 위반·3곳 중복 유지.
- **M-04** `get_metric_trend` 응답에 `best/worst`(이미 계산됨)를 노출하고 `peak`는 deprecate(한 릴리스 유지 후 제거). 타일 라벨(HSR-3)은 **방향 반영 "최고/최저"**, `higher_is_better=None`(중립·예측) 지표는 best/worst를 `null`로 두고 프론트가 **타일을 숨긴다**(`range` 필드·`extreme_kind` 불필요).
- **D-01** 6건 `{base}` 적용(`$app/paths`) + `scripts/check_frontend_links.py`(신규, ~40줄): `frontend/src/**/*.svelte`에서 `href="/`·`goto('/`로 시작하는 리터럴을 실패 처리, `check_docs.py`에 검사 추가 또는 pre-commit 연결.
- **D-03** `src/services/activity_counts.py`(신규, ~40줄) `activity_counts(conn) -> {canonical_total, canonical_running, raw_by_source}` 단일 정의. `data_service` 개요와 `sync_state_service.activity_count`가 이를 소비. 개요 타일(HSR-4)은 **전체 canonical·러닝을 둘 다 표시**하고 라벨로 구분. 소스별 행 수는 "소스별 수신"으로 별도 표기 유지.
- **C-01** 사용자 말풍선 클래스에 `whitespace-pre-wrap [overflow-wrap:anywhere]` + 부모 flex 자식 `min-w-0`. 어시스턴트 말풍선·답변 근거 카드에도 같은 유틸 클래스 적용 여부 동시 점검.

## 3. 변경 파일 표
| 파일 | 구분 | 예상 줄 |
|---|---|---|
| src/training/match_hooks.py | 신규(bg_sync 블록 추출 + 결과 반환) | ~40 |
| src/web/bg_sync.py, src/sync.py | 수정(호출·실행 전후 canonical 차이로 신규 활동 수 산출(HSR-9·10)·`counts_json.new_activities`·skip 사유·result_json 기록) | -12 +26 / +6 |
| src/training/match_select.py | 수정(같은 날 후보 1개면 비율 상한 무시) | +8 |
| src/services/story_period.py / story_service.py | 신규 / 수정 | ~60 / -25 |
| src/services/metric_change.py | 신규 | ~70 |
| src/utils/metric_def.py + 레지스트리 정의, scripts/gen_metric_dictionary.py, check_data_consistency 검사 | 수정(`scale`·지표별 floor 필드, **모든 지표**에 원단위 절댓값 채움(HSR-8), 사전 출력, scale·floor 누락 검사) | +15 / 지표 수만큼 / +5 / +10 |
| src/services/metrics_browser_service.py | 수정 | -20 +10 |
| src/services/activity_counts.py / data_service.py / sync_state_service.py | 신규 / 수정 | ~40 / ±10 |
| frontend/src/lib/trendChart.ts, metricMeaning.ts, routes/library/metrics/{+page,[slug]/+page}.svelte | 수정(% 계산 제거, 최고/최저 타일·중립 숨김) | -30 +15 |
| frontend 개요 타일(data 개요 페이지) | 수정(전체·러닝 두 값) | +8 |
| frontend/src/routes/data/{export,settings,settings/ai}/+page.svelte | 수정 | 6줄 |
| frontend/src/routes/coach/[threadId]/+page.svelte | 수정 | 2줄 |
| scripts/check_frontend_links.py, scripts/check_docs.py | 신규 / 수정 | ~40 / +10 |
| tests/test_match_hooks.py, test_match_select_ratio.py, test_story_period.py, test_metric_change.py, test_activity_counts.py, test_metrics_trend_extremes.py, test_metric_def_floor.py | 신규 | 각 3~8 테스트 |

## 4. 단계·검증
1. **즉시 수정(위험 낮음)**: M-01 → D-01 → C-01. 검증: `test_story_period`(2026-W40, 2027-W01↔2026-W53, 2026-12 ↔ 2027-01, 잘못된 키 400), `GET /api/v1/library/story/2026-W40` 200; 링크 검사 스크립트가 수정 전 6건 실패·수정 후 0건; 375px에서 300자 무공백 전송 시 `scrollWidth == clientWidth`, 여러 줄 입력 보존.
2. **G1 SSOT**: `MetricDef.scale`·지표별 floor 추가·채움 → metric_change → M-04 extremes → activity_counts(T-01 의 신규 활동 집계가 재사용하므로 T-01 보다 먼저). 검증: TSB/REC/ramp_rate/skin_temp 픽스처로 pct=None+사유, 같은 base 값이 지표 floor 에 따라 `near_zero_base` 여부가 달라짐(지표별 floor 적용 확인), 부호가 API·목록·상세 일치; `gen_metric_dictionary`·`check_docs`·`check_data_consistency` 통과(scale·floor 누락 지표 0 — 비율 척도 여부와 무관하게 전 지표, HSR-8); floor 없는 가짜 MetricDef 를 레지스트리에 넣으면 `test_metric_def_floor`·정합성 검사가 실패; marathon_prediction 등 중립·예측 지표는 best/worst null·타일 숨김, CIRS worst=최댓값·"최저" 라벨; 개요 타일 전체·러닝 값이 activity_counts와 같고 러닝 값 = sync-state.
3. **T-01**: 먼저 아래 실데이터 확인으로 후보 ①②③ 중 어느 것인지 판정 → match_hooks 추출·CLI 호출·result_json 기록·같은 날 단일 후보 상한 무시 → 사본 DB에서 `rematch` 1회 → 스트립 재확인(10/8·10/9 매칭). 테스트: 매칭 예외 시 job은 completed이고 `result_json.match.error`가 채워짐, 조기 return + 신규 활동 1건 이상이면 매칭 실행·0건이면 `match.skipped` 기록, 기존 활동 갱신만 있는 동기화(신규 0)는 skip(HSR-9), 같은 활동이 garmin·strava 로 처음 함께 들어오면 `counts_json.new_activities == 1`·서로 다른 활동 2건이면 2(HSR-10, `test_match_hooks` 또는 `test_activity_counts`), CLI 동기화 후 매칭 실행, 같은 날 후보 1개(비율 2.5) 매칭·후보 2개면 1.6 초과 탈락.
   **실데이터 확인 필요**(사용자 머신, 읽기 전용; `sync_jobs`는 v36에서 running.db가 아닌 `sync_jobs.db`로 이동 — `src/utils/sync_jobs.py:129-130`):
   | 확인 | 쿼리(대상 DB) | 판정 |
   |---|---|---|
   | 마지막 동기화 | `SELECT id,service,status,source_path,trigger,started_at,finished_at,last_error,counts_json FROM sync_jobs ORDER BY created_at DESC LIMIT 10;` (sync_jobs.db) | finished_at 이 c9e4b23 반영 이전이거나 기록 없음 → ①(HSR-6 (b) 재검토), status≠completed → ②, completed인데 미매칭 → ③ |
   | 주간 매칭 상태 | `SELECT id,date,source,workout_type,distance_km,matched_activity_id,completed FROM planned_workouts WHERE date BETWEEN '2026-10-05' AND '2026-10-11' ORDER BY date,id;` (running.db) | 전부 NULL → T-01 패턴, 일부만 채워짐 → P-06 패턴 |
   | `_effective` 결함 해당 | 위 결과에서 같은 date에 source≠'planner' 미매칭 행과 planner 매칭 행이 공존하는지 | 공존하면 해당 |
   | 실제 활동 거리 | `SELECT * FROM v_canonical_activities WHERE <날짜열> BETWEEN '2026-10-05' AND '2026-10-11';` (컬럼명은 뷰 정의로 먼저 확인) | 계획 대비 비율 >1.6 이면 상한 탈락 확정 |
4. `pytest tests/`, `npm run check`, `scripts/check_docs.py`, `scripts/gen_metric_dictionary.py`. 각 신규 파일 300줄 이하.
- 호환성: API는 필드 추가 위주(`peak`·`change_pct`는 한 릴리스 유지). 매칭 규칙 변경(HSR-1)으로 다음 4주 재매칭 시 기존 미매칭 행이 매칭으로 바뀔 수 있다. 공유 함수 `match_week_activities`(HSR-1 변경 대상)는 유지된다. 호출자 사실(2026-10-11 grep): v2 동기화는 `sync_trigger_service`→`src/web/bg_sync.py:277-290`(4주) — `src/web/` 에 있으나 v2 공용 파일이며 T-01 ①로 매칭 블록을 view 밖 `src/training/match_hooks.py` 로 이관한다. `src/web/app.py:_auto_match_after_sync`(113, 이번·지난 주 2주)는 v1 라우트 `/trigger-sync`(558)·`/trigger-sync-stream`(638)에서만 호출되고 v2 프런트는 이 라우트를 부르지 않는다 → 변경 없음, 라우트 일몰 시 함께 소멸(V1-2). Calculator·metric_store·DB 스키마 변경 없음(SCHEMA_VERSION 유지). `MetricDef.scale`·floor는 코드 정의 필드라 DB 무관.

## 5. 결정
- HSR-1~10(연관 PLN-6·PLN-10): 결정 완료(표 참조, `decisions-table.md` 2026-10-11). 본문 §2 각 항목에 반영.

## 6. 범위 밖 메모
- M-01의 `delta_pct`가 이전 값 0일 때 0을 반환(“변화 없음”으로 오독 가능) — M-03 규칙 적용 후보.
- 목록(14일 창)과 상세(선택 기간) 변화의 창 길이 차이는 문구 문제로 별도 UX 검토.
- `week_compliance`·`matcher`가 직접 SQL로 `v_canonical_activities`를 조회(서비스 계층이라 ADR-009 대상 아님) — 정의 공유는 D-03 헬퍼로 후속 통합 가능.

## 7. 동기화 중 발견한 모호점
1. HSR-1 "같은 날 후보 1개"의 기준(계획 행 기준 활동 수 vs 활동 기준 계획 행 수, 외부 계획 행 포함 여부) 미정 — `match_select`/`matcher.py:51` 구조로 구현 시 확인.
2. HSR-4 표시 정의와 `non-running-activities.md` 종목 정책의 일치 여부 미확인.
3. 해소(HSR-9·HSR-10). 남은 확인: 중복 그룹화가 동기화 실행 안에서 끝나는지(차이 계산 시점) — 구현 시 코드 확인.
4. 해소(HSR-8, 단위·적용 범위). 남은 것: floor 필드명과 각 지표의 구체 값(구현 시 지표별 산정, 사전으로 검토).
5. 해소(5차 동기화, grep): `_auto_match_after_sync` 는 v1 라우트 전용 호출자라 match_hooks 이관 대상 아님(§4 호환성). v2 경로는 `bg_sync.py` 블록만 이관.
