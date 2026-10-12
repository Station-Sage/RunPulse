# 설계: 비러닝 활동 처리 (종목 판정 단일 출처 + 종목별 표시 계약)

- 대상 ID: T-05 (`GET /api/v1/today/narrative` 월 내러티브·highlights·evidence·weeks), A-01 (수영 상세 히어로 페이스), A-02 (상세 해석 줄 "러닝" 접두), A-03 (근력 상세 거리·페이스 블록)
- 상태: 설계 확정 — NRA-1~8 결정 반영(2026-10-11). 구현 가능
- 변경 이력: 2026-10-11 설계서 동기화(NRA-1~8 결정 반영, HSR-4 정합, "결정 필요" → "결정됨") · 2026-10-11 6차 동기화(V1-7: §5 에 `get_runner_state`·`rule_based_chips` 필요 여부 검토 절차 추가, §7·§9 갱신) · 2026-10-11 7차 동기화(V1S-4 (b)·V1-13: 검토 절차를 '지금 제거' 결정으로 교체, `suggestions.py` `_RUN_TYPES` 사본을 NRA-8 대상에서 제외, §5·§7·§9) · 2026-10-12 9차 동기화(HSR-12·ADR-1, V1S-4 점검: `sync_state_service.py:183` LIKE 제거·`activity_counts` 이관을 §2.5·§4·§7·§9에 반영, ADR 번호 ADR-051 확정. V1S-4 서술은 결정과 일치 — 변경 없음)
- 관련 ADR: ADR-009 (Calculator raw SQL 금지 — 이번 변경은 서비스 계층만, Calculator 무변경), ADR-032 (Story 통계 `story_stats` — 같은 집계 쿼리 공유 대상), ADR-020 계열 원칙(판정·표시 규칙은 서버 SSOT)
- 이월: 2026-09 리뷰 F-DATA-13(월간 이야기에 수영 합산)이 "반영"으로 표시됐으나 집계 쿼리는 그대로 남아 있음

## 1. 근본 원인

**RC-1. "러닝인가"를 판정하는 단일 출처가 없고, v2에서 새로 만든 기간 집계는 아예 필터가 없다.**
- 수집 단계는 `src/utils/activity_types.normalize_activity_type()`로 종목을 정규화(running/cycling/swimming/walking/strength)해 저장한다. 그러나 읽기 단계는 각자 러닝 집합을 하드코딩한다: `LIKE '%running%'`(archive·impact·data_health·metric_unlock·sync_state), `IN ('running','trail_running','treadmill',...)`(week_compliance·engine·context_runs·classifier·heat_forecast·race_result), `('running','run','virtualrun','treadmill','highintensityintervaltraining')`(matcher·suggestions) 등 최소 6종의 서로 다른 정의가 공존한다. 프론트 `activityList.ts`도 `includes('running')`로 따로 판정한다.
- 월 내러티브(`today_service.get_today_narrative` 209-217행), 주 요약(`week_digest.week_digest` 43-46행), Story 통계(`story_stats` 17-22행)는 같은 `COUNT/SUM/MAX(distance_m) FROM v_canonical_activities` 쿼리를 3번 복제했고 셋 다 종목 조건이 없다. 결과: 수영 0.5km가 "51.5km(8회)"에 합산되고(T-05), `longest_run_km`도 MAX(distance_m)라 긴 라이딩이 "최장 러닝"이 될 수 있다. 주간 스트립(week_compliance, 러닝만)과 주 요약(전체)이 다른 숫자를 낸다(31.1 vs 31.6).

**RC-2. 활동 상세 응답 계약이 "러닝"을 암묵 전제로 하고, 종목별 표시 규칙을 서버가 내려주지 않는다.**
- `core`는 소스 avg_speed에서 만든 `avg_pace_sec_km` 하나만 노출한다. 산출 근거(이동시간인지 총시간인지)는 계약에 없다. 수영은 Garmin avgSpeed가 이동시간 기준이라 22:22/km가 나오고, 화면은 같은 줄에 총시간 25:42를 보여 모순이 생긴다(A-01).
- `+page.svelte` 히어로는 `distance_m != null`이면 km 블록을, 항상 "평균 페이스 … /km" 칸을 그린다. 근력은 distance 0.00, 페이스 `—/km`가 남는다(A-03).
- `activity_summary_extras.build_verdict()`는 `head = wc["label"] or "러닝"`, `_fmt_pace`는 `/km` 고정이다. 비러닝은 workout 분류 태그가 없어 항상 "러닝" 접두가 붙는다(A-02).
- 반면 `activity_impact_service`는 `'running' not in activity_type`이면 None으로 비러닝을 제외한다. 같은 상세 응답 안에서도 종목 판정 방식이 섞여 있다.

