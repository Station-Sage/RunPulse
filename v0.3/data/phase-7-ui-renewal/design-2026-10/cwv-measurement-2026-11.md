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
