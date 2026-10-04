# DESIGN-S1S4-REMAIN — Phase 3 Library S1~S4 잔여 인벤토리 + 미설계 항목 설계 (2026-10-05)

범위: 3-6(20:S4·S6 활동 상세), 3-7(21:S1~S4 메트릭 목록·상세), 3-9(20:S8·S9 활동 목록·Library 홈).
3-9는 엄밀히는 S1~S4 밖(20 §9의 S8·S9)이다. 다만 활동 탐색 흐름(`from`·뒤로가기)이 3-6·3-7 항목과 같은 파일을 건드리므로 함께 적는다. 표에서는 "범주" 열로 구분한다.
방식: 읽기 전용 조사다. `IMPL-PROGRESS.md`·`../BACKLOG.md`·20/21 design·`DESIGN-PENDING-12.md`를 커밋 로그(`git log`, efc8af9까지)와 코드 grep으로 대조했다. 코드·DB는 바꾸지 않았다.
표기: "확인" = 이번에 코드에서 직접 확인함. "미확인" = 문서만 보고 판단함(착수할 때 다시 확인해야 함).

---

## 0. IMPL-PROGRESS의 "남음" 중 이미 끝난 것 (문서가 낡음)

| 항목 | 근거 커밋 | 비고 |
|---|---|---|
| S2 Sparkline `min_span`·끝점 상태색·변화 캡션 | 5bf0360 | `metric_display.min_span`, `Sparkline minSpan/endColor` 확인 |
| D1d 활동 scope `@a{id}` drill(TRIMP) | e2abd27 | `drillStackCore` `a{id}` 파싱, `metrics_explain_activity.py` 확인 |
| S3 `PredictionEvidence`(예측 분해) + 브라우저 스모크 | 351988a, 8a95a61 | |
| 목표 달성 가능성(필요 개선 %, 신뢰 <0.5면 범위만) | ade5348 | |
| S3 Today 시트 → 추세 링크(`?from=today`) | 9559e7b | `DrillPanel fromTag` 확인 |
| S4 URL 필터(`?q=`·`?category=`·`?provider=`, replace) | 3a087dd, 78dcd4f | 21 §3에 정의된 URL 키는 전부 반영됨. 후보였던 "S4 URL 필터 확장"은 메트릭 쪽 잔여가 없다. 활동 목록 쪽은 A-11 참조 |
| 활동 목록 기간 프리셋·월 선택·URL 동기화 | 3d53bd0 | DESIGN-PENDING 12 |

IMPL-PROGRESS 297·299~302행과 307행의 "남음"은 위 내용으로 갱신이 필요하다(문서 작업만 하면 됨).

---

## 1. 인벤토리

### (A) 설계서가 있어 바로 개발 가능

