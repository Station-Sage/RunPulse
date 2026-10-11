# 설계: 상 심각도 잔여 7건 (T-01, M-01, M-03, M-04, D-01, D-03, C-01)

- 상태: 설계 초안 (구현 전). 범위 제외: P-01~P-08(훈련 계획 묶음), T-03/M-02(`data-freshness.md`), T-05/A-01(`non-running-activities.md`)
- 관련 ADR: ADR-009(Calculator raw SQL 금지 — 본 설계는 Calculator 무변경), ADR-020(판정·등급은 서버 SSOT)
- 묶음: **G1 "같은 수치를 여러 곳에서 각자 계산"**(M-03, M-04, D-03) / **G2 "v1 경로에만 걸린 부작용"**(T-01) / 단독: M-01, D-01, C-01

## 1. 근본 원인
- **T-01** (G2) `week_compliance.outcome_label`은 `planned_workouts.matched_activity_id`가 없으면 과거일을 `missed`로 판정한다. 그런데 이 값을 채우는 `matcher.match_week_activities`의 자동 호출은 v1 `src/web/app.py:_auto_match_after_sync`(v1 동기화 라우트 558·638행)뿐이고, v2 `POST /api/v1/data/sync`(`sync_trigger_service`/`sync_range_service`)와 `src/sync.py` CLI에는 없다(grep 확인). 추가로 `match_select.pick_activity`가 거리 비율 `[0.5, 1.6]` 밖이면 매칭을 거부한다 — 계획 3.2km에 실제 6.0km(1.88)는 탈락. 반면 "31.1/47.9km 완료"는 `v_canonical_activities`를 직접 합산하므로 두 수치가 모순된다. (사본 DB에서 두 원인 중 어느 쪽이 지배적인지 재확인 필요)
- **M-01** `story_service.py:153~192` 주 분기가 월 분기 지역변수 `prev_year`를 참조(→ UnboundLocalError 500). 같은 분기가 `prev_date.year`(달력 연도)와 `isocalendar()[1]`(ISO 주)를 섞어, 연말(예: 2027-01-01은 2026-W53)에 잘못된 범위·링크를 만든다. 기간 파싱/이전/다음 계산이 함수 안에 흩어져 있는 것이 원인.
- **M-03** (G1) 변화율 계산이 3곳에 따로 있다: 서버 `metrics_browser_service._change`(목록, 14일 창)·`get_metric_trend`의 `change_pct = (cur-first)/first`(부호 있는 분모), 프론트 `trendChart.periodChange`(`/abs(first)`)·`changeLabel`(30일 창). 분모 부호 처리 차이가 API↔UI 부호 반전(ramp_rate, skin_temp 등)을, 0 근처·부호 교차 기준(TSB, REC)이 수백~수천 %를 만든다. 근본적으로 "이 지표에 %가 의미 있는가(비율 척도인가)"라는 메타데이터가 없다.
- **M-04** (G1) `get_metric_trend` 219행 `peak = max(value)`로 방향성을 무시. 같은 함수가 이미 `HIGHER_IS_BETTER` 기반 `best/worst`를 계산하지만 상세 페이지는 `trend.peak`만 렌더한다. `higher_is_better=None`(예측·중립)은 "피크" 개념 자체가 없다.
- **D-01** `frontend/src/routes/data/{export,settings,settings/ai}/+page.svelte`에 `{base}` 없는 절대 경로 6건. 재발 방지 장치(정적 검사)가 없다.
- **D-03** (G1) 개요 타일은 `data_service.py:66`의 소스별 `activity_summaries` 원시 행 합(중복 포함 1,427), sync-state는 `v_canonical_activities` 중 running만(488), 중복 그룹 전체는 약 626. "활동 수" 정의가 서비스마다 다르다.
- **C-01** `coach/[threadId]/+page.svelte:220` 사용자 말풍선에 `whitespace-pre-wrap`·`overflow-wrap:anywhere`·`min-w-0`이 없어 무공백 문자열이 flex 컨테이너를 밀어내고 입력 줄바꿈이 합쳐진다.

