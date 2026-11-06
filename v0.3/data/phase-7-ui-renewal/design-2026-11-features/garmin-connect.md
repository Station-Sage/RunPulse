# V2-GARMIN-CONNECT — Garmin 연결·MFA v2 설계

- 작성 2026-11-06 · 상태: 설계 초안(승인 대기) · BACKLOG `[V2-GARMIN-CONNECT]`, `[V1-KEPT]`
- 범위: v2(`/frontend` + `src/api` + `src/services`)에서 Garmin 이메일·비밀번호 로그인, MFA 코드 입력, 토큰 붙여넣기 대체 경로, 연결 해제를 처리한 뒤 v1 `/connect/garmin*` 를 제거한다.
- 범위 밖: 동기화 로직(`src/sync/garmin*.py`의 토큰 기반 `_login`), Strava OAuth, 로컬 동기화 수신 라우트(`/api/garmin/local-sync`, V1-KEPT).

## 1. 현황 조사 (근거)

| 항목 | 현재 동작 | 문제 |
|---|---|---|
| v1 로그인 | `src/web/views_settings_garmin.py` `POST /connect/garmin` → `Garmin(email, pw, return_on_mfa=True).login(tokenstore=...)` | 오류 시 `str(e)[:200]`를 화면에 그대로 노출. 레이트리밋 없음 |
| MFA 대기 상태 | 모듈 전역 `_pending_mfa: dict` (uuid → Garmin 인스턴스) | **TTL 없음**(영구 누수), **사용자 바인딩 없음**(key만 알면 다른 사용자가 완료 가능), 잘못된 코드 1회에 `pop` 해서 재시도 불가 |
| tokenstore 경로 | `~/.garminconnect/<safe_uid>` (`@`→`_at`), 컨테이너 `/root/.garminconnect` = 호스트 `./.garminconnect` 바인드 | `data/users/<uid>/` 밖이라 사용자 격리·백업 경계와 어긋남. 경로가 MFA 폼 hidden·쿼리로 왕복 |
| 토큰 로딩 | `src/sync/garmin_auth.py::_tokenstore_path` 우선순위: ①config `garmin.tokenstore` 명시 ②`data/users/<uid>/.garminconnect` ③루트 | v1 이 ①을 항상 써서 ②가 사실상 미사용 |
| 토큰 파일 | `garmin_tokens.json`(di_token·di_refresh_token·di_client_id). garminconnect 0.3.18 `dump()`가 0600 파일·0700 디렉터리, 원자적 교체 | 평문(파일 권한으로만 보호) |
| 자격증명 암호화 | `src/utils/credential_store.py` Fernet `enc:` — `garmin.password` 가 대상 필드 | v1 은 비밀번호를 저장하지 않음(이메일만). 과거 저장분이 남아 있을 수 있음 |
| `garmin_push._login` | `src/training/garmin_push.py` 가 `src.sync.garmin_auth._login` 재사용(토큰 전용, 비밀번호 로그인 없음) | 변경 불필요. 토큰 경로만 일치하면 됨 |
| v2 | `data_connect_service.connect('garmin')` → `UNSUPPORTED`(422). `disconnect('garmin')` 은 `_CRED_FIELDS`에 garmin 없음 → **아무것도 지우지 않음** | 해제 버그 |
| 라이브러리 MFA | `client.resume_login()`: 잘못된 코드·429 는 대기 상태 유지(재시도 가능). MFA 상태는 **인스턴스 메모리**(`_mfa_session`/`_mfa_flow`)에만 있고 직렬화 불가 | 프로세스 내 보관 강제 |
| 프로세스 | Dockerfile `gunicorn --workers 1 --threads 8`(gthread) | 단일 프로세스라 메모리 보관 가능. workers>1 이면 깨짐 |
| v1 부가 기능 | 토큰 업로드/붙여넣기, 로컬 스크립트·`.env` 다운로드, CF Service Token 저장 | `cf-settings` 는 **아무 로그인 사용자나 `default` config 의 전역 CF 토큰을 덮어씀**, `.env` 다운로드에 전역 CF secret 포함 |

