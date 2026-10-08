# DESIGN — 원격 MCP (HTTP 전송 + 토큰 인증 + 읽기 전용·유저 스코프) (2026-10-08, 초안)

BACKLOG `[MCP-REMOTE]`. 선행 `MCP-TOKEN-OPT`(ADR-016) 완료. **노출/인증 설계 변경 → 착수 전 plan 승인 필수.**
재사용: 캘린더 구독 설계(`DESIGN-ICS-SUBSCRIBE.md`, ADR-033)의 전역 토큰 인덱스·해시 조회·`rate_window`·`auth_cf` 예외·`RedactingLogger` 패턴.

## 1. 배경과 문제

- 현재 `src/mcp_server.py`(163줄)는 stdio 전용. `RUNPULSE_USER_ID` 필수, `mode=ro`, 프로토콜 `2024-11-05`, 메서드 `initialize/tools/list/tools/call/ping`. 도구는 `src/ai/tools.py::_DISPATCH` 15개(전부 SELECT 전용).
- VPS 밖 클라이언트(Genspark 등)는 프로세스를 띄울 수 없으므로 HTTP 전송이 필요하다.
- 웹 인증은 `auth_cf._identify_user`(CF Access 이메일 헤더 → `session["user_id"]`, 운영 모드 헤더 없으면 401). 서버 대 서버 클라이언트는 CF 로그인을 할 수 없다.
- 주의: `auth_cf`의 CF 서비스 토큰 우회는 `session["user_id"]`를 **garmin 이메일(svc_user)** 로 세팅한다. MCP 경로가 이 분기를 타면 토큰 소유자가 아닌 서비스 계정으로 로그인되고 쿠키가 발급된다 → MCP 경로는 `auth_cf` 맨 앞에서 제외해야 한다(§2.4).

## 2. 제안 설계

### 2.1 전송 — Streamable HTTP, JSON 응답 전용, 무상태

| 항목 | 결정(추천) | 이유 |
|---|---|---|
| 전송 | MCP **Streamable HTTP**(2025-03-26+) 단일 엔드포인트 `POST /mcp` | 현행 사양. 구 HTTP+SSE(2024-11-05)는 폐기 예정, 연결 유지형이라 gthread 8스레드·CF 터널에 불리 |
| 응답 | `Content-Type: application/json` 단건 응답만. SSE 스트림 미제공 | 도구가 전부 동기·수백 ms. 서버 발신 알림/샘플링 불필요 |
| `GET /mcp` | 405 (사양 허용: 서버가 SSE 스트림을 제공하지 않을 때) | |
| 세션 | 무상태. `Mcp-Session-Id` 미발급, `DELETE /mcp` 405 | gunicorn `--reload`·워커 재시작에도 끊김 없음, 서버 상태 0 |
| 버전 | `initialize`에서 클라이언트 요청 버전이 `{2025-06-18, 2025-03-26}`이면 그대로, 아니면 `2025-03-26` 회신. 이후 요청의 `MCP-Protocol-Version` 헤더는 지원 목록 밖이면 400 | 사양의 버전 협상 규칙 |
| 배치 | JSON 배열 본문 거부(-32600) | 2025-06-18에서 배치 제거, 처리량 증폭 방지 |
| Origin | `Origin` 헤더가 있으면 허용 목록(`mcp_remote.allowed_origins`, 기본 빈 목록=거부)만 통과, 없으면 통과 | 사양 필수(DNS rebinding 방지). 서버 대 서버 클라이언트는 Origin 미전송 |
| 구현 위치 | 기존 Flask 앱의 새 블루프린트(별도 프로세스·포트 없음) | 같은 컨테이너·같은 cloudflared 경로 재사용. 공식 `mcp` SDK(ASGI)는 서버 2개 운영 부담 → §4 |

stdio와 HTTP는 **같은 프로토콜 코어**를 쓴다: `mcp_server.handle_request`를 `src/mcp_remote/protocol.py`로 옮기고, 도구 허용 집합과 연결 팩토리를 인자로 받게 한다. stdio 진입점(`python3 -m src.mcp_server`)은 그대로 유지(하위 호환).

### 2.2 인증 — Bearer 토큰, 해시 저장, 유저 바인딩

