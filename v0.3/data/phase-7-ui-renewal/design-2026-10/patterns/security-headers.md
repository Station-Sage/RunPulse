# 설계: 보안 헤더·정적 응답 정책 (E-01, E-04)

> 상태: 설계 초안 (미승인). 근거: `ux-review-2026-10/07-entry-common.md` E-01, E-04.
> 관련 설계: `server-input-origin-validation.md`(Origin 관문 `request_guard`, 세션 쿠키 속성). 이 문서는 그 영역을 다시 설계하지 않는다.

## 1. 근본 원인

1. **앱 전역 "응답 정책" 계층이 없다.** 헤더는 라우트마다 손으로 붙인다(`Cache-Control`이 `serve_v2`, 캘린더 피드, MCP, coach SSE에 따로 흩어져 있음). 그래서 CSP, `X-Frame-Options`/`frame-ancestors`, `nosniff`, `Referrer-Policy`처럼 모든 응답에 붙어야 하는 헤더를 둘 곳이 없다(E-01). 사용자 데이터 화면이 프레임에 들어갈 수 있어 클릭재킹이 가능하다.
2. **`serve_v2`가 "자산 경로"와 "클라이언트 라우트"를 구분하지 않는다.** `src/web/app.py` `serve_v2`는 파일이 없으면 무조건 `index.html`을 200으로 돌려준다. `_app/*.js`, `favicon.ico`, `manifest` 요청에도 HTML이 간다(E-04). 게다가 `_app/` 아래 전부를 `immutable, max-age=1y`로 캐시하는데, SvelteKit의 빌드 버전 파일 `_app/version.json`도 여기에 들어간다. 그러면 클라이언트가 새 배포를 감지하는 신호가 1년 동안 캐시되어 막힌다. 클라이언트 쪽에도 청크 로드 실패 시 복구(전체 새로고침) 경로가 없다.

## 2. 설계안 (추천: A안)

### 2.1 응답 정책 모듈 — `src/web/response_policy.py` (신규)
- `init_response_policy(app)`: `after_request` 1개를 등록한다. `create_app`에서 `request_guard` 초기화 바로 뒤에 호출한다.
- `classify_surface(path) -> str`: 응답을 `"v2"`(`/v2/`), `"api"`(`/api/`, `/mcp`), `"feed"`(`/feeds/`), `"v1"`(그 밖의 서버 렌더 HTML)로 나눈다.
- 공통 헤더(모든 표면): `X-Content-Type-Options: nosniff`, `Referrer-Policy`(D5), 프레임 금지(`X-Frame-Options` + CSP `frame-ancestors`, 값은 D3).
- 표면별 CSP(`build_csp(surface, script_hashes) -> str`):
  - `api`/`feed`: `default-src 'none'; frame-ancestors 'none'`. 문서가 아닌 응답이라 가장 엄격하게 둔다.
  - `v2`: `default-src 'self'; script-src 'self' <인라인 부트스트랩 해시>; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; base-uri 'self'; form-action 'self'; object-src 'none'`. `style-src 'unsafe-inline'`은 Svelte style 속성과 `app.html`의 `<div style>` 때문에 필요하다. 집행 모드는 D1.
  - `v1`: 인라인 `<script>`(약 30개 파일), `onclick`, ECharts CDN, Google Fonts를 쓰므로 엄격한 CSP를 걸면 깨진다. 처리는 D2.
- 라우트가 이미 붙인 헤더는 덮어쓰지 않는다(`headers.setdefault`). 기존 `Cache-Control` 테스트를 그대로 지키기 위해서다.
- HSTS는 D4 결과에 따라 설정 플래그 하나로만 켠다.

### 2.2 v2 정적 서빙 분리 — `src/web/spa_static.py` (신규)
- `resolve_v2(build_dir, path) -> (kind, file)`, `kind ∈ {asset, spa, missing}`:
  - 실제 파일이 있으면 `asset`.
  - 파일이 없고 경로가 `_app/`로 시작하거나 알려진 자산 확장자 목록(`.js .css .map .ico .png .svg .webmanifest .json .woff2`)으로 끝나면 `missing` → **404**, `Cache-Control: no-store`, text/plain.
  - 나머지는 `spa` → `index.html`, `no-cache`. 점(`.`)이 들어 있다고 모두 자산으로 보지 않는다. 날짜 같은 딥링크 세그먼트를 지키기 위해서다.