## 2. 상태 전이

```
            ┌──────────── cancel / TTL(300s) 만료 / 오답 5회 ────────────┐
            v                                                           │
 [disconnected] --POST connect{email,pw}--> (Garmin 로그인 시도)        │
     ^   ^                │ 성공(MFA 없음)        │ needs_mfa           │
     │   │                v                       v                     │
     │   │          [connected] <--성공-- [mfa_pending(uid, ticket, exp, tries)]
     │   │                │                       │ 오답 → tries+1, 유지 ┘
     │   │                │                       │ 429 → 유지, Retry-After
     │   └── 실패(비번오류/429/상류오류): 상태 변화 없음, 기존 토큰 보존
     └──── POST disconnect: 토큰 파일 삭제 + email/tokenstore 비움
 [connected] --토큰 만료(sync 시 GarminAuthRequired)--> [needs_reauth] --connect--> ...
```

- `needs_reauth` 는 저장 상태가 아니라 `check_garmin_connection` 결과로 화면이 판단한다(기존 그대로).
- 사용자당 대기 상태는 최대 1개. 새 `connect` 는 기존 대기 상태를 폐기한다.

## 3. 상세 설계

### 3.1 모듈

| 파일(신규/변경) | 책임 |
|---|---|
| `src/services/garmin_connect_service.py`(신규, ≤250줄) | 비밀번호 로그인, MFA 완료, 토큰 붙여넣기, 해제. 예외→오류코드 매핑 |
| `src/services/garmin_mfa_store.py`(신규, ≤120줄) | 대기 상태 보관: `put/get/consume/discard/sweep`, `threading.Lock`, 단조시계 TTL |
| `src/services/data_connect_service.py`(변경) | `connect('garmin')` → 서비스 위임, `_CRED_FIELDS['garmin']` 추가, 해제 시 토큰 파일 삭제 위임 |
| `src/api/routes_data.py`(변경) | 상태코드 매핑 확장, `/mfa`·`/mfa/cancel`·`/token` 라우트 추가(분량 초과 시 `routes_data_garmin.py` 분리) |

### 3.2 대기 상태 저장소

```python
@dataclass
class PendingMfa:
    user_id: str
    ticket_hash: str        # sha256(ticket). 원문 ticket 은 응답으로만 1회 전달
    client: "Garmin"        # MFA 세션을 쥔 인스턴스. password 는 None 으로 비운 뒤 보관
    email: str
    expires_at: float       # time.monotonic() + 300
    tries: int = 0          # 오답 누적, 5 도달 시 폐기

def put(user_id, client, email) -> str            # 기존 항목 폐기 후 저장, ticket(secrets.token_urlsafe(32)) 반환
def get(user_id, ticket) -> PendingMfa | None     # uid 일치 + hmac.compare_digest + 미만료
def discard(user_id) -> None
def sweep(now=None) -> int                        # put/get 호출 시마다 만료 항목 제거
```

- 키는 **user_id**(세션 인증 결과), ticket 은 2차 검증. 다른 사용자의 ticket 은 uid 불일치로 무효.
- TTL 300초: Garmin MFA 코드(이메일·앱) 유효시간보다 짧지 않게, 비밀번호 로그인 재시도 비용(429 위험)을 줄이는 쪽으로 선택.
- 단일 프로세스 전제: `app.py` 기동 시 `WEB_CONCURRENCY`/gunicorn workers > 1 이면 경고 로그 + 서비스가 MFA 단계에서 `MFA_UNAVAILABLE` 반환(조용한 실패 방지).
- 재시작(`--reload` 포함) 시 대기 상태 소실 → `MFA_EXPIRED` 로 처리, 화면은 처음 단계로.

### 3.3 로그인·토큰 저장 흐름