- 형식: `rpmcp_` + `secrets.token_urlsafe(32)`(256bit). 접두는 유출 스캔(GitHub secret scanning 커스텀 패턴 등)용.
- 전달: `Authorization: Bearer <token>`. **경로·쿼리 토큰은 기본 비활성**(로그·리퍼러 노출). 클라이언트가 헤더를 못 넣는 경우만 D3 대안.
- 저장: 전역 인덱스 `data/mcp_tokens.db`(파이프라인/앱 테이블 수에 포함하지 않음, 사용자 아카이브 zip 제외). 사용자 DB에 두면 토큰→사용자 조회가 불가(ADR-033과 같은 이유).

```sql
CREATE TABLE IF NOT EXISTS mcp_tokens (
    token_id     TEXT PRIMARY KEY,            -- 'mt_' + token_hex(6), 목록·감사 표시용
    user_id      TEXT NOT NULL,               -- data/users/<user_id>
    token_hash   TEXT NOT NULL UNIQUE,        -- hex(sha256(token)); 256bit 난수라 느린 KDF 불필요
    label        TEXT NOT NULL,               -- 'genspark' 등 클라이언트 이름
    scope        TEXT NOT NULL DEFAULT 'read',-- v1은 'read' 단일. 확장 여지
    last4        TEXT NOT NULL,               -- 마스킹 표시 '••••abcd'
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    expires_at   TEXT,                        -- 기본 발급+90일, NULL=무기한(비권장)
    revoked_at   TEXT,
    last_used_at TEXT,                        -- 10분 단위 억제 갱신(쓰기 증폭 방지)
    last_client  TEXT                         -- UA 족
);
CREATE INDEX IF NOT EXISTS ix_mcp_tokens_user ON mcp_tokens(user_id);
CREATE TABLE IF NOT EXISTS mcp_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL DEFAULT (datetime('now')),
    token_id TEXT,                            -- 인증 실패 시 NULL
    user_id TEXT, method TEXT, tool TEXT,
    args_json TEXT,                           -- 500자 절단, 도구 인자는 날짜·id뿐
    status TEXT NOT NULL,                     -- ok | tool_error | denied | auth_fail | rate_limited | bad_request
    latency_ms INTEGER, resp_bytes INTEGER,
    ip_hash TEXT                              -- sha256(salt|CF-Connecting-IP)[:16], 원문 IP 미저장
);
```

- 재표시: **1회 표시(해시만)** 추천 — 캘린더 URL(ADR-033, Fernet 재표시)과 달리 데이터 API 자격증명이고, 클라이언트 설정에 한 번 붙여 넣으면 끝이라 재표시 이득이 작다(D2).
- 발급: CLI `scripts/mcp_token.py issue --user <email> --label genspark [--days 90]` — **컨테이너 안에서 실행**(`docker compose exec runpulse ...`), 토큰을 stdout 1회 출력. `list`(token_id·label·last4·만료·마지막 사용), `revoke <token_id>`, `revoke --user <email> --all`. 웹 UI 발급도 v1 범위(D7 확정, R8): CLI와 같은 `token_index` 함수를 공유한다.
- 사용자 존재 검증: 발급 시 `get_db_path(uid, create=False)`가 존재해야 함. 사용자당 활성 토큰 상한 5개.
- 폐기: `revoked_at` 세팅 → 매 요청 조회이므로 즉시 효력. 만료·폐기·미존재·형식 오류·사용자 DB 없음은 **모두 동일한 401**(`WWW-Authenticate: Bearer`), 구분 정보 없음.
- 검증 순서: 형식(`^rpmcp_[A-Za-z0-9_-]{43}$`) → sha256 → UNIQUE 조회 → 만료·폐기 → DB 파일 존재. 해시 인덱스 조회라 문자열 비교 타이밍 문제 없음.
- **Cloudflare Access와의 관계**(D1):
  - (A, 추천) `/mcp` 경로 CF Access 앱에 **Service Auth 정책**(서비스 토큰 `CF-Access-Client-Id/Secret`) + 앱 Bearer. 엣지에서 1차 차단(무차별 요청이 컨테이너에 도달 안 함), 앱에서 2차·유저 바인딩. 클라이언트가 임의 헤더 3개를 넣을 수 있어야 한다.
  - (B, 폴백) `/mcp` **Bypass 정책** + 앱 Bearer만. Genspark가 Authorization 1개만 지원할 때. 엣지 보호는 WAF rate limit 규칙으로 보완.
  - 어느 쪽이든 앱은 CF 헤더를 신뢰 근거로 쓰지 않는다(Bearer가 유일한 신원). CF 서비스 토큰은 "클라이언트 종류" 인증, Bearer는 "사용자" 인증.
  - (C, 후속) MCP 사양 OAuth 2.1(CF Access를 인가 서버로) — Claude.ai/ChatGPT 커넥터처럼 OAuth만 받는 클라이언트가 필요해질 때. v1 범위 밖.

