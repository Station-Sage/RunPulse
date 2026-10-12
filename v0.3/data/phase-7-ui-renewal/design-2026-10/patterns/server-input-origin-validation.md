# 설계: 쓰기 API 서버 입력 검증·Origin 검증

- 대상 ID: T-15, P-04, P-05, D-22, E-02, C-02 (참고 동일 원인: P-17, C-18)
- 상태: 설계 확정 (구현 전). D1~D9 결정 완료(2026-10-11, `decisions-table.md` SRV-1~9). 2026-10-11 설계서 동기화. 2026-10-11 4차 동기화(V1-1). 2026-10-11 5차 동기화(V1-1 정정·V1-2·V1-3). 2026-10-11 6차 동기화(V1-8·V1-9·V1-10). 2026-10-11 7차 동기화(V1S-2·V1S-3·V1S-5·V1-12·V1-13). 2026-10-11 8차 동기화(V1-15·V1-16). 2026-10-12 9차 동기화(SRV-10~13·SEC-10·ADR-1·NEW-40). 2026-10-12 10차 동기화(V1-20, 설계 단계 마지막).
- 관련 ADR: ADR-034 (원격 MCP의 Origin 불일치 거부 — `_origin_ok`가 이미 있는 선례. 현 위치 `src/web/views_mcp_remote.py` → V1S-3 로 `src/mcp_remote/http.py` 이관), 신규 **ADR-048**(D9, 번호 확정 ADR-1 — SRV 048, SEC 049, FRS 050, NRA 051)

## 1. 근본 원인

**RC-1. 서버에 "요청 경계 계약"이 없다.** `/api/v1` 쓰기 라우트 38개는 모두 `request.get_json(silent=True) or {}`로 본문을 받는다.
- JSON이 아닌 본문(text/plain, 깨진 JSON)도 조용히 `{}`가 되어 선택 필드만 있는 라우트는 그대로 실행된다(D-22: 캘린더 피드 생성 201·삭제 204).
- 필드 타입·범위 검증은 라우트마다 따로 하거나(`_reported_km`, `_message_input`, `validate_patch` 3종) 아예 없다. 체크인(T-15)은 `save_checkin`에 원시값을 그대로 넘기고, 플랜 생성(P-05)은 `int(weeks)`·`float(distance_km)` 캐스팅만 하며, 서비스가 `max(1, min(weeks, avail))`로 조용히 보정한다. 템플릿 비교 GET(P-04)도 과거 날짜·범위 밖 목표 시간을 검증하지 않는다.
- 예상 못 한 타입이면 예외가 그대로 올라가는데 `api_bp`에 오류 처리기가 없어 HTML 500이 나간다(C-02 `initial_message: 123` → `.strip()` AttributeError, P-05 `distance_km:"abc"`). 엔벨로프 계약 `{error:{code,message}}` 위반.

**RC-2. 상태 변경 요청의 출처를 확인하는 앱 전역 관문이 없다.** 신원은 CF Access 헤더 → Flask 세션 쿠키로만 잡히고(`auth_cf._identify_user`), 쓰기 요청이 같은 출처에서 왔는지 아무도 보지 않는다. 세션 쿠키에 `SameSite`/`Secure`를 명시하지 않았다(`app.py`에 `SESSION_COOKIE_*` 설정 없음). Origin 검사는 `/mcp`에만 있다. v1 `/switch-user`(E-02)는 폼 입력 uid를 검증 없이 `init_db(uid)` → `get_db_path`가 `data/users/<uid>`를 `mkdir`하므로 `../` 등 경로 이탈 입력도 디렉터리를 만들 수 있고, `<option value>`가 이스케이프되지 않는다.

## 2. 설계안 (A안 확정)