```python
def start_login(user_id, email, password) -> tuple[dict, str | None]:
    client = Garmin(email, password, return_on_mfa=True)
    status, _ = client.login(tokenstore=None)   # 기존 토큰을 읽지 않는 새 로그인(다른 계정 토큰 재사용 방지)
    client.password = None                        # 라이브러리는 needs_mfa 경로에서 비밀번호를 비우지 않음
    if status == "needs_mfa":
        return {"status": "needs_mfa", "mfa_ticket": store.put(user_id, client, email), "expires_in": 300}, None
    return _persist(user_id, client, email), None
```

- `_persist`: 대상 `data/users/<uid>/.garminconnect/`(=`_tokenstore_path` 규칙 ②, uid 는 `validate_uid` 통과값). `client.client.dump(path)`(0600·원자 교체) → `update_service_config('garmin', {'email': email, 'tokenstore': '', 'password': ''}, user_id=uid)`. 명시 `tokenstore` 를 비워 규칙 ②로 수렴하고 과거 저장 비밀번호(`enc:`)를 제거한다.
- 저장 실패 시 기존 토큰 파일은 건드리지 않는다(dump 가 임시파일→replace).
- 비밀번호: 요청 본문 → 지역 변수 → 라이브러리 호출로만 흐른다. config·DB·로그·응답·대기 상태에 남기지 않는다. `user_id="default"`(단일 사용자 모드)도 같은 규칙, 경로는 규칙 ③.
- 토큰 파일 암호화(`enc:`)는 하지 않는다: 라이브러리가 파일을 직접 읽고 쓰며, 복호화 키가 같은 호스트 env 에 있어 실익이 작다. 0600 권한 + `data/` 비커밋으로 대응(잔여 위험 §5-R7).

### 3.4 API 명세 (봉투 `api_ok`/`api_error`, 모두 POST, 응답 `Cache-Control: no-store`)

| 경로 | 요청 | 성공 200 `data` | 오류 |
|---|---|---|---|
| `/api/data/sources/garmin/connect` | `{email, password}` | `{status:"connected", message_ko}` 또는 `{status:"needs_mfa", mfa_ticket, expires_in:300}` | 400 `INVALID_PARAM`(빈 값, email>254, pw>256) · 401 `GARMIN_AUTH_FAILED` · 429 `RATE_LIMITED`(로컬) · 503 `GARMIN_RATE_LIMITED`+`Retry-After` · 502 `GARMIN_UPSTREAM` |
| `/api/data/sources/garmin/mfa` | `{mfa_ticket, code}` (code `^\d{6,8}$`) | `{status:"connected", message_ko}` | 400 `INVALID_PARAM` · 422 `MFA_INVALID` `{attempts_left}` · 410 `MFA_EXPIRED` · 429/503 위와 동일 · 503 `MFA_UNAVAILABLE` |
| `/api/data/sources/garmin/mfa/cancel` | `{}` | `{status:"disconnected"}` (멱등) | — |
| `/api/data/sources/garmin/token` | `{token_json}` (≤16KB, `di_token` 또는 `di_refresh_token` 필수) | `{status:"connected"}` | 400 `INVALID_PARAM` · 401 `GARMIN_AUTH_FAILED`(검증 로그인 실패) |
| `/api/data/sources/garmin/disconnect` | `{keep_data:true}` (기존) | `{provider, keep_data:true}` | 기존과 동일 |
| `/api/data/sources/garmin/test` | (기존) | (기존) | — |

- 401 `GARMIN_AUTH_FAILED` 는 앱 세션 만료 401 과 구분되도록 프런트 `ApiError.code` 로 분기(세션 401 은 기존 `AUTH_REQUIRED`).
- 메시지는 고정 한국어 문자열. 예외 원문(`str(e)`)은 응답에 넣지 않고 `log.warning` 에 예외 **클래스명만** 기록.
- 연결 직후 동기화는 이 API 가 시작하지 않는다. 화면이 기존 v2 동기화 요청(Data 화면 동기화와 같은 API)을 호출한다.
- `/token` 은 저장 후 `Garmin().login(tokenstore=임시경로)` 로 1회 검증하고 통과 시에만 사용자 경로로 이동한다.

