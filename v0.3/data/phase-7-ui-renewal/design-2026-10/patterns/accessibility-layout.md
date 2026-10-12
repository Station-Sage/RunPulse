# 설계: 접근성 레이아웃 (셸·랜드마크·제목 위계·live region·375px) — A11Y-7/A11Y-15

- 상태: 설계 초안(2026-10-11). 결정 필요 A11Y-L1~L9. 코드 변경 없음
- 전제: `accessibility-common.md`(44px `.tap`, PageHead 보이는 h1, 포커스 링 2px, s3 하한, 라이트 테마), `overlay-common-behavior.md`(OVL-1~7)
- 근거: 2026-10-11 `frontend/src` grep 결과. 줄 번호는 이 날짜 기준

## 1. 근본 원인
**RC-L1. 주 내비가 한 DOM 노드로 두 위치를 맡음.** `routes/+layout.svelte:41-78` 은 `header → MenuDrawer → main → nav` 순서다. nav 하나가 모바일 하단 탭(`fixed bottom-0`)과 1280px 좌측 사이드바(`lg:inset-y-0 lg:w-52`)를 CSS 로만 바꿔 그린다. 그래서 A11Y-7(lg 만 본문 앞)은 CSS 로 풀 수 없다. skip link 와 `main` id 도 없다. 하단 탭 높이는 매직 넘버로 세 곳에 복제돼 있다: `main pb-20`(:58), `Toast bottom-20`(Toast.svelte:27), `YearMonthScrubber bottom-20`(:50).

**RC-L2. 알림 경로(live region)의 소유자가 정해져 있지 않음.** 메시지마다 그 메시지를 그리는 컴포넌트가 제각각 role 을 단다. 확인된 문제는 아래와 같다.

| 유형 | 위치 | 문제 |
|---|---|---|
| A. group+live(설계상) | OVL-1 `inlineConfirm`(overlay §2.3) → CalendarFeedCard:78, McpTokenCard:90, ConnectPanel:121(현재 `alertdialog`), BaselineRow:129(`role=alert`+버튼) | 확인 문구가 그룹 이름(`aria-labelledby`)이고 같은 문구가 live 로도 나간다. OVL-2 로 "취소"에 포커스가 가면 그룹 이름과 live 가 같은 문구를 두 번 읽는다(overlay §9) |
| B. 포커스 컨트롤 + live 복제 | ChartScrub:85-90(`role=slider`, valuetext 없음) + ActivityTimeline:81 `aria-live` | 키를 누를 때마다 슬라이더 값(인덱스 숫자)과 live 의 "x.xx km"를 연달아 읽는다 |
| C. 같은 문구를 두 영역에 출력 | `syncStore.notice`: SyncPanel:82-87(`role=status`) + data/sync/+page:93(`role=status`) | /data/sync 에서 패널을 열면 같은 안내가 두 영역에 나온다 |
| D. 중복 속성 | SyncPanel:82 `role="status" aria-live="polite"` | status 에 polite 가 이미 포함돼 있다 |
| E. live 안에 조작 요소 | StreamStatus:28(중단 버튼), McpTokenCard:73(입력·복사·닫기), ActivityHeatmap:75(툴팁 안 링크, hover 로 열림), DegradedBanner:14(링크) | 알림을 읽을 때 버튼·링크 이름까지 함께 읽는다 |
| F. 조건부 생성 live | `{#if}` 안의 `role=status/alert` 약 20곳(CalendarFeedCard:99, McpTokenCard:63·107, ConnectPanel:130, AutoSyncRow:69, BaselineRow:140, RecomputeSummary:37-41, data/export:96, settings/ai:106, sources/[provider]:83·87, import:127·151, Toast:28 등) | 영역이 내용과 동시에 생겨 읽히지 않거나 읽히는 시점이 들쭉날쭉할 수 있다(실기기 미확인) |
| G. 역할 혼용 | 같은 종류의 인라인 오류가 alert(RowActionSheet:211, AdjustmentCard:111, import:151)와 status(AutoSyncRow:69, BaselineRow:140, sources/[provider]:87)로 나뉨. 로드 실패 `role=alert` 가 첫 렌더에 나옴(ErrorState:23, RaceSummaryLine:15) | Today 처럼 로드 실패가 여럿이면 assertive 알림이 겹친다 |

