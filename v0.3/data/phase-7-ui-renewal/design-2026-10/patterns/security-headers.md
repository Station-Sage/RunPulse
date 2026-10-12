# 설계: 보안 헤더·정적 응답 정책 (E-01, E-04)

> 상태: 설계 확정 (구현 전). D1~D9 결정 완료(2026-10-11, `decisions-table.md` SEC-1~9, D2 의 'v1' 분기는 V1-15 로 제거), 후속 SEC-10·SEC-11 결정 반영. 2026-10-11 설계서 동기화(8차: V1-15·V1-16). 2026-10-12 9차 동기화(SEC-10·SEC-11·SRV-12·ADR-1·NEW-40·V1-18). 2026-10-12 10차 동기화(SEC-12, 설계 단계 마지막). ADR-049(ADR-1). 근거: `ux-review-2026-10/07-entry-common.md` E-01, E-04.
> 관련 설계: `server-input-origin-validation.md`(Origin 관문 `request_guard`, 세션 쿠키 속성). 이 문서는 그 영역을 다시 설계하지 않는다.

## 1. 근본 원인

1. **앱 전역 "응답 정책" 계층이 없다.** 헤더는 라우트마다 손으로 붙인다(`Cache-Control`이 `serve_v2`, 캘린더 피드, MCP, coach SSE에 따로 흩어져 있음). 그래서 CSP, `X-Frame-Options`/`frame-ancestors`, `nosniff`, `Referrer-Policy`처럼 모든 응답에 붙어야 하는 헤더를 둘 곳이 없다(E-01). 사용자 데이터 화면이 프레임에 들어갈 수 있어 클릭재킹이 가능하다.
2. **`serve_v2`가 "자산 경로"와 "클라이언트 라우트"를 구분하지 않는다.** `src/web/app.py` `serve_v2`는 파일이 없으면 무조건 `index.html`을 200으로 돌려준다. `_app/*.js`, `favicon.ico`, `manifest` 요청에도 HTML이 간다(E-04). 게다가 `_app/` 아래 전부를 `immutable, max-age=1y`로 캐시하는데, SvelteKit의 빌드 버전 파일 `_app/version.json`도 여기에 들어간다. 그러면 클라이언트가 새 배포를 감지하는 신호가 1년 동안 캐시되어 막힌다. 클라이언트 쪽에도 청크 로드 실패 시 복구 경로가 없다.

## 2. 설계안 (A안 확정)

