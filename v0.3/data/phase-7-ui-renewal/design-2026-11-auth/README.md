# 신규가입 · 다중 인증 · 비인증 방문자 설계서 (AUTH-2026-11)

- 작성 2026-11-04, system-architect. 상태: **G-1/G-3(안3 하이브리드, 새 ADR-043)·G-4/G-6(초대코드+일 20명) 확정, 1단계 구현. G-2/G-5/G-7/G-8/G-9·TXT-1 은 권고값 적용·사용자 확인 대기**
- 기준 브랜치 `feat/frs-f3`. 근거는 `파일:줄`로 표기(작성 시점 기준).
- **기존 결정과 충돌**: ADR-038 D-L1(b)("앱 인증 경계는 변경하지 않는다", 공개면은 별도 정적 사이트)·D-L3(초대제 유지)과
  05-tech-architecture §11.2(2단계 = 앱 자체 Google/Apple OAuth)를 이 설계가 다시 연다. 채택 시 새 ADR로 대체 명시 필요(G-1).

---

## A. 현 인증 경로 조사

### A.1 사용자 식별 (`src/web/auth_cf.py`)
| 순서 | 동작 | 근거 |
|---|---|---|
| 1 | `/feeds/cal/*` 무조건 통과(토큰 인증 위임) | auth_cf.py:78-79 |
| 2 | `/mcp`, `/mcp/` 정확 일치 통과(Bearer 위임) | auth_cf.py:81-82 |
| 3 | 세션에 `user_id` 있으면 규칙 검사만 하고 **CF 헤더를 다시 보지 않음** | auth_cf.py:85-91 |
| 4 | `CF-Access-Authenticated-User-Email` 헤더 → `validate_uid` → `session.permanent`, `session["user_id"]=email` | auth_cf.py:93-102 |
| 5 | POST `/api/garmin/local-sync` 통과(body `sync_key`) | auth_cf.py:106-108 |
| 6 | 서비스 토큰(`CF-Access-Client-Id/Secret`, 루트 config `cf.*`) 일치 시 uid=루트 config `garmin.email` | auth_cf.py:43-52, 111-123 |
| 7 | production → 401 text/plain / 개발 → `DEV_USER_ID` 또는 `default` | auth_cf.py:125-144 |

관찰된 문제(신규가입 전 반드시 해소):
- **F1 헤더 무서명 신뢰**: 이메일 헤더만 읽고 `Cf-Access-Jwt-Assertion` 서명 검증이 없다(`grep -i cf-access-jwt src` 0건).
  컨테이너가 127.0.0.1 바인딩(BACKLOG OPS-OCI-MIGRATION)이라 현재는 터널 경유만 가능하지만, 같은 호스트의
  다른 프로세스·오설정 프록시는 헤더를 위조할 수 있다. 공개 경로가 생기면 위험이 커진다.
- **F2 세션-신원 불일치**: 3번 때문에 같은 브라우저에서 CF 사용자가 바뀌어도(로그아웃 후 다른 계정) 앱 세션(7일,
  app.py:83)이 이전 사용자로 남는다. 앱에 로그아웃 경로가 없다(`grep logout` 0건).
- **F3 익명 → default 폴백**: `get_current_user_id()`는 세션이 없으면 `"default"`(user_context.py:103-110),
  `get_db_path`도 uid 없으면 `DEFAULT_USER`(db_setup.py:31, 51). `"default"`는 루트 `config.json`(CF 서비스 토큰 등
  비밀 포함, config.py:13-20)에 매핑된다. 지금은 7번 401이 익명 요청을 막아 드러나지 않을 뿐, 공개 경로를 여는 순간
  익명 요청이 default 데이터·설정에 닿을 수 있는 구조다.
- **F4 요청별 마이그레이션 훅**: `_ensure_user_db_migrated`는 `/feeds/cal/` 외 모든 요청에서 `_db_path()`를 호출한다
  (app.py:152-174) — 익명 요청이면 default DB를 연다.

### A.2 사용자 DB 프로비저닝
- 지연 생성: `/api/v1/` 요청 + 세션 uid + DB 없음 → `init_db(uid)`(app.py:157-167). `load_config(user_id=uid)`도
  `get_config_path`에서 디렉터리를 `mkdir`(config.py:18) — **설정을 읽기만 해도 디렉터리가 생긴다.**