### 2.3 노출 도구 화이트리스트와 쓰기 불가 보장

- `src/mcp_remote/policy.py`:
  - `REMOTE_TOOLS: frozenset` — v1 추천: `_DISPATCH` 15개 전부(모두 SELECT 전용, GPS·이메일 미포함 확인). 단 `get_runner_profile`(나이·최대심박·목표)은 D4.
  - `REMOTE_DENIED: frozenset` — 원격 금지 도구(현재 비어 있음).
  - 테스트로 **`_DISPATCH` 키 = REMOTE_TOOLS ∪ REMOTE_DENIED** 강제 → 새 도구가 분류 없이 자동 노출되지 않는다.
- `tools/list`는 `TOOL_DECLARATIONS`를 REMOTE_TOOLS로 필터, `tools/call`은 디스패치 **전에** 허용 집합 검사(불허 = 미존재와 같은 오류).
- `resources/*`, `prompts/*`, `completion/*`, `logging/setLevel`, `sampling` 미구현 → -32601. capabilities는 `{"tools": {}}`만.
- 쓰기 불가 4중 방어(`src/mcp_remote/safe_conn.py`, stdio도 공용 사용):
  1. `sqlite3.connect("file:...?mode=ro", uri=True)` (현행)
  2. `PRAGMA query_only=ON`
  3. `conn.set_authorizer`: `SQLITE_READ/SELECT/FUNCTION`과 읽기 PRAGMA만 허용, `INSERT/UPDATE/DELETE/CREATE*/DROP*/ALTER/ATTACH/DETACH/TRANSACTION`·쓰기 PRAGMA 거부. `ATTACH` 거부는 **타 사용자 DB 열기 차단**도 겸함.
  4. `conn.set_progress_handler`로 쿼리당 5초 초과 시 중단(무거운 집계로 단일 워커 점유 방지).
- 원격 응답의 예외 문자열은 일반화(`{"error":"도구 실행 실패"}`) — `str(exc)`에 DB 경로(=이메일)가 섞일 수 있음. 상세는 앱 로그(debug)·감사 status로만.

### 2.4 유저 스코프 격리

- 요청 사용자 = **토큰 행의 `user_id`만**. 헤더·쿼리·도구 인자의 사용자 지정 수단 없음(도구 스키마에 user 인자 없음, 미지 인자는 무시).
- `auth_cf._identify_user` 맨 앞에 `request.path == "/mcp"`(및 `/mcp/`) 예외 추가 — 세션을 읽지도 쓰지도 않음 → 로그인 브라우저 쿠키가 있어도 무관, `Set-Cookie` 없음, CF 서비스 토큰 우회(svc_user 로그인)도 타지 않음.
- 핸들러는 세션 의존 `helpers.db_path()`를 쓰지 않고 `get_db_path(uid, create=False)` + 기존 `resolve_db_path`의 uid 검증(경로 구분자·`..` 거부) 재사용.
- 요청마다 연결 열고 닫음(현행). 도구 실행 경로가 `get_current_user_id()`/`load_config()`를 간접 호출하지 않음을 테스트로 고정(monkeypatch로 호출 시 실패) — 컨텍스트 밖 호출 시 `'default'`로 조용히 빠지는 기존 함정 방지.

### 2.5 속도 제한·감사 로그·마스킹

- `rate_window`(워커 1개 전제, ADR-033과 동일):
  - 토큰별 `tools/call` 120회/10분, 1,500회/일 → 429 + `Retry-After`.
  - IP별 인증 실패 20회/10분 → 해당 IP 10분 429(IP는 `CF-Connecting-IP`, 메모리만).
  - 본문 64KB 초과 413(라우트 내 `request.content_length` 검사).
  - 워커 증설 시 무력화 → CF WAF Rate Limiting(`/mcp`, 300/10분/IP)로 대체(체크리스트).
