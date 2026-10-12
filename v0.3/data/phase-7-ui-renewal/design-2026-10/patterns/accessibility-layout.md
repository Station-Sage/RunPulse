# 설계: 접근성 레이아웃 (셸·랜드마크·제목 위계·live region·375px) — A11Y-7/A11Y-15

- 상태: 설계 확정(2026-10-12). A11Y-L1~L9 결정 완료(에이전트 위임 2026-10-12, 5절). 문구가 필요한 곳은 TXT-1 미확정. 코드 변경 없음
- 변경 이력: 2026-10-11 초안 / 2026-10-12 9차 동기화 — 사용자 지시로 1절 발견 전부를 수정 대상으로 전환(3.1 대응표 F-1~F-21 신설), coach/+page 분리 설계(2.5) 추가, L1~L9 결정 반영, OVL-1 수정(L1)·OVL-8 정합, YearMonthScrubber 키보드 없는 slider 발견 추가(F-18)
- 전제: `accessibility-common.md`(44px `.tap`, PageHead 보이는 h1, 포커스 링 2px, s3 하한, 라이트 테마, theme-color), `overlay-common-behavior.md`(OVL-1~8)
- 근거: 2026-10-11 `frontend/src` grep 결과. 줄 번호는 이 날짜 기준. coach/+page(310줄)·YearMonthScrubber·drillStack·Today 순서는 2026-10-12 재확인

## 1. 근본 원인
**RC-L1. 주 내비가 한 DOM 노드로 두 위치를 맡음.** `routes/+layout.svelte:41-78` 은 `header → MenuDrawer → main → nav` 순서다. nav 하나가 모바일 하단 탭(`fixed bottom-0`)과 1280px 좌측 사이드바(`lg:inset-y-0 lg:w-52`)를 CSS 로만 바꿔 그린다. 그래서 A11Y-7(lg 만 본문 앞)은 CSS 로 풀 수 없다. skip link 와 `main` id 도 없다. 하단 탭 높이는 매직 넘버로 세 곳에 복제돼 있다: `main pb-20`(:58), `Toast bottom-20`(Toast.svelte:27), `YearMonthScrubber bottom-20`(:50).

**RC-L2. 알림 경로(live region)의 소유자가 정해져 있지 않음.** 메시지마다 그 메시지를 그리는 컴포넌트가 제각각 role 을 단다. 확인된 문제는 아래와 같다.

| 유형 | 위치 | 문제 |
|---|---|---|
| A. group+live(OVL-1 원안) | OVL-1 `inlineConfirm`(overlay §2.3 원안) → CalendarFeedCard:78, McpTokenCard:90, ConnectPanel:121(현재 `alertdialog`), BaselineRow:129(`role=alert`+버튼) | 확인 문구가 그룹 이름(`aria-labelledby`)이고 같은 문구가 live 로도 나간다. OVL-2 로 "취소"에 포커스가 가면 그룹 이름과 live 가 같은 문구를 두 번 읽는다 |
| B. 포커스 컨트롤 + live 복제 | ChartScrub:85-90(`role=slider`, valuetext 없음) + ActivityTimeline:81 `aria-live` | 키를 누를 때마다 슬라이더 값(인덱스 숫자)과 live 의 "x.xx km"를 연달아 읽는다 |
| C. 같은 문구를 두 영역에 출력 | `syncStore.notice`: SyncPanel:82-87(`role=status`) + data/sync/+page:93(`role=status`) | /data/sync 에서 패널을 열면 같은 안내가 두 영역에 나온다 |
| D. 중복 속성 | SyncPanel:82 `role="status" aria-live="polite"` | status 에 polite 가 이미 포함돼 있다 |
| E. live 안에 조작 요소 | StreamStatus:28(중단 버튼), McpTokenCard:73(입력·복사·닫기), ActivityHeatmap:75(툴팁 안 링크, hover 로 열림), DegradedBanner:14(링크) | 알림을 읽을 때 버튼·링크 이름까지 함께 읽는다 |
| F. 조건부 생성 live | `{#if}` 안의 `role=status/alert` 약 20곳(CalendarFeedCard:99, McpTokenCard:63·107, ConnectPanel:130, AutoSyncRow:69, BaselineRow:140, RecomputeSummary:37-41, data/export:96, settings/ai:106, sources/[provider]:83·87, import:127·151, Toast:28 등) | 영역이 내용과 동시에 생겨 읽히지 않거나 읽히는 시점이 들쭉날쭉할 수 있다(실기기 미확인) |
| G. 역할 혼용 | 같은 종류의 인라인 오류가 alert(RowActionSheet:211, AdjustmentCard:111, import:151)와 status(AutoSyncRow:69, BaselineRow:140, sources/[provider]:87)로 나뉨. 로드 실패 `role=alert` 가 첫 렌더에 나옴(ErrorState:23, RaceSummaryLine:15) | Today 처럼 로드 실패가 여럿이면 assertive 알림이 겹친다 |

참고: `role=group` 은 13곳(RowActionSheet 5, ActivityFilters 4, WellnessDateBar, providers, streams, story)이다. 이 중 group 안에 live 가 함께 있는 곳은 현재 없다. RowActionSheet:206 의 live 미리보기는 group 밖에 있고, 내용도 칩의 상태와 다르다(km 변화).