### 3.5 레이트리밋·가드·헤더

- 로컬 제한(`src/utils/rate_window.hit`): `garmin:login:uid:<uid>` 5회/15분, `garmin:login:ip:<ip>` 10회/15분, `garmin:mfa:uid:<uid>` 10회/5분, `garmin:token:uid` 10회/15분. 초과 시 429 `RATE_LIMITED`.
- 상류 429(`GarminConnectTooManyRequestsError`): 사용자별 쿨다운 15분을 `rate_window` 키 `garmin:cooldown:<uid>` 로 기록, 쿨다운 중 `connect` 는 Garmin 호출 없이 503 + `Retry-After`. 라이브러리가 내부에서 전략 5종을 돌며 재시도하므로 **앱은 재시도하지 않는다**(코딩 규칙의 재시도 1회는 sync 용, 로그인은 계정 잠금 위험).
- Origin 관문(`src/web/request_guard.py`, ADR-048): `/api/*` POST 는 이미 enforce 대상, 면제 추가 없음. 테스트는 `headers={"Origin": "http://localhost"}`.
- 보안 헤더: `response_policy` 공통 헤더(nosniff·XFO DENY·Referrer-Policy) 유지 + 위 4개 라우트 `Cache-Control: no-store`.
- 로그: `RedactingLogger` 위에서 요청 본문 로깅 금지. 이메일은 `a***@domain` 마스킹.

### 3.6 화면 — 연결 설정 시트 (시각 상세는 product-architect 소관, 여기선 상태·데이터만)

`ConnectPanel.svelte` 의 `provider==='garmin'` 분기에서 v1 링크를 "Garmin 연결" 버튼 → 시트로 교체. `Step1Connect.svelte` 의 `href:'/connect/garmin'` 도 시트 진입으로 교체.

| 단계 | 입력/표시 | 전이 |
|---|---|---|
| ① 자격 입력 | 이메일(저장값 미리 채움, `autocomplete="username"`), 비밀번호(`type=password`, `autocomplete="current-password"`), 안내 "비밀번호는 저장하지 않아요" | connected→③, needs_mfa→② |
| ② MFA | 코드(`inputmode="numeric"`, `autocomplete="one-time-code"`, 6~8자리), 남은 시간(expires_in 카운트다운), 남은 시도, "처음부터"(cancel 호출) | connected→③, `MFA_EXPIRED`→① |
| ③ 완료 | "연결됐어요", "최근 30일 가져오기"(기존 동기화 API) | 닫기 |
| 접힘: 고급 | 토큰 JSON 붙여넣기(로컬 PC 발급본) | connected→③ |

- `mfa_ticket` 은 컴포넌트 메모리에만 보관(URL·localStorage 금지). 비밀번호 필드는 요청 직후 비운다.
- 오류 표시는 `ApiError.code` → 문구 매핑(§4).

## 4. 실패 시나리오