참고: `role=group` 은 13곳(RowActionSheet 5, ActivityFilters 4, WellnessDateBar, providers, streams, story)이다. 이 중 group 안에 live 가 함께 있는 곳은 현재 없다. RowActionSheet:206 의 live 미리보기는 group 밖에 있고, 내용도 칩의 상태와 다르다(km 변화).

**RC-L3. 페이지 골격(제목·섹션·순서)을 정하는 곳이 없음.**
- h1 을 그리는 곳이 세 갈래로 나뉜다: 페이지 파일 16(landing 포함)·`+error` 2, 하위 레이아웃 1(`library/[id]/+layout.svelte:52`, sticky header 안), 컴포넌트 4(TodayHero:37 `{#if view}` 안, ColdStartProgress:13, WellnessDateBar:26, Step0Intro:7). 셸 헤더의 앱 이름은 `<span>`(:52)이다.
- 컴포넌트 제목은 평평하다: h2 를 쓰는 파일 20개, h3 는 1개(RecomputeSummary), h4 는 없다. 섹션 이름을 `<p class="uppercase">` 로 흉내 내는 곳이 있다(today/+page:155·168, library/[id]/+page:140).
- nav 랜드마크가 7종인데 이름 짓는 방식이 다르다: "주 메뉴", "하위 메뉴"(SubTabs, Data), "Library 섹션", "활동 상세 탭", "경로"×3.
- 대화상자 10개 모두 `aria-label` 을 쓰고 `aria-labelledby` 는 0곳이다. 7개는 h2 가 있고, RowActionSheet·GarminCleanup·DemoBanner 는 제목이 없다.
- 시각 순서와 DOM 순서가 다르다: today/+page:106-167 이 `contents` + `order-1/4/2/3/5` 를 쓴다. 모바일 화면은 1·2·3·4 순서로 보이지만 DOM 과 Tab 순서는 1·4·2·3 이다. `order-*` 를 쓰는 곳은 여기뿐이다.

**RC-L4. 375px 레이아웃 기준이 없음(후보, 브라우저 측정 전).**
- 44px 미달: 셸 ☰ `p-1.5`+`h-5`=32px(+layout:44-49), YearMonthScrubber 레일 `w-5`=20px(:50), 통증 부위 칩 `h-9`(RowActionSheet:199), 확인·토큰 버튼 `px-3 py-1.5 text-xs`(CalendarFeedCard:85·89, McpTokenCard:66·77-78, ConnectPanel:124), 밑줄 텍스트 버튼(ConnectPanel:113-115, McpTokenCard:91-95).
- 경계값: WeekStrip `grid-cols-7 gap-1`(:28) 칸은 약 45px 로 추정한다. Library 탭 6개 `flex-1`(library/+layout:24) 은 칸당 약 62px 로, "소스 비교" 줄바꿈 여부를 실측해야 한다. 활동 상세 헤더는 `h-14` 고정 높이 안에 `truncate` h1 과 배지 행이 들어간다(library/[id]/+layout:43).
- 컴포넌트 단위 가로 스크롤: SubTabs:15(스크롤바 숨김), library/metrics:202·225 칩 행, ScenarioCompareTable:22 스냅 캐러셀, ProviderMatrix:24·LapTable:68·ProviderComparison:103 표, ActivityHeatmap:45.
- 시트: `max-h-[70~85vh]` 는 iOS 툴바 변동을 반영하지 않는다. 하단 safe-area 가 없는 시트: ScopeSheet:48, EngineSheet:17, MilestonesPanel:49, MetricBreakdown:60, RowActionSheet:125.

