# 설계: 보안 헤더·정적 응답 정책 (E-01, E-04)

> 상태: 설계 확정 (구현 전). D1~D9 결정 완료(2026-10-11, `decisions-table.md` SEC-1~9). 2026-10-11 설계서 동기화. 근거: `ux-review-2026-10/07-entry-common.md` E-01, E-04.
> 관련 설계: `server-input-origin-validation.md`(Origin 관문 `request_guard`, 세션 쿠키 속성). 이 문서는 그 영역을 다시 설계하지 않는다.

## 1. 근본 원인

1. **앱 전역 "응답 정책" 계층이 없다.** 헤더는 라우트마다 손으로 붙인다(`Cache-Control`이 `serve_v2`, 캘린더 피드, MCP, coach SSE에 따로 흩어져 있음). 그래서 CSP, `X-Frame-Options`/`frame-ancestors`, `nosniff`, `Referrer-Policy`처럼 모든 응답에 붙어야 하는 헤더를 둘 곳이 없다(E-01). 사용자 데이터 화면이 프레임에 들어갈 수 있어 클릭재킹이 가능하다.
2. **`serve_v2`가 "자산 경로"와 "클라이언트 라우트"를 구분하지 않는다.** `src/web/app.py` `serve_v2`는 파일이 없으면 무조건 `index.html`을 200으로 돌려준다. `_app/*.js`, `favicon.ico`, `manifest` 요청에도 HTML이 간다(E-04). 게다가 `_app/` 아래 전부를 `immutable, max-age=1y`로 캐시하는데, SvelteKit의 빌드 버전 파일 `_app/version.json`도 여기에 들어간다. 그러면 클라이언트가 새 배포를 감지하는 신호가 1년 동안 캐시되어 막힌다. 클라이언트 쪽에도 청크 로드 실패 시 복구 경로가 없다.

## 2. 설계안 (A안 확정)

### 2.1 응답 정책 모듈 — `src/web/response_policy.py` (신규)
- `init_response_policy(app)`: `after_request` 1개를 등록한다. `create_app`에서 `request_guard` 초기화 바로 뒤에 호출한다.
- `classify_surface(path) -> str`: 응답을 `"v2"`(`/v2/`), `"api"`(`/api/`, `/mcp`), `"feed"`(`/feeds/`), `"v1"`(그 밖의 서버 렌더 HTML)로 나눈다.
- 공통 헤더(모든 표면): `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`(D5), `X-Frame-Options: DENY`(D3), `Permissions-Policy`(D9, 앱이 쓰지 않는 기능을 빈 허용 목록으로 차단 — 항목은 구현 시 확정). COOP는 보내지 않는다.
- 표면별 CSP(`build_csp(surface, script_hashes) -> str | None`), 모든 CSP에 `frame-ancestors 'none'`(D3):
  - `api`/`feed`: `default-src 'none'; frame-ancestors 'none'`. 문서가 아닌 응답이라 가장 엄격하게 enforce.
  - `v2`: `default-src 'self'; script-src 'self' <인라인 부트스트랩 해시>; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; base-uri 'self'; form-action 'self'; object-src 'none'; frame-ancestors 'none'; report-uri /api/v1/csp-report`. `style-src 'unsafe-inline'`은 Svelte style 속성과 `app.html`의 `<div style>` 때문에 필요하다.
  - `v2` 집행 모드(D1): 설정값 `CSP_V2_MODE ∈ {report-only, enforce}`. 초기 `report-only`(`Content-Security-Policy-Report-Only` 헤더)로 운영하고, 위반 로그가 정리되면 `enforce`로 전환한다. 단, `frame-ancestors`는 Report-Only에서 무시되므로 프레임 보호는 `X-Frame-Options: DENY`가 처음부터 맡는다.
  - `v1`(D2): CSP 없음(`None`). 이 분기의 처리(일몰 시 제거·지금 제거·유지)는 **보류(V1-4, 설계 검토 필요)** — §10.
- 라우트가 이미 붙인 헤더는 덮어쓰지 않는다(`headers.setdefault`). 기존 `Cache-Control` 테스트를 그대로 지키기 위해서다.
- HSTS는 앱에서 송출하지 않는다(D4, Cloudflare 프록시에 위임).