- 감사: `mcp_audit`에 요청 1건 1행(`initialize`·`tools/list`도 기록, `ping`은 생략). 90일 보관, 발급 CLI·하루 1회 기동 시 정리. 조회는 `scripts/mcp_token.py audit [--user] [--since]`.
- 마스킹:
  - 토큰 원문은 DB·로그·감사 어디에도 저장하지 않음. 표시는 `token_id` + `••••last4`(`ai_settings_service.mask_key`와 같은 규칙).
  - gunicorn 접근 로그 기본 포맷은 헤더를 남기지 않음 → Authorization 미기록 확인 테스트. D3에서 경로 토큰을 택하면 `RedactingLogger` 정규식에 `/mcp/<...>` 추가.
  - 앱 로그는 `token_id`만, `user_id`는 debug에서만.

## 3. 배포

- 컨테이너·포트 변경 없음: gunicorn `0.0.0.0:18080` → override `127.0.0.1:80:18080` → cloudflared(token-file) → 기존 호스트명. 경로 `/mcp`만 추가.
- 킬 스위치: `config.json`의 `mcp_remote.enabled`(기본 `false`) — false면 `/mcp` 404. `config.json.example`에 키 추가.
- CF 운영자 조치(코드 밖, 체크리스트): (1) Access 앱에 `<host>/mcp` 경로 앱 추가, D1에 따라 Service Auth 또는 Bypass, (2) 서비스 토큰 발급(A안), (3) WAF rate limit 규칙, (4) 해당 경로 캐시 우회(Cache Rule: bypass) — 응답에 `Cache-Control: no-store`도 부여.
- 대안: 별도 호스트명 `mcp.<domain>`(Access 앱 분리가 깔끔, 메인 쿠키 미공유) — D5.
- 운영 주의: Dockerfile CMD에 `--reload`가 있어 소스 변경 시 rate_window 카운터가 초기화된다(수용 위험).

## 4. 대안과 트레이드오프

| 대안 | 기각 이유 |
|---|---|
| 공식 `mcp` SDK(FastMCP, ASGI) 별도 프로세스 | 의존성·포트·cloudflared ingress 추가, 인증·감사를 두 앱에 이중 구현. 기능(SSE·세션)은 불필요 |
| 구 HTTP+SSE 전송 | 폐기 예정 사양, 장기 연결. Genspark가 SSE만 지원하는 것으로 확인될 때만 `/mcp/sse` 어댑터 추가 |
| CF Access만으로 인증(앱 토큰 없음) | 사용자 바인딩 불가(서비스 토큰은 사용자 무관), 엣지 오설정 시 전면 노출 |
| 캘린더 인덱스(`calendar_feeds.db`) 일반화해 공용 | 스키마 성격 다름(사용자당 1개·재표시 vs 다수·1회 표시·감사). 해시 헬퍼만 공용화 |
| 무상태 서명 토큰(JWT) | 즉시 폐기에 결국 상태 필요(ADR-033과 동일 논리) |
| OAuth 2.1 지금 구현 | 1인 운영·1클라이언트에 과설계. 클라이언트 요구 시 후속 |
| 도구별 컬럼 수준 마스킹 | 현재 도구 출력에 GPS·이메일 없음. 도구 단위 화이트리스트로 충분 |

## 5. 위협 모델과 남는 위험