## 2. 설계안 (A안 — 읽기 시점 종목 SSOT + 서버 표시 계약)

### 2.1 종목 판정 SSOT — `src/utils/activity_types.py` 확장
- `SPORT_LABELS`를 `activity_list_filters.py`에서 이 모듈로 옮긴다(기존 위치는 re-export).
- `sport_family(raw_type, source=None) -> str`: `normalize_activity_type`의 의미 있는 별칭. 결과는 5종 + `"other"`.
- 경계 종목(NRA-7): `race`·`treadmill` → `running`, `highintensityintervaltraining`(HIIT) → `other`(비러닝), 매핑되지 않는 raw 값 → `other`.
- `family_raw_types(family) -> tuple[str, ...]`: `_TYPE_MAP`·소스 맵에서 그 family로 가는 모든 raw 문자열(정규화 전 레거시 행 포함)을 정적으로 돌려준다. DB 조회 없음.
- `family_clause(family, col="activity_type") -> tuple[str, list]`: `"{col} IN (?,?,…)"`와 params. LIKE는 쓰지 않는다(`trail_running`은 잡지만 오탐·미탐 규칙이 암묵적).
- `activity_list_filters.sport_types()`(DB의 DISTINCT 기반)는 facet용으로 유지하고, 집계 경로만 정적 집합을 쓴다.
- 이관 범위(NRA-8): 이번 작업은 이 문서 대상 경로(내러티브·week_digest·story_stats·활동 상세·impact)만 SSOT 로 옮긴다. 나머지 RUN_TYPES 사본(training·metrics·archive·matcher 등 10여 곳)은 별도 BACKLOG 항목으로 다룬다.

### 2.2 기간 집계 공유 — `src/services/run_totals.py` (신규)
- `run_totals(conn, start, end) -> {"count", "distance_km", "longest_km"}`: `family_clause("running")`를 적용한 단일 쿼리. 내러티브·week_digest·story_stats 3곳이 같이 쓴다. `count`는 러닝 활동 건수(같은 날 여러 건은 각각 1회, NRA-2 현행 유지).
- `other_totals(conn, start, end) -> list[{"family","label","count","distance_km","duration_sec"}]`: 비러닝 내역. **월/주 내러티브에서 호출한다(NRA-1 (b)).**
- 내러티브 표시(NRA-1 (b)): highlights·칩의 km·회·최장은 러닝 수치만 쓰고, 비러닝은 별도 한 줄로 붙인다(예: "그 외 수영 1회 · 근력 2회", 0건이면 줄 생략). 응답에 `highlights.other`(`other_totals` 결과)를 추가하고 기존 키는 불변.
- `_narrative.build_evidence / build_narrative_prompt / rule_narrative`의 문구는 "러닝" 기준임을 명시하고, evidence·프롬프트에 비러닝 한 줄을 넣는다. 규칙 기반 문구도 같은 한 줄을 쓴다.
- 내러티브 AI 캐시 키에 계약 버전 접미사를 붙인다(`today_narrative` 캐시 키 `…:r2`). TTL 8h 안의 오염된 캐시 응답이 남지 않게 하는 조치이며, 기존 행은 삭제하지 않고 키만 바꾼다.

### 2.3 활동 상세 표시 계약 — `src/services/activity_display.py` (신규)
- `build_display(core) -> dict` (응답 최상위 `display`에 추가, 기존 키 불변):
  `{"family", "label", "show_distance": bool, "pace": {"value_sec", "unit": "/km"|"/100m", "basis": "moving"}|null, "speed_kmh": float|null, "times": {"moving_sec", "elapsed_sec"}, "alt_fields": ["duration","avg_hr","calories","sets"]}`
- 규칙 표(NRA-4):

| family | 거리 | 페이스/속도 | basis |
|---|---|---|---|
| running | 표시 | /km | 이동시간 |
| walking(걷기·하이킹) | 표시 | /km | 이동시간 |
| swimming | 표시 | /100m | 이동시간 |
| cycling | 표시 | km/h(`speed_kmh`), 페이스 없음 | 이동시간 |
| strength·other(HIIT 포함) | 숨김 | 없음 | — |