| 상황 | 서버 판정 | 응답 | 화면 | 부수효과 |
|---|---|---|---|---|
| 잘못된 비밀번호 | `GarminConnectAuthenticationError` | 401 `GARMIN_AUTH_FAILED` | "이메일 또는 비밀번호가 맞지 않아요" ①유지 | 기존 토큰·config 불변, 로컬 카운터+1 |
| MFA 오답 | `resume_login` 인증 오류, 대기 유지 | 422 `MFA_INVALID {attempts_left}` | 코드 지우고 재입력 | tries+1, 5회째 폐기 후 410 |
| MFA 만료(5분 경과·재시작) | store 미존재 | 410 `MFA_EXPIRED` | "시간이 지났어요. 다시 로그인해 주세요" → ① | 없음 |
| 다른 사용자 ticket | uid 불일치 | 410 `MFA_EXPIRED`(존재 여부 숨김) | — | 보안 로그 |
| Garmin 429(로그인/MFA) | TooManyRequests | 503 `GARMIN_RATE_LIMITED`, `Retry-After: 900` | "Garmin이 잠시 막았어요. N분 뒤 다시" | 쿨다운 기록, MFA 대기는 유지 |
| 로컬 레이트리밋 | `rate_window.hit` False | 429 `RATE_LIMITED` | "시도가 너무 많아요" | Garmin 호출 없음 |
| 상류 연결 오류/검증 실패 | ConnectionError 등 | 502 `GARMIN_UPSTREAM` | "Garmin에 연결하지 못했어요" | 대기 상태 폐기 |
| 라이브러리 미설치 | ImportError | 503 `GARMIN_UPSTREAM` | 동일 | 운영 로그 error |
| 토큰 저장 실패(디스크) | OSError | 500 `INTERNAL` | 일반 오류 | 기존 토큰 보존(원자 교체) |
| 이중 제출 | 두 번째 요청이 소비된 ticket | 410 | 무시 | — |

## 5. 보안 위험과 대응

| ID | 위험 | 대응 |
|---|---|---|
| R1 | 비밀번호 유출(저장·로그·오류문) | 비저장, 본문 로깅 금지, 예외 원문 미노출, 대기 인스턴스 `password=None`, 과거 `garmin.password` 제거 |
| R2 | MFA 세션 탈취/교차 사용자 완료 | uid 키 + 256bit ticket 해시 비교, TTL 300s, 오답 5회 폐기 |
| R3 | 계정 무차별 대입·Garmin 계정 잠금 | uid·ip 이중 레이트리밋, 상류 429 쿨다운, 앱 재시도 금지 |
| R4 | CSRF | Origin 관문 enforce, JSON 본문 전용 |
| R5 | 다른 Garmin 계정 토큰 재사용 | 비밀번호 로그인은 `tokenstore=None` 새 세션, 성공 후에만 덮어쓰기 |
| R6 | 경로 조작(tokenstore 를 클라이언트가 지정) | 경로는 서버가 uid 로 계산(`validate_uid`), 요청에 경로 필드 없음 |
| R7 | 토큰 파일 평문 | 0600/0700, `data/` 비커밋. 잔여 위험으로 수용(§3.3) |
| R8 | 전역 CF 토큰 덮어쓰기(v1 `cf-settings`) | v2 로 이전하지 않음. 운영자가 `config.json` 직접 관리 |
| R9 | 메모리 대기 상태 누수 | sweep, 사용자당 1개 상한 |
| R10 | 붙여넣기 JSON 악용(대용량·임의 키) | 16KB 상한, 허용 키만 저장, 검증 로그인 통과 시에만 채택 |

## 6. 구현 작업 (외부 호출은 전부 `garminconnect.Garmin` mock)

| T | 내용 | 테스트 포인트(파일) |
|---|---|---|
| T1 | `garmin_mfa_store.py` | put/get/consume, TTL 만료(시계 주입), uid 불일치, 사용자당 1개, 오답 5회 폐기, sweep (`tests/test_garmin_mfa_store.py`, ~9) |
| T2 | `garmin_connect_service.start_login/_persist` | 성공 시 규칙② 경로 dump·config `tokenstore/password` 비움, needs_mfa 시 `password is None`, `login(tokenstore=None)` 호출 확인, 인증오류·429·연결오류 매핑, 실패 시 기존 토큰 보존 (`tests/test_garmin_connect_service.py`, ~10) |
| T3 | `complete_mfa`, `cancel` | 정상 완료, 오답 유지+attempts_left, 만료 410, 429 시 대기 유지 (~6, 같은 파일) |
| T4 | `submit_token` + 해제 | 크기·키 검증, 검증 로그인 실패 시 미채택, disconnect 가 토큰 파일 삭제·email/tokenstore 비움(현 버그 회귀) (~6) |
| T5 | API 라우트·상태코드·레이트리밋·쿨다운·`no-store` | Origin 헤더 포함 test_client, 429/503 `Retry-After`, 응답에 password·토큰 미포함 검사 (`tests/test_api_garmin_connect.py`, ~12) |
| T6 | 프런트 시트 + `lib/api/data.ts` 함수 3개 | 단계 전이·오류코드 문구(vitest), 브라우저 스모크(MFA 는 mock 서버) |
| T7 | 안내 문구·링크 교체 | `/connect/garmin` 참조 10곳(`bg_sync.py`, `garmin_auth.py`, `routes_v1_pages.py` 등)을 `/v2/data/sources/garmin` 으로, 문자열 테스트 갱신 |
| T8 | 로컬 동기화 키트 이전 | `GET /api/data/sources/garmin/local-kit/script`·`/env` — `.env` 에 CF secret 은 **빈칸**으로(R8). `tests/test_garmin_local_sync_api.py` 확인 |
| T9 | workers>1 감지 경고 | 설정값 주입 테스트 1 |