- 경로 방어: `validate_uid`(이메일 호환 1~254자, 선행 `.` 거부, 정규화 없음 — user_context.py:33-42, SRV-13),
  `get_db_path`의 `resolve().parent` 이중 확인(db_setup.py:39-54). 위반 시 403(V1-20, app.py:145-150).
- 시작 시 `list_user_ids()` 전원 마이그레이션, **자동 동기화는 사용자 1명만**(app.py:103-137) — 다중 가입 시 한계(G-9).
- 개발 전용 사용자 전환: `user_switch_service.dev_switch_enabled`(production 404, user_switch_service.py:19-21).

### A.3 세션 / 토큰
- Flask 서명 쿠키 세션, `FLASK_SECRET_KEY` 필수(production, app.py:60-72), 7일, SameSite=Lax·HttpOnly·Secure(SRV-10, app.py:83-87).
- Origin 관문은 인증 훅 **뒤** 등록(app.py:93-95) → 인증 통과 요청만 검사(request_guard.py:7-8). 모드 기본 `observe`(request_guard.py:44, SEC-10).
- MCP: `data/mcp_tokens.db`에 sha256 해시만(token_index.py:3, 55), 세션 사용자만 발급/폐기(routes_mcp_tokens.py:31-63), `/mcp`는 Bearer + `same_origin(allow_missing)`(mcp_remote/http.py:53-69, ADR-034).
- 캘린더 피드: `calendar_feed_index` 토큰 조회 → uid, 토큰 해시별 `rate_window` 제한(routes_calendar_feed.py:57-63).
- 레이트리밋 유틸: `src/utils/rate_window.py`(프로세스 메모리 슬라이딩 윈도 — gunicorn 워커 간 공유 안 됨).

### A.4 프런트
- SPA(`ssr=false`, routes/+layout.ts:4-5). 인증 개념 없음: 401 처리 없음(`frontend/src` 401 참조는 coachEngine 문구 1건).
- 이미 존재: `/v2/landing`(정적, CTA=mailto 초대 요청, routes/landing/+page.svelte:5), `/v2/demo`(fetch 가로채기 스냅샷,
  `lib/demoMode.ts`, `static/demo/snapshot.json`), `/v2/welcome`(S1). `/`는 항상 `/v2/today`(user_settings_service.py:50-52).

---

## B. 목표 아키텍처 비교

| 기준 | 안1 CF Access 확장 (IdP 추가, 헤더 신뢰) | 안2 앱 자체 인증 (OIDC+세션, CF는 일부) | 안3 하이브리드: CF Access=IdP 중개 + 앱 계정 레지스트리·JWT 검증 |
|---|---|---|---|
| IdP 추가 | CF 콘솔에서 Google·One-time PIN(이메일 코드) 추가 | Authlib 등으로 Google/GitHub OIDC 직접, 이메일은 매직링크(SMTP 필요) | 안1과 동일(CF 콘솔) |
| 스푸핑 | F1 그대로(헤더 신뢰) | 헤더 무관, 앱 세션만 | `Cf-Access-Jwt-Assertion` 서명·aud·exp 검증 → F1 해소 |
| CSRF | Lax+Origin 관문 | 동일 + OAuth `state`/PKCE/nonce 직접 구현 | Lax+Origin 관문(enforce 전제) |
| 세션 고정 | F2 잔존 | 로그인 시 세션 재발급 직접 구현 | 로그인 시 `session.clear()` 후 재설정 + JWT `sub`·이메일 대조로 F2 해소 |
| 오픈 리다이렉트 | 해당 적음 | `next`·콜백 검증 필요 | `next` 검증 필요(§D.5) |
| 가입 제한 | CF 정책뿐(초대=이메일 목록 수작업) | 앱에서 자유롭게 | 앱 레지스트리에서(초대코드/허용목록/오픈) |
| 운영 복잡도 | 최소 | 최대(비밀 관리, 메일 발송, 키 회전, 계정 복구, 봇 방어 전부 앱 책임) | 중간(레지스트리 1개, JWT 키 캐시) |
| 비용/한도 | CF Zero Trust 좌석(무료 플랜 한도 **확인 필요**) | 좌석 무관, 메일 발송 비용 | 안1과 동일 좌석 한도 |
| 마이그레이션 | 없음(uid=이메일 유지) | 기존 uid(이메일)↔OIDC subject 연결 필요, CF 제거 시 전 API가 인터넷 노출 | 백필 스크립트로 기존 디렉터리=active 계정, uid 불변 |
| 비밀번호 저장 | 없음 | 선택 시 해시·재설정·유출 대응 필요 | 없음 |