- 페이스·속도는 `distance_m`와 **이동시간**(`moving_time_sec`, 없으면 `duration_sec`로 대체하고 basis 를 `elapsed`로 표시)으로 재계산한다(NRA-3). 소스 `avg_pace_sec_km`를 그대로 단위 변환하지 않는다.
- 시간 병기(NRA-3): 페이스를 보이는 종목은 히어로에 **이동시간과 총시간을 함께** 보여 페이스 근거와 화면 시간이 모순되지 않게 한다(`times`). 두 값이 같으면 하나만 보인다.
- 대체 칸(NRA-5): 거리·페이스 칸이 빠지는 종목은 **활동 시간·평균 심박·칼로리**로 채운다. 데이터가 있는 값만 넣고, 세트 수는 있을 때만 넣는다. `alt_fields`는 값이 있는 항목만 순서대로 담는다.
- `build_verdict(core, wc, splits, environment, display)`: `head = wc["label"] or display["label"]`. 접두는 종목 라벨 그대로("수영", "근력", "걷기/하이킹")(NRA-6). 비러닝은 가용한 지표(시간·페이스/속도·심박 등 값 있는 것)만 설명한다. 페이스 변동·날씨 보정(km당)은 `family == "running"`일 때만 붙인다.
- `activity_impact_service`의 `'running' not in …` 판정을 `sport_family(...) == "running"`으로 바꾼다(출처 통일). `treadmill`·`race` 는 이제 러닝으로 판정된다.

### 2.4 프론트(v2)
- `+page.svelte` 히어로는 `display.show_distance`, `display.pace.unit`, `display.speed_kmh`, `display.times`, `display.alt_fields`만 읽는다. `/km` 리터럴과 `distance_m != null` 판정을 없앤다. 서버가 `display`를 주지 않으면(구 응답) 지금과 같이 동작한다.
- 표시 포맷은 순수 함수 `frontend/src/lib/activityDisplay.ts`로 분리하고 테스트한다(단위·시간 병기·대체 칸 선택).
- Today 월 내러티브 칩 아래에 비러닝 한 줄(`highlights.other`)을 그린다.

### 2.5 개요 활동 수와의 정합 (HSR-4)
- HSR-4 결정(개요 "활동"은 전체 canonical·러닝 둘 다 표시, 라벨로 구분)은 NRA-1 (b)(러닝 수치 + 비러닝 한 줄)와 같은 방향이다. 개요의 "러닝" 수는 `family_clause("running")` 기준으로 세어 내러티브·주 요약과 같은 정의를 쓴다. 전체 수는 종목 조건 없는 canonical 건수다.
- **러닝 수 단일 정의(HSR-12 (a))**: 러닝 수는 `family_clause("running")`로 통일하고 `src/services/activity_counts.py`(`bundles/high-severity-remaining.md` D-03 소관, 신규) 한 곳에서 센다. 소비처는 `data_service` 개요와 `sync_state_service.activity_count` — `sync_state_service.py:183`의 `LIKE '%running%'`는 제거되고 `activity_counts`로 이관된다(NRA-8 별도 BACKLOG의 예외로 이번 작업 포함). 결과: `treadmill`(LIKE가 놓치던 값)·`race`가 sync-state 러닝 수에 포함되어 값이 바뀔 수 있다(의도된 수정). `activity_counts`는 이 설계의 `family_clause`에 의존하므로 §4 1단계(SSOT 유틸)가 먼저다.

## 3. 변경 파일 표