**RC-L3. 페이지 골격(제목·섹션·순서·크기)을 정하는 곳이 없음.**
- h1 을 그리는 곳이 세 갈래로 나뉜다: 페이지 파일 16(landing 포함)·`+error` 2, 하위 레이아웃 1(`library/[id]/+layout.svelte:52`, sticky header 안), 컴포넌트 4(TodayHero:37 `{#if view}` 안, ColdStartProgress:13, WellnessDateBar:26, Step0Intro:7). 셸 헤더의 앱 이름은 `<span>`(:52)이다.
- 컴포넌트 제목은 평평하다: h2 를 쓰는 파일 20개, h3 는 1개(RecomputeSummary), h4 는 없다. 섹션 이름을 `<p class="uppercase">` 로 흉내 내는 곳이 있다(today/+page:155·168, library/[id]/+page:140, coach/+page:120·218·237·261).
- nav 랜드마크가 7종인데 이름 짓는 방식이 다르다: "주 메뉴", "하위 메뉴"(SubTabs, Data), "Library 섹션", "활동 상세 탭", "경로"×3.
- 대화상자 10개(MenuDrawer, SyncPanel, ScopeSheet, DrillPanel, RowActionSheet, DemoBanner, EngineSheet, MilestonesPanel, MetricBreakdown, GarminCleanup) 모두 `aria-label` 을 쓰고 `aria-labelledby` 는 0곳이다. 7개는 h2 가 있고, RowActionSheet·GarminCleanup·DemoBanner 는 제목이 없다.
- 시각 순서와 DOM 순서가 다르다: today/+page:104-167 이 `contents` + `order-1/4/2/3/5` 를 쓴다. 모바일 화면은 히어로(1)·준비도(2)·흐름 차트(3)·다음 세션(4) 순서로 보이지만 DOM 과 Tab 순서는 1·4·2·3 이다. `order-*` 를 쓰는 곳은 여기뿐이다.
- 페이지 300줄 규칙 위반: `coach/+page.svelte` 310줄(스크립트 1-112, 마크업 116-310). 인접 파일: `coach/[threadId]/+page.svelte` 299, `today/month/[ym]/+page.svelte` 295, `library/metrics/+page.svelte` 291. 프론트에는 줄 수 가드가 없다(`check_docs.py` 3번 검사는 `.py` 만).

**RC-L4. 375px 레이아웃 기준이 없음(후보, 브라우저 측정 전).**
- 44px 미달: 셸 ☰ `p-1.5`+`h-5`=32px(+layout:44-49), YearMonthScrubber 레일 `w-5`=20px(:50), 통증 부위 칩 `h-9`(RowActionSheet:199), 확인·토큰 버튼 `px-3 py-1.5 text-xs`(CalendarFeedCard:85·89, McpTokenCard:66·77-78, ConnectPanel:124), 밑줄 텍스트 버튼(ConnectPanel:113-115, McpTokenCard:91-95), coach 칩 `px-3 py-1`(coach/+page:223·225·245, coach/[threadId]:266).
- YearMonthScrubber 는 `role=slider tabindex=0` 이지만 키 처리기가 없다(:48-61). 키보드로 포커스는 되나 조작할 수 없다.
- 경계값: WeekStrip `grid-cols-7 gap-1`(:28) 칸은 약 45px 로 추정한다. Library 탭 6개 `flex-1`(library/+layout:24) 은 칸당 약 62px 로, "소스 비교" 줄바꿈 여부를 실측해야 한다. 활동 상세 헤더는 `h-14` 고정 높이 안에 `truncate` h1 과 배지 행이 들어간다(library/[id]/+layout:43).
- 컴포넌트 단위 가로 스크롤: SubTabs:15(스크롤바 숨김), library/metrics:202·225 칩 행, ScenarioCompareTable:22 스냅 캐러셀, ProviderMatrix:24·LapTable:68·ProviderComparison:103 표, ActivityHeatmap:45.
- 시트: `max-h-[70~85vh]` 는 iOS 툴바 변동을 반영하지 않는다. 하단 safe-area 가 없는 시트: ScopeSheet:48, EngineSheet:17, MilestonesPanel:49, MetricBreakdown:60, RowActionSheet:125.

## 2. 설계안
### 2.1 공통 셸 규칙 (RC-L1, A11Y-7)
- DOM 순서는 `skip link → ProgressBar/DemoBanner → header(banner) → [lg] nav 주 메뉴 → main#main[tabindex=-1] → [<lg] nav 주 메뉴` 로 둔다. MenuDrawer 는 overlay 설계대로 현재 위치를 유지한다(OVL-3).
- `ShellNav.svelte`(신규)를 `variant="side"`(`hidden lg:flex`)와 `variant="bottom"`(`lg:hidden`)으로 **두 번 렌더**한다. `display:none` 이 걸린 쪽은 접근성 트리와 Tab 순서에서 빠지므로 한 해상도에는 nav 가 하나만 남는다. 이 방식은 SSR 에서도 안전하고 깜빡임이 없다. JS `matchMedia` 로 노드를 옮기는 방식은 하이드레이션 불일치 때문에 기각했다.
- 탭 정의와 `isActive` 는 `lib/shell/navTabs.ts`(순수)로 옮긴다. `data-testid` 는 variant 접미사를 붙여 중복을 피한다.
- `layout.css` 에 `--shell-bottom`(하단 탭 높이 + safe-area, lg 에서 0)을 둔다. `main` 패딩, Toast, YearMonthScrubber 는 이 변수만 참조한다.
- 1280px 에서 DrillPanel 인라인 패널(`lg:grid-cols-[1fr_420px]`, DrillPanel:124)은 `<aside aria-labelledby=패널 h2>` 로 바꾼다. 모바일 시트 쪽은 OVL `use:modal` 을 그대로 쓴다. 드릴 스택의 history 처리는 두 해상도 공통으로 OVL-8(overlay §2.4)을 따른다.