**추천: 안3.** 이유
1. 기존 사용자·`data/users/<email>/` 그대로(uid 불변), 비밀번호·메일 발송 인프라 0 — 이메일 로그인은 CF One-time PIN이 검증까지 담당.
2. F1·F2·F3를 이번에 함께 닫는다(공개 경로를 여는 이상 어느 안이든 필요한 작업).
3. 인증 어댑터를 `identify(request) -> Identity | None` 한 곳으로 모아, 좌석 한도·UX 요구로 안2가 필요해지면
   어댑터만 추가(레지스트리·프로비저닝·프런트는 재사용). 안2를 처음부터 하지 않는 이유는 보안 표면 대비 지금 얻는 것이 적어서다.
- 안3의 약점: CF 좌석 한도가 가입자 수 상한이 된다(G-3). CF 로그인 화면은 앱이 꾸밀 수 없다(IdP 선택은 CF 화면).

---

## C. 비인증 방문자 표면 (안3 기준)

### C.1 공개 범위
| 경로 | 공개 | 비고 |
|---|---|---|
| `/v2/*` 정적 셸·자산(`_app/`, favicon, manifest, `demo/snapshot.json`) | 공개 | 셸에는 사용자 데이터 없음. 보호 화면도 셸은 내려가지만 데이터 API가 막힘 |
| `/v2/landing`, `/v2/demo`, `/v2/auth/*`(로그인 안내·대기·초대코드 화면) | 공개 | 클라이언트 라우트 |
| `GET /api/v1/auth/session` | 공개 | `{state: anonymous|pending|active, display_email?}` 만. 캐시 금지 |
| `GET /auth/start?next=` | **CF 보호** | CF가 IdP 로그인을 강제 → 앱이 JWT 검증·레지스트리 처리 → `next`로 302 |
| `POST /auth/logout` | 세션 필요 | 세션 삭제 → `/cdn-cgi/access/logout` 302 |
| `POST /api/v1/auth/invite`(pending 전용) | pending 세션 필요 | Origin 관문 적용 |
| 그 외 `/api/*`, `/mcp`, `/feeds/cal/`, v1 화면 | 현행 | 익명은 401(봉투 경로는 `{error:{code:"AUTH_REQUIRED"}}`) |

- `/` 처리: 활성 세션 → `/v2/today`, 그 외 → `/v2/landing`(user_settings_service.entry_path 확장).
- 대안(미결 G-2): ADR-038 D-L1(b) 유지 — 랜딩·데모는 별도 정적 사이트, 앱 도메인은 공개 경로 0(`/api/v1/auth/session`조차 불필요,
  가입 버튼은 앱 `/auth/start`로 링크). 경계 변경이 가장 작지만 "로그인 사용자는 랜딩 건너뛰기"(LIFECYCLE §2.1)가 불가하고 배포가 둘이 된다.

### C.2 `_identify_user` 변경 지점
1. 맨 앞에 **공개 경로 판정**(`src/auth/public_paths.py`, 정확/접두 목록 + 테스트로 고정). 공개 경로는 `g.auth_state="anonymous"`로 두고 통과.
   현재 하드코딩 예외(`/feeds/cal/`, `/mcp`, local-sync)도 이 목록으로 이동(LIFECYCLE §6-4 질문 해소).
2. 세션 경로(3번) 강화: CF JWT가 요청에 있으면 `sub`·이메일을 세션의 `auth_sub`·uid와 대조, 다르면 `session.clear()` 후 재식별(F2).
3. 이메일 헤더(4번) → **JWT 검증 결과**로 대체(`src/auth/cf_jwt.py`: 팀 도메인 certs 캐시, `aud`=Access 앱 AUD 태그, `exp`, `iss`).
   헤더 이메일은 JWT `email`과 일치할 때만 참고. 검증 실패 → 401 + 보안 로그(마스킹, S3-2 형식).
