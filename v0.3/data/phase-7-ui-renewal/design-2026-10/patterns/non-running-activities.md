# 설계: 비러닝 활동 처리 (종목 판정 단일 출처 + 종목별 표시 계약)

- 대상 ID: T-05 (`GET /api/v1/today/narrative` 월 내러티브·highlights·evidence·weeks), A-01 (수영 상세 히어로 페이스), A-02 (상세 해석 줄 "러닝" 접두), A-03 (근력 상세 거리·페이스 블록)
- 상태: 설계 초안 (구현 전, 사용자 결정 필요 항목 있음)
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

## 2. 설계안 (추천: A안 — 읽기 시점 종목 SSOT + 서버 표시 계약)

### 2.1 종목 판정 SSOT — `src/utils/activity_types.py` 확장
- `SPORT_LABELS`를 `activity_list_filters.py`에서 이 모듈로 옮긴다(기존 위치는 re-export).
- `sport_family(raw_type, source=None) -> str`: `normalize_activity_type`의 의미 있는 별칭. 결과는 5종 + `"other"`.
- `family_raw_types(family) -> tuple[str, ...]`: `_TYPE_MAP`·소스 맵에서 그 family로 가는 모든 raw 문자열(정규화 전 레거시 행 포함)을 정적으로 돌려준다. DB 조회 없음.
- `family_clause(family, col="activity_type") -> tuple[str, list]`: `"{col} IN (?,?,…)"`와 params. LIKE는 쓰지 않는다(`trail_running`은 잡지만 오탐·미탐 규칙이 암묵적).
- `activity_list_filters.sport_types()`(DB의 DISTINCT 기반)는 facet용으로 유지하고, 집계 경로만 정적 집합을 쓴다.

### 2.2 기간 집계 공유 — `src/services/run_totals.py` (신규)
- `run_totals(conn, start, end) -> {"count", "distance_km", "longest_km"}`: `family_clause("running")`를 적용한 단일 쿼리. 내러티브·week_digest·story_stats 3곳이 같이 쓴다.
- `other_totals(conn, start, end) -> list[{"family","label","count","distance_km","duration_sec"}]`: 비러닝 내역. **노출 여부는 결정 필요(D1)**이므로 함수만 두고 호출 여부는 결정 뒤에 정한다.
- `_narrative.build_evidence / build_narrative_prompt / rule_narrative`의 문구는 "러닝" 기준이라는 것을 명시하도록 바꾼다. 실제 문구는 D1·D6을 따른다. 프롬프트에 비러닝 줄을 넣을지도 D1을 따른다.
- 내러티브 AI 캐시 키에 계약 버전 접미사를 붙인다(`today_narrative` 캐시 키 `…:r2`). TTL 8h 안의 오염된 캐시 응답이 남지 않게 하는 조치이며, 기존 행은 삭제하지 않고 키만 바꾼다.

### 2.3 활동 상세 표시 계약 — `src/services/activity_display.py` (신규)
- `build_display(core) -> dict` (응답 최상위 `display`에 추가, 기존 키 불변):
  `{"family", "label", "show_distance": bool, "pace": {"value_sec", "unit": "/km"|"/100m"|null, "basis": "moving"|"elapsed"}|null, "speed_kmh": float|null}`
- 규칙 표(값 자체는 결정 필요 D3·D4·D5): running/walking → /km, swimming → /100m, cycling → km/h 또는 /km, strength·other → 거리·페이스 없음.
- 페이스는 `distance_m`와 basis에 맞는 시간(`moving_time_sec` 또는 `duration_sec`)으로 재계산한다. 소스 `avg_pace_sec_km`를 그대로 단위 변환하지 않는다. 근거가 계약에 드러나야 화면의 시간과 모순이 없다.
- `build_verdict(core, wc, splits, environment, display)`: `head = wc["label"] or display["label"]`, 페이스 문자열은 `display.pace`로 포맷하고, 페이스 변동·날씨 보정(km당)은 `family == "running"`일 때만 붙인다.
- `activity_impact_service`의 `'running' not in …` 판정을 `sport_family(...) == "running"`으로 바꾼다(동작 동일, 출처 통일).

### 2.4 프론트(v2)
- `+page.svelte` 히어로는 `display.show_distance`, `display.pace.unit`, `display.speed_kmh`만 읽는다. `/km` 리터럴과 `distance_m != null` 판정을 없앤다. 서버가 `display`를 주지 않으면(구 응답) 지금과 같이 동작한다.
- 표시 포맷은 순수 함수 `frontend/src/lib/activityDisplay.ts`로 분리하고 테스트한다. 숨겨진 칸을 무엇으로 채울지는 D5를 따른다.