### 2.2 페이지 골격·랜드마크·제목 규칙 (RC-L3)
1. 라우트의 **모든 상태(로드·빈·오류 분기 포함)에서 h1 이 정확히 1개**다. h1 은 PageHead(공통 §2.3) 또는 문서화된 예외 컴포넌트(TodayHero·ColdStartProgress·WellnessDateBar·활동 상세 레이아웃)만 그린다. TodayHero 의 `view` 가 없을 때도 h1 을 출력한다.
2. 위계는 h1(페이지) → h2(섹션·카드 그룹: `<section aria-labelledby>`) → h3(카드 내부)로 둔다. `<p uppercase>` 로 흉내 낸 섹션 이름은 같은 클래스의 h2 로 바꾼다. 시각 변화는 없다.
3. 대화상자와 시트는 `aria-labelledby` 로 자기 h2 를 가리킨다. 제목이 없는 3개(RowActionSheet·GarminCleanup·DemoBanner)와 이름 없는 Today 준비도 섹션은 **sr-only h2**(L3)를 두고 그것을 가리킨다. 문구는 TXT-1.
4. 랜드마크는 banner 1, main 1, 주 nav 1(해상도당), 보조 nav(서브탭·경로)로 둔다. 보조 nav 이름은 `"<영역> 하위 메뉴"`(Library·Data·활동 상세), 경로 nav 는 기존 "경로" 유지(L9). 셸 header 의 앱 이름은 제목 요소로 만들지 않는다(h1 은 페이지 몫). 서브탭은 지금처럼 h1 위에 둔다(L2).
5. 시각 순서와 DOM 순서를 일치시킨다. 라우트에서 `order-*`·`*-reverse` 를 금지하고 정적 가드로 검사한다. Today 는 L4(b): `contents`·`order-*` 를 지우고 모바일도 DOM 순서(히어로 → 다음 세션 → 준비도 → 흐름 → 원본)로 보인다. lg 2열은 지금과 같다(왼쪽 히어로·다음 세션, 오른쪽 준비도·흐름).
6. 페이지·컴포넌트 파일은 300줄 이하. 300줄에 가까운(≥280) 파일을 이 설계로 수정할 때는 순증 0 이하로 한다(2.5).

### 2.3 live region 단일 소유 규칙 (RC-L2, A11Y-15)
- **R1 단일 채널:** 한 메시지는 한 경로로만 알린다. 포커스 이동이 이미 이름·상태를 읽게 한다면 live 를 쓰지 않는다. 인라인 확인(유형 A)은 `group + aria-labelledby(확인 문구)` 와 "취소" 포커스(OVL-2)만 쓰고 live 를 쓰지 않는다(L1 → OVL-1 수정, overlay §2.3). BaselineRow:129 도 같은 패턴(`use:inlineConfirm`)으로 바꾼다.
- **R2 포커스 컨트롤 상태는 컨트롤이 말한다:** ChartScrub 에 `valueText(index)` prop 을 추가해 `aria-valuetext` 로 출력하고, ActivityTimeline:81 의 live 는 제거한다. 화면 표시는 그대로 둔다. TrendChart·FormChart·Sparkline 도 같은 prop 으로 값을 넘긴다.
- **R3 상시 영역 + 발신 함수:** `+layout.svelte` 에 sr-only `LiveRegion.svelte` 를 처음부터 빈 상태로 1회 마운트한다(polite·assertive 2개). 일회성 메시지(저장 결과, 토스트, 인라인 오류, 동기화 안내)는 `announce(text, 'polite'|'assertive')` 로 보낸다. 화면의 문구는 role 없는 `<p>` 로 남긴다. `lib/a11y/announce.ts`(순수 큐)는 같은 문구가 1초 안에 다시 들어오면 무시하고, 빈 문자열을 거른 뒤 다시 채워 같은 문구도 다시 읽히게 한다.
- **R4 store 메시지는 store 가 소유:** `syncStore.notice`·`summary` 는 store 갱신 지점에서 한 번만 announce 한다. SyncPanel·data/sync 는 표시만 한다(유형 C·D 해소).
- **R5 live 안에 조작 요소 금지:** StreamStatus 의 중단 버튼을 live `<p>` 밖으로 뺀다. McpTokenCard:73·DegradedBanner 는 role 을 제거하고 announce 로 바꾼다. ActivityHeatmap 툴팁은 role 을 제거하고, 선택 결과는 셀의 이름(`aria-label`)으로 전달한다.
- **R6 남는 상시 live 는 둘뿐:** 진행 상태가 계속 바뀌는 영역(StreamStatus 단계, RecomputeSummary 진행률)만 상시 마운트된 `role=status` 를 유지한다.
- **R7 오류 긴급도(L6):** 사용자 동작(저장·전송·연결·재시도) 직후의 오류는 `announce(…, 'assertive')`, 성공·진행 안내는 polite. 첫 렌더의 로드 실패(ErrorState, RaceSummaryLine 등)는 live 없이 정적 텍스트로 둔다(제목 탐색으로 발견). 유형 G 의 alert/status 혼용은 이 기준으로 모두 role 제거 + announce 로 정리된다.
- Toast 는 role 대신 announce 를 쓴다(공통 §2.2 — 오류 assertive, 성공·정보 polite).