### 2.1 응답 정책 모듈 — `src/web/response_policy.py` (신규)
- 위치(V1-16 (c')): `response_policy.py`·`spa_static.py`(2.3)·`request_guard.py`(`server-input-origin-validation.md`)는 `src/web/`(앱 조립 계층, v1 일몰 후에도 유지 — 'src/web = 앱 셸 전용': `app.py`·`auth_cf.py`·이 3파일)에 둔다.
- `init_response_policy(app)`: `after_request` 1개를 등록한다. `create_app`에서 `request_guard` 초기화 바로 뒤에 호출한다.
- `classify_surface(path) -> str`: 응답을 `"v2"`(`/v2/`), `"api"`(`/api/`, `/mcp`), `"feed"`(`/feeds/`)로 나누고, 그 밖 경로는 일반 표면(`"default"`)으로 둔다. **`"v1"` 분기는 두지 않는다**(V1-15 (a), V1-4 해소 — v1 HTML 도 일반 표면 정책을 받는다).
  - 일반 표면(V1-18 (a)): `/v2/`·`/api/`·`/mcp`·`/feeds/` 밖 경로(일몰 전 v1 화면, 일몰 후 남는 `app.py`의 `/trigger-sync`·`/bg-sync/*`·`/sync-status`·`/import*`·`/` 리다이렉트, 미정의 경로 404)는 공통 헤더 + 엄격 CSP 를 받고, CSP 집행 모드는 `v2`와 같은 `CSP_V2_MODE`(Report-Only → enforce) 단계를 따른다. v1 화면이 깨지는 것은 감수(V1-13).
  - 일반 표면 CSP 는 **v2 인라인 부트스트랩 해시를 넣지 않는다**(SEC-12 (a), 엄격): `script-src 'self'`(그 밖 지시어는 `v2`와 같고 `report-uri /api/v1/csp-report` 포함). 해시는 `v2` 표면의 `index.html` 전용 값이다(`build_csp("default", ...)`는 `script_hashes`를 쓰지 않는다).
  - `/api/context-episodes`(`/api/v1` 밖, NEW-40 (b) 현 경로 유지)는 `/api/` 접두 판정이라 `"api"` 표면이다. 표면 판정은 `/api/v1` 접두에 기대지 않으므로 이 경로가 빠지지 않는다 — 테스트로 단언한다(`adjustment-new-signals.md` §2.8·§4 S4).
- 공통 헤더(모든 표면): `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`(D5), `X-Frame-Options: DENY`(D3), `Permissions-Policy: camera=(), microphone=(), geolocation=()`(D9·SEC-11 — 최소 항목: 카메라·마이크·위치 차단). COOP는 보내지 않는다.
- 표면별 CSP(`build_csp(surface, script_hashes) -> str | None`), 모든 CSP에 `frame-ancestors 'none'`(D3):
  - `api`/`feed`: `default-src 'none'; frame-ancestors 'none'`. 문서가 아닌 응답이라 가장 엄격하게 enforce.
  - `v2`: `default-src 'self'; script-src 'self' <인라인 부트스트랩 해시>; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; base-uri 'self'; form-action 'self'; object-src 'none'; frame-ancestors 'none'; report-uri /api/v1/csp-report`. `style-src 'unsafe-inline'`은 Svelte style 속성과 `app.html`의 `<div style>` 때문에 필요하다.
  - `v2` 집행 모드(D1·SEC-10): 설정값 `CSP_V2_MODE ∈ {report-only, enforce}`. 초기 `report-only`(`Content-Security-Policy-Report-Only` 헤더)로 **2주** 운영하고, 그 기간 위반 보고가 0건이면 `enforce`로 전환한다(SEC-10 (b), Origin 관문 observe 기간과 같음). 단, `frame-ancestors`는 Report-Only에서 무시되므로 프레임 보호는 `X-Frame-Options: DENY`가 처음부터 맡는다.
  - (D2 → V1-15) v1 전용 'CSP 없음' 분기는 없다. v1 화면이 CSP 로 깨지는 것은 감수한다(V1-13).
- 라우트가 이미 붙인 헤더는 덮어쓰지 않는다(`headers.setdefault`). 기존 `Cache-Control` 테스트를 그대로 지키기 위해서다.
- HSTS는 앱에서 송출하지 않는다(D4, Cloudflare 프록시에 위임).

### 2.2 CSP 위반 보고 — `src/api/routes_csp_report.py` (신규, D6)
- `POST /api/v1/csp-report`: 본문(`application/csp-report`, `application/reports+json`)을 크기 제한(예: 16KB) 안에서 읽어 로그에 남기고 `204`를 반환한다. DB 저장 없음.
- 수용 형식 밖 본문(위 두 Content-Type 이 아니거나 파싱 불가)도 **`204` + 로그**만 남긴다(SEC-12 (a), 오류 코드 없음 — 브라우저 보고 경로라 4xx 를 줘도 쓰는 쪽이 없다).
- 봇·확장 프로그램 잡음(SEC-12 (a)): User-Agent 가 아니라 보고의 `blocked-uri`/`source-file`(`reports+json`은 `blockedURL`/`sourceFile`)이 확장 프로그램 스킴(`chrome-extension:`, `moz-extension:`, `safari-web-extension:` 등)인 보고를 거른다 — 로그에 별도 표시하고 '위반 0건' 집계(4절 4)에서 제외한다.
- `request_guard` 면제 목록에 추가한다(브라우저 보고는 Origin을 보장하지 않음). 로그 남용 방지를 위해 본문 크기 상한·필드 절삭만 둔다.
- **도달 경로 위험(SEC-12, 실환경 미확인)**: `/api/v1/csp-report`도 CF Access 와 사용자 식별(`auth_cf._identify_user`)을 거친다. 브라우저가 쿠키 없이 보고를 보내 엣지에서 막히거나 401 이 되면, 위반이 있어도 로그는 '0건'이 되어 enforce 전환을 잘못 판단한다 → 4절 4의 **의도적 위반 보고 도착 확인**을 전환 전 필수 단계로 둔다.
- 415 면제(SRV-12 (a)): 브라우저가 `application/csp-report`로 보내므로 `server-input-origin-validation.md` §2.2 `parse_body`의 비JSON 415 검사를 적용하지 않는다(`parse_body` 미사용, 전용 읽기). 본문 크기 상한·수용 형식(위 두 Content-Type) 제한은 이 엔드포인트 안에서 별도로 둔다.

### 2.3 v2 정적 서빙 분리 — `src/web/spa_static.py` (신규)
- `resolve_v2(build_dir, path) -> (kind, file)`, `kind ∈ {asset, spa, missing}`:
  - 실제 파일이 있으면 `asset`.
  - 파일이 없고 경로가 `_app/`로 시작하거나 알려진 자산 확장자 목록(`.js .css .map .ico .png .svg .webmanifest .json .woff2`)으로 끝나면 `missing` → **404**, `Cache-Control: no-store`, text/plain.
  - 나머지는 `spa` → `index.html`, `no-cache`. 점(`.`)이 들어 있다고 모두 자산으로 보지 않는다. 날짜 같은 딥링크 세그먼트를 지키기 위해서다.
- `cache_control_for(path)`: `immutable, max-age=1y`는 `_app/immutable/`에만 준다. `_app/version.json`과 그 밖의 파일은 `no-cache`다(근본 원인 2 해소).
- `inline_script_hashes(index_path) -> list[str]`: 빌드된 `index.html`의 인라인 `<script>`에서 sha256 해시를 뽑는다. 파일 mtime을 키로 캐시한다. SvelteKit `kit.csp`에 기대지 않는 이유는 adapter-static fallback 페이지가 meta CSP를 내보내는지가 확실하지 않아서다. 헤더 쪽을 단일 소스로 둔다.
- `app.py`의 `serve_v2` 본문은 이 모듈 호출 3~4줄로 줄인다.
- favicon·manifest(D7): 404 처리만이 아니라 `frontend/static/`에 `favicon.ico`, `manifest.webmanifest`, `apple-touch-icon.png`를 실제로 추가하고 `app.html`에 `apple-touch-icon`·manifest 링크를 넣는다. theme-color meta 는 이 문서에서 넣지 않는다 — 위치·값·갱신은 `accessibility-common.md` §2.5 단일 소유(SEC-11). E-21 메타 정비와 함께 처리한다.
- 아이콘 디자인은 별도 에이전트를 활용한다(SEC-11).

### 2.4 오래된 탭 복구 — 프론트엔드 (D8)
- `pollInterval`은 기존값을 유지한다(SEC-11). 2026-10-12 기준 `frontend/vite.config.ts`의 sveltekit 옵션에 `version` 설정이 없으므로(SvelteKit 기본값) `vite.config.ts`는 바꾸지 않는다.
- `frontend/src/hooks.client.ts`(신규)·레이아웃: SvelteKit `updated` 스토어가 참이 되거나 `vite:preloadError`·동적 import 실패가 나면 자동 새로고침하지 않고 "새 버전이 있습니다 — 새로고침" 알림을 띄운다. 사용자가 누를 때만 새로고침한다. 판정 함수 `shouldNotify(storage, buildId) -> bool`은 같은 빌드에서 알림을 중복 표시하지 않도록 `sessionStorage` 키를 쓰며, 따로 export해서 테스트한다.

## 3. 변경 파일 표

| 파일 | 구분 | 인터페이스 / 내용 | 예상 줄 |
|---|---|---|---|
| `src/web/response_policy.py` | 신규 | `init_response_policy`, `classify_surface`, `build_csp`, `common_headers`, `CSP_V2_MODE` | ~120 |
| `src/web/spa_static.py` | 신규 | `resolve_v2`, `cache_control_for`, `inline_script_hashes`, `serve_v2_response` | ~80 |
| `src/api/routes_csp_report.py` | 신규 | 로그 전용 보고 수신, 크기 상한 | ~40 |
| `src/web/request_guard.py` | 수정 | 면제 목록에 `/api/v1/csp-report` | +1 |
| `src/web/app.py` | 수정 | `serve_v2` 본문 위임, `init_response_policy(app)` 호출 (파일이 이미 1161줄이라 순감) | -12/+5 |
| `frontend/static/*`, `frontend/src/app.html` | 신규/수정 | favicon·manifest·apple-touch-icon 파일과 링크(theme-color meta 는 `accessibility-common.md` §2.5 소관 — SEC-11) | 자산 + ~3 |
| `frontend/src/hooks.client.ts` | 신규 | `shouldNotify`, preloadError 핸들러 | ~35 |
| `frontend/src/lib/components/UpdateNotice.svelte` | 신규 | "새 버전" 알림 UI(문구·위치는 product 영역) | ~30 |
| `tests/test_response_policy.py` | 신규 | 표면 분류('v1' 표면 없음 — V1-15, 폴백 경로 = 일반 표면 — V1-18, 일반 표면 `script-src`에 인라인 해시 없음 — SEC-12, `/api/context-episodes` = api 표면 — NEW-40), 표면별 CSP·Report-Only 전환(일반 표면도 `CSP_V2_MODE` 따름), 공통 헤더(Permissions-Policy 카메라·마이크·위치 항목, HSTS 없음), setdefault 보존, SSE | ~140 |
| `tests/test_csp_report.py` | 신규 | 204, Origin 없이 통과, `application/csp-report` 본문이 415 없이 204(SRV-12), 크기 상한, 수용 형식 밖 본문 204 + 로그(SEC-12), 확장 프로그램 스킴 보고는 집계 제외 표시(SEC-12) | ~55 |
| `tests/test_spa_static.py` | 신규 | 404/200 분기, 딥링크 보존, 캐시 규칙(version.json), 해시 추출·mtime 캐시, favicon 200 | ~90 |
| `frontend/tests/update-notice.test.ts` | 신규 | `shouldNotify` 중복 방지 | ~30 |

모든 신규 파일은 300줄 이하이고, 함수마다 테스트가 최소 1개씩 있다.

## 4. 적용 순서·검증

1. **`spa_static` 분리(E-04 서버)**: pytest로 `/v2/_app/immutable/x.js`가 404인지, `/v2/today`와 `/v2/activity/2026.10.01`이 200 HTML인지, `_app/version.json`이 `no-cache`인지 확인한다. 브라우저에서는 `npm run build` 후 DevTools Network로 확인한다.
2. **`response_policy` 공통 헤더 + api/feed CSP + csp-report**: 전체 pytest를 돌려 기존 `Cache-Control` 단언(캘린더, MCP, coach SSE)이 그대로 통과하는지 본다. `curl -I`로 `/api/v1/...`, `/api/context-episodes`, `/feeds/cal/...`에 `X-Frame-Options: DENY`, `Referrer-Policy`, `Permissions-Policy: camera=(), microphone=(), geolocation=()`가 있고 `Strict-Transport-Security`가 없는지 확인한다. Origin 없는 `POST /api/v1/csp-report`(`Content-Type: application/csp-report`) → 204(415 아님, SRV-12).
3. **v2·일반 표면 CSP Report-Only(2주, SEC-10)**: Flask 서빙 빌드(5173 dev 서버는 Flask를 거치지 않으니 검증 대상이 아니다)로 v2 주요 화면(today, coach, library, data, welcome)을 돌며 csp-report 로그를 수집한다. SSE(coach)와 차트가 정상인지도 확인한다. 2주 동안 위반 보고를 모은다.
4. **CSP enforce 전환(SEC-10·SEC-12)** — 아래 순서를 모두 통과해야 전환한다.
   1) **(필수) 보고 도착 확인**: 실환경(CF Access 경유)에서 v2 화면과 일반 표면 화면에 각각 **의도적 위반**(예: 허용되지 않은 인라인 스크립트를 개발자 도구로 주입)을 일으켜 `/api/v1/csp-report` 로그에 보고가 실제로 도착하는지 확인한다. 도착하지 않으면(엣지 차단·401 등) '위반 0건'은 판단 근거가 될 수 없으므로 전환하지 않는다.
   2) 2주 운영 기간의 위반 보고(확장 프로그램 스킴 보고 제외, SEC-12)가 0건이면 `CSP_V2_MODE=enforce`.
   3) 같은 화면에서 콘솔 CSP 위반 0건을 확인한다.
