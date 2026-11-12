# CWV 실측 (PHASE-7-REMAINING 5, 2026-11-11, S4-89)

합성 DB(`seed_synth.py`, 활동 14건) + `serve_synth.py`(Flask 개발 서버, HTTP/1.1·무압축)를 Playwright Chromium 으로 측정.
Lighthouse 는 쓰지 않았다(설치 없이 같은 조건을 CDP 로 재현). 페이지마다 새 컨텍스트(콜드 캐시) 5회, **중앙값**.

- 모바일: 375×812·DPR2·터치, CDP `setCPUThrottlingRate 4`, 네트워크 Lighthouse 'slow 4G' devtools 값(RTT 562.5ms·1.47Mbps↓·675kbps↑).
- 데스크톱: 1350×940, 스로틀 없음.
- LCP·CLS 는 `PerformanceObserver`(CLS 는 세션 창 최대값), TBT 는 FCP 이후 long task(>50ms) 초과분 합(INP 는 상호작용이 없어 **미측정**), 전송량은 CDP `encodedDataLength` 합.
- **H2 열**: 운영 엣지를 근사하려 로컬 HTTP/2+gzip 역프록시(node, 자체 서명)를 앞에 둔 값. 개발 서버는 HTTP/1.1 6연결 제한이라 JS 청크 52~78개가 RTT 마다 줄을 서서 모바일 수치가 과장된다(today 의 마지막 청크 도착 ~7s). 운영 프록시(Cloudflare 등)의 실제 프로토콜·압축·캐시는 확인하지 않았다.

| 페이지 | 모바일 LCP H1 / **H2** | 모바일 CLS(최대) | 모바일 TBT | 데스크톱 LCP(H1) | 전송량 H1 / H2(gzip) · 요청 |
|---|---|---|---|---|---|
| /v2/today | 8128 / **4748** ms | 0 | 270 ms | 1940 ms | 544 / 233 KB · 76 |
| /v2/library/activities | 2276 / **2168** ms ※ | 0 | 237 ms | 212 ms ※ | 393 / 178 KB · 53 |
| 활동 상세 /v2/library/100 | 7596 / **5008** ms | 0 | 263 ms | 1792 ms | 493 / 213 KB · 67 |
| /v2/coach | 6796 / **3976** ms | 0 | 102 ms | 1428 ms | 378 / 162 KB · 58 |
| 플랜 상세 /v2/coach/plan/1 | 6292 / **3936** ms | 0.043 (0.071) | 144 ms | 1348 ms | 409 / 187 KB · 56 |
| 설정 /v2/data/settings | 5304 / **3784** ms | 0 | 105 ms | 976 ms | 314 / 140 KB · 40 |

※ activities 의 LCP 는 "불러오는 중" 로더 — 목록 행이 로더보다 작아 LCP 후보가 되지 않는다. 실제 목록 API 도착은 모바일 H2 ~3.2s.
H2 데스크톱 값(1.3~3.1s)은 로컬 프록시·단일 개발 서버 처리량이 병목이라 표에서 뺐다. `/v2/settings` 경로는 실제 화면이 `/v2/data/settings`.

## 판단
- **CLS**: 전 페이지 0.1 미만(최대 0.071, 플랜 상세 모바일). 조치 없음.
- **LCP(모바일 스로틀)**: 전 페이지 2.5s 초과. 원인(today, H2 타임라인): HTML(0.6s) → 진입·레이아웃 청크(1.6s) → **라우트 노드 청크 2차 웨이브**(SPA fallback HTML 에는 라우트별 preload 가 없어 라우터 실행 후에야 시작, 2.9s) → today API(3.5s) → 렌더(LCP 3.9s). RTT 562ms 에서 직렬 5단계라 구조적 하한이 약 3s. auth/session 은 페이지 로드와 병렬(직렬 아님) 확인.
- **수정(S4-89)**: `ContextChips` 가 마운트 첫 조회 뒤에도 `onChange` 를 불러 오늘 화면이 매 방문 **전체 데이터를 두 번** 불렀다(today·narrative·race-hub·plan 2·trend 3 = 8요청 중복). 첫 조회는 `fetchList` 로 분리(사용자 변경 시에만 `onChange`). 요청 84→76, 544KB. LCP 는 중복 로드가 LCP 이후라 그대로.
- **후보(미착수, 승인 필요)**: ① 라우트 청크 조기 preload(경로→노드 매핑 인라인 또는 prerender 셸) — 1 RTT 절감 ② today 의 핵심 API 를 청크 대기와 병렬로 선요청 ③ activities 페이지 sync-state 3회 요청(Pill·페이지 중복) 정리 ④ 운영 엣지 HTTP/2·압축·immutable 캐시 확인 후 실사용 RTT 기준 재측정.
- 미확인: 운영 프록시 경유 값, INP, 대규모 데이터 DB, 실기기.

## S4-90 개선 — 라우트 청크 조기 preload + 핵심 API 선요청 (2026-11-12)