## 2. 설계안
### 2.1 공통 셸 규칙 (RC-L1, A11Y-7)
- DOM 순서는 `skip link → ProgressBar/DemoBanner → header(banner) → [lg] nav 주 메뉴 → main#main[tabindex=-1] → [<lg] nav 주 메뉴` 로 둔다. MenuDrawer 는 overlay 설계대로 현재 위치를 유지한다(OVL-3).
- `ShellNav.svelte`(신규)를 `variant="side"`(`hidden lg:flex`)와 `variant="bottom"`(`lg:hidden`)으로 **두 번 렌더**한다. `display:none` 이 걸린 쪽은 접근성 트리와 Tab 순서에서 빠지므로 한 해상도에는 nav 가 하나만 남는다. 이 방식은 SSR 에서도 안전하고 깜빡임이 없다. JS `matchMedia` 로 노드를 옮기는 방식은 하이드레이션 불일치 때문에 기각했다.
- 탭 정의와 `isActive` 는 `lib/shell/navTabs.ts`(순수)로 옮긴다. `data-testid` 는 variant 접미사를 붙여 중복을 피한다.
- `layout.css` 에 `--shell-bottom`(하단 탭 높이 + safe-area, lg 에서 0)을 둔다. `main` 패딩, Toast, YearMonthScrubber 는 이 변수만 참조한다.
- 1280px 에서 DrillPanel 인라인 패널(`lg:grid-cols-[1fr_420px]`, DrillPanel:124)은 `<aside aria-labelledby=패널 h2>` 로 바꾼다. 모바일 시트 쪽은 OVL `use:modal` 을 그대로 쓴다.

### 2.2 페이지 골격·랜드마크·제목 규칙 (RC-L3)
1. 라우트의 **모든 상태(로드·빈·오류 분기 포함)에서 h1 이 정확히 1개**다. h1 은 PageHead(공통 §2.3) 또는 문서화된 예외 컴포넌트(TodayHero·ColdStartProgress·WellnessDateBar·활동 상세 레이아웃)만 그린다. TodayHero 의 `view` 가 없을 때도 h1 을 출력한다.
2. 위계는 h1(페이지) → h2(섹션·카드 그룹: `<section aria-labelledby>`) → h3(카드 내부)로 둔다. `<p uppercase>` 로 흉내 낸 섹션 이름은 같은 클래스의 h2 로 바꾼다. 시각 변화는 없다.
3. 대화상자와 시트는 `aria-labelledby` 로 자기 h2 를 가리킨다. 제목이 없는 3개는 L3 결정을 따른다.
4. 랜드마크는 banner 1, main 1, 주 nav 1(해상도당), 보조 nav(서브탭·경로)로 둔다. 보조 nav 이름 형식은 L9. 셸 header 의 앱 이름은 제목 요소로 만들지 않는다(h1 은 페이지 몫).
5. 시각 순서와 DOM 순서를 일치시킨다. 라우트에서 `order-*`·`*-reverse` 를 금지하고 정적 가드로 검사한다. Today 처리는 L4.

