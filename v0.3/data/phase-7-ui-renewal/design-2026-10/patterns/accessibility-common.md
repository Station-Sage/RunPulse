# 설계: 접근성 공통 (대비·테마·터치 타깃·문서 구조·라벨) — 99-summary 횡단 패턴 6

- 변경 이력: 2026-10-11 A11Y-1·3·4·5 결정 반영, 라이트 테마 설계 / A11Y-9~12 결정 반영, stone 팔레트(slate 제안값 대체)
- 변경 이력: 2026-10-11 A11Y-13 B안 확정(미달 색 재조절), A11Y-14 심화 검토 / 설계서 동기화(A11Y-14 (a) 확정, NEW-10 참조 추가)
- 변경 이력: 2026-10-11 5차 동기화(V1-1 정정·V1-2) — 7절 검증 말미 호환성 뒤에 v1 화면 한 줄(스타일 비공유, `helpers.py` 공유 함수 유지) 추가
- 대상 증상: E-15, S-12, S-13, S-14, E-09, E-14, M-27, D-28, P-18, T-12, C-12, D-26, C-10, E-06, P-19, P-20, E-07, S-15, T-19, M-28, D-27 외 (4절 매핑 표)
- 상태: 설계 확정 — A11Y-1~14 결정 반영(2026-10-11). A11Y-7 내비 순서만 구현 전 별도 레이아웃 설계 필요
- 범위: `frontend/src/` (v2 전용). 오버레이 Esc·포커스 트랩은 `overlay-common-behavior.md`, 오류·재시도는 `error-retry-common.md`, CSP는 보안 헤더 설계 소관

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
**RC-1b. 색이 다크 단일 테마 전제로 토큰 밖에 흩어져 있음 (A11Y-3 라이트 도입 비용).** 2026-10-11 grep 결과:

| 구분 | 규모 | 라이트 대응 |
|---|---|---|
| 토큰 유틸리티(`bg-surface-*`, `text-fg-*` 등) | 1,889곳 | 자동 전환(비용 0) |
| `var(--color-*)` 인라인 style | 15파일 48곳 | 자동 전환 |
| 토큰 + 불투명도(`/40` 등) | 36곳 | 자동이나 합성 대비는 브라우저 확인 |
| #hex 리터럴 (SVG stroke/fill, JS 색 배열) | 9파일 49곳: FormChart 13, streams/+page 4, routeGeometry 3(lerp), ReadinessGauge, ArchiveTabCard, SourceCoverage·ActivityHeatmap(어두운 빈 칸 #1a2536/#1f2937 램프), RouteThumb, RacePredictionSummary | 토큰화 필요. 라이트 흰 배경에서 amber #f59e0b 2.15, teal #14b8a6 2.49 로 미달 |
| Tailwind 기본 팔레트(`text-red-500`, `bg-teal-500`, `bg-sky-400` 등) | 7파일 15곳 | 상태 토큰으로 교체 |
| `text-white` | 약 10파일 19곳 | 색 배경 위 글자 → `fg-on-*` 토큰 |
| `bg-black/30~50` 스크림 | 10곳 | 두 테마 공용 유지 가능 → `--color-scrim` |
| rgba/rgb 리터럴 | 3곳: Skeleton 흰 6% 반짝임(라이트에서 안 보임), ArchiveHero 그라디언트, ProviderMatrix 고정열 그림자 | 토큰화 |
| `shadow`/`shadow-lg` | 14곳 | 다크에서 거의 안 보이던 그림자가 라이트에서 드러남 → 시각 점검만 |
차트 라이브러리·canvas 는 없다(전부 자체 SVG). 라이트 도입 비용은 색 토큰화 약 25파일 수정 + 토큰 블록 추가 수준으로 추정한다. `dark:` 변형·`color-scheme` 선언은 현재 없다.
**RC-2. 인터랙티브 요소의 공용 부품이 없음 — 크기·이름·상태 표현을 화면마다 클래스로 다시 만듦.**
`Button`/`Chip`/`IconButton`/`TextField` 공용 컴포넌트가 없다. 크기는 `p-1.5`, `py-2 text-[11px]` 같은 즉석 클래스로 정해져 ☰ 32px, 칩 24~26px, 브레드크럼 16px 높이가 나온다. 토글은 `aria-pressed` 를 쓰는 곳과 안 쓰는 곳이 섞이고(M-28), `role=radiogroup` 아래 `button aria-pressed` 처럼 역할이 어긋난다(T-19 `QuickInput.svelte`). 입력은 placeholder 만 있고 이름이 없다(T-19, P-19, C-12, D-27).
**RC-3. 페이지 문서 구조(h1·title·랜드마크 순서·skip link)를 정하는 계약이 레이아웃에 없음.**
`+layout.svelte` 는 `header → main → nav(fixed)` 순서이고 skip link 와 `main` id 가 없다(E-07, S-15). h1·`<title>` 은 각 페이지 재량이라 `+page.svelte` 40개 중 6개는 title 이 없고(replan, story, wellness, race, races, 루트), `+error.svelte` 도 title 이 없다(E-06). 24개 페이지는 페이지 파일에 h1 이 없으며, 그중 Today·웰니스 날짜·활동 상세처럼 하위 컴포넌트가 h1 을 그리는 곳을 빼면 data/* 8개, coach 목록, plan 목록, 세션 상세, library 홈, story 등이 실제 누락이다(D-26, C-10, P-19).

## 2. 설계안 (추천: A안 — 토큰 계약 + 테마 + 공용 부품 + 정적 가드)

### 2.1 토큰 대비 계약 (RC-1)
- `lib/a11y/contrast.ts` (신규, 순수): `relativeLuminance(hex)`, `contrastRatio(a, b)`, `parseThemeTokens(cssText)` → `{ dark: Record, light: Record }`. `@theme` 블록을 다크(기본)로, `:root[data-theme='light']` 블록을 그 위에 덮어 라이트 값을 만든다. `var()` 는 같은 테마 안에서 한 단계 해석한다.
- `lib/a11y/contrastPairs.ts` (신규): 허용 조합 표 `{ fg, bg, use: 'text' | 'large' | 'ui', themes?: ('dark'|'light')[] }[]`. 기준은 text 4.5, large·ui(아이콘, 차트 마커, 포커스 링, 입력 테두리) 3.0. `themes` 생략 시 두 테마 모두 검사한다. 표에 없는 조합은 "사용 금지"이며, 2.6 표가 원본이다.
- `tests/tokenContrast.test.mjs` (신규): `layout.css` 를 읽어 표의 모든 조합을 **테마별로** 검사한다. 추가로 (a) 라이트 블록 2개(`[data-theme='light']`, `@media` 안)의 선언이 완전히 같은지, (b) 다크 `@theme` 의 모든 `--color-*` 가 라이트 블록에도 정의됐는지(누락 시 라이트에서 다크 값이 새어 나옴)를 검사한다. 실패 메시지에 `테마/전경/배경/값/기준` 을 출력한다.
- `layout.css`: `--color-focus-ring` 토큰과 전역 `:focus-visible { outline: 2px solid var(--color-focus-ring); outline-offset: 2px }` 를 추가한다. 개별 `outline-*` 클래스는 제거 대상이다(S-14). 색·두께는 결정 8.

### 2.2 공용 인터랙티브 부품 (RC-2) — `lib/components/ui/`
- `layout.css` 에 `--size-tap: 44px` 토큰(결정 2: 44px, 문장 속 인라인 링크·차트 점 예외)과 `.tap`(min-height/min-width) 유틸, 텍스트 링크용 `.tap-area`(가상 요소로 히트 영역만 넓히고 레이아웃은 유지)를 둔다.
- `IconButton.svelte`: `label` prop 을 필수로 받아 `aria-label` 로 출력하고 `.tap` 을 적용한다. ☰, ⓘ, 복사, 이전/다음, 닫기에 쓴다.
- `ToggleChip.svelte` + `ToggleGroup.svelte`: `mode='single'` 은 radiogroup/radio + `aria-checked` + 화살표 키 이동(roving tabindex), `mode='multi'` 는 `aria-pressed`. 그룹 `label` 은 필수다. 피로도·통증·기간·카테고리·Provider·월/주·대회 확인 토글이 대상이며, 대회 토글은 그룹 이름에 대회명을 넣는다(T-12). 선택 표시(A11Y-14): 배경만으로 선택을 표시하지 않는다 — `multi` 칩=테두리(fg-primary/teal 2px), `single` 세그먼트=반전 채움, hover 배경은 s3 까지.
- `lib/a11y/rovingIndex.ts` (신규, 순수): `nextIndex(current, key, count, disabled[])` 는 화살표·Home/End 를 처리하고 비활성 항목을 건너뛴다.
- `TextField.svelte`: `label` 필수, `labelHidden` 이면 sr-only 로 출력한다. placeholder 는 보조로만 쓴다. HH/MM/SS, 메모 textarea, 비밀번호, ChatComposer 에 적용한다.
- `Toast.svelte`: hover·focus 중 타이머를 멈춘다. 결정 5(A11Y-5): `kind='error'` 는 자동 닫힘 없이 닫기 버튼(IconButton)으로만 닫고 `role="alert"`, 성공·정보는 짧게(기존 시간) 자동 닫힘 + `role="status"`(S-11).

### 2.3 페이지 문서 계약 (RC-3)
- `lib/a11y/pageTitle.ts` (신규, 순수): `pageTitle(...parts)` 는 빈 값을 제거하고 `"A · B · RunPulse"` 를 만든다. 모든 부분이 비면 `"RunPulse"` 를 돌려준다.
- `PageHead.svelte` (신규): `title`(문서 제목), `heading`(h1 문구, 기본값은 title), `headingHidden`(sr-only). `<svelte:head><title>` 과 h1 을 한곳에서 출력한다. h1 을 컴포넌트가 그리는 화면(TodayHero 등)은 `heading={null}` 로 h1 출력을 끈다.
- `+layout.svelte`: 첫 포커스 요소로 "본문 바로가기" skip link → `<main id="main" tabindex="-1">`. 1280px 좌측 내비는 DOM 순서를 시각 순서에 맞춘다(모바일 하단 탭과의 관계는 결정 7).
- `+error.svelte`, `library/wellness/[date]/+error.svelte`: PageHead 를 적용해 title 을 채운다(E-06, E-24).

### 2.4 정적 가드 (회귀 방지)
- `tests/a11yStatic.test.mjs` (신규): `src/routes/**/+page.svelte` 와 `+error.svelte` 를 스캔한다. (a) PageHead 또는 `<title>` 이 있는지, (b) `<input|<textarea|<select>` 에 `aria-label`/`aria-labelledby`/`id`+`<label for>`/TextField 사용이 있는지, (c) `role="radiogroup"` 하위에 `aria-pressed` 가 함께 쓰였는지 검사한다.
- (d) 색 리터럴 가드(신규): `src/**/*.svelte|ts` 에서 `#hex`, `rgb(a)(`, Tailwind 기본 팔레트 클래스(`(bg|text|border|fill|stroke)-(red|teal|amber|sky|…)-\d+`), `text-white`/`text-black` 를 찾아 실패시킨다. 테마가 바뀌어도 따라오지 않는 색이 다시 들어오는 것을 막는다. `lib/a11y/contrast.ts`·테스트 파일은 제외.
- 기존 위반은 `tests/a11yBaseline.json` 허용 목록으로 시작한다. 목록은 줄어들 수만 있다(ratchet). 새 위반은 즉시 실패한다.