### 2.4 375px 레이아웃 규칙 (RC-L4)
- 기본은 한 열이다. 2열 이상은 (a) 비대화형 수치 타일이거나 (b) 칸이 44px 이상으로 측정된 경우만 허용한다.
- 페이지에는 가로 스크롤이 없어야 한다. 375px 에서 `documentElement.scrollWidth ≤ clientWidth` 를 검증한다. `overflow-x: clip` 같은 전역 은폐는 금지한다.
- 컴포넌트 내부 가로 스크롤(L5(b))은 **표·비교 캐러셀·칩 행·서브탭만** 허용한다. 조건: (1) 공용 유틸 `.scroll-x`(`overflow-x:auto` + 끝 가장자리 페이드 마스크로 "더 있음" 단서, 스크롤바 숨김 금지), (2) 버튼·링크만 담은 행(칩·서브탭)은 포커스 시 자동 스크롤되므로 추가 속성 없음, (3) 표·캐러셀처럼 포커스 요소가 없는 영역은 `role=region tabindex=0 aria-labelledby=표 제목`으로 키보드 스크롤을 가능하게 한다.
- 대화형 요소는 `.tap`(44px)을 쓴다. 칩 `h-9` 는 `h-11` 로, 확인 버튼·밑줄 버튼·coach 칩은 `.tap`/`.tap-area` 로 바꾼다.
- YearMonthScrubber 레일(L8(b)): 포인터 전용 가속기로 보고 44px 예외로 둔다. `role=slider`·`tabindex`·`aria-*` 를 제거하고 `aria-hidden="true"` 로 바꾼다. 같은 목적(특정 월 활동으로 이동)의 동등 수단은 ActivityFilters 월 칩(최근 12개월) + MonthHeader 이전/다음(전 기간 도달)이며, 둘 다 `.tap` 이어야 한다.
- 하단 시트에 공용 유틸 `.sheet-bottom`(`max-height: 85dvh` + `padding-bottom: env(safe-area-inset-bottom)`)을 적용한다. 5개 시트가 대상이다.
- 경계값 처리: WeekStrip 칸이 실측 44px 미만이면 `gap-1 → gap-0` 으로 칸을 넓힌다(구분은 칸 테두리). Library 탭이 줄바꿈하면 `flex-1` 을 버리고 `.scroll-x` 서브탭 패턴으로 바꾼다. 활동 상세 헤더는 `h-14` → `min-h-14` 로 바꿔 배지 행이 줄바꿈될 수 있게 한다.

### 2.5 coach/+page.svelte 분리 (RC-L3, 300줄 규칙)
이번 범위에서 이 파일도 h2 승격(2.2-2)·`.tap`(2.4)·오류 announce(R7)·PageHead(공통 A11Y-6) 대상이므로 **먼저 분리해 300줄 이하로 만든 뒤** 접근성 변경을 얹는다. 분리 경계는 마크업의 섹션 주석(`<!-- 최근 대화 섹션 -->`:118, `<!-- 새 대화 입력 폼 (토글) -->`:162, `<!-- 지금 답할 수 있는 질문 -->`:214, `<!-- 플랜 섹션 -->`:259, `<!-- QuickInput 체크인 섹션 -->`:285)과 일치한다(2026-10-12 grep).

| 신규 파일(`src/lib/components/coach/`) | 옮기는 범위(현 줄) | props / 소유 상태 | 예상 줄 수 |
|---|---|---|---|
| `CoachThreadList.svelte` | 118-160 + `titles` 파생(:24) + `formatRelativeTime`·`stripMarkdown`·`staleLabel`·`threadTitles` import | `threads`, `errorMessage` / 없음. "최근 대화" `<p>` → h2 | ~55 |
| `NewThreadForm.svelte` | 162-212 + `newInput`·`openNew`·`submitNew`·`handleKeydown`(:29·70-78·104-111) | `bind:open`(=`isCreating`, :215 게이트에 필요), `engine`, `sending`, `errorMessage`, `onSubmit(msg)`, `onOpenScope` / `newInput` | ~75 |
| `CoachStartChips.svelte` | 214-257(todos·chips 두 분기, 중복된 "준비 중/오류" 줄 1회로 통합) | `todos`, `limitNotice`, `chips`, `sending`, `errorMessage`, `onStart(input)` / 없음. 섹션 이름 h2 | ~50 |
| `CoachPlanCard.svelte` | 259-283 | `activePlan` / 없음. "플랜" h2 | ~30 |
| `CoachCheckin.svelte` | 285-304 + `checkin`·`savingCheckin`·`checkinError`·`handleSaveCheckin`(:55-68) | `initial`(CheckinRow\|null) / 체크인 상태 | ~45 |