- `cache_control_for(path)`: `immutable, max-age=1y`는 `_app/immutable/`에만 준다. `_app/version.json`과 그 밖의 파일은 `no-cache`다(근본 원인 2 해소).
- `inline_script_hashes(index_path) -> list[str]`: 빌드된 `index.html`의 인라인 `<script>`에서 sha256 해시를 뽑는다. 파일 mtime을 키로 캐시한다. v2 CSP의 `script-src`에 쓰며, 재빌드하면 자동으로 따라간다. SvelteKit `kit.csp`에 기대지 않는 이유는 adapter-static fallback 페이지가 meta CSP를 내보내는지가 확실하지 않아서다. 헤더 쪽을 단일 소스로 둔다.
- `app.py`의 `serve_v2` 본문은 이 모듈 호출 3~4줄로 줄인다.

### 2.3 오래된 탭 복구 — 프론트엔드
- `frontend/vite.config.ts`의 sveltekit 옵션에 `version: { pollInterval }`을 추가한다(값은 D8).
- `frontend/src/hooks.client.ts`(신규)에 `vite:preloadError`와 동적 import 실패를 받는 핸들러를 둔다. 같은 빌드에서는 새로고침을 1회만 하도록 `sessionStorage` 키로 무한 루프를 막는다. 판정 함수 `shouldReload(storage, buildId) -> bool`은 따로 export해서 테스트한다.
- 조용히 자동 새로고침할지, "새 버전" 알림을 띄울지는 D8에서 정한다.

## 3. 변경 파일 표

| 파일 | 구분 | 인터페이스 / 내용 | 예상 줄 |
|---|---|---|---|
| `src/web/response_policy.py` | 신규 | `init_response_policy`, `classify_surface`, `build_csp`, `common_headers` | ~110 |
| `src/web/spa_static.py` | 신규 | `resolve_v2`, `cache_control_for`, `inline_script_hashes`, `serve_v2_response` | ~80 |
| `src/web/app.py` | 수정 | `serve_v2` 본문 위임, `init_response_policy(app)` 호출 (파일이 이미 1161줄이라 순감) | -12/+5 |
| `frontend/src/hooks.client.ts` | 신규 | `shouldReload`, preloadError 핸들러 | ~35 |
| `frontend/vite.config.ts` | 수정 | `version.pollInterval` | +3 |
| `tests/test_response_policy.py` | 신규 | 표면 분류, 표면별 CSP, 공통 헤더, 라우트 헤더 보존(setdefault), SSE 응답 | ~120 |
| `tests/test_spa_static.py` | 신규 | 404/200 분기, 딥링크 보존, 캐시 규칙(version.json), 해시 추출·mtime 캐시 | ~90 |
| `frontend/tests/reload-guard.test.ts` | 신규 | `shouldReload` 1회 보장 | ~30 |

모든 신규 파일은 300줄 이하이고, 함수마다 테스트가 최소 1개씩 있다.

## 4. 적용 순서·검증

1. **`spa_static` 분리(E-04 서버)**: pytest로 `/v2/_app/immutable/x.js`와 `/v2/favicon.ico`가 404인지, `/v2/today`와 `/v2/activity/2026.10.01`이 200 HTML인지, `_app/version.json`이 `no-cache`인지 확인한다. 브라우저에서는 `npm run build` 후 DevTools Network로 확인한다.
2. **`response_policy` 공통 헤더 + api/feed CSP**: 전체 pytest를 돌려 기존 `Cache-Control` 단언(캘린더, MCP, coach SSE)이 그대로 통과하는지 본다. `curl -I`로 `/api/v1/...`, `/feeds/cal/...`를 확인한다.
3. **v2 CSP(D1 모드로)**: Flask 서빙 빌드(5173 dev 서버는 Flask를 거치지 않으니 검증 대상이 아니다)로 v2 주요 화면(today, coach, library, data, welcome)을 돌며 콘솔에 CSP 위반이 0건인지 본다. SSE(coach)와 차트가 정상인지도 확인한다.
4. **v1 처리(D2)**: v1 대시보드, 동기화, 임포트 화면에서 기능이 회귀하지 않았는지 확인한다.
5. **오래된 탭 복구**: 빌드 A로 탭을 연다 → 빌드 B로 재빌드한다 → 탭에서 내비게이션한다 → 1회 새로고침 후 정상 화면이 나오는지, 반복 새로고침이 없는지 확인한다.
6. 완료 후 `decisions.md`에 ADR-048(응답 정책 계층)을 기록하고 `check_docs.py`를 실행한다.