5. **favicon·manifest(D7)**: 아이콘 자산(디자인은 별도 에이전트, SEC-11) 추가 후 `/v2/favicon.ico`·manifest 200, 홈 화면 추가 시 아이콘 표시. theme-color 검증은 `accessibility-common.md` §5.
6. **오래된 탭 복구(D8)**: 빌드 A로 탭을 연다 → 빌드 B로 재빌드한다 → 탭에서 내비게이션한다 → 자동 새로고침 없이 알림이 1회 뜨고, 새로고침 버튼으로 정상 화면이 나오는지 확인한다.
7. 완료 후 `decisions.md`에 **ADR-049**(응답 정책 계층, ADR-1)를 기록하고 `check_docs.py`를 실행한다.

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

## 6. 결정됨 (2026-10-11, `decisions-table.md` SEC-1~11)

- **D1 (SEC-1·SEC-10)** v2 CSP는 Report-Only 후 enforce — 누락 출처로 화면이 깨지는 위험을 먼저 관찰. Report-Only 2주 운영 후 위반 0건이면 enforce(SEC-10 (b), Origin 관찰 모드와 같은 기간). V1-18 일반 표면도 같은 단계.
- **D2 (SEC-2 → V1-15)** SEC-2 의 'v1 은 CSP 없이 공통 헤더만'은 V1-15 (a)로 대체 — `classify_surface` `"v1"` 분기 제거(V1-4 해소, 근거 V1-13 v1 손상 허용). 공통 헤더는 모든 표면에 그대로.
- **D3 (SEC-3)** 프레임 `DENY` / `frame-ancestors 'none'` — 자체 임베드 수요가 없어 가장 안전한 값.
- **D4 (SEC-4)** HSTS는 Cloudflare 프록시에 위임, 앱 미송출 — 로컬 HTTP 영향 제거.
- **D5 (SEC-5)** `Referrer-Policy: strict-origin-when-cross-origin` — 호환성 높고 Referer 대체 판정 유지.
- **D6 (SEC-6·SRV-12)** 로그 전용 `/api/v1/csp-report` 추가, Origin 관문 면제 목록 갱신 — D1 관찰에 필요. 415(Content-Type) 검사 면제, 크기·형식 제한은 별도(SRV-12 (a)).
- **D7 (SEC-7·SEC-11)** favicon·manifest·apple-touch-icon 실제 파일 추가(E-21과 함께). theme-color 는 `accessibility-common.md` §2.5 에 일원화(SEC-11), 아이콘 디자인은 별도 에이전트 활용(SEC-11).
- **D8 (SEC-8·SEC-11)** "새 버전" 알림 후 사용자가 새로고침 — 입력 중 데이터 유실 방지. pollInterval 은 기존값 유지(SEC-11).
- **D9 (SEC-9·SEC-11)** `Permissions-Policy`만 추가(최소 항목: 카메라·마이크·위치 차단, SEC-11), COOP는 OAuth 팝업 영향 검증 전까지 보류.
- **D10 (SEC-12, 2026-10-12)** (a) 일반 표면 CSP 는 인라인 해시 미포함(엄격), csp-report 수용 형식 밖 본문은 204 + 로그, 봇·확장 프로그램 잡음은 확장 프로그램 스킴 보고를 걸러 '위반 0건' 집계에서 제외. enforce 전환 전 의도적 위반으로 보고 도착 확인 필수(2.1·2.2·4절 4).
- **ADR (ADR-1)** 응답 정책 계층은 ADR-049(SRV 048, SEC 049, FRS 050, NRA 051).