- 남는 `coach/+page.svelte`: 스레드·엔진·동의(ScopeSheet)·`start()`·재시도 키(:21-53·80-102) 스크립트와 6개 컴포넌트 배치만 남아 **~115줄**. `data-testid`(`coach-small-data`, `home-chip`)는 옮긴 컴포넌트에 그대로 둔다.
- 순수 함수 추출: `existing={checkin ? {fatigue…timestamp} : undefined}` 매핑이 coach/+page:289-296 과 today/+page:122-124 에 복제돼 있다. `lib/checkinView.ts` `toQuickInputExisting(checkin)`(~12줄)로 옮겨 두 곳이 같이 쓴다(today 는 −2줄).
- 인접 파일 순증 금지: `coach/[threadId]/+page.svelte`(299)·`today/month/[ym]`(295)·`library/metrics`(291)는 이 설계에서 클래스 교체(`.tap`·`.scroll-x`)와 role 제거만 하므로 순증 0 이하. PageHead 적용(공통 5단계)도 기존 `<svelte:head>`+h1 을 대체해 순증 0 이하로 한다. 넘치면 같은 방식으로 먼저 분리한다.
- 동작 불변: 분리는 마크업·상태 이동만이며 `start()` 흐름(동의 → ScopeSheet → 재시도 id 유지)은 페이지에 남긴다. 분리 커밋과 접근성 변경 커밋을 나눈다.

## 3. 변경 파일
### 3.1 발견 → 수정 항목 대응표
모든 발견(1절)은 수정 대상이다. 검증 열의 "가드"는 `a11yLayout.test.mjs`(4절 1단계) 검사 기호, "SR"은 4절 스크린리더 체크리스트.

| ID | 발견 | 변경 파일 | 방법 | 검증 |
|---|---|---|---|---|
| F-1 | 주 nav 한 노드가 하단 탭·사이드바 겸함 | +layout.svelte, shell/ShellNav.svelte(신규), shell/navTabs.ts(신규) | ShellNav variant side/bottom 이중 렌더(2.1) | navTabs.test, 가드 (e), 스니펫: 375·1280 각각 주 메뉴 nav 1개·위치 |
| F-2 | skip link·main id 없음 | +layout.svelte | skip link, `main#main tabindex=-1` | 가드 (e), 첫 Tab·Enter 후 activeElement=main |
| F-3 | 하단 탭 높이 매직 넘버 3곳 | layout.css, +layout, Toast, YearMonthScrubber | `--shell-bottom` | grep `pb-20\|bottom-20` 3파일 0건, iOS safe-area 화면 확인 |
| F-4 | 유형 A group+live(OVL-1 원안 4곳) | overlay.ts, CalendarFeedCard, McpTokenCard, ConnectPanel, BaselineRow | R1·L1: live 없이 group+labelledby+"취소" 포커스 | 가드 (g), SR "확인 문구 1회" |
| F-5 | 유형 B ChartScrub 값 이중 읽기 | ChartScrub, ActivityTimeline, TrendChart, FormChart, Sparkline | R2 valuetext, ActivityTimeline live 제거 | chart-scrub.test 에 valueText 케이스, SR "값 1회" |
| F-6 | 유형 C syncStore.notice 두 영역 | syncStore.svelte.ts, SyncPanel, data/sync/+page | R4 store 가 1회 announce, 두 화면은 표시만 | announce.test(중복 억제), SR "/data/sync 안내 1회" |
| F-7 | 유형 D role+aria-live 중복 | SyncPanel:82 | R4 로 role 자체 제거 | 가드 (a) |
| F-8 | 유형 E live 안 조작 요소 4곳 | StreamStatus, McpTokenCard, DegradedBanner, ActivityHeatmap | R5 | 가드 (c), SR "중단 반복 낭독 없음" |
| F-9 | 유형 F `{#if}` 안 role=status/alert 약 20곳 | 1절 F 행 파일 약 15개 | R3 role 제거 + announce | 가드 (b) baseline 0 |
| F-10 | 유형 G alert/status 혼용, 첫 렌더 alert | RowActionSheet, AdjustmentCard, import, AutoSyncRow, BaselineRow, sources/[provider], ErrorState, RaceSummaryLine | R7(L6) | 가드 (b)·(h), SR "Today 로드 실패 겹침 없음" |
| F-11 | h1 세 갈래, TodayHero `{#if view}` 안 h1 | TodayHero, 각 라우트(PageHead 는 공통 문서) | 2.2-1, TodayHero view 없을 때도 h1 | todayHero.test 에 view=null 시 제목 문자열 케이스, 스니펫 h1=1(로드·빈·오류) |
| F-12 | 평평한 제목·`<p uppercase>` 섹션 | today/+page, library/[id]/+page, coach 분리 컴포넌트 | 2.2-2 h2 승격(클래스 유지) | 가드 (i), SR 제목 목록 |
| F-13 | 보조 nav 이름 형식 제각각 | SubTabs, data/+layout, library/+layout, library/[id]/+layout | L9 `"<영역> 하위 메뉴"`, 경로 "경로" 유지 | 스니펫: nav 이름 목록 |
| F-14 | 대화상자 10개 aria-label 만, 3개 제목 없음 | 1절 대화상자 10개, DrillPanel(lg aside) | 2.2-3 `aria-labelledby`→h2, 3개는 sr-only h2(L3) | 가드 (f) |
| F-15 | Today `order-*` 로 Tab 1·4·2·3 | today/+page.svelte | L4(b) `contents`·`order-*` 제거(~−3줄) | 가드 (d), SR "낭독 순서=화면 순서", 375 스크린샷(다음 세션이 2번째) |
| F-16 | coach/+page 310줄, 인접 3파일 | coach/+page + 신규 5개, lib/checkinView.ts, today/+page | 2.5 분리, 인접 순증 금지 | `fileSize.test.mjs`, checkinView.test, coach 수동: 칩 전송·새 대화·동의 시트·체크인 저장 |
| F-17 | 44px 미달(☰, 칩 h-9, 확인·토큰·밑줄 버튼, coach 칩) | +layout(☰→IconButton), RowActionSheet, CalendarFeedCard, McpTokenCard, ConnectPanel, coach 컴포넌트, coach/[threadId] | `.tap`/`.tap-area`/`h-11`(2.4) | 스니펫 bbox ≥44 |
| F-18 | YearMonthScrubber 20px + 키 없는 slider | YearMonthScrubber, MonthHeader·ActivityFilters(크기만) | L8(b) aria-hidden 가속기, 동등 수단 `.tap` | 가드 (j) role=slider 는 keydown 필수, Tab 이 레일에 멈추지 않음 |
| F-19 | 경계값(WeekStrip·Library 탭·활동 상세 h-14) | WeekStrip, library/+layout, library/[id]/+layout | 2.4 경계값 처리(실측 후 조건부) | 375 실측 기록 |
| F-20 | 컴포넌트 가로 스크롤 | layout.css, SubTabs, library/metrics, ScenarioCompareTable, ProviderMatrix, LapTable, ProviderComparison, ActivityHeatmap | L5(b) `.scroll-x` + 표 region | 스니펫 scrollWidth, 키보드로 표 스크롤 |
| F-21 | 시트 vh·safe-area 없음 5개 | ScopeSheet, EngineSheet, MilestonesPanel, MetricBreakdown, RowActionSheet | `.sheet-bottom` | iOS Safari 툴바 변동·홈 인디케이터 화면 확인 |