### 호환성·v1 의존
- v1 서버 렌더 HTML은 인라인 스크립트, 인라인 핸들러, CDN(ECharts, Google Fonts)에 의존한다. v2와 같은 CSP를 걸면 깨지므로 표면을 분리했고, v1 제거 시 `"v1"` 분기만 삭제하면 된다.
- 프레임 금지는 저장소에서 자체 페이지를 iframe으로 넣는 곳을 찾지 못했으므로 회귀 위험이 낮다. 외부 서비스가 임베드하는지는 확인되지 않았다.
- `Referrer-Policy`를 `no-referrer`로 정하면 `request_guard`의 Referer 대체 판정이 무력화된다. D5는 그쪽 D1과 함께 정해야 한다.
- 지금까지 `/v2/<없는 자산>`이 HTML 200을 받던 동작은 404로 바뀐다. 이것이 의도한 변경이다.

## 5. 대안 비교

| 안 | 내용 | 장점 | 단점 |
|---|---|---|---|
| **A (추천)** | 자체 `after_request` 모듈 + `spa_static` 분리 | 의존성 0, 표면별 정책·라우트 헤더 보존을 직접 제어, pytest로 검증 가능 | 헤더 목록 유지보수 책임 |
| B | `flask-talisman` 도입 | 검증된 기본값, HSTS·nonce 지원 | 새 의존성, 기본 `force_https`가 로컬을 깨뜨림, nonce는 Jinja 대상이라 정적 SPA와 문자열 HTML v1에는 이점이 없음, 표면별 CSP는 데코레이터를 흩뿌려야 함. E-04는 해결 못 함 |
| C | 리버스 프록시(nginx 등)에서 헤더 부여 | 앱 코드 무변경 | 저장소에 프록시 설정이 없어 배포 환경마다 다름, 테스트 불가, 표면별 CSP 해시 자동화 불가. E-04는 해결 못 함 |

## 6. 결정 필요

| ID | 항목 | 선택지 · 장단점 |
|---|---|---|
| D1 | v2 CSP 집행 모드 | (a) 즉시 enforce: 바로 보호되지만 누락된 출처가 있으면 화면이 깨짐 / (b) 일정 기간 `Report-Only` 후 enforce: 안전하지만 보호가 늦어짐 |
| D2 | v1 표면 CSP | (a) CSP 없이 공통 헤더만: v1 무회귀, 제거 예정이라 투자 최소 / (b) `'unsafe-inline'`+CDN 허용 목록으로 enforce: 클릭재킹 외 보호 효과는 작음 / (c) Report-Only만 |
| D3 | 프레임 정책 | `DENY`/`'none'`(가장 안전) vs `SAMEORIGIN`/`'self'`(향후 자체 임베드 여지) |
| D4 | HSTS | (a) 앱에서 송출(설정 플래그, max-age 값 필요) / (b) 프록시에 위임 / (c) 미송출. HTTP 로컬 사용 시 영향 고려 |
| D5 | Referrer-Policy 값 | `strict-origin-when-cross-origin`(호환성 높음) / `same-origin`(외부 유출 0, Referer 대체 판정 유지) / `no-referrer`(request_guard 대체 판정 불가) |
| D6 | CSP 위반 보고 | (a) 수집 안 함 / (b) `/api/v1/csp-report` 로그 전용 엔드포인트 추가(Origin 관문 면제 목록 갱신 필요) |
| D7 | favicon·manifest | (a) 404만 반환 / (b) 실제 파일 추가(E-21과 합쳐 처리) |
| D8 | 새 버전 감지 UX | (a) 청크 실패 시 조용히 1회 새로고침 / (b) "새 버전" 알림 후 사용자 새로고침 / pollInterval 값(0=폴링 안 함 포함) |
| D9 | 추가 헤더 범위 | `Permissions-Policy`, `Cross-Origin-Opener-Policy` 포함 여부 |

## 7. 범위 밖 메모
- E-21: description, theme-color, apple-touch-icon 누락과 비표준 `text-scale` meta는 메타 정비 작업에서 다룬다.
- 세션 쿠키 `Secure/SameSite/HttpOnly`, Origin/CSRF 검사는 `server-input-origin-validation.md`에서 다룬다.
- v1 HTML의 문자열 조립 XSS 여부는 이번에 점검하지 않았다(CSP는 완화책일 뿐 대체가 아니다).
