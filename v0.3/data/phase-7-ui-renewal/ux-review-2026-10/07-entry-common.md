# UX 검토 2026-10 / 묶음 7 진입·공통 (식별만, 수정 없음)

검증 환경: DB 사본 서버(실DB 사본 5071, 빈 DB 5072), Playwright Chromium 375/768/1280, curl 헤더 점검. 운영 데이터 무변경.
공유 이슈 인용: D-22, D-25, D-26, C-03 (기존 문서 ID).

| ID | 화면/카드/항목 | 관점 | 증상 | 재현 | 심각도 |
|---|---|---|---|---|---|
| E-01 | 전 응답(Flask) | 7 보안 | CSP, X-Frame-Options, nosniff, Referrer-Policy 헤더가 전혀 없음. 클릭재킹 가능 | `curl -I /v2/today` | 상 |
| E-02 | 세션 쿠키/전역 POST | 7 보안 | 쿠키에 SameSite/Secure 미지정, Origin 검증 없음 (D-22 동일). `/switch-user`로 세션 사용자 전환이 폼 입력만으로 가능, 입력 검증 없이 `init_db(uid)` 실행, option value 이스케이프 없음 | `curl -i /v2/today`의 Set-Cookie 확인, `/switch-user` 코드 | 상 |
| E-03 | 인증 실패(운영) | 3/7 | CF 헤더가 없으면 text/plain 401만 표시. 로그인 안내·재시도 UI 없음 | production 설정에서 헤더 없이 접근 | 중 |
| E-04 | 존재하지 않는 `_app/*.js`, favicon.ico, manifest | 5/3 | SPA fallback이 200 text/html을 반환. 배포 후 오래된 탭이 옛 청크를 요청하면 HTML을 JS로 파싱하다 실패해 화면이 깨짐. 복구용 reload 처리 없음 | `curl -I /v2/_app/immutable/x.js` | 상 |
| E-05 | 알 수 없는 경로 `/v2/nope/x` | 3 | HTTP 200으로 404 화면을 표시 (검색엔진/모니터링에서 구분 불가). 문서 title은 빈 값 | `/v2/nope/x` | 하 |
| E-06 | `+error.svelte`(404/500) | 4 | `<title>`이 빈 값, h1 없음(제목은 h2 이하) | `/v2/nope/x`의 `document.title` | 중 |
| E-07 | 전역 레이아웃 | 4 | 건너뛰기 링크(skip link) 없음. 첫 Tab이 메뉴, 두 번째가 Garmin 필 → 본문까지 2~3번 더 거침 | `/v2/today`에서 Tab 연타 | 중 |
| E-08 | MenuDrawer | 4 | Esc로 닫히지 않음, 열린 직후 포커스가 드로어 안으로 이동하지 않음(메뉴 버튼에 남음), 포커스 복귀·스크롤 잠금(body overflow visible)·배경 inert 없음. aria-modal=true인데 실제 동작은 비모달 (D-25/C-03 계열) | 메뉴 클릭 → Esc, 활성 요소·body overflow 확인 | 상 |
| E-09 | MenuDrawer 항목 | 4/3 | 14개 항목 중 모든 링크/버튼 높이 44px 미만(touch target). "닫기"가 두 곳에 중복 | 375px에서 getBoundingClientRect | 중 |
| E-10 | MenuDrawer v1 링크 | 3 | v1 링크가 base 없는 절대경로 + `data-sveltekit-reload`(전체 새로고침). 되돌아오는 링크 일부는 `/v2/data` 하나뿐이라 v1↔v2 이동 일관성 낮음 | 드로어 링크 href 목록 | 하 |
| E-11 | `backToV1()` | 3 | PATCH `ui_default:'v1'` 실패해도 finally에서 `/dashboard`로 이동 → 다음 접속 때 v2로 되돌아와 선택이 무시됨, 실패 안내 없음 | PATCH 차단 후 "기존 화면" 클릭 | 중 |
| E-12 | 용어 | 6 | 하단 탭 Today/Library/Coach는 영어, 내용은 한국어. v1 이동 라벨이 "기존 화면(v1)"과 "이전 화면으로(v1)"로 혼재. 404의 "Today로" | 하단 nav, 드로어, 404 화면 | 하 |
| E-13 | SyncStatusPill | 1/3 | "▲ Garmin 확인 필요"가 welcome·404·에러 화면에서도 노출. 클릭 시 ?sheet=sync 시트가 열리는 동작을 사용자가 예측하기 어렵고 높이 26px | 모든 라우트 | 중 |
| E-14 | ☰ 버튼/브레드크럼/뒤로 링크 | 4 | ☰ 32x32px, 필 129x26, 브레드크럼 41x16, 뒤로 링크 42x20 등 44px 미만 | 375px에서 측정 | 중 |
| E-15 | 전역 색 토큰 | 4 | fg-muted(#64748b)/surface-1(#0f172a) 대비 3.75:1 (본문 소형 텍스트 기준 4.5 미달). 다크 단일 테마, prefers-color-scheme 대응 없음 | 계산 | 중 |
| E-16 | 로딩 상태 | 5/3 | API를 6초 지연시키면 1.5초 시점에 본문이 비어 있고 스켈레톤/aria-busy/status가 없음 | page.route 지연 + /v2/library | 중 |
| E-17 | 오프라인 | 3 | 오프라인 전환 시 안내/배너 없음 | context.setOffline(true) | 하 |
| E-18 | Today API 실패 | 3 | "오늘 권고를 불러오지 못했어요 / 다시 시도" 표시됨 — 정상. 단 원인(네트워크/서버) 구분 없음 | /api/v1/today abort | 하 |
| E-19 | 랜딩 `/v2/landing` | 1 | 375px에서 scrollWidth 410 > 375, 가로 스크롤 발생 (원인 요소는 뷰포트 밖으로 나간 요소로 검출되지 않아 overflow 컨테이너/negative margin 의심) | 375px 로드 후 scrollWidth | 중 |
| E-20 | 랜딩 초대 링크 | 7/3 | 개인 이메일 주소로 mailto 연결, 폼/대기자 등록 없음 | 랜딩의 두 번째 링크 | 하 |
| E-21 | 메타 | 5/3 | description, theme-color, manifest, apple-touch-icon 없음, favicon.ico는 HTML 200 (E-04). app.html의 `text-scale` meta는 표준 아님 | `<head>` 확인 | 하 |
| E-22 | 데모 격리 | 2/7 | 데모 가로채기는 `/api/v1`만 대상이며 비 API 요청(예: /switch-user, v1 페이지)은 실서버로 통과. 데모 플래그는 sessionStorage이고 같은 쿠키 세션을 공유 → 로그인 상태에서 데모 중에도 실서버 세션이 살아 있음 | demoMode.ts classifyRequest | 중 |
| E-23 | 데모 쓰기 차단 시트 | 4 | Esc 핸들러가 포커스 받지 않는 div에 붙어 Esc로 닫히지 않을 가능성 (코드 정독, 실행 미검증) | DemoBanner.svelte | 하 |
| E-24 | 데모 없는 경로 `/demo?to=/nope` | 3 | 스냅샷에 없는 화면은 404 화면 + 데모 배너가 같이 표시되고 title 빈 값. `to=//evil.com`은 `/v2/today`로 안전하게 처리됨 (문제 없음) | URL 직접 입력 | 하 |
| E-25 | welcome `?step=` | 3 | 4단계 진행 상태가 URL에 반영되지 않아 새로고침/뒤로가기로 단계 복원 불가. 저장 실패는 삼켜져 안내 없음. `?step=9`, `?step=abc`는 첫 단계로 안전하게 폴백 | `/v2/welcome?step=9` | 중 |
| E-26 | 빈 DB 첫 진입 | 3 | 빈 DB 사본에서 `/v2/today`가 `/v2/welcome`으로 리다이렉트되지 않고 Today 빈 상태 화면이 표시됨(onboarding=pending 조건 여부 미확인). 빈 상태 카피 자체는 "데이터 수집 중" 등 정상 | 5072 서버의 `/v2/today` | 중 |
| E-27 | `/v2/library/activities?page=-3` | 3 | 잘못된 page 값이 조용히 처리됨(오류 안내 없음), 월 `2099-99`도 현재 월로 대체 (사용자에게 변경 사실 미고지) | URL 직접 입력 | 하 |
| E-28 | 활동 상세 없음 | 6 | 404 화면 + 상세 쪽의 "활동을 찾을 수 없습니다" 중복, 라벨 "활동(으)로 돌아가기" 조사 처리 어색 | `/v2/library/activities/999999999` | 하 |
| E-29 | 정적 자원 캐시 | 5 | 폰트/스냅샷이 no-cache+ETag (immutable 아님), 폰트 URL이 `/v2/fonts/...`로 하드코딩되어 base 변경 시 깨짐, Flask gzip 미적용 의심(운영 프록시 미확인) | `curl -I /v2/fonts/*`, layout.css | 하 |
| E-30 | `/` 루트 | 3 | `/`는 v1 dashboard로, `/v2/`는 today 307. 시작점이 둘로 갈림 | `curl -I /` | 하 |

## 검증한 항목 (문제 없음 포함)
- `/v2` → `/v2/today` 리다이렉트: 문제 없음.
- demo `to` 파라미터 open redirect(`//evil.com`): 막힘, 문제 없음.
- 404/`metrics/zzz`/활동 없음 직접 진입 시 화면 렌더링 및 pageerror: 크래시 없음.
- 768px: main/nav 폭 768, 가로 스크롤 없음, 문제 없음.
- 375px 로드 시 12개 라우트 콘솔 오류: 랜딩 가로 스크롤 외 특이 없음.
- welcome 잘못된 step 값 폴백: 문제 없음.
- Today API 실패 시 재시도 UI: 존재, 문제 없음.
- 빈 DB의 Today 빈 상태 카피: 문제 없음.
- 랜딩 링크는 모두 `/v2/demo?to=` 형태로 base 포함.

## 미검증
- 드로어 Tab 순환(트랩) 정확 여부: 첫 Tab이 드로어 밖으로 나간 뒤 이후 안쪽으로 순환하는 것까지만 확인, 완전한 트랩 판정 불가.
- 드로어 열기 후 브라우저 뒤로가기 동작: 테스트 페이지 이력 문제로 판정 못 함.
- ?sheet=sync 새로고침/뒤로가기 복원, 토스트·시트 공통 동작(Esc/포커스): 시간 부족.
- welcome 4단계 입력 검증과 단계별 뒤로 동작, onboarding=pending 상태에서의 리다이렉트: 사본 DB 조건 미구성.
- 운영 환경의 gzip/캐시/CF 헤더, 운영 인증 흐름: 운영 접근 금지.
- 로그인한 실제 사용자가 데모 중 실서버 변경 요청을 보낼 수 있는지 실행 검증: 코드 정독만.