## 7. 범위 밖 메모
- E-21: description, 비표준 `text-scale` meta는 메타 정비 작업에서 다룬다(아이콘은 D7로 이 작업과 함께 처리, theme-color 는 `accessibility-common.md` §2.5 — SEC-11).
- 세션 쿠키 `Secure/SameSite/HttpOnly`, Origin/CSRF 검사는 `server-input-origin-validation.md`에서 다룬다.
- 레거시 v1 HTML: UI·라우트 일몰 예정(V1-1 정정·V1-2), 점검 범위 밖.
- COOP 도입 — OAuth 팝업 영향 검증 후 재검토(D9).

## 8. 변경 이력
- 초안 작성.
- 2026-10-11 설계서 동기화: D1~D9 결정(SEC-1~9) 반영 — Report-Only→enforce 단계, v1 CSP 제외, DENY, HSTS 위임, csp-report 엔드포인트·면제, 아이콘 자산, 새 버전 알림 UX, Permissions-Policy.
- 2026-10-11 4차 동기화(V1-1): 레거시 v1 고려 제거 — 4절 v1 무회귀 단계·호환성 v1 항목·테스트 'v1 CSP 없음' 삭제, D2·2.1 `v1` 분기·7절 v1 XSS 메모·대안 B 'v1' 언급 축약/삭제.
- 2026-10-11 5차 동기화(V1-1 정정·V1-3·V1-4): 일몰 = UI·라우트 일몰. `"v1"` 분기를 V1-4 보류 열린 항목으로 명시(2.1·D2·§10), 사용자 전환 v2 이관(V1-3)에 따른 표면 변화 기록(§10).
- 2026-10-11 6차 동기화(V1-8·V1-9·V1-10, V1-4 보류 유지): §10 사용자 전환 항목의 엔드포인트 표면 단정을 경로 규칙 의존으로 완화(경로는 구현 단계 제안), SRV-6 적용 시점(이관과 같은 변경) 반영, `src/web` 공용 4파일 view 밖 이관의 영향(없음) 명시.
- 2026-10-11 8차 동기화(V1-15·V1-16): `classify_surface` 'v1' 분기 제거(2.1·D2·테스트·§10, V1-4 해소), 남는 폴백 경로의 표면은 열린 항목으로 축소. `response_policy`·`spa_static`·`request_guard` 위치 `src/web/` 확정(2.1·§10, 'src/web = 앱 셸 전용'). 사용자 전환 SRV-6 은 v2 이관과 같은 변경(유지).
- 2026-10-11 7차 동기화(V1S-1~3·V1S-5·V1-12·V1-13, V1-4 보류 유지): §10 V1-10 항목의 '새 위치 미정'을 확정 위치로 교체(영향 없음 유지), V1-4 검토 입력에 D2 근거와 V1-13 충돌 기록, 사용자 전환 production 판정 키(V1-12) 반영.
- 2026-10-12 9차 동기화(SEC-10·SEC-11·SRV-12·ADR-1·NEW-40·V1-18): Report-Only 2주·위반 0건 enforce(2.1·4절·D1), Permissions-Policy 최소 항목(2.1·D9), pollInterval 기존값 유지로 `vite.config.ts` 변경 삭제(2.4·3절·D8), theme-color 서술 제거 → `accessibility-common.md` §2.5 참조(2.3·3절·4절 5·D7·7절), 아이콘 디자인 별도 에이전트, csp-report 415 면제(2.2·D6), ADR-049, 폴백 경로 일반 표면(V1-18, 2.1·§10 해소), `/api/context-episodes` api 표면 명시(NEW-40).
- 2026-10-12 10차 동기화(SEC-12, 설계 단계 마지막): 일반 표면 CSP 인라인 해시 미포함(2.1), csp-report 수용 형식 밖 본문 204 + 로그·확장 프로그램 스킴 보고 집계 제외·CF Access/사용자 식별 도달 위험(2.2), enforce 전환 전 의도적 위반 보고 도착 확인 필수 단계(4절 4), D10, 테스트 갱신(3절), §9 구현 확인 2건 해소, §11 S0 점검 목록.