### 2.3 live region 단일 소유 규칙 (RC-L2, A11Y-15)
- **R1 단일 채널:** 한 메시지는 한 경로로만 알린다. 포커스 이동이 이미 이름·상태를 읽게 한다면 live 를 쓰지 않는다. 인라인 확인(유형 A)은 `group + aria-labelledby(확인 문구)` 와 "취소" 포커스만 쓰고 live 를 쓰지 않는다. 이 설계안은 OVL-1 문구를 바꾸므로 L1 에서 결정한다. BaselineRow:129 도 같은 패턴으로 바꾼다.
- **R2 포커스 컨트롤 상태는 컨트롤이 말한다:** ChartScrub 에 `valueText(index)` prop 을 추가해 `aria-valuetext` 로 출력하고, ActivityTimeline:81 의 live 는 제거한다. 화면 표시는 그대로 둔다. TrendChart·FormChart·Sparkline 도 같은 prop 으로 값을 넘긴다.
- **R3 상시 영역 + 발신 함수:** `+layout.svelte` 에 sr-only `LiveRegion.svelte` 를 처음부터 빈 상태로 1회 마운트한다(polite·assertive 2개). 일회성 메시지(저장 결과, 토스트, 인라인 오류, 동기화 안내)는 `announce(text, 'polite'|'assertive')` 로 보낸다. 화면의 문구는 role 없는 `<p>` 로 남긴다. `lib/a11y/announce.ts`(순수 큐)는 같은 문구가 1초 안에 다시 들어오면 무시하고, 빈 문자열을 거른 뒤 다시 채워 같은 문구도 다시 읽히게 한다.
- **R4 store 메시지는 store 가 소유:** `syncStore.notice`·`summary` 는 store 갱신 지점에서 한 번만 announce 한다. SyncPanel·data/sync 는 표시만 한다(유형 C·D 해소).
- **R5 live 안에 조작 요소 금지:** StreamStatus 의 중단 버튼을 live `<p>` 밖으로 뺀다. McpTokenCard:73·DegradedBanner 는 role 을 제거하고 announce 로 바꾼다. ActivityHeatmap 툴팁은 role 을 제거하고, 선택 결과는 셀의 이름(`aria-label`)으로 전달한다.
- **R6 남는 상시 live 는 둘뿐:** 진행 상태가 계속 바뀌는 영역(StreamStatus 단계, RecomputeSummary 진행률)만 상시 마운트된 `role=status` 를 유지한다. 오류 role 의 기준(유형 G)은 L6 에서 정한다.
- Toast 는 role 대신 announce 를 쓴다(공통 §2.2 의 status/alert 의미를 politeness 로 대응).

### 2.4 375px 레이아웃 규칙 (RC-L4)
- 기본은 한 열이다. 2열 이상은 (a) 비대화형 수치 타일이거나 (b) 칸이 44px 이상으로 측정된 경우만 허용한다(WeekStrip 은 측정 대상).
- 페이지에는 가로 스크롤이 없어야 한다. 375px 에서 `documentElement.scrollWidth ≤ clientWidth` 를 검증한다. `overflow-x: clip` 같은 전역 은폐는 금지한다. 컴포넌트 내부 스크롤의 허용 범위는 L5.
- 대화형 요소는 `.tap`(44px)을 쓴다. 칩 `h-9` 는 `h-11` 로, 확인 버튼·밑줄 버튼은 `.tap`/`.tap-area` 로 바꾼다. 스크러버 레일은 L8.
- 하단 시트에 공용 유틸 `.sheet-bottom`(`max-height: 85dvh` + `padding-bottom: env(safe-area-inset-bottom)`)을 적용한다. 5개 시트가 대상이다.

## 3. 변경 파일 표 (`frontend/` 기준, 줄 수 추정)
| 파일 | 구분 | 줄 수 | 내용 |
|---|---|---|---|
| src/routes/+layout.svelte | 수정 | 80→~75 | skip link, main id, ShellNav 2회, LiveRegion |
| src/lib/components/shell/ShellNav.svelte | 신규 | ~45 | variant side/bottom |
| src/lib/shell/navTabs.ts | 신규 | ~20 | 탭 정의·isActive(순수) |
| src/lib/a11y/announce.ts, components/shell/LiveRegion.svelte | 신규 | ~50, ~25 | 큐·중복 억제, 상시 영역 2개 |
| src/routes/layout.css | 수정 | +12 | `--shell-bottom`, `.sheet-bottom` |
| tests/navTabs.test.mjs, tests/announce.test.mjs | 신규 | ~25, ~50 | 순수 함수 |
| tests/a11yLayout.test.mjs + a11yLayoutBaseline.json | 신규 | ~100 + 목록 | 2.5 정적 가드(ratchet) |
| CalendarFeedCard, McpTokenCard, ConnectPanel, BaselineRow | 수정 | 각 ±5~10 | 인라인 확인 R1(OVL `inlineConfirm` 적용과 같은 커밋) |
| src/lib/overlay.ts(OVL 신규 예정) | 수정 | ±5 | inlineConfirm 에서 live 제거(L1) |
| ChartScrub, ActivityTimeline, TrendChart, FormChart, Sparkline | 수정 | 각 ±2~5 | valuetext, live 제거 |
| SyncPanel, data/sync/+page, syncStore | 수정 | 각 ±2~6 | R4 |
| StreamStatus, DegradedBanner, ActivityHeatmap, Toast | 수정 | 각 ±2~8 | R5·Toast announce |
| 조건부 role 사용처 약 15파일 | 수정 | 각 ±1~3 | role 제거 + announce |
| today/+page.svelte | 수정 | 178→~180 | L4 결과, 섹션 h2 |
| library/[id]/+page.svelte, 시트 5개, RowActionSheet, YearMonthScrubber, Toast | 수정 | 각 ±1~3 | h2 승격, `.sheet-bottom`, `h-11`, `--shell-bottom` |
| DrillPanel | 수정 | ±3 | lg `aside` |
페이지 300줄 규칙: `coach/+page.svelte` 는 이미 310줄이다. 이 설계는 이 파일을 건드리지 않으며, 수정이 필요해지면 먼저 분리한다. `library/metrics/+page.svelte`(291)·`today/month/[ym]`(295)은 순증이 없게 한다(role 제거 위주).