4. 레지스트리 조회: active → `session["user_id"]=uid`; pending/미등록 → `session["pending_sub"]`만(**`user_id` 미설정**). 기존 코드는 전부 `user_id` 기준이라 pending 사용자는 어떤 사용자 DB에도 닿지 않는다.
5. 7번 production 401 유지. 개발 폴백(DEV_USER_ID)은 유지.
- 플래그 `AUTH_MODE=legacy|registry`(기본 legacy) — legacy는 현 동작 그대로(롤백 수단).

### C.3 익명 요청의 사용자 DB 비접근 보장 (F3·F4)
- `get_current_user_id()`: 요청 컨텍스트에서 `g.auth_state != "active"`이고 production이면 `NoUserContext` 예외(CLI·스레드 경로는 기존 `default` 유지).
  전역 errorhandler → 401 `AUTH_REQUIRED`. 즉 공개 핸들러가 실수로 사용자 데이터를 건드려도 default로 새지 않는다.
- `_ensure_user_db_migrated`: `user_id` 세션이 없으면 즉시 반환(app.py:157 앞).
- 검증 테스트: 공개 경로 전부를 production 모드로 호출하며 `get_db_path`/`load_config`를 spy → 호출 0, `data/users/` 디렉터리 생성 0.

### C.4 레이트리밋·봇
- 1차 방어는 CF(One-time PIN 발송 제한, WAF 속도 규칙 — 외부 작업). 앱: `rate_window`로 `/auth/start`·`/api/v1/auth/invite` IP·sub별 제한,
  **신규 계정 활성화 일일 상한**(전역, 값 미결 G-6). `rate_window`는 워커별 메모리라 상한은 레지스트리 DB 카운트로 판정.
- Turnstile 등 캡차는 1단계 미도입(CSP에 외부 출처 추가 필요 — S3-9와 충돌). 남용 관측 시 별도 결정.

### C.5 CSP·Origin 관문
- 안3은 외부 스크립트·폼 대상 추가 없음 → CSP(response_policy.py:73-84) 변경 없음. 로그인은 최상위 내비게이션(`location.assign('/auth/start…')`)이라 `connect-src`·`form-action` 무관.
  로그아웃은 같은 출처 POST 후 같은 출처 `/cdn-cgi/access/logout`로 302 → `form-action 'self'` 통과.
- Origin 관문은 공개 경로에도 그대로 적용(면제 목록에 추가 금지). **공개 전환 전 `ORIGIN_GUARD_MODE=enforce` 전제**(SEC-10 관찰 기간 상태 확인 필요).
- COOP 보류 사유(SEC-9, OAuth 팝업)는 리다이렉트 방식이라 해소 — 별도 결정으로 재검토 가능(이번 범위 아님).

---

## D. 가입 플로우

### D.1 계정 레지스트리 `data/auth.db`(전역, `mcp_tokens.db`와 같은 위치·패턴)
```sql
CREATE TABLE accounts (uid TEXT PRIMARY KEY, email_norm TEXT UNIQUE NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('pending','active','disabled')),
  created_at TEXT NOT NULL, activated_at TEXT, invite_id TEXT, consent_version TEXT);
CREATE TABLE identities (provider TEXT NOT NULL, subject TEXT NOT NULL, uid TEXT NOT NULL REFERENCES accounts(uid),
  email_at_link TEXT NOT NULL, idp_type TEXT, first_seen TEXT NOT NULL, last_seen TEXT NOT NULL,
  PRIMARY KEY (provider, subject));
CREATE TABLE invites (invite_id TEXT PRIMARY KEY, code_hash TEXT UNIQUE NOT NULL, max_uses INTEGER NOT NULL,
  uses INTEGER NOT NULL DEFAULT 0, expires_at TEXT, created_at TEXT NOT NULL, note TEXT);
CREATE TABLE auth_events (ts TEXT NOT NULL, kind TEXT NOT NULL, uid TEXT, subject_masked TEXT, ip_hash TEXT, detail TEXT);
```
- 사용자별 `running.db`가 아니라 전역 DB: 신원은 사용자 DB를 열기 **전에** 결정돼야 하므로. metric_store·CalcContext와 무관.
- 초대코드는 sha256 해시만 저장(MCP 토큰과 동일 원칙).