## 2. 설계안
- **T-01 (추천 A)** 매칭을 동기화 파이프라인의 공용 후처리로 이동: `src/training/match_hooks.py`(신규) `after_sync(conn, date_from, date_to) -> int` — 동기화된 날짜 범위가 걸친 모든 주(최소 이번·지난 주)에 `match_week_activities` 실행, 실패는 로그 후 계속(코딩 규칙). 호출 지점: `sync_trigger_service`·`sync_range_service` 작업 완료, `src/sync.py` CLI, v1 `app.py`(기존 `_auto_match_after_sync`를 이 함수 위임으로 축소 → v1 제거 시 영향 없음). 기존 DB 보정은 `rematch.py` 1회 실행 경로 재사용. 거리 비율 상한은 "결정 필요 1".
  - 대안 B: `week_compliance`가 읽기 시점에 미매칭 계획을 즉석 매칭(비저장). 저장 상태(session_outcomes, 코치 근거)와 화면이 갈라져 비추천.
- **M-01** `src/services/story_period.py`(신규, ~60줄) 값 객체 `Period(kind, key, start, end)` + `parse(key)`, `prev()`, `next()`. 주는 `date.fromisocalendar`/`isocalendar().year`만 사용(달력 연도 혼용 금지), 잘못된 키는 `ValueError` → 라우트 400. `story_service`는 `Period`만 소비(분기 제거).
- **M-03 (추천 A)** 서버 SSOT `src/services/metric_change.py`(신규, ~70줄) `compute_change(points, slug, window) -> {abs, pct|None, pct_suppressed: reason|None, window_days, direction: better|worse|neutral|None}`. 규칙: ① 분모는 `abs(base)` 단일 정의, ② `pct`는 지표가 비율 척도이고 `abs(base) >= floor`일 때만, 아니면 `pct=None`+사유(`interval_scale`/`near_zero_base`), ③ direction은 `HIGHER_IS_BETTER`로 서버가 판정. `_change`와 `get_metric_trend`가 이 함수를 호출, 프론트 `periodChange`/`changeLabel`의 % 계산 제거(렌더만). 척도 메타는 `metric_display.py`에 `PCT_MEANINGFUL`(또는 `MetricDef.scale`) 추가 — 위치는 결정 필요 2.
  - 대안 B: 프론트에서 임계값으로 숨김. ADR-020 위반·3곳 중복 유지로 비추천.
- **M-04** `get_metric_trend` 응답에 `best/worst`(이미 계산됨)와 `extreme_kind: "best"|"range"`를 노출하고 `peak`는 deprecate(한 릴리스 유지 후 제거). `higher_is_better=None`이면 best/worst 대신 `range: {min, max}`. 프론트 타일은 `extreme_kind`에 따라 렌더. 라벨 문구는 결정 필요 3.
- **D-01** 6건 `{base}` 적용(`$app/paths`) + `scripts/check_frontend_links.py`(신규, ~40줄): `frontend/src/**/*.svelte`에서 `href="/`·`goto('/`로 시작하는 리터럴을 실패 처리, `check_docs.py`에 검사 추가(16번째) 또는 pre-commit 연결.
- **D-03** `src/services/activity_counts.py`(신규, ~40줄) `activity_counts(conn) -> {canonical_total, canonical_running, raw_by_source}` 단일 정의. `data_service` 개요와 `sync_state_service.activity_count`가 이를 소비. 타일에 어떤 값을 쓸지는 결정 필요 4. 소스별 행 수는 "소스별 수신"으로 별도 표기 유지.
- **C-01** 사용자 말풍선 클래스에 `whitespace-pre-wrap [overflow-wrap:anywhere]` + 부모 flex 자식 `min-w-0`. 어시스턴트 말풍선·답변 근거 카드에도 같은 유틸 클래스 적용 여부 동시 점검.