| ID | 범주 | 항목 | 근거(문서·절) | 현재 상태 |
|---|---|---|---|---|
| A-1 | 3-9/3-6 | 활동 상세 ← 규칙: 앱 히스토리가 있으면 `history.back()`, 없으면 `from`별 경로. `from` 8종(today·home·list·plan·coach·pb·heatmap·month) + `providers`. 라벨은 `← Today`, `← Library`, `← 8월 활동` 등 | 20 §3 첫 문단, §8 흐름 | 확인: `lib/activityHeader.ts backTarget`은 4키만 받고(today/coach/plan/library), history.back을 쓰지 않으며, home·list·pb·providers는 "활동"으로 떨어짐 |
| A-2 | 3-9 | 남은 진입점에 `?from=` 붙이기: `PersonalBests`(pb), `MilestonesPanel`·`TodayNarrative`(today), `TodayHero` "활동 보기"(today), `ArchiveHero` 최장 활동(home), 계획 매칭·Coach 근거의 활동 링크(plan/coach) | 20 §3 표(PB 행·계획 매칭), §8 "모든 위치에서 1탭" | 확인: 위 5개 파일의 링크에 `from`이 없음. 계획·Coach 쪽 활동 링크 위치는 미확인 |
| A-3 | 3-7 S3 | 메트릭 상세 인라인 분해에서 "원천" 행을 누르면 활동 상세(`/library/{id}?from=metric`) 또는 웰니스 일자(`/library/wellness/{date}`)로 push | 21 §3 "분해 원천 행" | 확인(**결함**): `BreakdownView`가 활동 원천에 `m.trimp@a{id}`를 넘기는데, 상세 페이지 `drillTerm`이 scope를 버리고 `/library/metrics/trimp?date=`로 이동함. 웰니스 원천은 링크가 없음 |
| A-4 | 3-7 S3 | 분해 `conclusion{top_loss,text}` 결론 한 줄(UTRS·CIRS·RRI) | 21 §7.2(c), §2.3 인라인 패널 순서 | 확인: 서버·프론트 모두 `conclusion` 없음 |
| A-5 | 3-7 S3 | 인라인 패널 ④ 푸터: `Garmin 값과 비교 →`(`/library/providers/{group}?days=28`, 대상이 없으면 `RunPulse 단독 산출`) + `Coach에게 묻기 →`. 하단의 일반 "Provider 비교" 버튼(`/library/providers`)은 중복이므로 제거 | 21 §2.3 인라인 패널 문단, §3 | 확인: 하단에 일반 링크가 있고, 헤더에 `compare_group` 링크가 따로 있음 |
| A-6 | 3-7 S3 | 분해 패널 로딩: 높이 예약(행 5개) + 차트 pointerdown 때 prefetch, CLS 0 | 21 §6 분해 패널, §8 흐름 | 확인: 지금은 "불러오는 중…" 텍스트만 있어 높이가 바뀜 |
| A-7 | 3-7 S3 | "이 지표는" ③ 내 값 해석 `지금 {값} — {등급}. 90일 평균 {mean}보다 {높음/낮음}`(trend `baseline` 사용). 모바일은 첫 방문 때만 펼침 | 21 §4.3-3, §2.3 모바일 | 확인: `MetricAbout`에는 what·방향·밴드만 있음 |
| A-8 | 3-7 S3 | 비-explain 지표의 v1 `MetricBreakdown` 바텀시트를 `DrillPanel`(간이 카드 + 추세 링크)로 교체 — 메트릭 상세 화면 | 21 §7.1 MetricBreakdown 행, DESIGN-PENDING-12 §1(A) | 확인: `[slug]/+page.svelte`가 아직 MetricBreakdown 사용 |
| A-9 | 3-6 S4/S5 | 활동 요약·지표 탭의 판정 근거 칩·핵심 지표 행을 `DrillPanel`(활동 scope, scope 생략 = 그 활동)로 교체. 지원 안 하는 slug는 간이 카드로 | 20 §3 판정 근거 칩·핵심 지표 행, §3 "§C3.3 확장(활동 scope)", §7-1 MetricBreakdown 삭제 | 확인: `[id]/+page.svelte`·`[id]/metrics`가 자체 `drillStack` + MetricBreakdown 사용. D1d가 끝나 막는 조건이 사라짐. Today·Coach·Plan·MonthNarrative의 MetricBreakdown은 범위 밖 |
| A-10 | 3-6 S4 | 요약 보기 상태 URL: `?seg=`(지도·스플릿 선택), `split=1k`, `map=hr`, `pin`을 모두 replaceState | 20 §3 표(지도 구간·스플릿·경로 색·타임라인) | 확인: `seg`는 store에만 있음. `split`·`map` 토글이 있는지는 미확인 |
| A-11 | 3-6 S6 | 서브탭 4종: 랩 `LapTable`(고정 열·발산 막대 160px·인터벌 워크/회복 그룹), 지표 탭 2줄 행·섹션 결론·미매핑 숨김, 소스 탭 3섹션(기록/계산/관련)·차이 열·행 펼침, 스트림 탭 토글 칩·x축 시간/거리 | 20 §2-6, §5 랩·스트림, §7-1, §7-2 ③(API 필드는 d8cf6eb로 이미 있음) | 확인: `LapTable` 컴포넌트 없음. 나머지 탭의 세부 반영 여부는 미확인(파일이 각각 72·82·27·237줄) |
| A-12 | 3-7 S2 | 스파크라인의 "모든 값이 같음" 문구를 `고정값(프로필)`과 `계산 안 됨`(null 비율 >50%)으로 나눔 | 21 §5 스파크라인 | 확인: 지금은 "변동 없음" 한 가지 |
| A-13 | 3-7 S2 | 추세 x축 라벨: 3·6개월은 `7월`, 1년은 `25.10`(`scrub.ts axisDateLabel` 실사용) | 21 §5 x축 | 미확인(4주 주경계는 완료. IMPL-PROGRESS 73행 기준 axisDateLabel은 쓰이지 않음) |
| A-14 | 3-7 S4 | 브라우저 검색 0건 빈 상태 `'{q}'와 맞는 지표가 없어요` + [검색 지우기], 부하 섹션 머리에 `readiness_decision` 헤드라인 1줄 | 21 §6 브라우저 그리드, §10 F-DATA-08 | 미확인 |
| A-15 | 3-7 S3 | `MetricTerm` 약어 ⓘ 팝오버(내용은 분해 v2 `meaning`) | 21 §7.1, §3 "ⓘ 공식" | 확인: 컴포넌트 없음. 비-explain 지표는 `meaning`이 비어 있어 B-4(문구)가 끝나야 완전해짐 |
| A-16 | 3-9 S8 | 목록 무한 스크롤(센티널·다음 20건 미리 로드·끝 문구) + snapshot `{pages, scrollY}` 복원(±50px) | 20 §2-3, §3 ActivityRow 행, §6 다음 페이지, §8 흐름 | 미확인(현재 페이지네이션 방식) |
| A-17 | 3-9 S8 | `GET /library/activities/facets`(종목·유형·월 건수) + 종목 칩 하드코딩 제거 | 20 §7-2 ⑤ | 미확인 |
| A-18 | 3-9 S8 | 목록 API의 `type`·`sort`(date/distance/pace/load)·`q`·`sport_group` 노출, 행에 `display_title`·`load`·`is_race` 추가 | 20 §7-2 ④ | 부분: DESIGN-PENDING 12에서 sort를 노출했는지 미확인 |
| A-19 | 3-9 S8 | 월 헤더 `‹ 2026년 8월 ›`(pushState·스와이프) + `✕ 8월`, 연도 sticky 헤더, 연-월 스크러버(`at=` replace, A-17 months 사용) | 20 §2-3, §3, §5 | 미확인. 헤더에 들어갈 합계 데이터는 설계가 없음 → B-3 |
| A-20 | 3-9 S9 | Library 홈: archive만 await하고 나머지 스트리밍, 찾기 줄(검색 + 빠른 칩), 히어로 근거 칩 팝오버, 히트맵 고정 셀·팝오버·키보드, 월별 막대 라벨·진행 중 빗금, 출처 한 줄 요약 | 20 §2-2, §3, §5, §6, §7-2 ⑥ | 미확인(홈 116줄, ArchiveHero 월 막대 링크만 확인) |