| 구분 | 파일 | 내용 | 예상 줄 |
|---|---|---|---|
| 수정 | `src/utils/activity_types.py` | `SPORT_LABELS` 이동, `sport_family`(경계 종목 규칙)·`family_raw_types`·`family_clause` | 85→~130 |
| 수정 | `src/services/activity_list_filters.py` | `SPORT_LABELS` re-export | ±2 |
| 신규 | `src/services/run_totals.py` | `run_totals`, `other_totals` | ~60 |
| 신규 | `src/services/today_narrative.py` | `get_today_narrative` 이동(today_service가 이미 320줄로 규칙 초과) + `run_totals`·`other_totals` 사용 | ~140 |
| 수정 | `src/services/today_service.py` | 내러티브 제거, 하위호환 re-export | 320→~195 |
| 수정 | `src/services/_narrative.py` | evidence·prompt·rule 문구 러닝 명시, 비러닝 한 줄, 캐시 키 접미사 | 209→~230 |
| 수정 | `src/services/week_digest.py` | 집계를 `run_totals`로 교체 | ±0 |
| 수정 | `src/services/story_stats.py` | 집계를 `run_totals`로 교체 | −5 |
| 신규 | `src/services/activity_display.py` | `build_display` 종목별 규칙·시간 병기·대체 칸 | ~90 |
| 수정 | `src/services/activity_summary_extras.py` | `build_verdict`에 display 인자, 종목 라벨 접두·단위·러닝 전용 칩 분기 | 132→~150 |
| 수정 | `src/services/activity_detail_service.py` | `display` 조립·응답 추가 | 225→~229 |
| 수정 | `src/services/activity_impact_service.py` | `sport_family` 사용 | ±2 |
| 수정 | `frontend/src/lib/types/index.ts` | `ActivityDisplay` 타입, 상세·내러티브 응답 확장 | +16 |
| 신규 | `frontend/src/lib/activityDisplay.ts` | 히어로 칸 포맷 순수 함수 | ~55 |
| 수정 | `frontend/src/routes/library/[id]/+page.svelte` | 히어로가 `display`를 사용 | 204→~214 |
| 수정 | Today 내러티브 컴포넌트(v2) | 비러닝 한 줄 표시 | +6 |
| 테스트 | `tests/test_activity_types.py`(+6: 경계 종목 race·treadmill·HIIT·미매핑 포함), `tests/test_run_totals.py`(신규 ~7: 건수·other_totals), `tests/test_week_digest.py`(+1 수영 제외), `tests/test_narrative_cache.py`(+1 키), `tests/test_today_narrative.py`(신규 ~4: 수영 제외·최장 러닝·비러닝 줄), `tests/test_activity_display.py`(신규 ~8: 러닝/수영/근력/사이클 km/h/걷기/HIIT/unknown/시간 병기), `tests/test_activity_summary_extras.py`(+3 verdict), `frontend/tests/activityDisplay.test.mjs`(신규 ~6) | ~36 |

스키마·SCHEMA_VERSION·Calculator·metric_store 변경 없음. 신규 ADR **ADR-051**(ADR-1 (a) 번호 배정: "종목 판정은 `activity_types` 단일 출처, 기간 집계는 `run_totals`, 러닝 수는 `activity_counts`(HSR-12), 경계 종목 규칙") 기록 필요. `activity_counts.py`·`sync_state_service.py` 수정은 HSR 번들 변경 파일 표 소관이라 이 표에 중복 기재하지 않는다.

## 4. 적용 순서와 검증

1. **SSOT 유틸** (`activity_types.py`): `family_raw_types("running")`가 `_TYPE_MAP`의 모든 러닝 별칭과 `race`·`treadmill`을 포함하고, HIIT·`swimming`·`strength`가 running 집합에 없는지 단위 테스트. 로컬 사본 DB(운영 DB 아님)에서 `SELECT activity_type, COUNT(*) … GROUP BY 1`로 매핑되지 않는 값이 `other`로 가는지 확인한다.
2. **run_totals + 3곳 교체**: 픽스처(러닝 7건 51.0km + 수영 0.5km)로 내러티브 highlights `51.0/7`, 비러닝 줄 "수영 1회", week_digest·story_stats 같은 값을 assert. 내러티브 함수 이동 후 `routes_today`·`narrative_warm` import 경로 테스트 통과.
3. **브라우저**: `/v2/today` 월 내러티브 칩·비러닝 줄과 주간 스트립·주 요약의 km가 일치하는지, `/v2/library/story/<월>`과 숫자가 같은지 확인한다.
4. **display + verdict**: 17425(수영) `/100m`·이동시간 기준 페이스와 히어로의 이동·총시간 병기가 서로 맞는지, 598(근력) 거리·페이스 칸 대신 시간·심박·칼로리가 나오는지, 603(걷기) 접두가 "걷기/하이킹"이고 `/km`인지, 사이클이 km/h 인지 확인. 러닝 활동은 기존 verdict 문자열과 바이트 단위로 같아야 한다(회귀 테스트).
5. `python3 -m pytest tests/`, 프론트 테스트, `python3 scripts/check_docs.py`, files_index 재생성, ADR-051 기록.