예상 테스트 ~45개. 각 T 완료 시 전체 pytest(.venv) 통과.

## 7. v1 제거 절차

1. T1~T9 배포, 운영에서 브라우저로 실제 연결 1회(MFA 계정이면 MFA 포함) 확인 — `[V1-REMOVAL-BROWSER-TEST]` 항목에 기록.
2. 기존 사용자 토큰 이관: 운영 config 의 명시 `garmin.tokenstore`(`/root/.garminconnect/<safe_uid>`)는 규칙①로 계속 동작하므로 강제 이관하지 않는다. 사용자가 v2 에서 재연결하면 규칙②로 수렴. 일괄 이관이 필요하면 별도 스크립트(백업→복사→config 갱신, 사용자 승인 후).
3. `src/web/app.py` 에서 `settings_garmin_bp` import·등록 제거, `views_settings_garmin.py` 를 `v1_backup/` 으로 이동.
4. `tests/test_views_settings_garmin_migration.py` 의 유효 단언(토큰 마이그레이션 상태 문구)은 `check_garmin_connection` 테스트로 옮기고 나머지 삭제.
5. `data_connect_service` 의 `UNSUPPORTED` 분기 삭제, BACKLOG `[V1-KEPT]` 에서 `/connect/garmin` 제거, `docker-compose` 의 `./.garminconnect` 볼륨은 2단계 이관 완료 확인 후 제거(그 전엔 유지).
6. `grep -rn "/connect/garmin" src frontend/src tests` 결과 0건, `check_docs.py`·`gen_files_index.py` 실행, `decisions.md` 에 ADR(토큰 경로 규칙② 수렴, MFA 메모리 보관·TTL) 기록.

## 8. 확정한 판단 (미결 없음, 사용자 승인 대상)

- MFA 상태는 프로세스 메모리(직렬화 불가 + 단일 워커). DB·파일 보관 안 함.
- TTL 300초, 오답 5회, 로컬 로그인 5회/15분, 상류 429 쿨다운 15분.
- 토큰 경로는 `data/users/<uid>/.garminconnect` 로 수렴, 토큰 파일 암호화는 하지 않음.
- 토큰 붙여넣기는 v2 고급 경로로 유지, 업로드(multipart)는 붙여넣기로 통합. CF 설정 폼은 폐기.
- 연결 후 동기화는 화면이 기존 동기화 API 로 시작.

## 9. 검증 항목

1. 응답·로그·config·`data/users/<uid>/` 어디에도 비밀번호 원문·`enc:` garmin.password 가 남지 않는다.
2. 사용자 A 의 ticket 으로 사용자 B 세션이 완료할 수 없다.
3. 연결 후 `src.sync.garmin_auth._login` 과 `garmin_push` 가 같은 토큰 파일을 읽어 성공한다.
4. 해제 후 `check_garmin_connection` 이 미연결을 반환한다.
5. 429 연속 시 Garmin 호출 횟수가 쿨다운 동안 0이다(mock 호출 수 검사).