### (B) 설계가 필요한 것 → §2에서 설계

| ID | 범주 | 항목 | 왜 설계가 필요한가 |
|---|---|---|---|
| B-1 | 3-7 S3(3-17 연계) | D2 `x.taper` 특수 시트 | 10 §5에는 화면 개념(시나리오 3종·가정 문구)만 있고, DrillPanel의 `x.` 토큰 렌더 계약과 데이터 소스가 정해지지 않았다(BACKLOG 210행 "Today 드릴 설계 필요") |
| B-2 | 3-6 S4 | `impact.similar.basis = same_class` | 20 §7-2 ①에는 필드 이름만 있다. 후보 집합·창·최소 n·폴백 규칙이 없다(IMPL-PROGRESS 291행) |
| B-3 | 3-9 S8 | 목록 그룹 헤더 데이터(주 합계·12주 평균 틱, 월 요약: 건수·거리·유형별·전월 대비) | 20 §2-3·§5에 화면은 있지만 API가 없다. 무한 스크롤에서는 클라이언트가 합계를 내면 페이지 경계에서 틀린다 |
| B-4 | 3-7 S1·S3 | `description_short`·`action_hint` 문구 필드와 1차 대상 | 21 §4.2가 저장 위치(`MetricLabel` 선택 필드)를 정했다. 하지만 노출 범위, 등급별 action 키, 빈 문구 처리가 정해지지 않았고, 84개 문구가 없다 |
| B-5 | 3-7 S3 | 분해 "무엇을 바꾸면(추정)" 줄 | 21 §2.3·§10 F-UX-03은 "클라이언트 추정"이라고만 적었다. 공식이 없고, 임계·추정을 서버에 둬야 한다는 규칙과도 충돌한다 |
| B-6 | 3-7 S2 | 예측 추세의 기준 대회 교체 이벤트 | 21 §7.3 C5·10 §5는 표시하라고 하지만, `events.type` 계약은 `race`·`algo_change`뿐이고 파생 규칙이 없다 |