순서 의존(HSR-12): 1단계 `family_clause` 도입 뒤에 HSR 번들의 `activity_counts`(D-03)가 이를 소비한다. 검증은 사본 DB에서 `sync_state` 러닝 수 == `activity_counts.canonical_running` == 개요 러닝 수(같은 정의).

## 5. 호환성

- `highlights`·`evidence` 값의 의미가 "전체 활동"에서 "러닝"으로 바뀐다(키 불변, `highlights.other` 추가). 소비처는 v2 Today, `narrative_warm`, AI 캐시. 값 변화는 의도된 수정이다.
- `verdict.text`는 Coach 컨텍스트(`src/ai/ai_context.py` → `get_activity_detail`)에도 들어간다. 비러닝 문구가 바뀌면 Coach 근거 문장도 바뀐다.
- `story_stats` 숫자가 바뀌면 ADR-032 Story 월/주 카드 값이 바뀐다(같은 결함 수정).
- `activity_impact_service`는 `LIKE '%running%'` 기준에서 SSOT 기준으로 바뀌어 `treadmill`·`race` 활동에도 영향 블록이 생길 수 있다.
- `today_service.get_today_narrative`는 re-export로 남겨 import 호환을 유지한다.
- **`suggestions.get_runner_state`·`rule_based_chips`(V1S-4 (b) 결정 2026-10-11: 지금 제거)**: v2 대체(`coach_rule_handlers.suggestion_chips`·`answerable_chips`) 완료로 보고 두 함수를 제거한다. 제거 작업은 `bundles/v1-sunset-prep.md` §2.4·§4 5단계 소관이며 이 설계는 두 함수를 수정하지 않는다. 두 함수 전용 `RunnerState`·`suggestions.py:39` `_RUN_TYPES` 사본도 함께 사라지므로 NRA-8 이관 대상에서 빠진다. `CHIP_REGISTRY`는 유지. v1 `/ai-coach` 칩 소멸은 감수(V1-13).

## 6. 대안 비교 (기록용 — A안 채택)

| | A안(채택) 읽기 시점 SSOT + `display` 계약 | B안 수집 시점 `sport_family` 컬럼 + 종목별 페이스 저장 |
|---|---|---|
| 방법 | 유틸 함수·서비스 계층만 변경, 응답에 추가 필드 | `activity_summaries`에 컬럼 추가·뷰 재생성·백필, `avg_pace_sec_100m` 등 저장 |
| 장점 | 스키마·재동기화 불필요, 단계별 배포 가능, 러닝 경로 회귀 범위 작음 | SQL이 단순(`WHERE sport_family='running'`), 외부 소비처(MCP·export)도 같은 값 |
| 단점 | 집계 SQL마다 `family_clause`를 호출해야 함(규칙 누락 위험은 grep 검사로 보완) | SCHEMA_VERSION 상승, 백필·재정규화 필요. 종목별 컬럼은 "새 스포츠는 컬럼이 아니라 metric_store" 원칙에 어긋남 |

B안의 장점(단일 WHERE)은 A안의 `family_clause`로 대부분 얻을 수 있다. 후속으로 `check_docs.py`에 "`LIKE '%running%'`·하드코딩 RUN_TYPES 금지" 검사를 추가할지는 NRA-8 별도 BACKLOG 항목에서 함께 검토한다.

## 7. 결정됨 (2026-10-11)