| 위협 | 대응 | 남는 위험 |
|---|---|---|
| 토큰 유출(클라이언트 설정·로그·화면 공유) | 읽기 전용·1사용자 범위·90일 만료·즉시 폐기·접두 스캔·감사 | 폐기 전까지 해당 사용자 훈련·웰니스 전량 열람 가능 |
| 타 사용자 데이터 접근 | 토큰→uid 단일 경로, 세션 미사용, ATTACH 거부 | 없음(테스트로 고정) |
| 쓰기·스키마 변조 | ro + query_only + authorizer + 허용 메서드 최소화 | 없음 |
| 무차별 토큰 추측 | 256bit, IP 실패 제한, (A안) 엣지 차단 | B안은 요청이 컨테이너까지 도달(소음) |
| DoS(단일 워커를 웹앱과 공유) | 토큰·IP 제한, 5초 쿼리 중단, 64KB, WAF | 대량 분산 요청 시 웹 UI 지연 |
| DNS rebinding·브라우저 CSRF | Origin 검사, 쿠키 미사용 | 없음 |
| 오류 메시지 정보 노출 | 원격 오류 일반화, 동일 401 | 없음 |
| CF 오설정(Bypass 범위 확대) | 앱 Bearer 독립 검증, `auth_cf` 예외는 `/mcp` 정확 일치만 | 웹 경로까지 Bypass되면 웹앱 노출 — 체크리스트 의존 |
| 프롬프트 인젝션으로 LLM이 과다 조회 | 레이트리밋·응답 상한(ADR-016) | 조회 데이터 자체는 클라이언트(LLM 업체)로 전송됨 |
| 제3자 보관 | — | **Genspark 측 저장·학습 정책, CF의 TLS 종단 평문 열람**은 운영자 수용 위험 |

## 6. 단계별 구현 계획 (각 파일 300줄 이하, 테스트 동반)

| 슬라이스 | 내용 | 파일 | 테스트(예상 수) |
|---|---|---|---|
| R1 코어 분리 | `handle_request`를 허용 집합·연결 팩토리 주입형으로 이동, 버전 협상, stdio 유지 | 신규 `src/mcp_remote/__init__.py`(docstring), `protocol.py`; 수정 `src/mcp_server.py` | 기존 `test_mcp_server.py` 통과 + `test_mcp_protocol.py`(8) |
| R2 안전 연결 | ro·query_only·authorizer·progress handler, stdio도 사용 | 신규 `src/mcp_remote/safe_conn.py` | `test_mcp_safe_conn.py`(8: SELECT 성공, INSERT/UPDATE/DELETE/CREATE/ATTACH/쓰기 PRAGMA 실패, 장기 쿼리 중단) |
| R3 정책 | REMOTE_TOOLS/DENIED, 분류 강제 | 신규 `src/mcp_remote/policy.py` | `test_mcp_remote_policy.py`(4) |
| R4 토큰 인덱스 + CLI | DDL·issue/list/revoke/lookup/touch, 만료, 상한 | 신규 `src/mcp_remote/token_index.py`, `scripts/mcp_token.py` | `test_mcp_token_index.py`(10: 평문 미저장 바이트 검색, 폐기 즉시 무효, 만료, 미존재 사용자 발급 거부 등) |
| R5 감사·제한 | `mcp_audit` 기록·정리, rate 키 | 신규 `src/mcp_remote/audit.py` | `test_mcp_audit.py`(5) |
| R6 HTTP 경로 | `POST/GET/DELETE /mcp`, Origin·버전 헤더·배치 거부·413·401·429, 킬 스위치 | 신규 `src/web/views_mcp_remote.py`; 수정 `src/web/auth_cf.py`(예외), `src/web/app.py`(등록), `config.json.example` | `test_mcp_http_routes.py`(14: 쿠키만→401, A쿠키+B토큰→B 데이터, Set-Cookie 없음, 비허용 도구, `get_current_user_id` 미호출, 접근 로그에 토큰 없음 등) |
| R8 웹 발급 | API `GET/POST/DELETE /api/v1/settings/mcp-tokens`(세션 사용자 본인 한정, 평문 1회 응답, 상한 5개), Svelte 설정 카드 | 신규 `src/api/routes_mcp_tokens.py`, 프런트 설정 컴포넌트 | `test_mcp_token_routes.py`(타 사용자 토큰 조회·폐기 불가, 평문 목록 미노출) + 프런트 단위 테스트 |
| R7 문서·운영 | ADR-034, CF 체크리스트, `files_index`·`check_docs`, `.claude/skills/runpulse-data`에 원격 연결법 | `v0.3/data/decisions.md` 등 | 실클라이언트 스모크: Claude Code `claude mcp add --transport http`, Genspark 1회 |

순서: R1 → R2 → R3 → R4 → R5+R6(같은 PR, 감사·제한 없이 공개 경로 배포 금지) → R8 → R7. 운영 배포는 `enabled=false`로 먼저 올리고 CF 정책 적용 후 켠다.