## 4. 단계·검증
1. **가드 먼저:** `a11yLayout.test.mjs` 를 추가하고 현재 위반을 baseline 에 넣는다. 검사 항목: (a) `role=status|alert` 와 `aria-live` 동시 사용, (b) `{#if}` 직하 `role=status|alert`, (c) live 요소 안의 `<button|<a|<input`, (d) 라우트 `order-\d`·`-reverse`, (e) `+layout.svelte` 에서 skip link < header < lg nav < main 순서, (f) `role="dialog"` 에 `aria-labelledby` 없음. 이 단계에서 동작 변화는 없다.
2. **announce + LiveRegion:** 유형 C·D·E·F 를 이전하고 baseline 을 줄인다.
3. **R1·R2:** L1 결정 후 overlay 구현과 함께 인라인 확인을 바꾼다. ChartScrub valuetext 를 넣는다.
4. **셸:** ShellNav 이중 렌더, skip link, `--shell-bottom`.
5. **골격:** PageHead 적용(공통 5단계)과 함께 h2 승격, dialog labelledby, Today 순서(L4)를 반영한다.
6. **375px:** `.tap`·`.sheet-bottom` 을 적용하고 측정 후보를 확인한다.

검증
- `npm run test:unit`, `npm run check`(svelte-check a11y 경고 수가 단계마다 줄거나 같아야 함), `python3 -m pytest tests/`(백엔드 무변경 확인).
- axe: 브라우저 확장으로 주요 라우트 × 375/1280 × 다크/라이트를 점검한다. 자동화 여부는 L7.
- 브라우저 스니펫: 전 라우트(`/demo` 포함)에서 375px 기준으로 `scrollWidth ≤ clientWidth`, h1 1개, nav 랜드마크(주 메뉴) 1개, 대화형 bbox ≥44px 를 확인한다. 1280px 에서는 Tab 순서가 skip → ☰ → 동기화 Pill → 주 메뉴 → 본문인지 본다.
- 수동 스크린리더 체크리스트(VoiceOver iOS Safari, NVDA Chrome):
  - □ 첫 스와이프/Tab 이 "본문 바로가기"이고, 실행하면 main 으로 이동
  - □ 랜드마크 목록: 모바일은 main 다음 주 메뉴, 1280px 은 main 앞
  - □ 제목 목록이 h1 1개에서 h2·h3 순으로 건너뜀 없음
  - □ 연결 해제 확인 문구가 1회만 읽힘
  - □ 스크럽 ←/→ 한 번에 값이 1회만 읽힘
  - □ /data/sync 에서 패널을 열고 동기화하면 안내가 1회만 읽힘
  - □ 오류 토스트는 즉시, 성공 토스트는 현재 낭독 뒤에 읽힘
  - □ 스트림 진행 중 "중단" 이 단계 문구와 함께 반복 낭독되지 않음
  - □ Today 낭독 순서가 화면 순서와 같음