### (C) 사용자 결정 필요·보류 (건드리지 않음)

| ID | 항목 | 근거 |
|---|---|---|
| C-1 | S1b PMC 감쇠·GAP 잔여 3건 | BACKLOG DESIGN-PENDING 4, DESIGN-PENDING-12 §4 |
| C-2 | ◆ 알고리즘 버전 마커 | BACKLOG 210행 ③(changelog 소스 부재), DESIGN-PENDING-12 §9(e) |
| C-3 | 세션 피드백 RPE 저장(⑦)·`⋯` 메뉴(3-10) | DESIGN-PENDING 5, 20 §7-2 ⑦ — ADR 승인 필요 |
| C-4 | 3-16(D4) | DESIGN-PENDING 6 |
| C-5 | 내러티브 캐시 워밍·MonthNarrative 레이어링 | DESIGN-PENDING 7 |
| C-6 | 계정 설정 스키마·sync_jobs | DESIGN-PENDING 10 |
| C-7 | PB 공식 기록 입력(✎, 쓰기) | 20 §3 PB 행·§7-2 ⑥. 저장 컬럼 존재가 미확인이고 실 DB 쓰기가 생김 → 저장소 확인·승인 후 진행 |
| C-8 | 대표 소스 변경 메뉴, OSM 타일, 부하 미니 막대 | 20 §10 F-UX-12·F-UI-06·F-UX-13 "보류" |
| C-9 | `--delta-better/worse` 색·provider 배지 대비 | 20 §11-1, 21 §11-1 — dataviz 팔레트 검증 필요 |
| C-10 | UTRS BB 이중 계산(D7)·UTRS v2 | 21 §7.3 C6, 3-18 |
| 범위 밖 | 3-1/3-17 이월(대안 목표·볼륨 민감도·기온 환산·직전 마라톤 기준선), S6 §8-1~4, S7 | 각각 10 S5, ADR-021, 21 S7 |

참고: 21 §7.1의 `ContributionBars`는 별도 파일이 없다. `BreakdownView` 안의 기여 막대가 같은 기능(±색·factor 비율·1위 태그)을 하므로 잔여 항목으로 세지 않는다.

---

## 2. (B) 설계

공통 규칙: 등급 경계·최소 n·창 같은 임계값은 서버 상수로만 둔다(프론트는 `status`·`label`을 그대로 렌더). 파일은 300줄 이하로 유지한다. Calculator 안에서 raw SQL을 쓰지 않는다(아래 설계는 전부 서비스 계층 읽기 전용이고 Calculator 변경은 없다). 새 함수마다 테스트를 1개 이상 둔다. 데이터가 부족하면 에러 대신 "데이터 수집 중" 문구를 보이고, 서버는 빈 값·null을 돌려준다. DB 스키마 변경은 없다.

### B-1. D2 `x.taper` 레이스 아침 폼 시트

**사용자 시나리오**: Coach 답변의 투영 칩("계획대로 가면 레이스 아침 폼 약 +18")이나 레이스 허브의 레이스 아침 폼 줄을 누른 사용자가 묻는 것은 "그 숫자는 어떤 가정에서 나왔고, 다르게 하면 어떻게 되나?"다. 지금은 허브 페이지 전체로 이동해서 질문의 맥락을 잃는다.

**정보 계층**
- L0(시트 헤더): `레이스 아침 폼 — 계획대로 가면 +18 · 신선` (의미 먼저. 등급 라벨은 서버 `status_label`)
- L1: 시나리오 3행 비교표 `계획대로 / 유지 / 테이퍼` × `레이스 아침 TSB · 등급 · 체력 변화율(−6%)`. 현재 선택(기본 계획대로) 행을 강조한다.
- L2: 오늘~레이스일 TSB 투영 미니 차트(선택한 시나리오 1선 + 레이스 최적 밴드), 가정 문구(`계획 세션 거리 × 개인 TRIMP/km`, 계획이 없으면 `균일 부하 가정`), `레이스 허브에서 자세히 →`.