## 3. 변경 파일 표

| 구분 | 파일 | 내용 | 예상 줄 |
|---|---|---|---|
| 수정 | `src/utils/activity_types.py` | `SPORT_LABELS` 이동, `sport_family`·`family_raw_types`·`family_clause` | 85→~125 |
| 수정 | `src/services/activity_list_filters.py` | `SPORT_LABELS` re-export | ±2 |
| 신규 | `src/services/run_totals.py` | `run_totals`, `other_totals` | ~60 |
| 신규 | `src/services/today_narrative.py` | `get_today_narrative` 이동(today_service가 이미 320줄로 규칙 초과) + `run_totals` 사용 | ~130 |
| 수정 | `src/services/today_service.py` | 내러티브 제거, 하위호환 re-export | 320→~195 |
| 수정 | `src/services/_narrative.py` | evidence·prompt·rule 문구 러닝 명시, (D1에 따라) 비러닝 줄, 캐시 키 접미사 | 209→~225 |
| 수정 | `src/services/week_digest.py` | 집계를 `run_totals`로 교체 | ±0 |
| 수정 | `src/services/story_stats.py` | 집계를 `run_totals`로 교체 | −5 |
| 신규 | `src/services/activity_display.py` | `build_display` 종목별 규칙 | ~70 |
| 수정 | `src/services/activity_summary_extras.py` | `build_verdict`에 display 인자, 접두·단위·러닝 전용 칩 분기 | 132→~145 |
| 수정 | `src/services/activity_detail_service.py` | `display` 조립·응답 추가 | 225→~229 |
| 수정 | `src/services/activity_impact_service.py` | `sport_family` 사용 | ±2 |
| 수정 | `frontend/src/lib/types/index.ts` | `ActivityDisplay` 타입, 상세 응답 확장 | +12 |
| 신규 | `frontend/src/lib/activityDisplay.ts` | 히어로 칸 포맷 순수 함수 | ~40 |
| 수정 | `frontend/src/routes/library/[id]/+page.svelte` | 히어로가 `display`를 사용 | 204→~210 |
| 테스트 | `tests/test_activity_types.py`(+4), `tests/test_run_totals.py`(신규 ~6), `tests/test_week_digest.py`(+1 수영 제외), `tests/test_narrative_cache.py`(+1 키), `tests/test_today_narrative.py`(신규 ~3: 수영 제외·최장 러닝), `tests/test_activity_display.py`(신규 ~6: 러닝/수영/근력/사이클/걷기/unknown), `tests/test_activity_summary_extras.py`(+3 verdict), `frontend/tests/activityDisplay.test.mjs`(신규 ~5) | ~29 |

스키마·SCHEMA_VERSION·Calculator·metric_store 변경 없음. 신규 ADR(ADR-048 후보: "종목 판정은 `activity_types` 단일 출처, 기간 집계는 `run_totals`") 기록 필요.

## 4. 적용 순서와 검증

1. **SSOT 유틸** (`activity_types.py`): `family_raw_types("running")`가 `_TYPE_MAP`의 모든 러닝 별칭을 포함하는지, `swimming`·`strength`가 running 집합에 없는지 단위 테스트. 로컬 사본 DB(운영 DB 아님)에서 `SELECT activity_type, COUNT(*) … GROUP BY 1`로 매핑되지 않는 값이 있는지 확인한다(있으면 D7).
2. **run_totals + 3곳 교체**: 픽스처(러닝 7건 51.0km + 수영 0.5km)로 내러티브 highlights `51.0/7`, week_digest·story_stats 같은 값을 assert. 내러티브 함수 이동 후 `routes_today`·`narrative_warm` import 경로 테스트 통과.
3. **브라우저**: `/v2/today` 월 내러티브 칩과 주간 스트립·주 요약의 km가 일치하는지, `/v2/library/story/<월>`과 숫자가 같은지 확인한다.
4. **display + verdict**: 17425(수영) `/100m`·basis 표기와 히어로 시간이 서로 맞는지, 598(근력) 거리·페이스 칸이 없는지, 603(걷기) 접두가 "러닝"이 아닌지 확인. 러닝 활동은 기존 verdict 문자열과 바이트 단위로 같아야 한다(회귀 테스트).
5. `python3 -m pytest tests/`, 프론트 테스트, `python3 scripts/check_docs.py`, files_index 재생성.

## 5. 호환성·v1 의존