### 2.1 Origin 관문 — `src/web/request_guard.py` (신규)
- 위치(V1-16 (c')): `src/web/` — 앱 조립 계층으로 v1 일몰 후에도 유지('src/web = 앱 셸 전용': `app.py`·`auth_cf.py`·`request_guard.py`·`response_policy.py`·`spa_static.py`). view 밖 이관(V1-10) 대상이 아니다.
- 앱 전역 `before_request` 1개. 대상: 메서드가 POST/PUT/PATCH/DELETE인 모든 요청.
- 판정(D2): 허용 출처 = `public_base_url()`의 출처 + 개발용 허용 목록 상수 `DEV_ALLOWED_ORIGINS`(`http://localhost:5173` 등, development 설정에서만 적용). 프록시 뒤 `request.host`(Host 헤더)는 비교 기준으로 쓰지 않는다. `Origin`이 있으면 그것으로, 없으면 `Referer`의 출처로 판정한다.
- Origin·Referer 둘 다 없는 쓰기 요청은 **거부**한다(D1).
- 모드(D8): `ORIGIN_GUARD_MODE ∈ {observe, enforce}` 설정값. `observe`는 거부 대상 요청을 로그(path·method·Origin·Referer)만 남기고 통과, `enforce`는 거부. 초기 배포는 `observe`로 **2주** 운영하고, 그 기간 거부 대상(위반) 로그가 0건이면 `enforce`로 전환한다(SEC-10 (b), CSP Report-Only 와 같은 기간).
- 면제 목록(명시적 상수 `EXEMPT_PATHS`): `/mcp`(자체 Origin·Bearer 검사, ADR-034), `/api/garmin/local-sync`(sync_key 2차 인증, 로컬 스크립트), `/feeds/cal/`(GET 전용 공개 피드), `/api/v1/csp-report`(브라우저 CSP 보고, 로그 전용 — `security-headers.md` D6). `/api/context-episodes`는 면제가 아니다(NEW-40).
- **봉투 경로 규칙(NEW-40 (b))**: `/api/v1` 접두에 기대던 규칙(거부 응답 봉투 형식, 2.3 오류 핸들러 등록 대상)은 접두 하드코딩 대신 봉투 경로 상수 `ENVELOPE_PATH_PREFIXES = ("/api/v1/", "/api/context-episodes")`(`request_guard.py`)로 판정한다. `/api/context-episodes`는 현 경로를 유지하면서(`/api/v1` 밖) 같은 응답 봉투·Origin 관문·입력 제한을 예외 없이 받는 명시 대상이다(`adjustment-new-signals.md` §2.8). 2.2 입력 검증은 라우트별 `parse_body` 호출이라 접두와 무관하며 이 경로의 쓰기 라우트도 적용한다(2.4). 앞으로 `/api/v1` 밖에 봉투 API 를 두면 이 상수에 추가한다.
- 거부 응답: `ENVELOPE_PATH_PREFIXES` 경로 → `api_error("FORBIDDEN_ORIGIN", ..., 403)`, 그 외 → text 403.
- `_origin_ok` 로직은 이 모듈의 `same_origin(request) -> bool`로 옮기고 `src/mcp_remote/http.py`(V1S-3, 현 `views_mcp_remote`)가 재사용한다(중복 제거).
- 세션 쿠키(D3·SRV-10): `SESSION_COOKIE_SAMESITE="Lax"`, `SESSION_COOKIE_HTTPONLY=True`, `SESSION_COOKIE_SECURE`를 `create_app`에서 명시한다. `SESSION_COOKIE_SECURE`는 `APP_ENV == "production"`일 때 참(SRV-10 (a)) — 코드가 이미 같은 키로 운영을 판정한다(`app.py:156` `_resolve_secret_key`, `auth_cf.py:24` `_IS_PRODUCTION`). 별도 설정값 없음.

### 2.2 요청 스키마 계층 — `src/api/validation.py` (신규)
- 라우트 경계에서 쓰는 작은 선언형 검증기. 외부 의존성(pydantic 등) 없이 순수 함수로 만든다.
  ```python
  Field = int_field(lo, hi) | float_field(lo, hi, lo_exclusive=False) | enum_field(values)
        | date_field(min_date=None, max_date=None) | str_field(max_len, required)
        | int_list_field(...)   # 정수 배열(중복 제거) — NEW-40, adjustment-new-signals.md §2.8 chat_thread_ids
  def parse_body(schema: dict[str, Field], *, require_json: bool = True)
      -> tuple[dict, ApiErrorResponse | None]
  def parse_args(schema) -> tuple[dict, ApiErrorResponse | None]   # GET 쿼리(P-04 templates)
  ```
- 규칙: 형식이 틀리거나 범위 밖이면 **조용히 보정하지 않고** `400 INVALID_PARAM` + `details={field: reason}`로 거부한다. 타입 강제 변환은 문자열 숫자("5")처럼 손실 없는 경우만 허용, `5.5`→int, `True`→int는 거부.
- `require_json=True`일 때 `request.is_json`이 아니면 `415 UNSUPPORTED_MEDIA_TYPE`, JSON 파싱 실패면 `400 INVALID_PARAM`(D5). 본문 없는 DELETE·multipart(`/data/import/preview`)는 `require_json=False`.
- 415 면제(SRV-12 (a)): `POST /api/v1/csp-report`는 브라우저가 `application/csp-report`(또는 `application/reports+json`)로 보내므로 `parse_body`를 쓰지 않고 415 검사에서 빠진다. 본문 크기·형식 제한은 그 엔드포인트 전용 처리로 별도로 둔다(`security-headers.md` 2.2).
- 도메인 값의 SSOT(D4): 범위·열거값은 상수 모듈 `src/services/input_limits.py`(신규) 한 곳에 둔다. 스키마와 서비스 함수가 같은 상수를 참조하고, 서비스는 내부 호출(MCP·CLI)을 위해 최소 불변식(`ValueError`)을 유지한다. 값은 운영 데이터로 확인 후 조정한다.

  | 상수 | 값 |
  |---|---|
  | `FATIGUE_RANGE` | 정수 1~10 |
  | `PAIN_LEVELS` | `none/mild/moderate/severe` |
  | `CHECKIN_NOTE_MAX` | 500자 |
  | `COACH_MESSAGE_MAX` | 4,000자 |
  | `DISTANCE_KM` | 0 초과 250 이하 |
  | `WEEKS_RANGE` | 정수 1~52 |
  | `TARGET_TIME_SEC` | 0 초과 172,800 이하 |
  | `RACE_DATE_WINDOW` | 오늘(포함) ~ 오늘+5년 |
- weeks 보정(D7): `WEEKS_RANGE` 밖은 400. 범위 안이지만 대회일까지 가능 주수(`avail`)를 넘으면 `min(weeks, avail)`로 보정을 유지하고, 성공 응답의 `meta` 안에 경고(`meta.warnings: [{code:"WEEKS_ADJUSTED", requested, applied}]`)를 함께 반환한다(SRV-11 (a) — `api_ok(data, status, meta)`의 기존 `meta` 인자, `src/api/__init__.py:18`, 엔벨로프 형식 변경 없음). 서비스는 보정 사실을 반환값으로 알린다(조용한 보정 제거).
- 기존 `_reported_km`, `_message_input`, `validate_patch`/`validate_auto_patch`/`validate_changes`는 1차 적용 범위 밖이지만, 형태를 맞춰 점진 이관할 수 있게 `(clean, err)` 반환 규약을 그대로 따른다.

### 2.3 엔벨로프 보장 — `src/api/__init__.py` (수정)
- `errorhandler(HTTPException)` → 같은 상태코드의 `api_error`, `errorhandler(Exception)` → 로그 + `api_error("INTERNAL", ..., 500)`. 입력 검증이 빠진 라우트가 남아도 HTML 500은 나가지 않는다(안전망이지 검증 대체가 아님).
- 공용 등록 함수(NEW-40): 두 핸들러를 `register_envelope_handlers(bp)`(`src/api/__init__.py`)로 만들어 `api_bp`(`url_prefix="/api/v1"`)와 `/api/context-episodes`의 별도 블루프린트 `context_bp`(`routes_context.py`, `adjustment-new-signals.md` §2.8)에 같은 함수로 등록한다(핸들러 복제 금지). 2.1 `ENVELOPE_PATH_PREFIXES`와 대상이 일치해야 한다.

### 2.4 1차 적용 라우트
| 증상 | 라우트 | 스키마 요지 (값은 2.2 상수) |
|---|---|---|
| T-15 | POST `/today/checkin` | fatigue `FATIGUE_RANGE`, pain enum `PAIN_LEVELS`(프론트 `PainLevel`), note ≤`CHECKIN_NOTE_MAX` |
| P-05 | POST `/coach/plan` | distance_km `DISTANCE_KM`, weeks `WEEKS_RANGE`(가능 주수 초과는 보정+경고), race_date `RACE_DATE_WINDOW`, target_time_sec `TARGET_TIME_SEC`, name str |
| P-04 | GET `/coach/plan/templates` | 위와 같은 race_date·target_time_sec·distance_km 규칙(`parse_args`) |
| C-02 | POST `/coach/threads`, `/threads/<id>/messages` | initial_message/text ≤`COACH_MESSAGE_MAX`, chip_id enum(`CHIP_TEXT`) — `_message_input`을 스키마 위로 재작성 |
| E-02 | 사용자 전환(현 v1 POST/GET `/switch-user` → v2 이관, 2.5) | production에서 차단(404, D6 — 이관 후 v2 엔드포인트에 적용). 개발 환경은 uid 허용 규칙(2.6, SRV-13) + `get_db_path` 경로 이탈 차단(`resolve()`가 `data/users` 하위인지) |
| NEW-40 | `/api/context-episodes`(GET/POST/PATCH/DELETE, `/api/v1` 밖) | 스키마는 `adjustment-new-signals.md` §2.8(`chat_thread_ids` → `int_list_field`, 상수는 `input_limits.py`). 이 문서의 규칙(2.1 봉투 경로·Origin 관문, 2.2 `parse_body`, 2.3 공용 핸들러)을 예외 없이 적용 |

### 2.5 사용자 전환 v2 이관 (V1-3 (b) 결정)
v1 일몰은 UI·라우트 일몰이다(V1-2). 사용자 전환 로직은 유지해 v2 로 이관한 뒤 v1 `/switch-user` 라우트를 제거한다.
- **현행(코드 확인 2026-10-11)**: `app.py:266` 라우트 안에 로직이 인라인이다 — POST는 `session["user_id"] = uid` + `init_db(uid)` 후 `/` 리다이렉트, GET은 `data/users` 하위 디렉터리 목록을 `<option>` 문자열로 조립(미이스케이프). v2 API도 같은 Flask 세션(`get_current_user_id` — 현 `src/web/helpers.py`, V1S-2 로 `src/utils/user_context.py` 이동)을 쓰므로 세션 키를 바꾸는 방식은 v2 에서 그대로 유효하다. v2 `MenuDrawer.svelte:115`가 `/switch-user`를 `data-sveltekit-reload`로 링크한다.
- **view 밖 모듈**: 사용자 목록·uid 검증·전환(`session` 갱신 + `init_db`)을 서비스 함수로 분리(`src/services/` 신규 모듈). 라우트는 얇게 유지.
- **v2 노출**: JSON 엔드포인트(목록 GET, 전환 POST)와 v2 화면. **엔드포인트 경로와 화면 위치는 구현 단계에서 제안한다(V1-8 (c))** — 이 문서는 경로명·위치를 정하지 않는다. 쓰기(POST)는 2.1 Origin 관문(경로 무관 전역)·2.2 `parse_body`(uid 필드) 적용 대상이 된다(거부 응답 형식은 2.1 규칙대로 제안 경로에 따름). HTML 문자열 조립이 사라지므로 `<option value>` 이스케이프 결함(E-02 후반)은 이관으로 소멸한다(프론트 렌더는 텍스트 바인딩).
- **SRV-6 정합(V1-9 (b)·V1-12 (a)·SRV-10)**: production 차단(404)은 v2 이관과 **같은 변경**에서 v2 엔드포인트에 적용한다(D6 변경 없음, v1 라우트 선적용 없음). 응답 헤더는 이관 후 경로에 따라 `security-headers.md` `classify_surface`의 표면을 받는다 — 'v1' 표면은 V1-15 로 없다. production 판정 키는 기존 `APP_ENV`(`APP_ENV == "production"`, `app.py:156`·`auth_cf.py:24`)로 종결(SRV-10 — V1-12 의 키 확인 결과, 신규 키 없음). production에서 v2 진입점(MenuDrawer 링크)도 숨긴다. 개발 환경 경로 이탈 차단(`get_db_path` `resolve()`)은 이관과 무관하게 `db_setup.py`에 둔다.
- **순서**: ① 서비스 분리 + v2 엔드포인트(production 404, SRV-6 동시 적용) → ② v2 화면·MenuDrawer 링크 교체 → ③ v1 `/switch-user` 라우트 삭제(`app.py` -30줄).
- **열린 항목**: 엔드포인트 경로·v2 화면 위치는 구현 단계 제안 대상(V1-8 (c), 위치는 V1-5 MenuDrawer 별도 BACKLOG와 연결).
- **V1-10 확정 위치(V1S-2·V1S-3·V1S-5, V1-16)**: 신규 `request_guard.py`는 `src/web/`(V1-16). 신규 사용자 전환 서비스·라우트는 `get_current_user_id`를 `src.utils.user_context`에서, `src/mcp_remote/http.py`는 `request_guard.same_origin`을 import 한다. `app.py`의 `mcp_remote_bp` 등록 import 와 테스트 patch 문자열(`tests/test_mcp_http_routes.py`의 `src.web.views_mcp_remote` → `src.mcp_remote.http`, `src.web.helpers.get_current_user_id` → `src.utils.user_context.get_current_user_id`)은 이관 커밋에서 함께 바뀐다(shim 없음). 순서: 이관(`bundles/v1-sunset-prep.md` §4 2·3단계)이 이 문서 2.5 ①보다 먼저. 면제 목록(`/mcp`)·Origin 판정은 URL 경로 기준이라 영향이 없다.

### 2.6 uid 허용 규칙 (SRV-13 (a))
- **현 구조(코드 사실, 2026-10-12)**: `user_id`는 CF Access 이메일 헤더 원문이 그대로 세션에 들어가고(`auth_cf.py:72-80` — 세션에 값이 있으면 재검사 없이 통과(:73), 없으면 `session[_SESSION_KEY] = email`(:79). 서비스 토큰 경로도 `svc_user`(`config.garmin.email`, 기본 `"service"`)를 그대로 기록(:96)), `get_db_path`가 그 값을 `data/users/<uid>/` 경로 조립에 쓰며 `create=True`면 `mkdir`한다(`db_setup.py:39-49`). 어느 단계에도 uid 형식 검증이 없다. 개발 기본값은 `DEV_USER_ID` 또는 `"default"`.
- **규칙**: 이메일 호환 허용 목록 정규식(예 `^[A-Za-z0-9._%+@-]{1,254}$`)에 맞고, 다음을 거부한다 — 값 `.`·`..`, 경로 구분자(`/`·`\`), 선행 `.`. 기존 형식(CF 이메일, `default`)은 그대로 통과한다.
- **위치**: 검증 함수(예 `validate_uid(uid) -> str`, 실패 시 `ValueError`)는 V1S-2 로 `project_root`·`get_current_user_id`·`db_path`가 옮겨 가는 `src/utils/user_context.py`에 둔다(uid 해석과 같은 모듈 — Flask 무의존 순수 함수). `src/web/helpers.py`에는 두지 않는다.
- **적용 대상(모든 uid 입력 경로)**: ① 사용자 전환 v2 이관 엔드포인트(2.5, `parse_body`의 uid 필드 → 실패 시 400 `INVALID_PARAM`) ② 2.5 사용자 전환 서비스 ③ `auth_cf._identify_user`의 CF 이메일 → 세션 기록 **전**(V1-20) ③-1 세션에 **이미 저장된** `user_id`(규칙 도입 전 세션 우회 방지 — :73 조기 통과 전에 같은 규칙으로 검증, V1-20) ③-2 서비스 토큰 경로의 `svc_user`(같은 규칙, V1-20) ④ `DEV_USER_ID` 폴백 ⑤ 최종 관문 `db_setup.get_db_path`(`validate_uid` + `resolve()`가 `data/users` 하위인지 — 이중 방어). `db_setup`→`user_context` import 는 순환을 만들지 않는다(`user_context.db_path`의 `db_setup` import 는 지연 import 유지, 구현 시 확인).
- 거부 시 응답·동작: 사용자 전환 API 경로(①)는 400 봉투. **CF 이메일·세션 저장값·`svc_user`가 규칙 위반이면 `403` + 보안 로그**(V1-20 (a)): 세션에 기록하지 않고(③), 로그에는 이메일을 마스킹해 남긴다(예: 로컬 부분 앞 1자 + `***@` + 도메인, 원문 미기록). default 사용자로 폴백하지 않는다. `get_db_path`는 `ValueError`를 던지고, 호출 경로는 이를 **처리해 HTML 500 으로 새지 않게 한다**(V1-20 — 403 판정이 앞에서 먼저 걸리므로 남는 경로는 이중 방어용).

## 3. 변경 파일 표
| 파일 | 신규/수정 | 내용 | 예상 줄 |
|---|---|---|---|
| `src/web/request_guard.py` | 신규 | `same_origin`, 허용·면제 목록, `ENVELOPE_PATH_PREFIXES`(NEW-40), observe/enforce 모드, `init_request_guard(app)` | ~95 |
| `src/api/validation.py` | 신규 | Field 생성자(`int_list_field` 포함, NEW-40), `parse_body`(415/400), `parse_args` | ~165 |
| `src/services/input_limits.py` | 신규 | D4 범위·열거 상수(에피소드 상수는 `adjustment-new-signals.md` §2.8) | ~30 |
| `src/api/__init__.py` | 수정 | `register_envelope_handlers(bp)`(errorhandler 2개, `api_bp`·`context_bp` 공용 — NEW-40). `warnings`는 기존 `api_ok` `meta` 인자 사용(SRV-11, 변경 없음) | +22 |
| `src/web/app.py` | 수정 | guard 등록, 쿠키 설정(`SESSION_COOKIE_SECURE` = `APP_ENV == "production"`, SRV-10), v1 `/switch-user` 라우트 삭제(2.5 ③) | +5/-30 (이미 1161줄, 늘리지 않음) |
| `src/utils/user_context.py` | 수정 | `validate_uid`(2.6, SRV-13) — V1S-2 3함수 이동과 같은 모듈 | +12 |
| `src/web/auth_cf.py` | 수정 | CF 이메일·`svc_user`·`DEV_USER_ID` → 세션 기록 전 `validate_uid`, 세션 저장값 재검증, 위반 시 403 + 마스킹 보안 로그(2.6, V1-20) | +14 |
| `src/services/`(사용자 전환 신규 모듈) | 신규 | 사용자 목록, uid 검증(`validate_uid` 재사용), 전환(session + `init_db`) — 2.5 | ~40 |
| `src/api/`(사용자 전환 라우트) | 신규/수정 | 목록 GET·전환 POST, production 404(D6, 이관과 같은 변경 — V1-9). 경로는 구현 단계 제안(V1-8) | ~30 |
| `frontend/src/lib/components/MenuDrawer.svelte` 외 v2 화면 | 수정 | `/switch-user` 링크 → v2 화면(위치는 구현 단계 제안, V1-8), production 숨김 | 범위(product 영역 포함) |
| `src/mcp_remote/http.py`(현 `src/web/views_mcp_remote.py`, V1S-3) | 수정 | `_origin_ok` → `request_guard.same_origin` | -3/+2 |
| `src/db_setup.py` | 수정 | `get_db_path` uid 허용 규칙(`validate_uid`) + 경로 이탈 거부(ValueError) | +8 |
| `src/api/routes_today.py` | 수정 | 체크인 스키마 | +12 |
| `src/api/routes_plan.py` | 수정 | create/templates 스키마, weeks 경고 반환, `_reported_km` 이관 | +20/-15 |
| `src/api/routes_coach.py` | 수정 | `_message_input` 스키마화 | ±10 |
| `src/services/today_service.py`, `plan_template_service.py` | 수정 | `input_limits` 참조, weeks 보정 결과 반환 | +12 |
| `tests/test_request_guard.py` | 신규 | 동일/위조/누락 Origin, Referer 대체, 둘 다 없음 거부, observe 통과+로그, 면제 경로(`/api/context-episodes` 미포함 단언), 봉투 경로 403 형식(`/api/context-episodes` 포함), 쿠키 속성(`APP_ENV`별 `Secure`) | ~150 |
| `tests/test_api_validation.py` | 신규 | Field별 경계값(`int_list_field` 포함), 비JSON 415, 깨진 JSON 400, details 형태 | ~160 |
| `tests/test_api_input_contracts.py` | 신규 | T-15·P-04·P-05·C-02 재현 케이스 → 400 JSON, weeks 보정 경고(`meta.warnings`), errorhandler → JSON 500 | ~130 |
| `tests/test_switch_user.py` | 신규 | 서비스·v2 엔드포인트: production 404(`APP_ENV`), uid 규칙(`.`·`..`·`/`·`\`·선행 `.`·빈 값·255자·허용 목록 밖 문자 거부, 이메일·`default` 통과), 전환 후 세션 user_id, Origin 관문 적용 | ~70 |
| `tests/test_user_context.py`(기존 파일) | 수정 | `validate_uid` 경계값, `get_db_path` 거부 | +30 |
| `tests/test_auth_cf.py`(기존 파일) | 수정 | V1-20: 규칙 위반 CF 이메일 → 403·세션 미기록·로그에 원문 이메일 없음(마스킹), 규칙 위반 값이 이미 든 세션 → 403, 규칙 위반 `svc_user` → 403, 정상 이메일·`default` 통과, `get_db_path` `ValueError`가 HTML 500 으로 나가지 않음 | ~60 |
| `frontend/src/lib/api/*` | 수정 가능 | `details` 필드 오류·`meta.warnings` 표시(UI 범위는 product 영역) | 범위 밖 |

합계: 신규 약 880줄(테스트 540 포함, 2.5 이관으로 `views_switch_user.py` ~45줄 대신 서비스·라우트 ~70줄), 수정 약 130줄(프론트 제외). `src/api/routes_context.py`(NEW-40)는 `adjustment-new-signals.md` 변경 파일 표 소관.

## 4. 적용 순서·검증
1. **errorhandler (2.3)** — 가장 안전, 단독 배포 가능. 검증: C-02·`distance_km:"abc"` 재현 시 JSON 500/400, `pytest tests/test_api_*.py` 전체 통과.
2. **input_limits + validation.py + 4개 라우트 (2.2/2.4)** — 검증: 재현 값(fatigue 0·11·5.5·"x", pain "bogus", weeks 0/-3/500, race_date "garbage"·2020-01-01·오늘+6년, 99:99:99, distance_km 0·251, note 501자) 전부 400 + `details`, text/plain 본문 415. race_date 오늘은 통과. 가능 주수 초과 weeks는 201 + `meta.warnings`. 브라우저(사본 DB): 오늘 체크인 저장, `/v2/coach/plan/new` 정상 생성·과거 날짜 오류 표시.
3. **Origin 관문 + 쿠키 (2.1), observe 모드 2주(SEC-10)** — 배포 후 2주 동안 거부 대상 로그를 관찰한다. 검증: observe에서 위조 Origin 요청이 통과하며 로그가 남는지, `curl -i /v2/today`의 `Set-Cookie`에 `SameSite=Lax; HttpOnly`(`APP_ENV=production`이면 `Secure` 포함, SRV-10).
4. **enforce 전환(SEC-10)** — 2주 관찰 기간의 거부 대상 로그가 0건이면 `ORIGIN_GUARD_MODE=enforce`. 검증: `curl -X POST -H 'Origin: http://evil.example'` → 403(`/api/v1/*`·`/api/context-episodes`는 `FORBIDDEN_ORIGIN` 봉투), Origin·Referer 없는 POST → 403, 같은 출처 → 정상, `/mcp`·`/api/garmin/local-sync`·`/api/v1/csp-report` 면제 확인. 브라우저: v2 전 화면 쓰기 동작(체크인·코치·플랜·데이터 설정·가져오기 업로드·캘린더 피드 삭제·컨텍스트 에피소드 저장/삭제) 1회씩.
5. **사용자 전환 v2 이관 / uid 규칙 / get_db_path (2.5·2.6, V1-3·SRV-13)** — 구현 전 운영 실사용 여부 확인(D6). production 판정 키는 `APP_ENV`(SRV-10). 선행: `helpers` 3함수·`views_mcp_remote` 이관(`bundles/v1-sunset-prep.md` §4 2·3단계 — `validate_uid`가 `src/utils/user_context.py`에 들어감). 2.5 순서 ①→②→③(SRV-6 차단은 ①에서 v2 엔드포인트와 함께, V1-9). 검증: `APP_ENV=production`에서 v2 사용자 전환 엔드포인트 404·링크 숨김, 개발 환경에서 규칙 위반 uid(2.6) 400·`get_db_path` `ValueError`·디렉터리 미생성, 규칙 위반 CF 이메일 헤더·세션 저장값·`svc_user` → 403 + 마스킹 로그(V1-20), 기존 사용자(이메일·`default`) 전환 후 v2 화면이 해당 사용자 DB를 읽음, ③ 후 `/switch-user` 404.
6. 완료 체크리스트: `pytest tests/`, `scripts/check_docs.py`, `decisions.md`에 **ADR-048**("쓰기 요청은 Origin 관문 + 경계 스키마", ADR-1) 기록(D9).

### 호환성
- **깨지는 동작**: 범위 밖 값 400, 비JSON 본문 415, Origin 위조와 Origin·Referer 없는 쓰기 요청 403(enforce 이후). 기존 테스트 중 Origin 없이 POST하는 `test_client` 호출은 헤더 추가가 필요하다(공통 fixture 기본 헤더로 처리).
- **weeks**: 범위(1~52) 안의 보정 동작은 유지되고 응답 `meta`에 `warnings`가 추가된다(하위 호환, SRV-11).
- **uid(SRV-13)**: 이메일·`default` 형식 기존 사용자는 그대로 통과한다. 규칙 밖 문자를 가진 기존 `data/users/` 디렉터리가 있으면 거부된다 — 구현 전 운영 디렉터리 목록으로 확인.
- **외부 클라이언트**: `/api/garmin/local-sync`는 면제. CF 서비스 토큰으로 Origin 없이 쓰기 호출하는 스크립트가 있으면 enforce 후 거부된다 — observe 기간 로그로 확인.
- **사용자 전환(V1-3)**: v2 로 이관 후 v1 `/switch-user` 제거(2.5). v2 `MenuDrawer.svelte` 링크는 v2 화면으로 교체하고 production에서 숨긴다. 그 밖의 레거시 v1 화면·라우트는 일몰 예정(V1-1·V1-2 — 일몰은 UI·라우트 일몰).

## 5. 대안 비교
| | A안(채택): 전역 Origin 관문 + 라우트 경계 경량 스키마 | B안: CSRF 토큰(Flask-WTF 등) + pydantic 모델 |
|---|---|---|
| CSRF | 헤더 검사만, 프론트 변경 없음. Origin·Referer 누락은 거부(D1) | 토큰 이중 제출로 가장 강함. 모든 v2 fetch에 토큰 주입 필요, 세션 의존 증가 |
| 입력 검증 | 의존성 0, 150줄 내, 기존 `(clean, err)` 규약과 일치 | 표현력 높음. 신규 의존성, 오류 포맷을 엔벨로프로 다시 매핑해야 함 |
| 비용 | 소 (약 2~3 작업 단위) | 중~대 (프론트 전 쓰기 호출 수정) |
- A 채택 근거: CF Access가 앞단 인증을 하고, 같은 출처 SPA + JSON API 구조라 Origin 검사 + SameSite 쿠키로 대부분의 CSRF 경로를 막을 수 있으며, ADR-034 선례와 일관된다. B는 v1 제거 이후 위협 모델이 바뀌면 재검토.

## 6. 결정됨 (2026-10-11, `decisions-table.md` SRV-1~13, SEC-10, ADR-1, NEW-40)
- **D1 (SRV-1)** Origin·Referer 둘 다 없는 쓰기 요청 거부 — 브라우저 외 경로를 열어 두지 않는 가장 안전한 선택.
- **D2 (SRV-2)** `public_base_url()` + 개발용 허용 목록(localhost:5173 등) — 프록시 Host 헤더를 신뢰하지 않기 위해.
- **D3 (SRV-3)** SameSite `Lax` — 외부 링크 진입 시 CF 재식별 비용을 피하면서 교차 사이트 POST 차단.
- **D4 (SRV-4)** 2.2 상수 표의 제안 값으로 진행, 운영 데이터로 확인 후 조정.
- **D5 (SRV-5)** 비JSON 본문 415 Unsupported Media Type — 원인이 본문 형식임을 코드로 구분.
- **D6 (SRV-6)** 운영에서 `/switch-user` 차단 — 인가 문제를 입력 검증보다 앞서 제거. 운영 실사용 여부는 구현 전 확인. V1-3 (b)에 따라 차단은 v2 로 이관된 사용자 전환 엔드포인트에 적용되며, V1-9 (b)에 따라 이관과 같은 변경에서 적용한다(v1 라우트 선적용 없음, 2.5).
- **D7 (SRV-7)** `min(weeks, 가능 주수)` 보정 유지 + 보정 경고 응답 반환 — 사용성 유지, 조용한 보정만 제거.
- **D8 (SRV-8·SEC-10)** 관찰 모드(로그만) 선행 후 enforce 전환 — 정상 클라이언트 오차단 방지. 관찰 2주, 위반 0건이면 enforce(SEC-10 (b)).
- **D9 (SRV-9·ADR-1)** 새 ADR로 기록 — 번호 ADR-048 확정(SRV 048, SEC 049, FRS 050, NRA 051).
- **D10 (SRV-10)** `SESSION_COOKIE_SECURE`는 `APP_ENV`로 판정(V1-12 의 production 판정 키도 `APP_ENV`로 종결).
- **D11 (SRV-11)** `warnings`는 `api_ok`의 `meta` 안.
- **D12 (SRV-12)** `/api/v1/csp-report`는 415 검사 면제(본문 크기·형식 제한은 별도).
- **D13 (SRV-13)** uid 는 이메일 호환 허용 목록 + `.`·`..`·경로 구분자·선행 `.` 거부(2.6).
- **D14 (V1-20, 2026-10-12)** 규칙 위반 CF 이메일은 403 + 보안 로그(이메일 마스킹). 세션 기록 전 검증, 세션에 이미 저장된 값과 `svc_user`도 같은 규칙으로 검증, `get_db_path` `ValueError` 처리(2.6).
- **NEW-40** `/api/context-episodes`는 현 경로 유지 + 같은 봉투, Origin 관문·입력 제한을 예외 없이 적용(2.1 봉투 경로 상수, 2.3 공용 핸들러).

## 7. 범위 밖 메모
- E-01 보안 헤더(CSP·X-Frame-Options 등) — `security-headers.md`.
- `src/web/app.py` 1161줄 — 300줄 규칙 위반, 별도 분리 작업(이번엔 switch-user 라우트만 제거, 2.5).
- 프론트에서 서버 `details`·`warnings`를 보여 주는 UX — product-architect 영역.

## 8. 변경 이력
- 초안 작성.
- 2026-10-11 설계서 동기화: D1~D9 결정(SRV-1~9) 반영 — 관찰→enforce 롤아웃, 면제 목록에 `/api/v1/csp-report` 추가, `input_limits` 상수 모듈, switch-user 운영 차단·분리, weeks 경고 반환.
- 2026-10-11 4차 동기화(V1-1): 레거시 v1 고려 제거 — 관문 대상 'v1 폼' 표기·4단계 'v1 폼 1회' 검증·호환성 v1 폼 25곳·v1 제거 시 정리 서술 삭제, 대안 B 'v1 폼' 언급 삭제.
- 2026-10-11 5차 동기화(V1-1 정정·V1-2·V1-3): 일몰 = UI·라우트 일몰. E-02를 v2 이관 설계(2.5)로 재작성 — `views_switch_user.py` 분리 대신 서비스 모듈 + v2 엔드포인트, v1 라우트 삭제, SRV-6 차단을 v2 엔드포인트에 적용.
- 2026-10-11 6차 동기화(V1-8·V1-9·V1-10): 2.5 엔드포인트 경로·화면 위치 단정을 '구현 단계 제안'(V1-8 c)으로 완화, SRV-6은 v2 이관과 같은 변경에서 적용(V1-9 b — 이관 전 v1 선적용 서술 제거), `helpers.py`·`views_mcp_remote.py` view 밖 이관(V1-10)에 따른 경로·import·테스트 영향 명시.
- 2026-10-11 8차 동기화(V1-15·V1-16): `request_guard.py` 위치 `src/web/` 확정('src/web = 앱 셸 전용', 2.1·2.5·§10 열린 항목 해소), 사용자 전환 엔드포인트의 응답 표면에 'v1' 분기 제거(V1-15) 반영, SRV-6 = v2 이관과 같은 변경 재확인.
- 2026-10-11 7차 동기화(V1S-2·V1S-3·V1S-5·V1-12·V1-13): '새 위치 미정'을 확정 위치(`src/utils/user_context.py`·`src/mcp_remote/http.py`, shim 없음)로 교체, production 판정 = 기존 설정 키 재사용(키 확인은 구현 첫 단계), §10 열린 항목 정리.
- 2026-10-12 9차 동기화(SRV-10~13·SEC-10·ADR-1·NEW-40): `SESSION_COOKIE_SECURE`·production 판정 = `APP_ENV`(2.1·2.5·4절), `warnings` → `meta.warnings`(2.2·3절·호환성), csp-report 415 면제(2.2), uid 허용 규칙 2.6 신설(현 구조 코드 사실·`validate_uid` 위치 `src/utils/user_context.py`·적용 경로), observe 2주·위반 0건 enforce(2.1·4절·D8), ADR-048 확정, `/api/context-episodes` 봉투 경로 상수·공용 오류 핸들러·`int_list_field`(2.1·2.2·2.3·2.4·3절, `adjustment-new-signals.md` §2.8 정합), 9절 해소 정리.
- 2026-10-12 10차 동기화(V1-20, 설계 단계 마지막): 2.6 적용 대상에 세션 저장값·`svc_user` 추가, 규칙 위반 CF 이메일 403 + 마스킹 보안 로그·`get_db_path` `ValueError` 처리(2.6·3절·4절 5·D14), 코드 사실 줄 번호 `auth_cf.py:72-80` 정정, 9절 열린 질문 해소, 11절 S0 점검 목록.

## 9. 동기화 중 발견한 충돌/확인 필요
- 해소(ADR-1): ADR 번호 — 이 문서 ADR-048, `security-headers.md` ADR-049.
- 해소(SRV-10): `SESSION_COOKIE_SECURE`는 `APP_ENV`로 판정. `HttpOnly`는 초안 설계값 유지(별도 결정 기록 없음, 변경 없음).
- 해소(SRV-13): uid 허용 규칙(2.6).
- 해소(SRV-11): `warnings`는 `api_ok` `meta` 안.
- 해소(SRV-12): `/api/v1/csp-report` 415 면제(2.2).
- 해소(NEW-40): `/api/context-episodes` 봉투·관문·입력 제한 적용(2.1·2.3·2.4).
- D6 production 차단 시 v2 사용자 전환 진입점(현 `MenuDrawer.svelte` 링크) 숨김이 프론트 범위로 남는다(2.5 ②).
- 해소(V1-20): 규칙 위반 CF 이메일은 403 + 마스킹 보안 로그, 세션 저장값·`svc_user`도 같은 규칙, `get_db_path` `ValueError` 처리(2.6).
- (구현 확인) SEC-10 의 '위반 0건' 판정에서 observe 로그 중 정상 클라이언트가 아닌 요청(봇·스캐너)을 어떻게 제외할지는 결정에 없다.

## 10. 동기화 중 발견한 모호점
- (V1-1, 5차에서 해소) E-02 처리 — V1-3 (b) 결정으로 v2 이관 후 v1 제거(2.5).
- (V1-3 → 6차 동기화) 2.5의 v2 엔드포인트 경로·v2 화면 위치는 구현 단계에서 제안(V1-8 (c), 위치는 V1-5 MenuDrawer BACKLOG와 연결). 이관 전 v1 라우트 선적용 여부는 V1-9 (b)로 해소 — v2 이관과 같은 변경에서 SRV-6 적용. 해소(SRV-10): production 판정 키는 `APP_ENV`(V1-12 종결).
- (V1-10, 7차에서 해소) 4파일 새 위치는 V1S-1~3 으로 확정(2.5 확정 위치 줄). (8차, V1-16 으로 해소) 신규 `request_guard.py`는 `src/web/`에 둔다 — 'src/web = 앱 셸 전용' 정의에 포함되어 view 밖 이관 원칙과 충돌하지 않는다.
- (V1-1) 2.1 거부 응답 '그 외 → text 403'과 5절 'B는 v1 제거 이후 위협 모델이 바뀌면 재검토'는 v1 호환 서술이 아니라고 보고 유지했다.

## 11. S0 점검 목록 (10차 — 구현 착수 때 한 줄씩 확인, 새 결정 아님)
- V1-20: 세션 저장값이 규칙 위반일 때 403 과 함께 그 세션 키를 지울지(다음 요청에서 CF 헤더로 재식별되게 할지) 구현 시 확인.
- V1-20: 403 응답 형태 — `/api/v1/*`·`/api/context-episodes`(봉투 경로, 2.1 `ENVELOPE_PATH_PREFIXES`)는 JSON 봉투, 그 밖은 text 403 으로 2.1 거부 응답 규칙을 그대로 따를지 확인.
- V1-20: 마스킹 형식(로컬 부분 앞 1자 + 도메인 유지 여부)과 보안 로그 로거 이름·레벨을 기존 `[auth_cf]` 로그와 맞춰 확정.
- V1-20: `get_db_path` `ValueError`의 처리 위치(2.3 공용 오류 핸들러에서 잡을지, `user_context.db_path` 호출부에서 잡을지)와 응답 코드(400/403) 확인.