### D.2 식별자 정규화
- 조회 키 `email_norm = email.strip().lower()`. Gmail 점·`+` 별칭은 **정규화하지 않음**(다른 서비스 의미 변경 위험).
- uid: 기존 계정은 디렉터리명 그대로(대소문자 포함 불변). 신규 계정은 `email_norm`(validate_uid 통과 필수, 실패 시 가입 거부 403).
- 대안(미결 G-5): 신규는 불투명 uid(`u_<base32>`) — 이메일 변경에 강하지만 local-sync 본문 `user_id`(routes_v1_sync.py:253-254)·운영 디렉터리 판독성 영향.

### D.3 다중 IdP 연결·중복 병합
- CF Access는 IdP와 무관하게 이메일로 사용자를 식별하고 GitHub·Google·One-time PIN 모두 **검증된 이메일**만 넘긴다 →
  같은 `email_norm`이면 같은 계정에 `identities` 행을 자동 추가(자동 연결). 기록은 `auth_events`.
- 이메일이 다른 두 계정의 병합은 **지원하지 않음**(데이터 디렉터리 병합은 사용자 DB 간 충돌 해결이 필요한 별도 작업). 운영자가 수동 처리.
- 이메일 검증: IdP 위임(JWT에 담긴 이메일 = 검증됨). 앱 자체 검증 메일 없음.

### D.4 프로비저닝 시점
- `pending → active` 전이 시 `src/auth/provisioning.py`가 디렉터리·`init_db(uid)`·빈 config를 **한 번에** 생성(멱등). 실패 시 status 롤백.
- app.py:157-167의 지연 생성은 registry 모드에서 제거(legacy 모드는 유지). "DB 없음"은 active인데 디렉터리 없음 = 서버 오류(503 구분, LIFECYCLE §6-1).
- pending 상태에선 `load_config(user_id=…)` 호출 금지(config.py:18 mkdir 부작용) — C.2-4로 구조적으로 보장.