## 5. 결정 필요
- **A11Y-L1 인라인 확인의 알림 경로(OVL-1 수정):** (a) live 제거, 그룹 이름과 "취소" 포커스만 사용 — 한 번만 읽힘, OVL-1 문구 수정 필요 / (b) live 유지, 그룹 이름을 짧은 고정 라벨("연결 해제 확인")로 — 문구는 live 로 1회 읽히지만 라벨이 추가로 읽힘 / (c) live 유지, 포커스 이동 안 함 — OVL-2 와 충돌.
- **A11Y-L2 서브탭과 h1 의 위치:** (a) 현행 유지(탭이 h1 위) — 시각 변화 없음, 제목보다 탭이 먼저 읽힘 / (b) h1 을 탭 위로 — 읽는 순서가 자연스러움, Data·Library 화면 시각 변화.
- **A11Y-L3 이름 없는 섹션·시트의 제목:** (a) 보이는 제목 추가 — 문구 결정 필요(Today 섹션 2, RowActionSheet·GarminCleanup·DemoBanner) / (b) sr-only 제목 — 시각 변화 없음, 시각 사용자는 단서 없음 / (c) 제목 없이 `aria-label` 만 사용.
- **A11Y-L4 Today 순서:** (a) DOM 을 모바일 순서로 맞추고 lg 는 행 정렬 그리드로 — 모바일 정합, lg 칸 높이가 맞춰져 시각 변화 / (b) 모바일 표시 순서를 DOM 순서로(다음 세션을 2번째로) — 마크업 변경 최소, 모바일 정보 우선순위 변화 / (c) 현행 유지(위반 수용).
- **A11Y-L5 컴포넌트 가로 스크롤 허용 범위:** (a) 표(`<table>`)만 허용, 칩 행·서브탭·캐러셀은 줄바꿈이나 세로 배치 — 기준 단순, 칩 행 높이 증가 / (b) 표 + 칩 행·서브탭 허용(스크롤 단서 표시 필수) — 현행에 가까움, 숨긴 스크롤바 대체 필요 / (c) 현행 전부 허용.
- **A11Y-L6 인라인 오류의 긴급도:** (a) 사용자 동작 직후 오류는 assertive, 로드 실패는 polite / (b) 전부 polite(오류 토스트만 assertive, A11Y-5) / (c) 전부 assertive.
- **A11Y-L7 axe 자동화:** (a) 수동(브라우저 확장)만 — 의존성 0 / (b) `@axe-core/playwright` 를 CI 에 추가 — 회귀 차단, 브라우저 테스트 의존성·시간 증가(공통 문서 B안과 같은 쟁점).
- **A11Y-L8 YearMonthScrubber 레일(20px):** (a) 44px 로 넓힘 — 목록 오른쪽 가림 증가 / (b) 드래그 전용 보조 조작으로 보고 예외 처리, 같은 기능을 키보드·목록 필터로 제공되는지 확인 / (c) 제거.
- **A11Y-L9 보조 nav 이름 형식:** (a) "<영역> 하위 메뉴" 통일(Library·Data·활동 상세), 경로는 "현재 위치" / (b) 현행 유지.

## 6. 범위 밖 메모
- 토큰 대비·라이트 테마·PageHead·`.tap` 정의는 `accessibility-common.md` 소관이다. 이 문서는 그 위에서의 배치 규칙만 다룬다.
- 공통 §2.2 의 Toast `role=alert/status` 는 R3 에서 announce 로 대체된다. 공통 문서 동기화 시 반영해야 한다.
- OVL `overlay.ts` 는 아직 없다(신규 예정). R1 은 그 구현과 같은 커밋에서 들어가야 한다.
- 칩 그룹(ToggleGroup) 키보드 패턴, 차트 텍스트 요약(M-26), ActivityMoreMenu 메뉴 패턴은 다른 설계 소관이다.
- 375px 후보 수치(WeekStrip 45px, 탭 62px)는 클래스로 추정한 값이라 브라우저 실측 전이다. 스크린리더 실기기 동작(유형 A·F)도 미검증이다.