## 3. 변경 파일 표
| 파일 | 구분 | 예상 줄 |
|---|---|---|
| src/training/match_hooks.py | 신규 | ~50 |
| src/services/sync_trigger_service.py, sync_range_service.py, src/sync.py, src/web/app.py | 수정 | 각 +3~-15 |
| src/services/story_period.py / story_service.py | 신규 / 수정 | ~60 / -25 |
| src/services/metric_change.py / metric_display.py | 신규 / 수정 | ~70 / +15 |
| src/services/metrics_browser_service.py | 수정 | -20 +10 |
| src/services/activity_counts.py / data_service.py / sync_state_service.py | 신규 / 수정 | ~40 / ±10 |
| frontend/src/lib/trendChart.ts, metricMeaning.ts, routes/library/metrics/{+page,[slug]/+page}.svelte | 수정 | -30 +20 |
| frontend/src/routes/data/{export,settings,settings/ai}/+page.svelte | 수정 | 6줄 |
| frontend/src/routes/coach/[threadId]/+page.svelte | 수정 | 2줄 |
| scripts/check_frontend_links.py, scripts/check_docs.py | 신규 / 수정 | ~40 / +10 |
| tests/test_match_hooks.py, test_story_period.py, test_metric_change.py, test_activity_counts.py, test_metrics_trend_extremes.py | 신규 | 각 3~8 테스트 |

## 4. 단계·검증
1. **즉시 수정(위험 낮음)**: M-01 → D-01 → C-01. 검증: `test_story_period`(2026-W40, 2027-W01↔2026-W53, 2026-12 ↔ 2027-01, 잘못된 키 400), `GET /api/v1/library/story/2026-W40` 200; 링크 검사 스크립트가 수정 전 6건 실패·수정 후 0건; 375px에서 300자 무공백 전송 시 `scrollWidth == clientWidth`, 여러 줄 입력 보존.
2. **G1 SSOT**: metric_change → M-04 extremes → activity_counts. 검증: TSB/REC/ramp_rate/skin_temp 픽스처로 pct=None+사유, 부호가 API·목록·상세 일치; marathon_prediction best=최소 시간, CIRS worst=최댓값, 중립 지표는 range; 개요·sync-state 수치 동일 정의.
3. **T-01**: match_hooks + 호출 지점 → 사본 DB에서 `rematch` 1회 → `/today` 스트립이 done/partial로 바뀌고 "km 완료"와 정합. 테스트: v2 동기화 완료 콜백이 매칭을 호출, 매칭 예외가 동기화 결과를 실패로 바꾸지 않음.
4. `pytest tests/`, `npm run check`, `scripts/check_docs.py`. 각 신규 파일 300줄 이하.
- 호환성: API는 필드 추가 위주(`peak`·`change_pct`는 한 릴리스 유지). v1 `app.py`는 위임 1줄만 남겨 v1 제거 시 함께 삭제. Calculator·metric_store·스키마 변경 없음(SCHEMA_VERSION 유지).

## 5. 결정 필요 (4건)
1. **T-01 거리 비율 상한** — (a) 1.6 유지: 다른 세션 오매칭 방지, 대신 이번 사례는 계속 missed·"계획 외 러닝" 처리 (b) 상한 제거/완화(예: 3.0)하고 초과분은 `overperformed`로 라벨: 이행률이 실제와 맞지만 다른 날 계획 세션과 섞일 위험 (c) 같은 날 후보가 1개면 비율 무시: 절충, 규칙 복잡도 증가.
2. **M-03 비율 척도 메타 위치** — (a) `metric_display.py` 상수(빠름, 레지스트리와 분리) (b) `MetricDef.scale` 필드(SSOT, `gen_metric_dictionary`·check_docs 동반 수정). floor 값(지표별 vs 공통)도 함께.
3. **M-04 타일 라벨** — "최고/최저"(방향 반영) vs "최댓값/최솟값"(중립 표기) vs 중립 지표는 타일 숨김.
4. **D-03 개요 "활동" 정의** — (a) canonical 전체(~626, 비러닝 포함) (b) canonical 러닝(488, sync-state와 동일) (c) 둘 다 표시. non-running-activities.md의 종목 정책과 맞춰야 함.

## 6. 범위 밖 메모
- M-01의 `delta_pct`가 이전 값 0일 때 0을 반환(“변화 없음”으로 오독 가능) — M-03 규칙 적용 후보.
- 목록(14일 창)과 상세(선택 기간) 변화의 창 길이 차이는 문구 문제로 별도 UX 검토.
- `week_compliance`·`matcher`가 직접 SQL로 `v_canonical_activities`를 조회(서비스 계층이라 ADR-009 대상 아님) — 정의 공유는 D-03 헬퍼로 후속 통합 가능.