### 2.2 CSP 위반 보고 — `src/api/routes_csp_report.py` (신규, D6)
- `POST /api/v1/csp-report`: 본문(`application/csp-report`, `application/reports+json`)을 크기 제한(예: 16KB) 안에서 읽어 로그에 남기고 `204`를 반환한다. DB 저장 없음.
- `request_guard` 면제 목록에 추가한다(브라우저 보고는 Origin을 보장하지 않음). 로그 남용 방지를 위해 본문 크기 상한·필드 절삭만 둔다.

### 2.3 v2 정적 서빙 분리 — `src/web/spa_static.py` (신규)
- `resolve_v2(build_dir, path) -> (kind, file)`, `kind ∈ {asset, spa, missing}`:
  - 실제 파일이 있으면 `asset`.
  - 파일이 없고 경로가 `_app/`로 시작하거나 알려진 자산 확장자 목록(`.js .css .map .ico .png .svg .webmanifest .json .woff2`)으로 끝나면 `missing` → **404**, `Cache-Control: no-store`, text/plain.
  - 나머지는 `spa` → `index.html`, `no-cache`. 점(`.`)이 들어 있다고 모두 자산으로 보지 않는다. 날짜 같은 딥링크 세그먼트를 지키기 위해서다.
- `cache_control_for(path)`: `immutable, max-age=1y`는 `_app/immutable/`에만 준다. `_app/version.json`과 그 밖의 파일은 `no-cache`다(근본 원인 2 해소).
- `inline_script_hashes(index_path) -> list[str]`: 빌드된 `index.html`의 인라인 `<script>`에서 sha256 해시를 뽑는다. 파일 mtime을 키로 캐시한다. SvelteKit `kit.csp`에 기대지 않는 이유는 adapter-static fallback 페이지가 meta CSP를 내보내는지가 확실하지 않아서다. 헤더 쪽을 단일 소스로 둔다.
- `app.py`의 `serve_v2` 본문은 이 모듈 호출 3~4줄로 줄인다.
- favicon·manifest(D7): 404 처리만이 아니라 `frontend/static/`에 `favicon.ico`, `manifest.webmanifest`, `apple-touch-icon.png`를 실제로 추가하고 `app.html`에 `theme-color`·`apple-touch-icon`·manifest 링크를 넣는다. E-21 메타 정비와 함께 처리하며 아이콘 디자인이 선행되어야 한다.

### 2.4 오래된 탭 복구 — 프론트엔드 (D8)
- `frontend/vite.config.ts`의 sveltekit 옵션에 `version: { pollInterval }`을 추가한다(값은 구현 시 정함).
- `frontend/src/hooks.client.ts`(신규)·레이아웃: SvelteKit `updated` 스토어가 참이 되거나 `vite:preloadError`·동적 import 실패가 나면 자동 새로고침하지 않고 "새 버전이 있습니다 — 새로고침" 알림을 띄운다. 사용자가 누를 때만 새로고침한다. 판정 함수 `shouldNotify(storage, buildId) -> bool`은 같은 빌드에서 알림을 중복 표시하지 않도록 `sessionStorage` 키를 쓰며, 따로 export해서 테스트한다.

## 3. 변경 파일 표