### 2.5 라이트 테마 구조 (A11Y-3)
- **시맨틱 토큰 → 테마별 값.** 컴포넌트는 지금처럼 `--color-surface-1`, `--color-fg-muted`, `--color-status-danger` 같은 의미 이름만 쓴다. 값만 테마별로 바꾼다. 원시 팔레트 이름(`slate-500` 등)을 토큰 이름에 넣지 않는다.
- **선언 위치(`layout.css`):**
  1. `@theme { … }` — 지금과 같이 다크 값(기본). Tailwind v4 는 사용된 변수만 내보내므로 인라인 `var()` 로만 쓰는 토큰이 빠지지 않도록 `@theme static` 으로 바꾸거나 빌드 산출물에서 확인한다(구현 시 확인).
  2. `:root { color-scheme: dark; }` — 스크롤바·폼 컨트롤·자동완성 배경도 테마를 따르게 한다.
  3. `@media (prefers-color-scheme: light) { :root:not([data-theme='dark']) { color-scheme: light; --color-…: …; } }` — 시스템 따름(결정 10: 기본값). `data-theme` 가 없으면 이 블록이 적용된다.
  4. `:root[data-theme='light'] { color-scheme: light; --color-…: …; }` — 설정 화면 수동 선택(결정 9). 3·4 의 선언은 같아야 하며 2.1 테스트 (a)가 보장한다. 수동 '다크'는 `data-theme='dark'` 로 3 을 막아 `@theme` 기본값이 남는다.
  - `@theme` 의 별칭(`--color-status-danger: var(--color-semantic-red)`)은 `:root` 에서 계산되므로 원본만 덮으면 따라온다.
  - 대안 `light-dark()` 함수는 선언 중복이 없지만 iOS 17.4 이하에서 색이 통째로 사라져 채택하지 않는다.
  - 두 블록은 각 40줄 안팎이라 `layout.css` 가 300줄을 넘으면 `src/routes/theme-light.css` 로 분리해 `@import` 한다.
- **FOUC 방지(결정 9 로 필요):** 시스템 따름은 CSS 미디어 쿼리라 스크립트가 필요 없지만, 수동 선택은 저장된 값을 첫 페인트 전에 적용해야 한다. 저장값 없음·'system' 은 `data-theme` 를 두지 않는다.
  - `frontend/static/theme-init.js` (신규, ~12줄): `<head>` 맨 앞에서 동기 로드. `try { const t = localStorage.getItem('rp-theme'); if (t === 'light' || t === 'dark') document.documentElement.dataset.theme = t; } catch {}`.
  - `src/app.html`: `<script src="%sveltekit.assets%/theme-init.js"></script>` 를 `%sveltekit.head%` 앞에, `<meta name="theme-color" media="(prefers-color-scheme: …)">` 2개를 추가한다. 외부 파일이므로 CSP `script-src 'self'` 로 통과한다(인라인으로 두면 SEC-1 CSP 에 sha256 해시를 따로 관리해야 함).
- **런타임 모듈:** `lib/theme/theme.ts` (신규, 순수 + 얇은 DOM 래퍼): `resolveTheme(pref: 'system'|'light'|'dark', systemLight: boolean)`, `readPref()`/`writePref()`(try/catch, 실패 시 'system'), `applyTheme(pref)`(`data-theme` 설정/제거). 전환 UI(결정 9)는 **설정 화면에만** `ThemeSwitch`(`ToggleGroup mode='single'` 3상태 시스템/라이트/다크, 기본 '시스템')로 두고 셸(헤더·MenuDrawer)은 바꾸지 않는다. '시스템' 상태에서 OS 테마가 바뀌면 CSS 가 즉시 따라가므로 `matchMedia` 리스너는 `theme-color` 갱신용으로만 쓴다.

### 2.6 테마별 대비 조합 표 (허용 조합 원본, WCAG 상대휘도 스크립트 계산)
배경: 다크 s1 #0f172a / s2 #1e293b / s3 #334155(유지). 라이트는 결정 13 **B 따뜻한 종이**: s1 #f7f5f2(페이지) / s2 #fffdfa(카드) / s3 #efebe5(칩·hover·중첩), border-subtle #e6e0d7(장식). 기준 text 4.5, ui 3.0. ✗ 는 금지 조합. 미달 색은 hue·채도를 두고 HSL 명도만 낮춰 s3 기준 text 4.6·ui 3.1 이상(여유 0.1)이 되는 가장 밝은 값으로 재조절했다. 표기 `원래 → 조절(ΔL)`. 계산: scratchpad `paper_contrast.py`·`state_check.py` → 구현 시 `tokenContrast.test.mjs` 가 같은 표를 재검증한다.