### D.5 흐름
1. 익명 → 랜딩 "시작하기" → `/auth/start?next=/v2/welcome`(CF IdP 선택: GitHub/Google/이메일 코드).
2. 앱: JWT 검증 → 레지스트리. 기존 active → 세션 설정 → `next`. 미등록 → 가입 정책(G-4)에 따라 즉시 active 또는 pending.
3. pending → `/v2/auth/pending`(초대코드 입력 또는 "승인 대기" 안내). 코드 통과 → active + 프로비저닝 → `/v2/welcome`.
4. `/v2/welcome` 온보딩(기존 S1). 민감정보 동의 문구는 **TXT-1 미결 유지** — `consent_version` 컬럼만 예약, 값 기록은 TXT-1 확정 후.
- `next` 검증: `^/v2/[A-Za-z0-9/_-]*$`(demo 라우트와 같은 규칙), `//`·`\`·스킴 거부, 실패 시 `/v2/today`. 서버(`/auth/start`)와 프런트 양쪽.
- 세션 고정: active 세션 설정 직전 `session.clear()`, `session["auth_sub"]` 저장.

### D.6 가입 제한 옵션 (미결 G-4)
| 옵션 | 장점 | 단점 |
|---|---|---|
| (a) 초대코드 | 남용·비용 통제, 공유 가능 | 코드 발급 수단(CLI) 필요 |
| (b) 이메일 허용 목록 | 현행 CF 정책과 같은 감각 | 운영자 수작업, "가입"이라기보다 등록 |
| (c) 완전 개방 + 일일 상한 | 요구 1 그대로 | CF 좌석·LLM·동기화 비용과 Garmin 비공식 경로 차단 위험이 사용자 수에 비례 |
- **추천 (a) + 일일 상한**, 이후 (c)로 플래그 전환 가능하게(`SIGNUP_MODE=invite|allowlist|open`). CF Access 정책은 "모든 이메일 허용"으로 열고 제한은 앱이 담당.

---

## E. 프런트 변경
- `lib/auth/session.ts`: `GET /api/v1/auth/session` → `authState` 스토어(anonymous/pending/active). 루트 `+layout.ts` load에서 1회.
- 라우팅 가드: 공개 라우트 목록(`landing`, `demo`, `auth/*`) 외에서 anonymous → `/v2/landing`, pending → `/v2/auth/pending`.
  데모 모드(`isDemoActive`)는 가드 예외(기존 fetch 가로채기 유지). 랜딩은 active면 `/v2/today`로 즉시 이동(LIFECYCLE §2.1).
- 화면: `/v2/auth/login`(한 버튼 "로그인 또는 가입" + 사용 가능한 수단 안내 — IdP 선택은 CF 화면), `/v2/auth/pending`(초대코드 TextField),
  랜딩 CTA를 mailto(landing/+page.svelte:5) → "시작하기"로(G-4가 open/invite일 때). 메뉴에 로그아웃(POST).
- 세션 만료: `apiFetch`(lib/api/client.ts)에 `redirect: 'manual'` — CF 세션 만료 시 CF가 302를 돌려 `opaqueredirect`가 되므로 이를 `AUTH_REQUIRED`로 정규화.
  401 `AUTH_REQUIRED`와 함께 전역 처리: 작성 중 입력이 있을 수 있으니 즉시 이동하지 않고 알림 + "다시 로그인"(현재 경로를 `next`로).
  `loadFailure.ts` 분류(S4-43)에 `auth` 종류 추가.
- 접근성: 기존 공용 TextField·Toast·IconButton(S4-61) 사용, 오류는 `aria-live="polite"`, 화면 전환 시 `h1` 포커스, 로그인 버튼은 `<a>`(내비게이션 의미).

---

## F. 구현 단계 (큰 묶음 4개)

| 단계 | 내용 | 변경 파일 후보 | 테스트 |
|---|---|---|---|
| 1 서버 신원 코어 | `src/auth/` 패키지(`cf_jwt`·`registry`·`public_paths`), `_identify_user` 재구성(F1·F2), `NoUserContext`(F3·F4), `/auth/start`·`/auth/logout`·`/api/v1/auth/session`, `AUTH_MODE` 플래그, 기존 사용자 백필 스크립트(`scripts/auth_backfill.py`, 드라이런 기본) | auth_cf.py, app.py(152-174·`/`), user_context.py, user_settings_service.py, 신규 `src/api/routes_auth.py`, requirements.txt(PyJWT — cryptography는 이미 있음) | pytest: JWT 위조·만료·aud 불일치 거부, 세션-sub 불일치 재식별, 공개 경로 spy(DB·config 접근 0), legacy 모드 무회귀(test_auth_cf.py 유지), `next` 검증 표 |
| 2 가입 게이트·프로비저닝 | pending/active 전이, 초대코드(CLI 발급 `scripts/auth_invite.py`), `SIGNUP_MODE`, 일일 상한·레이트리밋, `provisioning.py`, auth_events 감사 | 신규 `src/auth/provisioning.py`·`invites.py`, routes_auth.py, request_guard.py(변경 없음 확인만) | pytest: 상한 초과 429, 코드 재사용·만료, 프로비저닝 멱등·실패 롤백, pending이 사용자 DB 0 접근 |
| 3 프런트 | 세션 스토어·가드·login/pending 화면·랜딩 CTA·로그아웃·apiFetch 인증 실패 정규화 | routes/+layout.ts, lib/api/client.ts, lib/loadFailure.ts, routes/auth/*, routes/landing, MenuDrawer | vitest: 가드 판정 순수함수, `next` 검증, opaqueredirect→auth 분류. 브라우저 스모크(scripts/synth_smoke/pw): 익명 랜딩→데모, 보호 경로 리다이렉트, 로그아웃 |
| 4 외부 설정·공개 전환 | CF 콘솔 작업(아래), 운영 `AUTH_MODE=registry` 전환, 백필 실행, 운영 스모크, ADR·결정표 기록 | `.env`/compose(운영), decisions.md, decisions-table.md, 05 §11 갱신 | 운영 스모크: 3개 IdP 각각 신규·기존 로그인, 공개 경로 응답에 사용자 데이터 없음, 위조 헤더 직접 요청 401 |

- 진행 상태(2026-11-05): 1~3단계 구현·운영 배포 완료(S4-64~66, 운영 legacy). 4단계는 사용자 외부 설정 체크리스트 완료 후 전환 확인 대기.
- 롤백: `AUTH_MODE=legacy` 환경변수 + 재시작 → 현 동작. `auth.db`는 추가 전용이라 남겨도 무해. CF는 Bypass 애플리케이션 삭제·정책 원복. `data/users/` 무변경.
- 사용자 외부 작업 체크리스트
  - [ ] CF Zero Trust 플랜의 좌석 한도·현재 사용량 확인(G-3 판단 근거)
  - [ ] Google Cloud 콘솔: OAuth 클라이언트 생성(리디렉션 URI = `https://<team>.cloudflareaccess.com/cdn-cgi/access/callback`), 동의 화면 게시 상태 결정
  - [ ] CF Access: Google IdP·One-time PIN 추가, GitHub 유지. 앱 정책 Include를 허용 목록 → "Everyone"(G-4가 open/invite일 때)
  - [ ] CF Access: 공개 경로용 Bypass 애플리케이션(`/v2/*`, `/api/v1/auth/session`) — G-2가 같은 도메인일 때만
  - [ ] Access 앱 AUD 태그·팀 도메인을 운영 환경변수(`CF_ACCESS_AUD`, `CF_ACCESS_TEAM`)로 전달
  - [ ] WAF 속도 규칙(`/auth/*`, `/api/v1/auth/*`), `ORIGIN_GUARD_MODE=enforce` 상태 확인
  - [ ] 운영 `data/users/` 목록 확인 — 테스트성 디렉터리(예: p0의 `new@example.com`, `runner`, `u`)는 백필 제외 목록에

---

## G. 미결 사항 (사용자 결정 필요)

| ID | 질문 | 선택지 | 추천 |
|---|---|---|---|
| G-1 | ADR-038 D-L1·D-L3, 05 §11.2를 이 설계로 대체할지 | 대체 / 부분 대체 / 보류 | 대체(새 ADR), 요구 1·3이 기존 결정과 정면으로 다름 |
| G-2 | 공개면 위치 | (a) 같은 도메인 Bypass + 앱 공개 목록 / (b) ADR-038 별도 정적 사이트 유지 | (a) — 앱 계층 default-deny(C.2·C.3)가 CF 오설정의 2차 방어가 됨, 랜딩 건너뛰기 가능 |
| G-3 | 아키텍처 | 안1 / 안2 / 안3 | 안3. 좌석 한도가 예상 가입 규모보다 작으면 안2 어댑터를 4단계 뒤 별도 착수 |
| G-4 | 가입 제한 | 초대코드 / 허용 목록 / 개방 | 초대코드 + 일일 상한, 플래그로 개방 전환 가능 |
| G-5 | 신규 uid 형식 | 정규화 이메일 / 불투명 id | 정규화 이메일(기존과 동일 체계) |
| G-6 | 일일 신규 활성화 상한 값 | 숫자 | 20/일(근거: 비용 통제 출발값, 관측 후 조정) |
| G-7 | 이메일 비밀번호 로그인 | 도입 / 미도입 | 미도입 — 이메일 로그인은 CF One-time PIN으로 대체 |
| G-8 | 앱 세션 수명 | 현행 7일 / CF 세션과 맞춤 | CF Access 세션 수명과 동일하게(불일치 시 F2류 혼란) |
| G-9 | 다중 사용자 자동 동기화·LLM 비용 | 이번 범위 / 별도 항목 | 별도 항목 — 현재 자동 동기화는 1명만(app.py:132-137), 개방 전 필수 선행 |
| TXT-1 | 가입 직후 민감정보 동의 문구 | — | 기존 미결 유지(`consent_version`만 예약) |

## 검증 항목 요약
1. production에서 공개 경로 전수 호출 시 `get_db_path`·`load_config`·`data/users` 생성 0회.
2. JWT 없는/위조 이메일 헤더만 있는 요청 401, 다른 사용자 JWT로 기존 세션 쿠키 재사용 시 재식별.
3. 같은 이메일 GitHub→Google 로그인 시 같은 uid, `identities` 2행.
4. 기존 사용자 백필 후 uid·디렉터리·MCP 토큰·캘린더 피드 토큰 동작 불변.
5. `AUTH_MODE=legacy` 전환만으로 현 테스트 스위트 전부 통과.