| 파일 | 구분 | 인터페이스 / 내용 | 예상 줄 |
|---|---|---|---|
| `src/web/response_policy.py` | 신규 | `init_response_policy`, `classify_surface`, `build_csp`, `common_headers`, `CSP_V2_MODE` | ~120 |
| `src/web/spa_static.py` | 신규 | `resolve_v2`, `cache_control_for`, `inline_script_hashes`, `serve_v2_response` | ~80 |
| `src/api/routes_csp_report.py` | 신규 | 로그 전용 보고 수신, 크기 상한 | ~40 |
| `src/web/request_guard.py` | 수정 | 면제 목록에 `/api/v1/csp-report` | +1 |
| `src/web/app.py` | 수정 | `serve_v2` 본문 위임, `init_response_policy(app)` 호출 (파일이 이미 1161줄이라 순감) | -12/+5 |
| `frontend/static/*`, `frontend/src/app.html` | 신규/수정 | favicon·manifest·apple-touch-icon 파일, theme-color 등 메타 | 자산 + ~5 |
| `frontend/src/hooks.client.ts` | 신규 | `shouldNotify`, preloadError 핸들러 | ~35 |
| `frontend/src/lib/components/UpdateNotice.svelte` | 신규 | "새 버전" 알림 UI(문구·위치는 product 영역) | ~30 |
| `frontend/vite.config.ts` | 수정 | `version.pollInterval` | +3 |
| `tests/test_response_policy.py` | 신규 | 표면 분류, 표면별 CSP·Report-Only 전환, 공통 헤더(Permissions-Policy, HSTS 없음), setdefault 보존, SSE | ~130 |
| `tests/test_csp_report.py` | 신규 | 204, Origin 없이 통과, 크기 상한 | ~40 |
| `tests/test_spa_static.py` | 신규 | 404/200 분기, 딥링크 보존, 캐시 규칙(version.json), 해시 추출·mtime 캐시, favicon 200 | ~90 |
| `frontend/tests/update-notice.test.ts` | 신규 | `shouldNotify` 중복 방지 | ~30 |

모든 신규 파일은 300줄 이하이고, 함수마다 테스트가 최소 1개씩 있다.

## 4. 적용 순서·검증

1. **`spa_static` 분리(E-04 서버)**: pytest로 `/v2/_app/immutable/x.js`가 404인지, `/v2/today`와 `/v2/activity/2026.10.01`이 200 HTML인지, `_app/version.json`이 `no-cache`인지 확인한다. 브라우저에서는 `npm run build` 후 DevTools Network로 확인한다.
2. **`response_policy` 공통 헤더 + api/feed CSP + csp-report**: 전체 pytest를 돌려 기존 `Cache-Control` 단언(캘린더, MCP, coach SSE)이 그대로 통과하는지 본다. `curl -I`로 `/api/v1/...`, `/feeds/cal/...`에 `X-Frame-Options: DENY`, `Referrer-Policy`, `Permissions-Policy`가 있고 `Strict-Transport-Security`가 없는지 확인한다. Origin 없는 `POST /api/v1/csp-report` → 204.
3. **v2 CSP Report-Only**: Flask 서빙 빌드(5173 dev 서버는 Flask를 거치지 않으니 검증 대상이 아니다)로 v2 주요 화면(today, coach, library, data, welcome)을 돌며 csp-report 로그를 수집한다. SSE(coach)와 차트가 정상인지도 확인한다.
4. **v2 CSP enforce 전환**: 위반 로그가 정리되면 `CSP_V2_MODE=enforce`. 같은 화면에서 콘솔 CSP 위반 0건을 확인한다.
5. **favicon·manifest(D7)**: 아이콘 자산 추가 후 `/v2/favicon.ico`·manifest 200, 홈 화면 추가 시 아이콘·theme-color 표시.
6. **오래된 탭 복구(D8)**: 빌드 A로 탭을 연다 → 빌드 B로 재빌드한다 → 탭에서 내비게이션한다 → 자동 새로고침 없이 알림이 1회 뜨고, 새로고침 버튼으로 정상 화면이 나오는지 확인한다.
7. 완료 후 `decisions.md`에 응답 정책 계층 ADR을 기록하고(번호는 9절 참조) `check_docs.py`를 실행한다.

### 호환성
- 프레임 DENY는 저장소에서 자체 페이지를 iframe으로 넣는 곳을 찾지 못했으므로 회귀 위험이 낮다. 외부 서비스가 임베드하는지는 확인되지 않았다.
- `Referrer-Policy: strict-origin-when-cross-origin`은 같은 출처 요청에 Referer 전체를 보내므로 `request_guard`의 Referer 대체 판정과 충돌하지 않는다(SRV-1과 정합).
- HSTS는 Cloudflare 설정에 의존한다. 로컬 HTTP 사용에는 영향이 없다.
- 지금까지 `/v2/<없는 자산>`이 HTML 200을 받던 동작은 404로 바뀐다. 이것이 의도한 변경이다.

## 5. 대안 비교