## 7. 검증 항목 (DoD)

1. 운영 모드에서 유효 Bearer로 `initialize`→`tools/list`→`tools/call` 왕복 성공, 토큰 없음·폐기·만료는 동일 401.
2. 다른 사용자 토큰으로 상대 데이터 0건, 세션 쿠키가 결과에 영향 없음, 응답에 `Set-Cookie` 없음.
3. 쓰기 SQL·ATTACH가 authorizer에서 거부(stdio 포함).
4. `_DISPATCH`에 미분류 도구 추가 시 테스트 실패.
5. `mcp_tokens.db`·감사·gunicorn/앱 로그·caplog에 토큰 원문 없음, 아카이브 zip 미포함.
6. 429·413·405·400(버전) 응답 확인, `enabled=false`면 404.
7. Claude Code(HTTP)·Genspark 실연결 스모크.
8. `python3 -m pytest tests/` 전체 통과, `scripts/check_docs.py` 통과.

## 8. 사용자 결정 필요 (추천안)

- **D1 CF Access 정책**: A(Service Auth + Bearer) vs B(Bypass + Bearer). 추천: Genspark가 커스텀 헤더 다수를 지원하면 A, 아니면 B. → 선행 확인: Genspark MCP 설정이 지원하는 전송(Streamable HTTP/SSE)과 헤더 입력 방식.
- **D2 토큰 재표시**: 1회 표시(해시만) vs Fernet 재표시. 추천: 1회 표시.
- **D3 헤더 불가 클라이언트용 경로 토큰(`/mcp/t/<token>`)**: 추천: 미제공, Genspark가 헤더 불가로 확인될 때만 추가(+리댁션).
- **D4 `get_runner_profile` 원격 노출**: 추천: 노출(코칭 품질에 필요, 민감도 낮음). 보수적으로 가면 제외.
- **D5 경로 vs 별도 호스트명**: `/mcp` vs `mcp.<domain>`. 추천: `/mcp`(운영 조치 최소). Access 정책 혼선이 우려되면 호스트명 분리.
- **D6 기본값**: 만료 90일, 레이트 120/10분·1,500/일, 감사 90일. 추천: 그대로.
- **D7 발급 진입점 (확정: CLI + 웹 UI)**: 사용자 결정으로 웹 발급 포함. 웹은 CF 세션 로그인 사용자 본인 토큰만 다룸(`/api/v1/settings/mcp-tokens` GET 목록·POST 발급(평문 1회 응답)·DELETE `<token_id>` 폐기). `/mcp` 자체와 달리 세션 인증을 쓰고, 발급·폐기는 감사 기록. Svelte 설정 화면에 '외부 AI 연결' 카드(발급 폼: 라벨·만료일, 1회 표시 모달+복사, 목록·폐기).

## 9. 임시 방식 — Genspark로 로그 전달 (MCP-REMOTE 완료 전)

- 원본 위치(SSOT): `data/2026_marathon_plan/30_LOGS/{daily,weekly}/`(gitignore, 현재 21파일·약 200KB). 계획·리뷰는 `20_PLANS`, `40_REVIEWS`.
- **권고: 복붙 기본, 대량일 때만 단일 .md 묶음 파일 업로드. zip은 비권장.**
  - 복붙: 질문 범위가 1~2주(주간 로그 + 해당 일일 로그, 수 KB)면 가장 확실하다. 모델이 실제로 읽은 내용이 대화에 남아 검증 가능.
  - zip: 채팅형 LLM 서비스는 압축 내부 파일을 일부만 읽거나 무시하는 경우가 있어 "읽었는지" 확인이 어렵다. 전체 200KB(약 6만 토큰 이상)를 한 번에 넘기면 요약 손실도 크다.
  - 대량(블록 회고 등): 대상 기간 파일을 날짜순으로 이어 붙인 **단일 .md 1개**를 업로드(파일 경계에 `## <파일명>` 헤더). 필요 시 `scripts/` 묶음 스크립트는 별도 BACKLOG 항목으로.
- 공통: 로그는 건강 데이터이므로 Genspark 보관 정책을 수용하는 범위에서만 전달. MCP-REMOTE 완료 후에는 로그 대신 MCP 도구 조회로 대체(원본 데이터 기준이라 로그 전사 오류도 피함).