**토큰·URL**: `?drill=x.taper`(scope 생략 = 활성 목표 레이스), 시나리오 선택은 `scn=` replaceState(10 §3 B7과 같은 키). 스택 규칙(최대 3단, Esc = pop)은 §C3과 같다. 시트 안에서 `m.tsb@{race_date}`로 push할 수 있게 둔다.

**서버(API 형태)** — 신규 엔드포인트 없이 기존 레이스 허브 응답을 재사용하는 것이 1안이다. 허브가 이미 `RaceMorningForm` 시나리오를 내려주므로(필드 이름은 착수할 때 `types`에서 확인), DrillPanel이 그대로 읽는다. 시트에 필요한데 허브에 없는 필드만 추가한다.
```json
"race_morning": {
  "race_date": "2026-11-22", "basis": "plan" | "uniform",
  "scenarios": [{"key":"plan","label":"계획대로","tsb":18.2,"status":"great","status_label":"레이스 최적","ctl_change_pct":-6.1,
                 "series":[{"date":"2026-10-05","tsb":-4.0}, "..."]}, "..."],
  "assumption": "계획 세션 거리 × 개인 TRIMP/km(최근 8주 중앙값)"
}
```
- `status`·`status_label`은 `bands.grade("tsb", …)`에 레이스 국면 재판정을 더해 서버에서 만든다(21 §4.4). 프론트에 임계값을 두지 않는다.
- `series`는 이미 계산된 투영값을 날짜로 다운샘플한 것(최대 60점)이다. 투영 로직을 새로 만들지 않는다.
- 목표 레이스가 없으면 `race_morning: null` → 시트에 `목표 대회를 정하면 레이스 아침 폼을 예측해요 · 대회 정하기 ›`. 부하 이력이 28일 미만이면 `체력 계산에 28일 기록이 필요해요 (지금 n일)`.

**프론트 파일**
- `lib/drillStackCore.ts`: 토큰 kind `x` 파싱(`parseDrillToken('x.taper')` → `{kind:'x', id:'taper'}`), 기존 `m.` 동작은 그대로.
- `lib/components/drill/TaperSheet.svelte`(신규, 120줄 이하): 비교표 + 미니 차트(`TrendChart`의 bands·selectedDate 재사용) + 가정 문구.
- `DrillPanel.svelte`: 스택 top의 kind가 `x`면 `x` 레지스트리(`taper` → TaperSheet)로 분기한다. DrillPanel이 이미 203줄이므로 분기 표는 `lib/drillSpecial.ts`로 뺀다.
- `lib/answerEvidence.ts chipTarget`: 투영 칩 목적지를 `/today/race`에서 `openDrill('x.taper')`로 바꾼다. 허브의 "레이스 아침 폼" 줄도 같다.

**검증**: 단위 — `parseDrillToken`/`formatDrillToken`의 `x.` 왕복, `drillSpecial` 매핑 없음 → 간이 "지원하지 않아요" 폴백. pytest — 허브 응답에 `race_morning` 필드·status 존재, 목표 없음 → null, 이력 28일 미만 → `scenarios: []`. Playwright(실 DB 사본) — Coach 투영 칩 → `?drill=x.taper` 시트, `scn` 전환 시 히스토리가 늘지 않음, Esc 닫힘, 390px 가로 넘침 0.

### B-2. `impact.similar.basis = same_class`

**시나리오**: 판정 문장 "부하는 평소 이지런보다 조금 높음"의 "평소"는 같은 유형 세션이어야 의미가 있다. 지금 basis는 거리(`distance`)라 이지 10km와 템포 10km가 섞인다.

**서버 규칙(상수는 `activity_similar.py` 모듈 상단)**
- 후보: 같은 `sport_group`(러닝 계열)의 캐노니컬 활동, 대상 활동 이전 `SIMILAR_WINDOW_DAYS`일, 최대 `SIMILAR_MAX_CANDIDATES = 80`개(최신순).
- 후보의 `workout_class`는 상세 응답과 **같은 분류 함수**로 구한다(4d88967에서 도입한 분류기 재사용, 로직 복제 금지). 비용을 줄이려고 분류에 필요한 요약 컬럼만 한 번에 배치 조회한다(서비스 계층 1쿼리).
- 같은 class가 `SIMILAR_MIN_N = 3`개 이상이면 `basis:"same_class"`, 아니면 기존 거리 기반으로 폴백하고 `basis:"distance"`로 둔다. 둘 다 n<3이면 `similar: null`.
- 응답 형태(기존 필드 유지 + 추가):
```json
"similar": {"basis":"same_class","class":"easy","class_label":"이지런","n":10,"window_days":90,
            "pace_rank":7,"load_median":72.0,"load_pct_vs_median":35.1}
```
- verdict 문구의 "평소 {class_label}보다"는 서버가 만든다. 비교 등급(높음·조금 높음 등)의 경계도 서버 상수다.