## 9. 동기화 중 발견한 충돌/확인 필요
- 해소(ADR-1): ADR 번호 — 이 문서 ADR-049, `server-input-origin-validation.md` ADR-048.
- 해소(SEC-10): D1 Report-Only 운영 기간 2주, 위반 0건이면 enforce(Origin observe 도 같은 기간).
- 해소(SRV-12): D6 엔드포인트는 415 검사 면제(2.2).
- 해소(SEC-11): D7 아이콘 디자인은 별도 에이전트 활용(일정은 결정 기록 없음), theme-color 는 A11Y 일원화. D9 Permissions-Policy 항목은 카메라·마이크·위치.
- D8 알림 문구·위치는 product 영역이며 이 문서에서 확정하지 않았다.
- (구현 확인) pollInterval 기존값(설정 없음 = SvelteKit 기본)에서는 `updated` 스토어가 주기적으로 갱신되지 않을 수 있다 — 2.4 알림 트리거는 `vite:preloadError`·동적 import 실패 경로가 주가 되며, `updated` 경로의 동작은 구현 시 SvelteKit 버전 기준으로 확인한다.
- 해소(SEC-12): 일반 표면 CSP 는 인라인 해시 미포함(2.1), csp-report 수용 형식 밖 본문은 204 + 로그(2.2), 봇 제외는 확장 프로그램 스킴 필터(2.2), enforce 전 보고 도착 확인 필수(4절 4).