| 토큰 | 용도 | 다크 값 | 다크 s1/s2/s3 | 라이트 값(B) | 라이트 s1/s2/s3 |
|---|---|---|---|---|---|
| fg-primary | text | #f1f5f9 | 16.3/13.4/9.45 | #1c1917 | 16.1/17.2/14.7 |
| fg-secondary | text | #94a3b8 | 6.96/5.71/**4.04 large만** | #57534e | 7.01/7.51/6.42 |
| fg-muted (A11Y-1) | text | **#8494a9**(현 #64748b) | 5.77/4.73/**3.35 ✗** | #6b645c | 5.36/5.74/4.91 |
| semantic-red / status-danger | text·ui | #f87171(현 #ef4444) | 6.45/5.29/3.74 ui만 | #b91c1c | 5.95/6.37/5.45 |
| semantic-amber | text·ui | #f59e0b | 8.31/6.81/4.82 | #b45309(s3 4.23 ✗) → **#aa4f09**(ΔL −2.0%p) | 5.04/5.40/4.62 |
| semantic-green | text·ui | #22c55e | 7.83/6.42/4.54 | #15803d(s3 4.22 ✗) → **#14793a**(−1.6%p) | 5.04/5.41/4.62 |
| semantic-blue | text·ui | (현 값 유지, 다크 표 미기재) | — | #1d4ed8 | 6.16/6.60/5.64 |
| semantic-teal | text·ui | #14b8a6 | 7.17/5.88/4.16 ui만 | #0f766e | 5.03/5.39/4.61 |
| delta-better / worse | text | #38bdf8 / #fb923c | 6.83 / 6.46 (s2) | #0369a1 / #c2410c(s3 4.36 ✗) → **#bb3f0c**(−1.4%p) | 5.45·5.84·5.00 / 5.04·5.40·4.62 |
| series-1 | ui | #7dd3fc | 10.7/8.77/6.21 | #0284c7 | 3.76/4.03/3.45 |
| series-2 | ui | #cbd5e1 | 12.0/9.85/6.97 | #57534e | 7.01/7.51/6.42 |
| series-3 (마크) | ui | **#8a98ad**(현 #475569) | 6.10/5.00/3.54 | #8c847b(s3 3.10, 여유 0) → **#887f76**(−1.8%p) | 3.61/3.87/3.31 |
| border-strong (신규, 입력 테두리) | ui | #64748b | 3.75/3.07/✗ | series-3 과 같은 값 **#887f76** | 3.61/3.87/3.31 |
| border-subtle | 장식(검사 제외) | #334155 | — | #e6e0d7 | — |
| focus-ring (A11Y-8) | ui | #38bdf8 | 8.33/6.83/4.83 | #0369a1 | 5.45/5.84/5.00 |
- **B 재조절 후 표의 전 조합 통과**(최소: amber·green·delta-worse 텍스트 s3 4.62, teal 4.61, series-3·border s3 3.31). 재조절 폭은 명도 −1.4~−2.0%p 로 다크와 색 의미(hue)는 그대로다. 조절값은 라이트 블록에만 쓰고 다크 값은 바꾸지 않는다.
- **금지 조합:** 다크 s3 위 fg-muted·semantic 텍스트(red·teal 은 ui만, secondary 는 큰 글자만). 다크 series-1/2/3 값을 라이트 배경에 쓰는 것(1.25~2.88 ✗ — series 는 반드시 테마별 토큰). **원래 값(#b45309·#15803d·#c2410c·#fc4c02·#16a34a)을 라이트 s3 위 text/마크로 쓰는 것**. 라이트 s3 보다 어두운 배경 위 semantic 텍스트·provider 마크(2.7·결정 14). semantic 틴트는 라이트 `/10` 까지만 같은 색 텍스트를 허용(amber/10 위 amber 4.70, amber/20 위 4.05 ✗ — `/15` 이상 틴트 위 글자는 fg-primary 13.0+만).
- 다크 semantic-red #f87171 은 RC-1 미달(s2 3.89) 해소 목적의 제안값이다. 합성 색(`/40` 등 36곳)은 표 대상이 아니며 5절 브라우저 점검으로 확인한다.
- 폐기안 참고(결정 13): A stone(s1 #fafaf9/s2 #fff/s3 #f5f5f4)은 원래 색 그대로 전 조합 통과, C stone-200 칩(s3 #e7e5e4)은 재조절 폭이 더 커서(amber·green s3 4.00) 채택하지 않았다.

### 2.7 차트·provider 마크·배지 (A11Y-4)
- **provider 토큰 3층:** `--color-provider-{x}`(브랜드, 배지 배경 — 두 테마 원색 고정), `--color-provider-{x}-mark`(점·선·아이콘, 테마별, ui 3.0), `--color-provider-{x}-on`(배지 글자, 테마 무관, 배경 대비로 흑/백 선택). **A11Y-12 수정(결정 13 의 효과):** 라이트 mark 는 원색 별칭이 아니라 대비 통과용 조절값을 허용한다. 원색과 같으면 별칭, 다르면 독립 값이다.

| provider | 브랜드(배지 배경) | 다크 mark (s1/s2/s3) | 라이트 mark (B s1/s2/s3) | 배지 글자 (대비) |
|---|---|---|---|---|
| garmin | #0056b3 | #4c8fe0 (5.37/4.40/3.11) | 브랜드 (6.47/6.94/5.93) | 흰 #fff (7.04) |
| strava | #fc4c02 | 브랜드 (5.25/4.30/3.04) | #fc4c02(s3 2.86 ✗) → **#f14902**(ΔL −2.2%p) (3.39/3.63/3.11) | 검정 #0f172a (5.25) |
| intervals | #7c3aed | #a78bfa (6.56/5.38/3.80) | 브랜드 (5.24/5.61/4.80) | 흰 (5.70) |
| runalyze | #16a34a | 브랜드 (5.42/4.44/3.14) | #16a34a(s3 2.78 ✗) → **#159946**(−2.2%p) (3.40/3.64/3.12) | 검정 (5.42) |
| runpulse | #6b7280 | #8b95a5 (5.90/4.83/3.42) | 브랜드 (4.44/4.76/4.07) | 흰 (4.83) |
| primary(★) | #fbbf24 | 브랜드 (10.7/8.76/6.20) | semantic-amber 별칭 #aa4f09 (5.04/5.40/4.62) | 검정 (10.7) |
- strava·runalyze 라이트 mark 는 s3 에서 여유 0.11~0.12 다. s3 보다 어두운 배경 위 마크는 결정 14 대상이며, 그런 자리(선택 칩·다른 provider 배지 위·heat 셀)에서는 마크 대신 배지(원색 배경 + on 글자) 또는 이름 병기로 표현한다.
- **해결 불가로 남는 금지 조합:** 흰 글자 on strava/runalyze 배지(3.40/3.30 — 배지 배경은 원색 고정이라 on 은 검정만), 원색 #fc4c02·#16a34a 를 라이트 s2·s3 위 마크로 쓰는 것. strava(주황)·runalyze(초록)와 semantic amber·green 이 같은 차트에 함께 나오면 색만으로 구분되지 않으므로 범례·이름 병기를 둔다.
- 다크 strava 3.04·runalyze 3.14(s3)는 기존 A11Y-4 설계대로 유지한다.
- **차트 토큰(신규, 테마별, ui 3.0):** `--color-chart-ctl/atl/tsb/taper`(FormChart), `--color-chart-hr/alt/cad/power`(streams), `--color-route-low/high`·`--color-route-slow/fast`(routeGeometry), `--color-heat-0..4`(ActivityHeatmap·SourceCoverage 공용 램프), `--color-gauge-*`(ReadinessGauge → status 토큰 재사용). 다크 값은 현재 hex 그대로 옮겨 시각 변화 없음, 라이트(B s1/s2/s3): CTL #2563eb(4.75/5.09/4.35), ATL = amber #aa4f09(5.04/5.40/4.62), TSB #0f766e(5.03/5.39/4.61), HR #dc2626(4.44/4.76/4.07), 고도 #047857(5.04/5.40/4.62), 파워 #7c3aed(5.24/5.61/4.80), 경로 #0d9488(s3 3.15, 여유 0.15) → **#0d9085**(−0.8%p, 3.61/3.87/3.31), heat 램프 #e6e0d7(heat-0, s2 대비 1.29 — 빈 칸 구분용, 위에 글자·마크 금지)→#99f6e4→#2dd4bf→#0d9488→#0f766e. 차트 색을 글자로 쓰면(범례 수치) text 4.5 가 필요하므로 CTL·HR 은 범례 글자에 쓰지 않고 fg 토큰을 쓴다.
- SVG 는 `stroke="#hex"` 대신 `style="stroke: var(--color-chart-ctl)"` 또는 클래스로 칠한다(presentation 속성의 `var()` 는 브라우저마다 다름). JS 색 배열(`series=[{color}]`)은 `'var(--color-chart-ctl)'` 문자열을 넘긴다.
- `routeGeometry.ts` 의 hex lerp 는 `color-mix(in oklab, var(--color-route-fast) ${p}%, var(--color-route-slow))` 문자열을 돌려주도록 바꾼다(순수 함수 유지, `routeGeometry.test.mjs` 기대값 갱신). heat 램프 인접 단계 간 대비는 1.4.11 대상 아님(값은 툴팁·텍스트로 제공), 빈 칸(heat-0)은 배경과 구분만 확인한다.
- 기타: `--color-scrim`(두 테마 `rgb(0 0 0 / .4)`), `--color-shimmer`(다크 흰 6% / 라이트 #1c1917 6%), `--color-fg-on-accent`(teal·red 버튼 위 글자; 라이트 흰 글자 on #0f766e 5.47·#b91c1c 6.47, 다크는 구현 시 확인), ArchiveHero 그라디언트·ProviderMatrix 고정열 그림자 토큰화.

## 3. 변경 파일 표 (경로는 `frontend/` 기준, 줄 수는 추정)

| 파일 | 신규/수정 | 줄 수 | 내용 |
|---|---|---|---|
| src/lib/a11y/contrast.ts | 신규 | ~60 | 휘도·대비·테마별 토큰 파서 |
| src/lib/a11y/contrastPairs.ts | 신규 | ~60 | 허용 조합 표(테마 태그) |
| src/lib/a11y/rovingIndex.ts, pageTitle.ts | 신규 | ~30, ~15 | 화살표 키 인덱스, 문서 제목 조립 |
| src/lib/theme/theme.ts | 신규 | ~40 | 선호 읽기/쓰기, 해석, 적용 |
| static/theme-init.js, src/app.html | 신규, 수정 | ~12, +4 | FOUC 방지 초기 스크립트, theme-color meta |
| tests/tokenContrast.test.mjs | 신규 | ~80 | 두 테마 조합 전수, 라이트 블록 동일성·누락 검사, 파서 단위 |
| tests/theme.test.mjs | 신규 | ~30 | resolveTheme·저장 실패 fallback |
| tests/rovingIndex.test.mjs, tests/pageTitle.test.mjs | 신규 | ~30, ~20 | 순수 함수 테스트 |
| tests/a11yStatic.test.mjs + a11yBaseline.json | 신규 | ~110 + 목록 | 라우트 정적 스캔·색 리터럴 가드(ratchet) |
| src/lib/components/ui/IconButton, ToggleChip, ToggleGroup, TextField, PageHead (.svelte) | 신규 | 각 25~60 | 공용 부품 |
| src/lib/components/ui/ThemeSwitch.svelte | 신규 | ~30 | 3상태(시스템/라이트/다크) 전환, 기본 '시스템' |
| 설정 화면 라우트(+page.svelte) | 수정 | +5 | ThemeSwitch 배치(셸 무변경, 결정 9) |
| src/routes/layout.css (+ 필요 시 theme-light.css) | 수정(+신규) | +120 | 다크 값 조정, 마크·on·차트·heat·scrim 토큰, B(따뜻한 종이) 라이트 블록 2개(`@media`·`data-theme`), color-scheme, focus-ring·tap |
| FormChart, streams/+page, routeGeometry.ts, ActivityHeatmap, SourceCoverage, ReadinessGauge, ArchiveTabCard, RouteThumb, RacePredictionSummary | 수정 | 각 ±3~15 | hex → 차트 토큰 |
| GarminCleanup, SyncStatusPill, SyncPanel, UiDefaultCard, ProviderComparison, coach/new, story/[period] | 수정 | 각 ±1~4 | Tailwind 기본 팔레트 → 상태 토큰 |
| text-white 사용 약 10파일, Skeleton, ArchiveHero, ProviderMatrix, provider 배지·마크 사용처 | 수정 | 각 ±1~5 | on/mark/shimmer/그림자 토큰 |
| src/routes/+layout.svelte | 수정 | +8 | skip link, main id, 내비 DOM 순서, ☰ → IconButton |
| +error.svelte 2개, Toast.svelte | 수정 | +2, +15 | PageHead, 오류 지속·hover/focus 일시정지 |
| 라우트 +page.svelte 약 30개 | 수정 | 각 +1~3 | PageHead 적용(h1/title) |
| QuickInput, RaceConfirmList, MenuDrawer, ChatComposer, ConnectPanel, AI 설정, plan/session·new 폼, metrics 목록/상세, wellness, story 등 약 20개 | 수정 | 각 ±5~20 | 부품으로 교체 |
| 배경만 선택 표시 6곳(story 월/주, streams x축, ArchiveTabCard, `+layout` lg 내비, TaperSheet, WeekStrip)·`hover:bg-border-subtle` 1·ActivityRow | 수정 | 각 ±1~4 | A11Y-14: 전경 지시자 추가, amber/20 위 amber 글자 → `/10` 또는 fg-primary |
모든 파일은 300줄 이하를 유지한다. Svelte 부품의 로직은 순수 모듈로 빼서 함수마다 테스트를 둔다.

## 4. ID 처리 매핑

| ID | 처리 | 근거/비고 |
|---|---|---|
| E-15, S-12, S-13 | 이 설계(2.1·2.5~2.7) + 결정 1·3·4 | 토큰 계약, 두 테마 대비 테스트 |
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
| NEW-10 단건 삭제 UI·RC 시트 | 참조 | 이 문서 계약을 따른다: 시트는 `use:modal`(overlay), 버튼 44px(`.tap`/IconButton), 보이는 h1(PageHead) |
| E-05 | 범위 밖 | 404 HTTP 상태(서버) |

## 5. 단계·검증

1. 대비 모듈과 테스트를 먼저 넣는다(테마 파서 포함, 라이트 블록이 없으면 라이트 검사는 skip). 현재 실패 조합을 `expectedFail` 로 표시해 목록을 확정한다(동작 변화 없음).
2. **다크 그대로 토큰화:** 2.7 의 차트·heat·scrim·shimmer·on 토큰을 현재 값 그대로 만들고 hex·rgba·기본 팔레트·`text-white` 를 교체한 뒤 색 리터럴 가드를 켠다. 교체 전후 다크 스크린샷이 같아야 한다.
3. **다크 값 조정:** A11Y-1 fg-muted #8494a9, semantic-red, series-3 마크, provider mark·on 토큰(A11Y-4), focus-ring(결정 8 후)과 전역 `:focus-visible` 을 넣고 다크 `expectedFail` 을 비운다.
4. **라이트 도입:** B 라이트 블록 2개·`color-scheme`·theme-init·theme.ts·설정 화면 ThemeSwitch 를 넣고 라이트 `expectedFail` 없이 통과시킨다. 2.6·2.7 의 금지 조합은 `contrastPairs.ts` 에 넣지 않아 사용 시 정적 검토로 걸리게 하고, 여유 0.15 이하 조합(strava·runalyze 마크 × s3, teal 텍스트 × s3)은 테스트 메시지에 "s3 하한 — 배경을 어둡게 하지 말 것(결정 14)" 을 붙인다. 재조절 색은 원래 값과 함께 주석으로 남겨 브랜드 이탈을 추적한다.
5. 레이아웃 skip link·main·내비 순서와 PageHead 를 넣고, 전 라우트에 적용한 뒤 정적 가드를 켠다.
6. 공용 부품을 넣고 영역별(shell → Today → Library → Coach → Data)로 교체하면서 baseline 을 줄인다. 마지막으로 Toast(오류 지속)를 수정한다.
검증: `npm run test:unit`(tokenContrast 두 테마·라이트 블록 동일성 포함), `npm run check`, `python3 -m pytest tests/`(백엔드 무변경 확인).
- 브라우저 375px·1280px × 다크·라이트: DevTools Rendering 의 `prefers-color-scheme` 에뮬레이션과 `data-theme` 수동 값 양쪽으로 Today·Library 목록/상세(FormChart·streams·지도)·Coach·Data(ProviderMatrix)·설정 화면을 본다. 불투명도 합성 36곳과 그림자, 배지 글자, 스켈레톤 반짝임을 확인한다.
- 테마 3상태: 설정에서 시스템/라이트/다크 각각 선택 → 새로고침 후 유지, '시스템'에서 OS 테마 전환 시 즉시 따라가는지 본다.
- FOUC: 수동 라이트 선택 후 네트워크 Slow 3G 로 새로고침해 첫 프레임이 다크로 깜빡이지 않는지, localStorage 차단(시크릿·쿠키 차단)에서도 오류 없이 시스템 따름으로 뜨는지 본다.
- 첫 Tab 이 skip link 이고 Enter 시 포커스가 main 으로 이동하는지, 1280px Tab 순서가 시각 순서와 같은지 본다. 포커스 링이 두 테마 s1~s3 위에서 보이는지 본다.
- DevTools 스니펫으로 전 라우트를 돌며 `document.title` 비어 있지 않음, `h1` 정확히 1개, `a,button,input,[role=radio]` bbox 가 44px 이상인지 확인한다(인라인 텍스트 링크는 예외 목록). 데모 모드(`/demo`) 화면도 같은 점검을 한다.
호환성: 다크 값 조정(3단계)과 라이트 기본 적용(4단계, 결정 10)은 기존 사용자에게 보이는 변화이므로 단계 전후 주요 화면 스크린샷을 비교한다. 저장 키 `rp-theme` 외 서버·API 변화는 없다. CSP(SEC-1) 는 외부 `theme-init.js` 라 추가 해시가 필요 없다.
레거시 v1 화면: 스타일은 `src/web/helpers.py:11` 인라인 `_CSS` 로 v2 토큰과 공유하지 않는다(grep) — 이 설계 대상 아님. 같은 `helpers.py` 의 `db_path`·`get_current_user_id` 는 v2 `src/api`·`src/services` 가 import 하는 공유 함수라 유지. 재설계: view 밖으로 이관 후 UI 일몰(V1-2).
대안
- A안(추천): 위 설계. 원인 단계에서 막고 런타임 의존이 없다. 단점은 정적 스캔이라 실제 렌더 크기·합성 색(불투명도)은 브라우저 점검에 의존한다는 점이다.
- B안: axe-core + Playwright E2E 감사를 CI 에 추가. 렌더 결과를 두 테마로 직접 검사해 누락이 적지만 현재 package.json 에 브라우저 테스트 도구가 없어 의존성·실행 시간이 늘고, 부품이 없어 고치는 방식은 여전히 화면별이 된다. A 완료 후 보강으로 둘 수 있다.

## 6. 결정됨 (2026-10-11)

1. fg-muted 처리 — **결정됨(2026-10-11, A11Y-1): (a) 값을 올림.** 다크 #8494a9(s1 5.77 / s2 4.73 / s3 3.35 → s3 텍스트 금지), 라이트 #6b645c(B안 s1 5.36 / s2 5.74 / s3 4.91)로 재검증(2.6).
2. 터치 타깃 기준 — **결정됨(2026-10-11, A11Y-2): 44px, 문장 속 인라인 링크·차트 점 예외.**
3. 라이트 테마·`prefers-color-scheme` 도입 시점 — **결정됨(2026-10-11, A11Y-3): 이번 접근성 작업에 함께 도입, 구현 전 토큰·조합 표 재설계(2.5~2.7).**
4. Provider 색·배지 — **결정됨(2026-10-11, A11Y-4): 어두운 배경용 마크 토큰 분리(비텍스트 3:1), 배지 글자는 배경에 맞춰 흑/백 선택(2.7).**
5. 오류 토스트 — **결정됨(2026-10-11, A11Y-5): 닫을 때까지 유지, 성공 토스트는 짧게(2.2).**
6. 제목이 보이지 않는 화면의 h1 — **결정됨(2026-10-11, A11Y-6): 보이는 제목 추가(이미 보이는 제목이 있는 화면은 h1 으로 승격).** 근거: /data/*·/coach 목록은 탭 하이라이트가 없고 첫 가시 제목이 h2.
7. 내비 DOM 순서 — **결정됨(2026-10-11, A11Y-7): 1280px 만 내비를 본문 앞으로(모바일 하단 탭은 본문 뒤 유지). 레이아웃 변경이라 구현 전 별도 설계 필요.**
8. 포커스 링 색(teal·흰색·하늘색 등)과 — **결정됨(2026-10-11, A11Y-8): 두께 2px, 색은 두 테마 각각 대비 검증(후보 다크 #38bdf8, 라이트 #0369a1).**
9. 수동 테마 전환 UI — **결정됨(2026-10-11, A11Y-9): (b) 설정 화면에 3상태(시스템/라이트/다크), 셸 변경 없음, FOUC 방지 스크립트 포함(2.5).**
10. 기본 테마 정책 — **결정됨(2026-10-11, A11Y-10): (a) 시스템 따름(기본).** 라이트 OS 사용자는 업데이트 직후 밝게 바뀌므로 4단계 전후 스크린샷 비교(5절).
11. 라이트 팔레트 방향 — **결정됨(2026-10-11, A11Y-11): (b) 따뜻한 중성.** slate 반전 제안값은 폐기, 최종 톤은 결정 13(B 따뜻한 종이).
12. 라이트 provider 마크 — **결정됨(2026-10-11, A11Y-12): (a) 브랜드 원색 유지, 배지 배경은 두 테마 원색 고정.** **수정 메모(2026-10-11, 결정 13 의 효과):** B 안에서 원색 strava(s3 2.86)·runalyze(2.78) 마크가 미달하므로 '라이트용 마크는 대비 통과하도록 조절 허용'으로 바뀐다 — strava #f14902, runalyze #159946(명도 −2.2%p). 배지 배경 원색 고정은 그대로(2.7).
13. 라이트 팔레트 최종 톤 — **결정됨(2026-10-11, A11Y-13): B 따뜻한 종이** s1 #f7f5f2 / s2 #fffdfa / s3 #efebe5, 텍스트 fg #1c1917/#57534e/#6b645c. 미달 색 재조절(명도만 −0.8~−2.2%p): amber #b45309→#aa4f09, green #15803d→#14793a, delta-worse #c2410c→#bb3f0c, series-3·border-strong #8c847b→#887f76, strava 마크 #fc4c02→#f14902, runalyze 마크 #16a34a→#159946, 경로 #0d9488→#0d9085. 재조절 후 2.6·2.7 전 조합 통과(최소 text 4.61, ui 3.11).
14. 라이트 s3 보다 어두운 상태 배경 — **결정됨(2026-10-11, A11Y-14): (a) 라이트 배경 하한 s3 + 전경 지시자.** 선택·pressed·current 는 테두리(fg-primary/teal 2px) 또는 반전·의미색 채움 필수, hover 는 s3 까지. 다중 선택 칩=테두리, 단일 세그먼트=반전 채움(2.2). 근거: s2 대비 3:1 이 되려면 배경 상대휘도 ≤0.30 이어서 라이트의 어떤 어두운 배경도 단독 상태 표시가 될 수 없고(s3 vs s2 1.17, 후보 #e9e4dc 1.25), (b) 전용 state 토큰은 금지 조합 7개 또는 추가 색 이탈만 늘린다. 1.4.11 대상은 선택·pressed·current 뿐(hover 장식·disabled·스크림 제외). 수정: 배경만 선택 표시 6곳 + `hover:bg-border-subtle` 1 + ActivityRow(amber/20 위 amber 4.05 ✗) ≈ 8파일(3절), 나머지는 ToggleChip 교체에 흡수. heat-0 #e6e0d7 은 데이터 셀(위 전경 금지) 예외. 토큰 추가 0.

## 7. 범위 밖 메모

- E-05: 알 수 없는 경로가 HTTP 200 — 서버 라우팅 문제.
- M-09: 메트릭 상세 h1 명명 불일치 — 용어 정리 소관.
- E-21: description·manifest 메타와 비표준 `text-scale` meta(theme-color 는 2.5 에서 테마별로 추가).
- svelte-check a11y 경고 0 을 통과 기준으로 둘지, 스크린리더·실기기 점검(미검증)은 별도 판단.
- 고대비 모드(`prefers-contrast: more`)·`forced-colors` 대응은 이번 범위 밖. 토큰 구조상 같은 방식으로 블록을 추가할 수 있다.

## 8. 동기화 중 발견한 충돌/확인 필요

- A11Y-12 결정 원문은 "(a) 브랜드 원색 유지"이나 A11Y-13 결정이 라이트 마크 조절 허용으로 사실상 수정했다(결정 12 수정 메모·2.7 에 반영). decisions-table 의 A11Y-12 줄 자체는 원문 그대로다.
- A11Y-7(1280px 내비 DOM 순서)은 "구현 전 별도 레이아웃 설계 필요"로 결정돼 이 문서에 레이아웃 설계가 없다.
- NEW-10 의 "RC 시트" 설계서는 이 동기화에서 읽지 않았다. 4절 참조 행은 계약 적용만 명시한다.