**프론트**: `ActivityVerdict` 근거 칩 `부하 97 · 이지 중앙값 72 대비 +35%`는 서버 필드만 렌더한다. `basis === 'distance'`면 라벨을 `비슷한 거리 중앙값`으로 쓴다. `similar === null`이면 칩을 숨기고, 판정 블록에 `판정할 기준이 아직 부족해요(같은 유형 세션 3회 필요)`(20 §6)를 보인다.

**파일**: `src/services/activity_similar.py`(신규, 약 100줄) — `activity_detail_service.py`(187줄)는 호출만 한다.
**검증**: pytest — same_class n≥3, n<3 → distance 폴백, 둘 다 부족 → None, 대상 활동 자신 제외, 창 밖 제외(4건). Playwright(실 DB 사본) — 이지런 1건·인터벌 1건 상세에서 칩 문구 확인, 콘솔 에러 0.

### B-3. 활동 목록 그룹 헤더 데이터

**시나리오**: 8월 막대에서 들어온 사용자는 "8월에 얼마나 뛰었고 전월보다 어땠나"를 행보다 먼저 보고 싶어 한다. 전체 목록을 스크롤하는 사용자는 주 단위 리듬(이번 주가 평소보다 많은지)을 원한다.

**서버(API 형태)** — 신규 `GET /api/v1/library/activities/summary?from=&to=&month=&sport_group=&type=`(목록과 같은 필터 파서 공유):
```json
{"weeks":[{"start":"2026-09-21","n":4,"km":34.7,"sec":11839,"in_range_only":false}],
 "avg_week_km_12w":38.2,
 "month":{"month":"2026-08","n":18,"km":183.4,"by_class":[{"key":"easy","label":"이지","n":9}],"prev_month_pct":33.0}}
```
- `weeks`는 요청 범위 안의 주(월~일)다. 월 모드에서 경계 주는 그 달의 활동만 합하고 `in_range_only:true`로 표시한다(와이어프레임 `7/27–8/2 (8월분만)`).
- `avg_week_km_12w`는 필터와 무관하게 오늘 기준 최근 12주 러닝 계열 평균이다(주 막대 100% 틱, 20 §5). 이력이 4주 미만이면 null → 막대 대신 숫자만.
- `month`는 `month=`가 있을 때만 준다. 전월 0건이면 `prev_month_pct: null`.
- 파일: `src/services/activity_list_summary.py`(신규), 라우트는 `routes_library.py`가 이미 293줄이므로 새 라우트 파일(`routes_library_activities.py`)로 분리하는 것을 권장한다.

**프론트**: `MonthHeader.svelte`(월 요약·‹ ›·✕), `WeekHeader.svelte`(합계 + 12주 평균 틱 막대, 필터 중에는 막대 숨김), `+page.ts`가 목록 첫 페이지와 summary를 동시에 시작하되 summary는 await하지 않는다(스트리밍). summary가 실패하면 헤더는 합계 없이 날짜만 보인다(목록은 막지 않음).

**검증**: pytest — 월 경계 주 `in_range_only`, 12주 평균, 전월 0건 → null, 필터 공유(type=interval)(4건). 단위 — 주 키 계산(월요일 시작, 연말 경계). Playwright(실 DB 사본) — `?month=2026-08` 헤더 값이 summary와 일치, 무한 스크롤 2페이지 후에도 주 합계가 그대로인지 확인.

### B-4. `description_short`·`action_hint` 문구