| 안 | 내용 | 장점 | 단점 |
|---|---|---|---|
| **A (채택)** | 자체 `after_request` 모듈 + `spa_static` 분리 | 의존성 0, 표면별 정책·라우트 헤더 보존을 직접 제어, pytest로 검증 가능 | 헤더 목록 유지보수 책임 |
| B | `flask-talisman` 도입 | 검증된 기본값, HSTS·nonce 지원 | 새 의존성, 기본 `force_https`가 로컬을 깨뜨림, nonce는 Jinja 대상이라 정적 SPA에는 이점이 없음, 표면별 CSP는 데코레이터를 흩뿌려야 함. E-04는 해결 못 함 |
| C | 리버스 프록시(nginx 등)에서 헤더 부여 | 앱 코드 무변경 | 저장소에 프록시 설정이 없어 배포 환경마다 다름, 테스트 불가, 표면별 CSP 해시 자동화 불가. E-04는 해결 못 함 |

## 6. 결정됨 (2026-10-11, `decisions-table.md` SEC-1~9)

- **D1 (SEC-1)** v2 CSP는 Report-Only 후 enforce — 누락 출처로 화면이 깨지는 위험을 먼저 관찰.
- **D2 (SEC-2)** v1은 CSP 없이 공통 헤더만. `classify_surface` `"v1"` 분기의 일몰 처리는 V1-4 보류(§10).
- **D3 (SEC-3)** 프레임 `DENY` / `frame-ancestors 'none'` — 자체 임베드 수요가 없어 가장 안전한 값.
- **D4 (SEC-4)** HSTS는 Cloudflare 프록시에 위임, 앱 미송출 — 로컬 HTTP 영향 제거.
- **D5 (SEC-5)** `Referrer-Policy: strict-origin-when-cross-origin` — 호환성 높고 Referer 대체 판정 유지.
- **D6 (SEC-6)** 로그 전용 `/api/v1/csp-report` 추가, Origin 관문 면제 목록 갱신 — D1 관찰에 필요.
- **D7 (SEC-7)** favicon·manifest·theme-color·apple-touch-icon 실제 파일 추가(E-21과 함께, 아이콘 디자인 필요).
- **D8 (SEC-8)** "새 버전" 알림 후 사용자가 새로고침, pollInterval 값은 구현 시 정함 — 입력 중 데이터 유실 방지.
- **D9 (SEC-9)** `Permissions-Policy`만 추가, COOP는 OAuth 팝업 영향 검증 전까지 보류.

## 7. 범위 밖 메모
- E-21: description, 비표준 `text-scale` meta는 메타 정비 작업에서 다룬다(아이콘·theme-color는 D7로 이 작업과 함께 처리).
- 세션 쿠키 `Secure/SameSite/HttpOnly`, Origin/CSRF 검사는 `server-input-origin-validation.md`에서 다룬다.
- 레거시 v1 HTML: UI·라우트 일몰 예정(V1-1 정정·V1-2), 점검 범위 밖.
- COOP 도입 — OAuth 팝업 영향 검증 후 재검토(D9).

## 8. 변경 이력
- 초안 작성.
- 2026-10-11 설계서 동기화: D1~D9 결정(SEC-1~9) 반영 — Report-Only→enforce 단계, v1 CSP 제외, DENY, HSTS 위임, csp-report 엔드포인트·면제, 아이콘 자산, 새 버전 알림 UX, Permissions-Policy.
- 2026-10-11 4차 동기화(V1-1): 레거시 v1 고려 제거 — 4절 v1 무회귀 단계·호환성 v1 항목·테스트 'v1 CSP 없음' 삭제, D2·2.1 `v1` 분기·7절 v1 XSS 메모·대안 B 'v1' 언급 축약/삭제.
- 2026-10-11 5차 동기화(V1-1 정정·V1-3·V1-4): 일몰 = UI·라우트 일몰. `"v1"` 분기를 V1-4 보류 열린 항목으로 명시(2.1·D2·§10), 사용자 전환 v2 이관(V1-3)에 따른 표면 변화 기록(§10).
- 2026-10-11 6차 동기화(V1-8·V1-9·V1-10, V1-4 보류 유지): §10 사용자 전환 항목의 엔드포인트 표면 단정을 경로 규칙 의존으로 완화(경로는 구현 단계 제안), SRV-6 적용 시점(이관과 같은 변경) 반영, `src/web` 공용 4파일 view 밖 이관의 영향(없음) 명시.