- **NRA-1 월/주 내러티브의 비러닝 처리**: (b) 러닝 수치 + 비러닝 별도 한 줄. 근거: 러닝 앱 목적·주간 스트립과 일치하면서 비러닝 훈련이 사라지지 않음(2.2).
- **NRA-2 "회" 단위**: 러닝 활동 건수(현행 유지)(2.2).
- **NRA-3 수영 페이스 basis**: 이동시간 기준 + 히어로에 이동·총시간 병기. 근거: Garmin·Strava 관례, 병기로 화면 모순 해소(2.3).
- **NRA-4 단위**: 사이클 km/h, 걷기·하이킹 /km, 수영 /100m(2.3 표).
- **NRA-5 대체 칸**: 거리·페이스가 빠지면 활동 시간·평균 심박·칼로리(데이터 있는 값만, 세트 수는 있을 때만)(2.3).
- **NRA-6 해석 줄 접두**: 종목 라벨 그대로('수영','근력','걷기/하이킹') + 가용한 지표만 설명(2.3).
- **NRA-7 경계 종목**: race·treadmill=러닝, HIIT=기타(비러닝), 미매핑 raw=other. 계획 매칭에서 HIIT 가 빠지는 영향은 구현 시 확인(2.1, 9절).
- **NRA-8 범위**: 나머지 RUN_TYPES 사본 이관은 이번 작업에서 제외, 별도 BACKLOG(2.1). 예외: `sync_state_service.py:183` LIKE는 HSR-12 (a)로 이번에 `activity_counts`로 이관(§2.5).
- **`src/ai/` RUN_TYPES 사본 2곳(코드 확인 2026-10-11)**:
  - `ai_context_legacy.py:16` `_RUN_TYPES`(`build_context`가 사용): AI 공용 경로(`ai_context.py:14` 재노출 → `briefing.build_chip_prompt` → `chat_engine` → `coach_service`, v2 `/api/v1/coach`). v1 전용이 아니므로 NRA-8 별도 BACKLOG 대상 사본에 포함된다.
  - `suggestions.py:39` `_RUN_TYPES`(`get_runner_state` 전용): V1S-4 (b)로 두 함수와 함께 제거된다(§5) — NRA-8 대상 아님.

## 8. 범위 밖 메모

- A-31 라이브러리 홈 최근 활동 수영 `/km` 표시: 같은 원인이며 `activityDisplay.ts`를 재사용할 수 있다(이번 ID 아님).
- CTL·부하에 비러닝 활동 부하가 포함되는지는 별도 메트릭 정책 문제다(NRA-8 BACKLOG 와 함께 검토).
- `today_service.py` 320줄 규칙 초과는 이번 분리로 해소되지만 원래 이 패턴의 범위는 아니다.

## 9. 동기화 중 발견한 충돌/확인 필요

- NRA-7(HIIT=비러닝)과 현재 matcher 의 러닝 집합(HIIT 포함)이 다르다(suggestions 사본은 V1S-4 로 제거). NRA-8 로 matcher 이관은 이번 범위 밖이라 이번 작업 후에도 matcher 는 HIIT 를 러닝으로 매칭한다. 이관 시 계획 매칭에서 HIIT 가 빠지는 영향을 확인해야 한다.
- NRA-8 의 "별도 BACKLOG" 항목은 이 동기화에서 `BACKLOG.md` 에 등록하지 않았다(수정 범위 밖). 등록이 필요하다.
- (해소, HSR-12) 러닝 수 정의 이원화 — `family_clause`로 통일, `activity_counts` 헬퍼로 일원화하고 `sync_state_service.py:183` LIKE를 제거해 이관 대상에 포함(§2.5·§7 NRA-8 예외). HSR-4 의 러닝 488건(LIKE 기준)은 이관 후 `treadmill`·`race` 포함으로 달라질 수 있다.
- `normalize_activity_type` 의 현재 HIIT·race·treadmill 매핑 값은 이 동기화에서 코드로 확인하지 않았다. 수집 단계 매핑이 NRA-7 과 다르면 정규화 저장값과 읽기 판정이 어긋나므로 구현 1단계에서 확인이 필요하다.
- (5차 동기화, 사실 확인) 4차 이전 §5의 "v1 쪽 RUN_TYPES 사본(`ai_context_legacy.py`·`suggestions.py`)은 v1과 함께 제거"는 코드와 맞지 않았다 — 두 파일 모두 v2 Coach 경로가 쓰는 공유 파일이다(§5). V1-1 정정(일몰 = UI·라우트 일몰)에 따라 두 사본은 NRA-8 별도 BACKLOG 대상으로 남는다.
- (6차 열린 항목 → 7차 동기화, V1S-4 (b)로 해소) `suggestions.get_runner_state`·`rule_based_chips`는 지금 제거한다(수행은 `bundles/v1-sunset-prep.md` §4 5단계). NRA-8 BACKLOG 등록 시 `suggestions.py` 사본은 목록에서 뺀다.
- (5차 동기화 사실 정정 보충) 위 항목의 "두 사본 모두 NRA-8 대상"은 7차부터 `ai_context_legacy.py` 1곳만 해당한다(§7).