**규칙(21 §4.2 확장 위치 그대로)**: `MetricLabel(name_ko, abbr, description_short=None, action_hint=None)`. `action_hint`는 `dict[status, str]`로, 키는 §C7 5단 status다. 현재 status에 해당하는 문장만 내려간다.
**API**: `/library/metrics` 항목과 `/trend.meta`에 `description_short`(없으면 null), `/trend`에 `action_hint`(현재 status에 맞는 1문장 또는 null). explain `meaning.what`이 비어 있으면 `description_short`로 채워서 A-15 `MetricTerm`·A-7이 같은 출처를 쓰게 한다.
**표시**: 카드 2행 = `description_short` 또는(없으면) A-7 해석 한 줄. 둘 다 없으면 줄을 렌더하지 않는다(빈 문구 금지).
**파일**: `metric_labels.py`가 300줄을 넘으면 `metric_labels/` 패키지(`daily_core.py`, `daily_wellness.py` …)로 나눈다. 공개 API(`METRIC_LABELS`)는 유지한다.
**테스트**: `test_metric_labels.py`에 40자 이내, `action_hint` 키 ⊆ 5단 status, 1차 대상 집합 전부 등록을 추가한다. 단위 — 카드 2행 선택 함수.
**1차 범위·문구 검수는 열린 결정 D-4.**

### B-5. 분해 "무엇을 바꾸면(추정)"

**규칙**: 추정은 서버에서만 한다. explain 응답에 선택 필드를 둔다.
```json
"what_if":[{"key":"rest_today","label":"오늘 휴식하면","target":"내일 아침","value_est":68,"status":"neutral",
            "assumption":"오늘 부하 0, 다른 입력은 오늘과 같다고 가정"}]
```
- 1차 지원: `tsb`(오늘 부하 0 → 내일 `tsb_morning` = PMC α로 1스텝 진행), `utrs`(위 TSB 추정값으로 TSB 항만 교체하고 나머지 항은 유지한 채 재정규화). 계산은 기존 explainer 입력값과 `pmc`/`utrs` 상수를 재사용하는 순수 함수다(`metrics_explain_whatif.py`, 신규).
- 선택일이 오늘이 아니면 `what_if`를 생략한다(과거에는 가정이 무의미).
- 프론트: `BreakdownView` ③ 원천 아래 1줄 `무엇을 바꾸면(추정): 오늘 휴식 → 내일 약 68`, `추정` 배지(§C6 확장)와 가정 문구 ⓘ.
**검증**: pytest — TSB 1스텝 수식(α=1/42·1/7), UTRS 다른 항 불변, 과거 날짜 → 생략(3건). 브라우저 — 오늘 UTRS 상세에서 1줄 표시, 과거 날짜 선택 시 사라짐.
**수면 시나리오 포함 여부는 열린 결정 D-5.**

### B-6. 예측 추세의 기준 대회 교체 이벤트

**규칙**: `/trend`의 `events[]`에 `type:"basis_change"`를 추가한다. 예측 slug(`race_pred_*_sec`) 기간 안에서 일자별 `json_value`의 기준 대회 activity id가 전날과 달라진 첫 날을 이벤트로 낸다. label은 `기준 대회 변경: 10K 2026-05-09`다. json 키 이름은 착수할 때 `metrics_explain_prediction.py`가 읽는 키와 맞춘다(같은 키를 쓰는 헬퍼로 추출하고 중복 파싱을 금지). 서비스 계층 1쿼리(기간 내 json_value 배치)로 처리한다.
- 프론트: `TrendChart` 이벤트 마커에 세 번째 모양을 추가하고, 판독줄에 label을 보인다. ◆(algo_change, C-2)와 겹치지 않는 모양을 쓴다(D-6).
**검증**: pytest — 기준 id가 바뀐 날 1건, 변경 없음 0건, json 키 없음 → 생략. Playwright(실 DB 사본) — 1y 마라톤 예측에 마커가 보이고 판독줄 문구가 나오는지.

---

## 3. 구현 순서(유닛)와 검증

A와 B를 섞어 결정 없이 할 수 있는 것부터 배치한다. 각 유닛이 끝날 때 `pytest tests/`, `cd frontend && npm run test:unit && npm run check && npm run build`, `python3 scripts/check_docs.py`를 돌린다. 화면 유닛은 실 DB 사본 + Flask + 빌드 산출물로 Playwright를 돌린다(서버는 절대경로 한 줄 명령, `readlink /proc/<pid>/cwd`로 워크트리 확인).

