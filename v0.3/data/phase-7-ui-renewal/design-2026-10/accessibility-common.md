# 설계: 접근성 공통 (대비·터치 타깃·문서 구조·라벨) — 99-summary 횡단 패턴 6

- 대상 증상: E-15, S-12, S-13, S-14, E-09, E-14, M-27, D-28, P-18, T-12, C-12, D-26, C-10, E-06, P-19, P-20, E-07, S-15, T-19, M-28, D-27 외 (4절 매핑 표)
- 상태: 설계 초안. 구현 전 "6. 결정 필요" 확인 필요
- 범위: `frontend/src/` (v2 전용). 오버레이 Esc·포커스 트랩은 `overlay-common-behavior.md`, 오류·재시도는 `error-retry-common.md` 소관

## 1. 근본 원인
**RC-1. 토큰에 "어느 배경 위에 쓰는가" 계약과 대비 검증이 없음.**
`src/routes/layout.css` `@theme` 은 색 값만 정의하고 전경/배경 조합 규칙이 없다. `text-fg-muted` 는 124개 파일 488곳에 쓰이며, surface-2/3 위에서도 제한 없이 쓰인다. 재계산(WCAG 상대휘도, 이번 설계 중 스크립트로 확인) 결과:

| 전경 \ 배경 | surface-1 | surface-2 | surface-3 |
|---|---|---|---|
| fg-muted #64748b | 3.75 | 3.07 | 2.18 |
| fg-secondary #94a3b8 | 6.96 | 5.71 | 4.04 |
| semantic-red #ef4444 | 4.74 | 3.89 | 2.75 |
| series-3 #475569 | 2.36 | 1.93 | 1.37 |
| provider-garmin / intervals | 2.54 / 3.13 | 2.08 / 2.57 | 1.47 / 1.82 |
| 흰 글자 on strava / runalyze 배지 | 3.40 / 3.30 | | |
포커스 링 토큰·전역 `:focus-visible` 규칙도 없어 브라우저 기본 1px 이 그대로 나온다(S-14, A-33).
**RC-2. 인터랙티브 요소의 공용 부품이 없음 — 크기·이름·상태 표현을 화면마다 클래스로 다시 만듦.**
`Button`/`Chip`/`IconButton`/`TextField` 공용 컴포넌트가 없다. 크기는 `p-1.5`, `py-2 text-[11px]` 같은 즉석 클래스로 정해져 ☰ 32px, 칩 24~26px, 브레드크럼 16px 높이가 나온다. 토글은 `aria-pressed` 를 쓰는 곳과 안 쓰는 곳이 섞이고(M-28), `role=radiogroup` 아래 `button aria-pressed` 처럼 역할이 어긋난다(T-19 `QuickInput.svelte`). 입력은 placeholder 만 있고 이름이 없다(T-19, P-19, C-12, D-27).
**RC-3. 페이지 문서 구조(h1·title·랜드마크 순서·skip link)를 정하는 계약이 레이아웃에 없음.**
`+layout.svelte` 는 `header → main → nav(fixed)` 순서이고 skip link 와 `main` id 가 없다(E-07, S-15). h1·`<title>` 은 각 페이지 재량이라 `+page.svelte` 40개 중 6개는 title 이 없고(replan, story, wellness, race, races, 루트), `+error.svelte` 도 title 이 없다(E-06). 24개 페이지는 페이지 파일에 h1 이 없으며, 그중 Today·웰니스 날짜·활동 상세처럼 하위 컴포넌트가 h1 을 그리는 곳을 빼면 data/* 8개, coach 목록, plan 목록, 세션 상세, library 홈, story 등이 실제 누락이다(D-26, C-10, P-19).

## 2. 설계안 (추천: A안 — 토큰 계약 + 공용 부품 + 정적 가드)

### 2.1 토큰 대비 계약 (RC-1)
- `lib/a11y/contrast.ts` (신규, 순수): `relativeLuminance(hex)`, `contrastRatio(a, b)`, `parseThemeTokens(cssText)` (`@theme` 블록의 `--color-*: #hex` 추출, `var()` 한 단계 해석).
- `lib/a11y/contrastPairs.ts` (신규): 허용 조합 표 `{ fg, bg, use: 'text' | 'large' | 'ui' }[]`. 기준은 text 4.5, large·ui(아이콘, 차트 마커, 포커스 링) 3.0. 표에 없는 조합은 "사용 금지"로 간주하고 문서화한다.
- `tests/tokenContrast.test.mjs` (신규): `layout.css` 를 읽어 표의 모든 조합이 기준 이상인지 검사한다. 토큰 값을 바꾸거나 조합을 추가할 때 자동으로 실패한다.
- `layout.css`: `--color-focus-ring` 토큰과 전역 `:focus-visible { outline: 2px solid var(--color-focus-ring); outline-offset: 2px }` 를 추가한다. 개별 `outline-*` 클래스는 제거 대상이다(S-14).
- 토큰 값 자체(fg-muted, red, series-3, provider 색)의 변경 방식은 결정 1·4.

### 2.2 공용 인터랙티브 부품 (RC-2) — `lib/components/ui/`
- `layout.css` 에 `--size-tap` 토큰과 `.tap`(min-height/min-width) 유틸, 텍스트 링크용 `.tap-area`(가상 요소로 히트 영역만 넓히고 레이아웃은 유지)를 둔다. 기준값은 결정 2.
- `IconButton.svelte`: `label` prop 을 필수로 받아 `aria-label` 로 출력하고 `.tap` 을 적용한다. ☰, ⓘ, 복사, 이전/다음, 닫기에 쓴다.
- `ToggleChip.svelte` + `ToggleGroup.svelte`: `mode='single'` 은 radiogroup/radio + `aria-checked` + 화살표 키 이동(roving tabindex), `mode='multi'` 는 `aria-pressed`. 그룹 `label` 은 필수다. 피로도·통증·기간·카테고리·Provider·월/주·대회 확인 토글이 대상이며, 대회 토글은 그룹 이름에 대회명을 넣는다(T-12).
- `lib/a11y/rovingIndex.ts` (신규, 순수): `nextIndex(current, key, count, disabled[])` 는 화살표·Home/End 를 처리하고 비활성 항목을 건너뛴다.
- `TextField.svelte`: `label` 필수, `labelHidden` 이면 sr-only 로 출력한다. placeholder 는 보조로만 쓴다. HH/MM/SS, 메모 textarea, 비밀번호, ChatComposer 에 적용한다.
- `Toast.svelte`: hover·focus 중 타이머를 멈춘다. 오류 토스트 지속 방식은 결정 5(S-11).

### 2.3 페이지 문서 계약 (RC-3)
- `lib/a11y/pageTitle.ts` (신규, 순수): `pageTitle(...parts)` 는 빈 값을 제거하고 `"A · B · RunPulse"` 를 만든다. 모든 부분이 비면 `"RunPulse"` 를 돌려준다.
- `PageHead.svelte` (신규): `title`(문서 제목), `heading`(h1 문구, 기본값은 title), `headingHidden`(sr-only). `<svelte:head><title>` 과 h1 을 한곳에서 출력한다. h1 을 컴포넌트가 그리는 화면(TodayHero 등)은 `heading={null}` 로 h1 출력을 끈다.
- `+layout.svelte`: 첫 포커스 요소로 "본문 바로가기" skip link → `<main id="main" tabindex="-1">`. 1280px 좌측 내비는 DOM 순서를 시각 순서에 맞춘다(모바일 하단 탭과의 관계는 결정 7).
- `+error.svelte`, `library/wellness/[date]/+error.svelte`: PageHead 를 적용해 title 을 채운다(E-06, E-24).

### 2.4 정적 가드 (회귀 방지)
- `tests/a11yStatic.test.mjs` (신규): `src/routes/**/+page.svelte` 와 `+error.svelte` 를 스캔한다. (a) PageHead 또는 `<title>` 이 있는지, (b) `<input|<textarea|<select>` 에 `aria-label`/`aria-labelledby`/`id`+`<label for>`/TextField 사용이 있는지, (c) `role="radiogroup"` 하위에 `aria-pressed` 가 함께 쓰였는지 검사한다.
- 기존 위반은 `tests/a11yBaseline.json` 허용 목록으로 시작한다. 목록은 줄어들 수만 있다(ratchet). 새 위반은 즉시 실패한다.

## 3. 변경 파일 표 (경로는 `frontend/` 기준, 줄 수는 추정)

| 파일 | 신규/수정 | 줄 수 | 내용 |
|---|---|---|---|
| src/lib/a11y/contrast.ts | 신규 | ~45 | 휘도·대비·@theme 파서 |
| src/lib/a11y/contrastPairs.ts | 신규 | ~40 | 허용 전경/배경 조합 표 |
| src/lib/a11y/rovingIndex.ts, pageTitle.ts | 신규 | ~30, ~15 | 화살표 키 인덱스, 문서 제목 조립 |
| tests/tokenContrast.test.mjs | 신규 | ~50 | 조합 표 전수 검사, 파서 단위 테스트 |
| tests/rovingIndex.test.mjs, tests/pageTitle.test.mjs | 신규 | ~30, ~20 | 순수 함수 테스트 |
| tests/a11yStatic.test.mjs + a11yBaseline.json | 신규 | ~90 + 목록 | 라우트 정적 스캔(ratchet) |
| src/lib/components/ui/IconButton, ToggleChip, ToggleGroup, TextField, PageHead (.svelte) | 신규 | 각 25~60 | 공용 부품 |
| src/routes/layout.css | 수정 | +20 | focus-ring·tap 토큰, :focus-visible, .tap/.tap-area, (결정 후) 색 값 |
| src/routes/+layout.svelte | 수정 | +8 | skip link, main id, 내비 DOM 순서, ☰ → IconButton |
| +error.svelte 2개, Toast.svelte | 수정 | +2, +10 | PageHead, hover/focus 일시정지 |
| 라우트 +page.svelte 약 30개 | 수정 | 각 +1~3 | PageHead 적용(h1/title) |
| QuickInput, RaceConfirmList, MenuDrawer, ChatComposer, ConnectPanel, AI 설정, plan/session·new 폼, metrics 목록/상세, wellness, story 등 약 20개 | 수정 | 각 ±5~20 | 부품으로 교체 |
모든 파일은 300줄 이하를 유지한다. Svelte 부품의 로직은 순수 모듈로 빼서 함수마다 테스트를 둔다.

## 4. ID 처리 매핑

| ID | 처리 | 근거/비고 |
|---|---|---|
| E-15, S-12, S-13 | 이 설계(2.1) + 결정 1·3·4 | 토큰 계약과 대비 테스트 |
| S-14, A-33 | 이 설계(2.1 포커스 링) | 역할 없는 `tabindex` DIV(S-14 후반)는 BACKLOG 개별 |
| E-09, E-14, M-27, D-28, P-18 | 이 설계(2.2 .tap/IconButton) + 결정 2 | E-09 "닫기" 중복은 overlay 설계 참조 |
| T-12, T-19, M-28 | 이 설계(2.2 ToggleGroup 그룹 이름·역할, TextField) | T-19 저장 확인/되돌리기는 BACKLOG 개별 |
| P-19, D-27 | 이 설계(2.2 TextField/IconButton, 2.3 h1) | |
| C-12 | 일부 이 설계(라벨·크기) | role=log live region, 빈 입력 전송 비활성은 BACKLOG 개별 |
| D-26, C-10, E-06, P-20, E-24 | 이 설계(2.3 PageHead) | |
| E-07, S-15, P-21 | 이 설계(2.3 skip link·DOM 순서) + 결정 7 | |
| S-11 | 이 설계(2.2 Toast) + 결정 5 | |
| M-26, T-02 | BACKLOG 개별 | 차트 텍스트 요약(TrendChart·WellnessTrends), 스트립 기호 범례(문구 결정) |
| T-29 | 제외 | 접근성 결함이 아님(390px 양호, 노출 여부 미확인) |
| E-08, C-03, S-07, S-08, S-10, D-25, E-23 | 참조 | overlay-common-behavior.md |
| E-05 | 범위 밖 | 404 HTTP 상태(서버) |

## 5. 단계·검증

1. 대비 모듈과 테스트를 먼저 넣는다. 현재 실패 조합을 `expectedFail` 로 표시해 목록을 확정한다(동작 변화 없음).
2. 결정 1·3·4 후 토큰 값이나 조합 표를 갱신하고 `expectedFail` 을 비운다. 포커스 링 규칙도 이 단계에 넣는다.
3. 레이아웃 skip link·main·내비 순서와 PageHead 를 넣고, 전 라우트에 적용한 뒤 정적 가드를 켠다.
4. 공용 부품을 넣고 영역별(shell → Today → Library → Coach → Data)로 교체하면서 baseline 을 줄인다. 마지막으로 Toast 를 수정한다.
검증: `npm run test:unit`, `npm run check`, `python3 -m pytest tests/`(백엔드 무변경 확인).
- 브라우저 375px·1280px: 첫 Tab 이 skip link 이고 Enter 시 포커스가 main 으로 이동하는지, 1280px Tab 순서가 시각 순서와 같은지 본다.
- DevTools 스니펫으로 전 라우트를 돌며 `document.title` 비어 있지 않음, `h1` 정확히 1개, `a,button,input,[role=radio]` bbox 가 결정 2 기준 이상인지 확인한다(인라인 텍스트 링크는 예외 목록). 데모 모드(`/demo`) 화면도 같은 점검을 한다.
호환성·v1: v1(Flask 템플릿)은 건드리지 않는다(제거 예정이라 토큰 동기화 불필요). 토큰 값을 바꾸면 v2 전 화면 색이 바뀌므로 2단계 전후로 주요 화면 스크린샷을 비교한다. API 변화는 없다.
대안
- A안(추천): 위 설계. 원인 단계에서 막고 런타임 의존이 없다. 단점은 정적 스캔이라 실제 렌더 크기·합성 색(불투명도)은 브라우저 점검에 의존한다는 점이다.
- B안: axe-core + Playwright E2E 감사를 CI 에 추가. 렌더 결과를 직접 검사해 누락이 적지만 현재 package.json 에 브라우저 테스트 도구가 없어 의존성·실행 시간이 늘고, 부품이 없어 고치는 방식은 여전히 화면별이 된다. A 완료 후 보강으로 둘 수 있다.

## 6. 결정 필요

1. fg-muted 처리: (a) 값을 올림(예: #8494a9 → s1 5.77 / s2 4.73 / s3 3.35, s3 는 여전히 미달) — 변경은 가장 적지만 "약한 텍스트" 위계가 줄어듦 / (b) 값 유지 + surface-1 위 큰 글자·비텍스트만 허용 — 위계는 유지되지만 488곳 재분류가 필요 / (c) fg-secondary 로 통합 — 단순하지만 단계가 하나 사라짐.
2. 터치 타깃 기준: 44px(Apple HIG·WCAG 2.5.5 AAA, 손가락 기준) vs 24px + 간격(WCAG 2.2 2.5.8 AA, 밀도 유지). 인라인 텍스트 링크·차트 점 예외 여부도 정해야 한다.
3. 라이트 테마·`prefers-color-scheme` 도입 시점: 지금 도입하면 조합 표가 두 배가 되고 토큰을 다시 설계해야 함 / 나중에 하면 이번 계약은 다크 기준으로 단순하다.
4. Provider 색(Garmin 2.54, Intervals 3.13, series-3): 어두운 배경 전용 "마크" 토큰 분리(브랜드 색에서 벗어남) vs 테두리·형태 보강만(색 유지). 배지 글자(Strava 3.4, Runalyze 3.3)는 흰 글자 → 검은 글자 vs 배지 색을 어둡게 할지.
5. 오류 토스트: 닫을 때까지 유지 vs 시간 연장 vs 오류는 페이지 내 영역으로 이동.
6. 제목이 보이지 않는 화면(data/*, coach 목록 등)의 h1: 보이는 제목 추가 vs sr-only.
7. 내비 DOM 순서: 1280px 만 본문 앞으로 옮김(모바일 하단 탭은 본문 뒤 유지) vs 전 해상도 skip link 만.
8. 포커스 링 색(teal·흰색·하늘색 등)과 두께 2px vs 3px.

## 7. 범위 밖 메모

- E-05: 알 수 없는 경로가 HTTP 200 — 서버 라우팅 문제.
- M-09: 메트릭 상세 h1 명명 불일치 — 용어 정리 소관.
- E-21: description·theme-color·manifest 메타와 비표준 `text-scale` meta.
- svelte-check a11y 경고 0 을 통과 기준으로 둘지, 스크린리더·실기기 점검(미검증)은 별도 판단.