### 3.2 변경 파일 표 (`frontend/` 기준, 줄 수 추정)
| 파일 | 구분 | 줄 수 | 내용 |
|---|---|---|---|
| src/routes/+layout.svelte | 수정 | 80→~75 | skip link, main id, ShellNav 2회, LiveRegion |
| src/lib/components/shell/ShellNav.svelte | 신규 | ~45 | variant side/bottom |
| src/lib/shell/navTabs.ts | 신규 | ~20 | 탭 정의·isActive(순수) |
| src/lib/a11y/announce.ts, components/shell/LiveRegion.svelte | 신규 | ~50, ~25 | 큐·중복 억제, 상시 영역 2개 |
| src/routes/layout.css | 수정 | +18 | `--shell-bottom`, `.sheet-bottom`, `.scroll-x` |
| tests/navTabs.test.mjs, tests/announce.test.mjs | 신규 | ~25, ~50 | 순수 함수 |
| tests/a11yLayout.test.mjs + a11yLayoutBaseline.json | 신규 | ~120 + 목록 | 4절 정적 가드(ratchet) |
| tests/fileSize.test.mjs | 신규 | ~30 | `src/**/*.{svelte,ts}` 300줄 상한, 기존 초과(`lib/types/index.ts`)는 baseline 줄 수 이하(ratchet) |
| CalendarFeedCard, McpTokenCard, ConnectPanel, BaselineRow | 수정 | 각 ±5~10 | 인라인 확인 R1(OVL `inlineConfirm` 적용과 같은 커밋) |
| src/lib/overlay.ts(OVL 신규 예정) | 수정 | ±5 | inlineConfirm 에 live 없음(L1) |
| ChartScrub, ActivityTimeline, TrendChart, FormChart, Sparkline | 수정 | 각 ±2~5 | valuetext, live 제거 |
| SyncPanel, data/sync/+page, syncStore | 수정 | 각 ±2~6 | R4 |
| StreamStatus, DegradedBanner, ActivityHeatmap, Toast | 수정 | 각 ±2~8 | R5·Toast announce |
| 조건부·혼용 role 사용처 약 15파일 | 수정 | 각 ±1~3 | role 제거 + announce(R3·R7) |
| today/+page.svelte | 수정 | 178→~174 | L4(b) order 제거, 섹션 h2, checkinView 사용 |
| src/routes/coach/+page.svelte | 수정(분리) | 310→~115 | 2.5 |
| src/lib/components/coach/CoachThreadList, NewThreadForm, CoachStartChips, CoachPlanCard, CoachCheckin (.svelte) | 신규 | ~55, ~75, ~50, ~30, ~45 | 2.5 |
| src/lib/checkinView.ts, tests/checkinView.test.mjs | 신규 | ~12, ~25 | `toQuickInputExisting` |
| library/[id]/+page.svelte, 시트 5개, RowActionSheet, YearMonthScrubber, MonthHeader, Toast | 수정 | 각 ±1~5 | h2 승격, `.sheet-bottom`, `h-11`, `--shell-bottom`, 레일 aria-hidden |
| SubTabs, library/metrics, ScenarioCompareTable, ProviderMatrix, LapTable, ProviderComparison | 수정 | 각 ±0~3 | `.scroll-x`, 표 region |
| 대화상자 10개, 보조 nav 4곳 | 수정 | 각 ±1~3 | labelledby·sr-only h2, nav 이름 |
| WeekStrip, library/+layout, library/[id]/+layout | 수정(조건부) | 각 ±1 | 경계값 처리 |
| DrillPanel | 수정 | ±3 | lg `aside` |
페이지 300줄 규칙: coach/+page 는 2.5 로 해소한다. `coach/[threadId]`(299)·`today/month/[ym]`(295)·`library/metrics`(291)는 순증 0 이하이며 `fileSize.test.mjs` 가 상한을 강제한다.