| 유닛 | 내용 | 검증 |
|---|---|---|
| U1 | A-3 원천 행 결함 수정(활동·웰니스 링크) + A-5 푸터 정리 | 단위(원천 → href 함수), Playwright: UTRS 상세 원천 탭 → 활동 상세·웰니스 일자 |
| U2 | A-1 `backTarget` 확장 + history.back 우선 + A-2 진입점 from 부착 | 단위(from 9종 라벨·경로, 알 수 없는 값 폴백), Playwright: PB·마일스톤·Today·홈·목록에서 진입 → ← 라벨·목적지 |
| U3 | A-4 conclusion(서버) + A-6 패널 높이 예약·prefetch + A-7 내 값 해석 | pytest conclusion 3종, 단위 해석 문장, Playwright CLS·문구 |
| U4 | A-8·A-9 MetricBreakdown → DrillPanel(메트릭 상세·활동 요약·지표 탭) | Playwright: `/library/{id}?drill=m.trimp` 복원, 2단 스택 ← 1회 pop, 비지원 slug 간이 카드 |
| U5 | B-2 same_class | §2 B-2 검증 |
| U6 | A-10 요약 URL 보기 상태 + A-11 서브탭 4종 | Playwright: `?seg=3` 새로고침 복원, 랩 인터벌 그룹, 소스 3섹션 |
| U7 | A-12·A-13·A-14(브라우저·차트 잔여) | 단위 문구 분기·축 라벨, Playwright 검색 0건 |
| U8 | B-1 `x.taper` | §2 B-1 검증 |
| U9 | B-6 기준 대회 이벤트 | §2 B-6 검증 |
| U10 | A-17 facets + A-18 목록 API + B-3 summary | pytest 각 2건 이상 |
| U11 | A-16 무한 스크롤·snapshot + A-19 월·주 헤더·스크러버 | Playwright: 8월 목록 → 상세 → ← 스크롤 ±50px·페이지 수 유지, 2023-10 스크러버 1회 도달 |
| U12 | A-20 Library 홈 | Playwright: 히어로 ≤1.0s, 히트맵 셀 팝오버, 블록 실패 격리 |
| U13 | B-4 문구(D-4 결정 후) + A-15 MetricTerm | `test_metric_labels` 확장, 카드 2행 100% |
| U14 | B-5 what-if(D-5 결정 후) | §2 B-5 검증 |

U1~U4는 결함·설계 완료 항목이라 먼저 한다. U13·U14는 열린 결정이 풀린 뒤에 한다. 각 유닛은 커밋 1개 이상으로 나누고, 운영 반영은 지시가 있을 때만 한다.

---

## 4. 열린 결정 (추정으로 확정하지 않음)

| ID | 결정 | 선택지 | 권장(참고용) |
|---|---|---|---|
| D-1 | `x.taper` 데이터 출처 | (a) 레이스 허브 응답 재사용 + 필드 보강 (b) 전용 `GET /today/race/taper` | (a) — 투영 로직 단일 출처 |
| D-2 | `x.taper` 시트에 투영 미니 차트를 넣을지 | (a) 표 + 차트 (b) 표만(차트는 허브) | (a), 단 모바일 높이 확인 후 |
| D-3 | same_class 창·최소 n | 창 30일(설계 `same_class_30d`와 일치, n 부족 위험) / 90일 / n=3 또는 5 | 90일·n=3, 폴백 distance |
| D-4 | `description_short`·`action_hint` 1차 범위와 문구 검수 | (a) 내 지표 기본 8 + 오늘 상태·부하 대표 약 20개 (b) daily 84개 전부 | (a). 문구는 사용자 검수 후 커밋 |
| D-5 | what-if 시나리오 범위 | (a) 오늘 휴식(TSB)만 (b) + 수면 7시간(수면 점수 환산 규칙 필요) | (a) |
| D-6 | 기준 대회 교체 마커 모양·노출 | ◇ 별도 모양 / ▲와 같은 모양에 라벨만 다르게 / 숨김 | ◇, ◆ 결정(C-2)과 함께 확정 |
| D-7 | 활동 목록 summary 라우트 분리 | `routes_library.py`에 추가(300줄 초과) / 새 파일 분리 | 새 파일 |
| D-8 | 3-9 항목(A-16~A-20, B-3)을 이번 S1~S4 잔여 묶음에 넣을지, 3-9 별도 묶음으로 둘지 | 함께 / 분리 | 범위 판단은 사용자 몫 |