후보 ①②를 구현했다. 빌드 후처리 `frontend/scripts/route-preload.mjs`(`npm run build` = `vite build && node scripts/route-preload.mjs`)가
SvelteKit 서버 산출물(`manifest.js` 라우트 정규식·`nodes/N.js` 의 imports/stylesheets — 실행하지 않고 글자로 읽음)로 표를 만들어
`build/index.html` 에 인라인 스크립트 1개(약 6.8KB, gzip 전)를 넣는다. 스크립트는 파싱 시점에
- 현재 경로에 맞는 라우트(첫 매치)의 노드 청크를 `modulepreload`, 노드 CSS 를 `preload as=style` 로 걸고(레이아웃 청크는 HTML 이 이미 걸어 제외),
- `/auth/session`(루트 레이아웃 load 가 기다림)과 `scripts/bootPrefetchRoutes.mjs` 표의 GET(오늘 `/today`, 코치 7건, 플랜 상세·활동 상세(숫자 id 일 때만), 설정 `/settings/mcp-tokens`)을
  `apiFetch` 와 같은 옵션(`Content-Type`·`redirect: manual`)으로 쏴 `window.__rpBoot` 에 둔다.
- `apiFetch` 는 init 없는 GET 이 같은 경로면 그 응답을 **1회만** 넘겨받는다(`lib/api/bootPrefetch.ts`, 20초 지나면 버림). 루트 레이아웃 onMount 에서 남은 선요청을 버린다(이후 이동에 재사용 안 함). 데모 중(sessionStorage 플래그)엔 API 선요청을 하지 않는다(스냅샷 fetch 층 우회 방지).
- CSP: 인라인 스크립트 해시는 서버가 `build/index.html` 에서 매번 계산(`spa_static.inline_script_hashes`) — 콘솔 CSP 위반 0건 확인.
- 인증·동의 흐름: 미인증이면 선요청도 401/리다이렉트를 받고, 레이아웃 load 의 `authRedirect` 가 이전과 같이 이동시킨다(페이지 load 는 원래도 레이아웃과 병렬). 스트리밍 로더는 그대로(선요청은 로더가 **기다리는** 요청만).

**스크립트 위치 실측**(모바일 H2, 5회 중앙값): 머리 맨 앞(theme-init 앞)에 두면 청크·API 가 렌더 차단 CSS 와 대역폭을 다퉈 FCP 2.0→4.1s(today), API 만 맨 앞에 둬도 요청 8건인 coach 는 FCP +0.8s.
`</head>` 앞(CSS 뒤)은 인라인 스크립트가 CSS 도착까지 실행을 기다려 이득이 줄었다. → **첫 stylesheet 링크 바로 앞**으로 확정.

같은 방법(합성 DB 활동 14건, 로컬 HTTP/2+gzip 역프록시, 모바일 slow-4G·CPU 4x, 페이지당 새 컨텍스트 5회 중앙값). 이전 열은 같은 날 같은 서버에서 후처리만 뺀 빌드(`vite build`)로 다시 잰 값:

| 페이지 | 모바일 LCP H2 이전 → **이후** | 모바일 FCP 이전 → 이후 | 모바일 CLS(최대) 이후 | 데스크톱 LCP(H1) 이전 → 이후 | 요청 수(이후) |
|---|---|---|---|---|---|
| /v2/today | 5012 → **4060** ms | 2104 → 2176 | 0 | 2088 → 2004 | 76(동일) |
| /v2/library/activities ※ | 2264 → **2196** | 2264 → 2196 | 0 | 236 → 208 | 53 |
| /v2/library/100 | 4804 → **4064** | 2188 → 2116 | 0 | 1832 → 1792 | 67 |
| /v2/coach | 3996 → **3584** | 2288 → 2160 | 0 | 1540 → 1692 | 58 |
| /v2/coach/plan/1 | 4044 → **3004** | 2308 → 2296 | 0.071 (0.071) | 1388 → 1208 | 56 |
| /v2/data/settings | 3636 → **2792** | 1872 → 2352 | 0 | 908 → 884 | 40 |

※ activities 의 LCP 는 여전히 "불러오는 중" 로더(목록 API 는 선요청 표에 없음 — 쿼리스트링이 붙는 목록 요청이라 제외).
요청 수가 이전과 같다 = 선요청 응답을 로더가 실제로 넘겨받았다(이중 요청 없음). 데스크톱(무스로틀)은 변화가 잡음 수준(±150ms).
전송량은 HTML +약 2KB(gzip) 외 동일. 브라우저 확인(375×812·1280×900, today·coach·플랜 상세·활동 상세·설정): CLS ≤0.052, 콘솔 오류·CSP 위반 0, 부트 스플래시 제거·`__rpBoot` 정리 확인.

- **판단**: 모바일 LCP 0.4~1.0s 단축(5페이지), 그래도 2.5s 초과 — 남은 병목은 slow-4G 대역폭(JS 약 160~240KB gzip)과 CPU 4x 실행. 다음 후보: ③ sync-state 중복 요청 정리(활동 상세·코치·플랜 상세에서도 2회 확인), JS 청크 크기 감축(레이아웃 공통 청크 분석), ④ 운영 엣지 경유 재측정.
- 미확인(이전과 동일): 운영 프록시 경유 값, INP, 대규모 데이터 DB, 실기기. 데모 모드 새로고침 시 오늘 화면 API 가 데모 층 설치 전에 실제 서버로 나가는 것은 후처리 전 빌드에서도 같았다(기존 경합, 이번 변경과 무관).