## 4. 단계·검증
1. **가드 먼저:** `a11yLayout.test.mjs`·`fileSize.test.mjs` 를 추가하고 현재 위반을 baseline 에 넣는다. 검사 항목: (a) `role=status|alert` 와 `aria-live` 동시 사용, (b) `{#if}` 직하 `role=status|alert`, (c) live 요소 안의 `<button|<a|<input`, (d) 라우트 `order-\d`·`-reverse`, (e) `+layout.svelte` 에서 skip link < header < lg nav < main 순서, (f) `role="dialog"` 에 `aria-labelledby` 없음, (g) `role="group"` 요소 안의 `aria-live`/`role=status|alert`, (h) `role="alert"` 사용(상시 영역 외 0 목표), (i) `<p class="…uppercase…">` 단독 섹션 이름, (j) `role="slider"` 인데 `onkeydown` 없음. 이 단계에서 동작 변화는 없다.
2. **coach 분리(2.5):** 동작 불변 커밋. `fileSize` baseline 에서 coach/+page 를 뺀다.
3. **announce + LiveRegion:** 유형 C·D·E·F·G 를 이전하고 baseline 을 줄인다.
4. **R1·R2:** overlay 구현과 함께 인라인 확인을 바꾼다(L1). ChartScrub valuetext 를 넣는다.
5. **셸:** ShellNav 이중 렌더, skip link, `--shell-bottom`.
6. **골격:** PageHead 적용(공통 5단계)과 함께 h2 승격, dialog labelledby, nav 이름, Today 순서(L4)를 반영한다.
7. **375px:** `.tap`·`.sheet-bottom`·`.scroll-x`·스크러버 예외를 적용하고 경계값을 실측해 조건부 항목을 처리한다.

검증
- `npm run test:unit`, `npm run check`(svelte-check a11y 경고 수가 단계마다 줄거나 같아야 함), `python3 -m pytest tests/`(백엔드 무변경 확인).
- axe: 브라우저 확장으로 주요 라우트 × 375/1280 × 다크/라이트를 수동 점검한다(L7(a), CI 자동화 없음).
- 브라우저 스니펫: 전 라우트(`/demo` 포함)에서 375px 기준으로 `scrollWidth ≤ clientWidth`, h1 1개, nav 랜드마크(주 메뉴) 1개, 대화형 bbox ≥44px(인라인 링크·차트 점·스크러버 레일 예외)를 확인한다. 1280px 에서는 Tab 순서가 skip → ☰ → 동기화 Pill → 주 메뉴 → 본문인지 본다.
- 수동 스크린리더 체크리스트(VoiceOver iOS Safari, NVDA Chrome):
  - □ 첫 스와이프/Tab 이 "본문 바로가기"이고, 실행하면 main 으로 이동
  - □ 랜드마크 목록: 모바일은 main 다음 주 메뉴, 1280px 은 main 앞
  - □ 제목 목록이 h1 1개에서 h2·h3 순으로 건너뜀 없음
  - □ 연결 해제 확인 문구가 1회만 읽힘(그룹 이름 + "취소")
  - □ 스크럽 ←/→ 한 번에 값이 1회만 읽힘
  - □ /data/sync 에서 패널을 열고 동기화하면 안내가 1회만 읽힘
  - □ 오류 토스트·동작 오류는 즉시, 성공 토스트는 현재 낭독 뒤에 읽힘. Today 로드 실패가 여럿이어도 assertive 가 겹치지 않음
  - □ 스트림 진행 중 "중단" 이 단계 문구와 함께 반복 낭독되지 않음
  - □ Today 낭독 순서가 화면 순서와 같음
  - □ 활동 목록에서 Tab 이 스크러버 레일에 멈추지 않고, 월 칩·MonthHeader 로 원하는 월에 도달