## 9. 동기화 중 발견한 충돌/확인 필요
- ADR 번호: 초안 4절이 ADR-048을 "응답 정책 계층"에 배정했으나, `decisions-table.md` SRV-9가 ADR-048 후보를 "쓰기 요청 Origin 관문 + 경계 스키마"로 확정했다. 이 문서의 ADR 번호 배정이 필요하다.
- D1 Report-Only 운영 기간과 enforce 전환 기준이 결정에 없다(SRV-8 관찰 기간도 미정).
- D6 엔드포인트는 브라우저 보고 형식(`application/csp-report`)을 받으므로 `server-input-origin-validation.md` D5(비JSON 415) 적용 대상에서 빼야 한다.
- D7은 아이콘 디자인이 선행 조건이며 담당·일정이 정해지지 않았다.
- D9 `Permissions-Policy`의 구체 항목 목록은 결정에 없다(구현 시 확정으로 둠).
- D8 알림 문구·위치는 product 영역이며 이 문서에서 확정하지 않았다.

## 10. 동기화 중 발견한 모호점
- **(V1-4, 열린 항목 — 보류)** `classify_surface`의 `"v1"` 분기(그 밖의 서버 렌더 HTML → CSP 없음, D2/SEC-2) 처리는 미결정: (a) 일몰 시 제거·그 전까지 유지 / (b) 지금 제거 / (c) 유지. V1-2의 일몰 정의(UI·라우트 일몰)와 함께 설계 검토 후 결정한다. 검토 입력(사실): D2의 근거는 v1 서버 렌더 HTML이 인라인 스크립트·인라인 핸들러·CDN(ECharts, Google Fonts)에 의존한다는 것(초안 호환성 절). `"v1"`은 `/v2/`·`/api/`·`/mcp`·`/feeds/` 이외 경로 전체의 폴백 표면이라, v1 화면 라우트가 사라져도 남는 비API 경로(예: `app.py`의 `/trigger-sync`·`/bg-sync/*`·`/sync-status`·`/import/*`)와 미정의 경로 404 응답이 어느 표면·정책을 받을지가 분기 제거 시 함께 정해져야 한다. 2026-10-11 grep 기준 v2 프론트(`frontend/src`)는 이 v1 경로들을 호출하지 않는다(`/switch-user` 링크 1건 제외).
- (V1-3 정합) 사용자 전환은 v2 로 이관한 뒤 v1 `/switch-user`를 제거한다(`server-input-origin-validation.md` 2.5). 현재 `/switch-user`는 `"v1"` 표면(CSP 없음)이다. 이관 후 v2 엔드포인트 경로·화면 위치는 구현 단계에서 제안하므로(V1-8 (c)) 받을 표면은 `classify_surface`의 경로 규칙을 그대로 따른다(예: `/api/` 아래면 `"api"`, `/v2/` 아래 화면이면 `"v2"`) — 이 문서의 추가 변경은 없다. SRV-6 production 차단(404)은 v2 이관과 같은 변경에서 그 엔드포인트에 적용되며(V1-9 (b)) 같은 표면 정책을 받는다.
- (V1-10 영향) `src/web` 공용 4파일(`bg_sync.py`·`helpers.py`·`auto_sync.py`·`views_mcp_remote.py`)은 이번 작업에서 모두 view 밖으로 이관된다(새 위치 미정). 이 문서는 네 파일을 경로로 참조하지 않는다 — §10 V1-4 항목의 `/bg-sync/*`·`/trigger-sync` 등은 `app.py`의 URL 경로이고 `/mcp` 표면 분류도 URL 경로 기준이라, 모듈 이관은 `classify_surface`·CSP 판정, 이 문서의 파일 경로·테스트(`test_response_policy.py` 등) 범위, import 경로 어느 것에도 영향이 없다. 단, 이 문서의 신규 `src/web/response_policy.py`·`src/web/spa_static.py`는 V1-10 대상이 아니며 `src/web/` 위치 유지 여부는 결정 기록이 없다(열린 항목).