- `highlights`·`evidence` 값의 의미가 "전체 활동"에서 "러닝"으로 바뀐다(키 불변). 소비처는 v2 Today, `narrative_warm`, AI 캐시. 값 변화는 의도된 수정이다.
- `verdict.text`는 Coach 컨텍스트(`src/ai/ai_context.py` → `get_activity_detail`)에도 들어간다. 비러닝 문구가 바뀌면 Coach 근거 문장도 바뀐다.
- `story_stats` 숫자가 바뀌면 ADR-032 Story 월/주 카드 값이 바뀐다(같은 결함 수정).
- `today_service.get_today_narrative`는 re-export로 남겨 import 호환을 유지한다.
- v1 의존: `src/web/`(v1)은 이번 변경 모듈을 import하지 않는다(grep 확인). v1 쪽 RUN_TYPES 사본(`ai_context_legacy.py`·`suggestions.py`)은 손대지 않고 v1과 함께 제거한다.

## 6. 대안 비교

| | A안(추천) 읽기 시점 SSOT + `display` 계약 | B안 수집 시점 `sport_family` 컬럼 + 종목별 페이스 저장 |
|---|---|---|
| 방법 | 유틸 함수·서비스 계층만 변경, 응답에 추가 필드 | `activity_summaries`에 컬럼 추가·뷰 재생성·백필, `avg_pace_sec_100m` 등 저장 |
| 장점 | 스키마·재동기화 불필요, 단계별 배포 가능, 러닝 경로 회귀 범위 작음 | SQL이 단순(`WHERE sport_family='running'`), 외부 소비처(MCP·export)도 같은 값 |
| 단점 | 집계 SQL마다 `family_clause`를 호출해야 함(규칙 누락 위험은 grep 검사로 보완) | SCHEMA_VERSION 상승, 백필·재정규화 필요. 종목별 컬럼은 "새 스포츠는 컬럼이 아니라 metric_store" 원칙에 어긋남. 페이스 basis가 정책 결정 전에 저장값으로 굳음 |

추천 A안. B안의 장점(단일 WHERE)은 A안의 `family_clause`로 대부분 얻을 수 있고, 표시 단위·basis가 아직 결정 전이라 저장값으로 굳히면 안 된다. 후속으로 `check_docs.py`에 "`LIKE '%running%'`·하드코딩 RUN_TYPES 금지" 검사를 추가할지 검토한다.

## 7. 결정 필요

- **D1 월/주 내러티브의 비러닝 처리**: (a) 러닝만 집계하고 비러닝은 언급 안 함 — 단순하지만 수영·근력 훈련이 "기록 없음"처럼 보일 수 있음 / (b) 러닝 수치 + 별도 한 줄("그 외 수영 1회") — 정확하지만 문구·칩이 늘어남 / (c) 전체 "활동"으로 집계하되 라벨을 바꿈 — 러닝 앱 목적과 주간 스트립과의 불일치가 남음.
- **D2 "회" 단위**: 러닝 세션 수만 셀지, 같은 날 여러 건을 1회로 볼지(현재는 건수).
- **D3 수영 페이스 basis**: 이동시간(Garmin·Strava 관례, 휴식 제외) vs 총시간(화면 시간과 직관적 일치). 이동시간을 쓰면 히어로에 이동시간도 같이 보여야 모순이 없다.
- **D4 사이클 표시**: km/h 속도 vs /km 페이스. 걷기·하이킹을 /km 페이스로 둘지.
- **D5 근력·기타 히어로 대체 칸**: 숨기기만 할지, 심박·칼로리·세트 수 등 다른 칸으로 채울지(UX 결정, product 영역).
- **D6 해석 줄 접두 문구**: 종목 라벨("수영", "근력", "걷기/하이킹" 그대로 vs "걷기") 및 비러닝에 페이스·심박 외 어떤 내용을 둘지.
- **D7 경계 종목 분류**: `highintensityintervaltraining`(matcher는 러닝 취급), `race`(현재 running 매핑), `treadmill`, 매핑 안 된 raw 값을 어느 family로 둘지.
- **D8 범위**: 나머지 RUN_TYPES 사본(training·metrics·archive 등 10여 곳)의 SSOT 이관을 이 작업에 포함할지, 별도 BACKLOG 항목으로 나눌지. 일부는 Calculator 입력(CTL·classifier)이라 결과값이 바뀔 수 있다.

## 8. 범위 밖 메모

- A-31 라이브러리 홈 최근 활동 수영 `/km` 표시: 같은 원인이며 `activityDisplay.ts`를 재사용할 수 있다(이번 ID 아님).
- CTL·부하에 비러닝 활동 부하가 포함되는지는 별도 메트릭 정책 문제다.
- `today_service.py` 320줄 규칙 초과는 이번 분리로 해소되지만 원래 이 패턴의 범위는 아니다.