## 10. 동기화 중 발견한 모호점
- 해소(V1-18): `classify_surface`의 `"v1"` 분기 제거(V1-15) 후 `/v2/`·`/api/`·`/mcp`·`/feeds/` 밖 경로(일몰 전 v1 화면, `app.py`의 `/trigger-sync`·`/bg-sync/*`·`/sync-status`·`/import/*`·`/` 리다이렉트, 미정의 경로 404)는 일반 표면 정책(엄격 CSP, `CSP_V2_MODE` 단계)을 받는다(2.1). 2026-10-11 grep 기준 v2 프론트(`frontend/src`)는 이 경로들을 호출하지 않는다(`/switch-user`·MenuDrawer quickLinks 의 v1 링크 제외). v1 화면이 이 정책으로 깨지는 것은 감수(V1-13).
- 해소(NEW-40): `/api/context-episodes`는 `/api/` 접두 판정으로 `"api"` 표면(2.1). Origin 관문 거부 응답 봉투 판정은 `server-input-origin-validation.md` 2.1 `ENVELOPE_PATH_PREFIXES` 소관.
- (V1-3 정합) 사용자 전환은 v2 로 이관한 뒤 v1 `/switch-user`를 제거한다(`server-input-origin-validation.md` 2.5). 현재 `/switch-user`는 서버 렌더 HTML 이라 위 일반 표면 경로에 해당한다(V1-15 로 'v1' 표면 없음). 이관 후 v2 엔드포인트 경로·화면 위치는 구현 단계에서 제안하므로(V1-8 (c)) 받을 표면은 `classify_surface`의 경로 규칙을 그대로 따른다(예: `/api/` 아래면 `"api"`, `/v2/` 아래 화면이면 `"v2"`) — 이 문서의 추가 변경은 없다. SRV-6 production 차단(404)은 v2 이관과 같은 변경에서 그 엔드포인트에 적용되며(V1-9 (b), production 판정 키는 `APP_ENV` — V1-12·SRV-10) 같은 표면 정책을 받는다.
- (V1-10·V1S-1~3 영향) `src/web` 공용 4파일은 이번 작업에서 모두 view 밖으로 이관된다 — `bg_sync.py`·`auto_sync.py` → `src/sync/`, `helpers.py` 공용 3함수 → `src/utils/user_context.py`(HTML 헬퍼 잔류), `views_mcp_remote.py` → `src/mcp_remote/http.py`(shim 없음, V1S-5). 이 문서는 네 파일을 경로로 참조하지 않는다 — §10 V1-4 항목의 `/bg-sync/*`·`/trigger-sync` 등은 `app.py`의 URL 경로이고 `/mcp` 표면 분류도 URL 경로 기준이라, 모듈 이관은 `classify_surface`·CSP 판정, 이 문서의 파일 경로·테스트(`test_response_policy.py` 등) 범위, import 경로 어느 것에도 영향이 없다. 이 문서의 신규 `response_policy.py`·`spa_static.py`는 V1-16 (c')로 `src/web/` 위치 확정(해소 — 앱 조립 계층, 일몰 후 유지).

## 11. S0 점검 목록 (10차 — 구현 착수 때 한 줄씩 확인, 새 결정 아님)
- SEC-12: 걸러낼 확장 프로그램 스킴 목록(`chrome-extension`·`moz-extension`·`safari-web-extension` 외)과 `blocked-uri`가 `inline`·`eval`일 때 `source-file`로만 판정하는 규칙 확정.
- SEC-12: 크기 상한을 넘는 보고 본문도 '수용 형식 밖'과 같이 204 + 로그(절삭)로 처리하는지 확인.
- SEC-12: 4절 4-1) 의도적 위반 재현 절차(주입 방법·대상 화면·확인할 로그 줄 형식)를 구현 시 한 줄 절차로 고정.
- SEC-12: 브라우저가 `report-uri` 보고에 같은 출처 쿠키를 싣는지를 실환경 확인 결과로 기록(4절 4-1)의 판정 근거).