## 5. 결정 완료 (에이전트 위임 2026-10-12)
사용자 지시(2026-10-12)로 마이너 결정을 에이전트에 위임했다. decisions-table 기록은 메인이 한다.
- **A11Y-L1 인라인 확인의 알림 경로 — 결정 완료(에이전트 위임 2026-10-12): (a) live 제거, group 이름 + "취소" 포커스만.** 근거: 포커스 이동이 그룹 이름(확인 문구)을 이미 1회 읽게 하므로 live 는 순수 중복이고, (b)는 라벨 추가 낭독, (c)는 OVL-2 와 충돌. OVL-1 문구를 이에 맞춰 수정(overlay §2.3·§7).
- **A11Y-L2 서브탭과 h1 의 위치 — 결정 완료(에이전트 위임 2026-10-12): (a) 현행 유지(탭이 h1 위).** 근거: 서브탭은 이름 있는 nav 랜드마크라 건너뛰기·제목 탐색이 가능하고, (b)는 h1 을 하위 레이아웃으로 끌어올리는 구조 변경과 Data·Library 시각 변화가 따른다.
- **A11Y-L3 이름 없는 섹션·시트의 제목 — 결정 완료(에이전트 위임 2026-10-12): (b) sr-only h2 + `aria-labelledby`.** 근거: 대화상자 이름·제목 탐색은 확보하면서 시각 변화가 없고, 시트는 내용 자체가 시각 맥락을 준다(보이는 h1 원칙 A11Y-6 은 페이지 단위). 문구는 TXT-1.
- **A11Y-L4 Today 순서 — 결정 완료(에이전트 위임 2026-10-12): (b) 모바일 표시 순서를 DOM 순서로(다음 세션이 2번째).** 근거: lg 2열의 열 단위 읽기 순서가 현 DOM 과 이미 같아 두 해상도가 함께 맞는 유일한 안이며, (a)는 lg 에서 다시 grid 배치와 DOM 이 어긋난다. 모바일 우선순위 변화는 375 스크린샷으로 확인.
- **A11Y-L5 컴포넌트 가로 스크롤 — 결정 완료(에이전트 위임 2026-10-12): (b) 표·비교 캐러셀·칩 행·서브탭 허용, 스크롤 단서 필수, 숨긴 스크롤바 대체.** 근거: 표는 2차원 배치가 본질이고 칩·탭 행은 포커스 시 자동 스크롤되어 키보드 접근이 되며, (a)는 375 에서 칩 행 높이가 커져 목록이 밀린다.
- **A11Y-L6 인라인 오류의 긴급도 — 결정 완료(에이전트 위임 2026-10-12): (a) 사용자 동작 직후 오류는 assertive, 그 밖은 polite, 첫 렌더 로드 실패는 live 없음.** 근거: 결과를 기다리는 사용자에게만 즉시성이 필요하고(A11Y-5 오류 토스트와 일관), Today 의 다중 로드 실패 assertive 겹침(유형 G)이 사라진다.
- **A11Y-L7 axe 자동화 — 결정 완료(에이전트 위임 2026-10-12): (a) 수동(브라우저 확장)만.** 근거: package.json 에 브라우저 테스트 도구가 없고, 회귀는 정적 가드(ratchet)로 막으며, 공통 문서도 axe+Playwright 를 A안 완료 후 보강(B안)으로 두었다.
- **A11Y-L8 YearMonthScrubber 레일 — 결정 완료(에이전트 위임 2026-10-12): (b) 포인터 전용 가속기로 예외, `aria-hidden`, 동등 수단 확인.** 근거: 월 칩(12개월)+MonthHeader 이전/다음이 전 기간 도달을 제공해 WCAG 2.5.8 동등 컨트롤 예외에 해당하고, (a)는 목록 가림, (c)는 긴 목록 탐색 손실.
- **A11Y-L9 보조 nav 이름 형식 — 결정 완료(에이전트 위임 2026-10-12): (a) "<영역> 하위 메뉴" 통일, 단 경로 nav 는 이미 통일된 "경로" 유지.** 근거: 랜드마크 목록에서 영역 구분이 이름에만 의존하고, 경로 3곳은 이미 같은 이름이라 바꿀 이득이 없다. 실제 이름 문자열은 형식에서 기계적으로 나온다(TXT-1 불필요).

## 6. 범위 밖 메모
- 토큰 대비·라이트 테마·theme-color·PageHead·`.tap` 정의는 `accessibility-common.md` 소관이다. 이 문서는 그 위에서의 배치 규칙만 다룬다.
- 공통 §2.2 Toast 는 R3·R7 의 announce 로 대체(2026-10-12 공통 문서 동기화 완료).
- OVL `overlay.ts` 는 아직 없다(신규 예정). R1 은 그 구현과 같은 커밋에서 들어가야 한다.
- 칩 그룹(ToggleGroup) 키보드 패턴, 차트 텍스트 요약(M-26), ActivityMoreMenu 메뉴 패턴은 다른 설계 소관이다.
- 375px 후보 수치(WeekStrip 45px, 탭 62px)는 클래스로 추정한 값이라 브라우저 실측 전이다. 스크린리더 실기기 동작(유형 A·F)도 미검증이다.
- TXT-1 대상(문구 미확정): sr-only h2 4개(RowActionSheet·GarminCleanup·DemoBanner·Today 준비도 섹션), skip link 문구("본문 바로가기" 후보).
