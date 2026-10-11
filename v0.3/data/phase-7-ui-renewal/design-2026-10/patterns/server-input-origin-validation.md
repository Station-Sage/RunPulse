# 설계: 쓰기 API 서버 입력 검증·Origin 검증

- 대상 ID: T-15, P-04, P-05, D-22, E-02, C-02 (참고 동일 원인: P-17, C-18)
- 상태: 설계 확정 (구현 전). D1~D9 결정 완료(2026-10-11, `decisions-table.md` SRV-1~9). 2026-10-11 설계서 동기화. 2026-10-11 4차 동기화(V1-1).
- 관련 ADR: ADR-034 (원격 MCP의 Origin 불일치 거부 — `views_mcp_remote._origin_ok`가 이미 있는 선례), 신규 ADR-048 후보(D9)

## 1. 근본 원인

**RC-1. 서버에 "요청 경계 계약"이 없다.** `/api/v1` 쓰기 라우트 38개는 모두 `request.get_json(silent=True) or {}`로 본문을 받는다.
- JSON이 아닌 본문(text/plain, 깨진 JSON)도 조용히 `{}`가 되어 선택 필드만 있는 라우트는 그대로 실행된다(D-22: 캘린더 피드 생성 201·삭제 204).
- 필드 타입·범위 검증은 라우트마다 따로 하거나(`_reported_km`, `_message_input`, `validate_patch` 3종) 아예 없다. 체크인(T-15)은 `save_checkin`에 원시값을 그대로 넘기고, 플랜 생성(P-05)은 `int(weeks)`·`float(distance_km)` 캐스팅만 하며, 서비스가 `max(1, min(weeks, avail))`로 조용히 보정한다. 템플릿 비교 GET(P-04)도 과거 날짜·범위 밖 목표 시간을 검증하지 않는다.
- 예상 못 한 타입이면 예외가 그대로 올라가는데 `api_bp`에 오류 처리기가 없어 HTML 500이 나간다(C-02 `initial_message: 123` → `.strip()` AttributeError, P-05 `distance_km:"abc"`). 엔벨로프 계약 `{error:{code,message}}` 위반.

**RC-2. 상태 변경 요청의 출처를 확인하는 앱 전역 관문이 없다.** 신원은 CF Access 헤더 → Flask 세션 쿠키로만 잡히고(`auth_cf._identify_user`), 쓰기 요청이 같은 출처에서 왔는지 아무도 보지 않는다. 세션 쿠키에 `SameSite`/`Secure`를 명시하지 않았다(`app.py`에 `SESSION_COOKIE_*` 설정 없음). Origin 검사는 `/mcp`에만 있다. v1 `/switch-user`(E-02)는 폼 입력 uid를 검증 없이 `init_db(uid)` → `get_db_path`가 `data/users/<uid>`를 `mkdir`하므로 `../` 등 경로 이탈 입력도 디렉터리를 만들 수 있고, `<option value>`가 이스케이프되지 않는다.

## 2. 설계안 (A안 확정)

### 2.1 Origin 관문 — `src/web/request_guard.py` (신규)
- 앱 전역 `before_request` 1개. 대상: 메서드가 POST/PUT/PATCH/DELETE인 모든 요청.
- 판정(D2): 허용 출처 = `public_base_url()`의 출처 + 개발용 허용 목록 상수 `DEV_ALLOWED_ORIGINS`(`http://localhost:5173` 등, development 설정에서만 적용). 프록시 뒤 `request.host`(Host 헤더)는 비교 기준으로 쓰지 않는다. `Origin`이 있으면 그것으로, 없으면 `Referer`의 출처로 판정한다.
- Origin·Referer 둘 다 없는 쓰기 요청은 **거부**한다(D1).
- 모드(D8): `ORIGIN_GUARD_MODE ∈ {observe, enforce}` 설정값. `observe`는 거부 대상 요청을 로그(path·method·Origin·Referer)만 남기고 통과, `enforce`는 거부. 초기 배포는 `observe`.
- 면제 목록(명시적 상수 `EXEMPT_PATHS`): `/mcp`(자체 Origin·Bearer 검사, ADR-034), `/api/garmin/local-sync`(sync_key 2차 인증, 로컬 스크립트), `/feeds/cal/`(GET 전용 공개 피드), `/api/v1/csp-report`(브라우저 CSP 보고, 로그 전용 — `security-headers.md` D6).
- 거부 응답: `/api/v1/*` → `api_error("FORBIDDEN_ORIGIN", ..., 403)`, 그 외 → text 403.
- `_origin_ok` 로직은 이 모듈의 `same_origin(request) -> bool`로 옮기고 `views_mcp_remote`가 재사용한다(중복 제거).
- 세션 쿠키(D3): `SESSION_COOKIE_SAMESITE="Lax"`, `SESSION_COOKIE_HTTPONLY=True`, `SESSION_COOKIE_SECURE`(production만 — 결정 범위 밖, 9절 참조)를 `create_app`에서 명시.

### 2.2 요청 스키마 계층 — `src/api/validation.py` (신규)
- 라우트 경계에서 쓰는 작은 선언형 검증기. 외부 의존성(pydantic 등) 없이 순수 함수로 만든다.
  ```python
  Field = int_field(lo, hi) | float_field(lo, hi, lo_exclusive=False) | enum_field(values)
        | date_field(min_date=None, max_date=None) | str_field(max_len, required)
  def parse_body(schema: dict[str, Field], *, require_json: bool = True)
      -> tuple[dict, ApiErrorResponse | None]
  def parse_args(schema) -> tuple[dict, ApiErrorResponse | None]   # GET 쿼리(P-04 templates)
  ```
- 규칙: 형식이 틀리거나 범위 밖이면 **조용히 보정하지 않고** `400 INVALID_PARAM` + `details={field: reason}`로 거부한다. 타입 강제 변환은 문자열 숫자("5")처럼 손실 없는 경우만 허용, `5.5`→int, `True`→int는 거부.
- `require_json=True`일 때 `request.is_json`이 아니면 `415 UNSUPPORTED_MEDIA_TYPE`, JSON 파싱 실패면 `400 INVALID_PARAM`(D5). 본문 없는 DELETE·multipart(`/data/import/preview`)는 `require_json=False`.
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
- weeks 보정(D7): `WEEKS_RANGE` 밖은 400. 범위 안이지만 대회일까지 가능 주수(`avail`)를 넘으면 `min(weeks, avail)`로 보정을 유지하고, 성공 응답에 경고(`warnings: [{code:"WEEKS_ADJUSTED", requested, applied}]`)를 함께 반환한다. 서비스는 보정 사실을 반환값으로 알린다(조용한 보정 제거).
- 기존 `_reported_km`, `_message_input`, `validate_patch`/`validate_auto_patch`/`validate_changes`는 1차 적용 범위 밖이지만, 형태를 맞춰 점진 이관할 수 있게 `(clean, err)` 반환 규약을 그대로 따른다.

### 2.3 엔벨로프 보장 — `src/api/__init__.py` (수정)
- `@api_bp.errorhandler(HTTPException)` → 같은 상태코드의 `api_error`, `@api_bp.errorhandler(Exception)` → 로그 + `api_error("INTERNAL", ..., 500)`. 입력 검증이 빠진 라우트가 남아도 HTML 500은 나가지 않는다(안전망이지 검증 대체가 아님).

### 2.4 1차 적용 라우트
| 증상 | 라우트 | 스키마 요지 (값은 2.2 상수) |
|---|---|---|
| T-15 | POST `/today/checkin` | fatigue `FATIGUE_RANGE`, pain enum `PAIN_LEVELS`(프론트 `PainLevel`), note ≤`CHECKIN_NOTE_MAX` |
| P-05 | POST `/coach/plan` | distance_km `DISTANCE_KM`, weeks `WEEKS_RANGE`(가능 주수 초과는 보정+경고), race_date `RACE_DATE_WINDOW`, target_time_sec `TARGET_TIME_SEC`, name str |
| P-04 | GET `/coach/plan/templates` | 위와 같은 race_date·target_time_sec·distance_km 규칙(`parse_args`) |
| C-02 | POST `/coach/threads`, `/threads/<id>/messages` | initial_message/text ≤`COACH_MESSAGE_MAX`, chip_id enum(`CHIP_TEXT`) — `_message_input`을 스키마 위로 재작성 |
| E-02 | v1 POST/GET `/switch-user` | production에서 라우트 차단(404, D6). 개발 환경은 `get_db_path` 경로 이탈 차단(`resolve()`가 `data/users` 하위인지) + option 값 `html.escape` |

## 3. 변경 파일 표
| 파일 | 신규/수정 | 내용 | 예상 줄 |
|---|---|---|---|
| `src/web/request_guard.py` | 신규 | `same_origin`, 허용·면제 목록, observe/enforce 모드, `init_request_guard(app)` | ~90 |
| `src/api/validation.py` | 신규 | Field 생성자, `parse_body`(415/400), `parse_args` | ~150 |
| `src/services/input_limits.py` | 신규 | D4 범위·열거 상수 | ~30 |
| `src/api/__init__.py` | 수정 | errorhandler 2개 | +20 |
| `src/web/app.py` | 수정 | guard 등록, 쿠키 설정, `/switch-user`를 `views_switch_user.py`로 분리 | +5/-30 (이미 1161줄, 늘리지 않음) |
| `src/web/views_switch_user.py` | 신규 | production 차단 분기, 개발용 전환 + escape | ~45 |
| `src/web/views_mcp_remote.py` | 수정 | `_origin_ok` → `request_guard.same_origin` | -3/+2 |
| `src/db_setup.py` | 수정 | `get_db_path` uid 경로 이탈 거부(ValueError) | +6 |
| `src/api/routes_today.py` | 수정 | 체크인 스키마 | +12 |
| `src/api/routes_plan.py` | 수정 | create/templates 스키마, weeks 경고 반환, `_reported_km` 이관 | +20/-15 |
| `src/api/routes_coach.py` | 수정 | `_message_input` 스키마화 | ±10 |
| `src/services/today_service.py`, `plan_template_service.py` | 수정 | `input_limits` 참조, weeks 보정 결과 반환 | +12 |
| `tests/test_request_guard.py` | 신규 | 동일/위조/누락 Origin, Referer 대체, 둘 다 없음 거부, observe 통과+로그, 면제 경로, 쿠키 속성 | ~140 |
| `tests/test_api_validation.py` | 신규 | Field별 경계값, 비JSON 415, 깨진 JSON 400, details 형태 | ~150 |
| `tests/test_api_input_contracts.py` | 신규 | T-15·P-04·P-05·C-02 재현 케이스 → 400 JSON, weeks 보정 경고, errorhandler → JSON 500 | ~130 |
| `tests/test_switch_user.py` | 신규 | production 차단, `../`·빈 값·특수문자 uid 거부, escape | ~60 |
| `frontend/src/lib/api/*` | 수정 가능 | `details` 필드 오류·`warnings` 표시(UI 범위는 product 영역) | 범위 밖 |

합계: 신규 약 795줄(테스트 480 포함), 수정 약 110줄.

## 4. 적용 순서·검증
1. **errorhandler (2.3)** — 가장 안전, 단독 배포 가능. 검증: C-02·`distance_km:"abc"` 재현 시 JSON 500/400, `pytest tests/test_api_*.py` 전체 통과.
2. **input_limits + validation.py + 4개 라우트 (2.2/2.4)** — 검증: 재현 값(fatigue 0·11·5.5·"x", pain "bogus", weeks 0/-3/500, race_date "garbage"·2020-01-01·오늘+6년, 99:99:99, distance_km 0·251, note 501자) 전부 400 + `details`, text/plain 본문 415. race_date 오늘은 통과. 가능 주수 초과 weeks는 201 + `warnings`. 브라우저(사본 DB): 오늘 체크인 저장, `/v2/coach/plan/new` 정상 생성·과거 날짜 오류 표시.
3. **Origin 관문 + 쿠키 (2.1), observe 모드** — 배포 후 거부 대상 로그를 관찰한다(기간 미정, D8). 검증: observe에서 위조 Origin 요청이 통과하며 로그가 남는지, `curl -i /v2/today`의 `Set-Cookie`에 `SameSite=Lax; HttpOnly`.
4. **enforce 전환** — 관찰 로그에 정상 클라이언트 거부가 없을 때 `ORIGIN_GUARD_MODE=enforce`. 검증: `curl -X POST -H 'Origin: http://evil.example'` → 403, Origin·Referer 없는 POST → 403, 같은 출처 → 정상, `/mcp`·`/api/garmin/local-sync`·`/api/v1/csp-report` 면제 확인. 브라우저: v2 전 화면 쓰기 동작(체크인·코치·플랜·데이터 설정·가져오기 업로드·캘린더 피드 삭제) 1회씩.
5. **switch-user / get_db_path** — 구현 전 운영 실사용 여부 확인(D6). 검증: production 설정에서 `/switch-user` 404, 개발 환경에서 경로 이탈 uid 거부·기존 사용자 전환 정상.
6. 완료 체크리스트: `pytest tests/`, `scripts/check_docs.py`, `decisions.md`에 ADR-048 후보("쓰기 요청은 Origin 관문 + 경계 스키마") 기록(D9).

### 호환성
- **깨지는 동작**: 범위 밖 값 400, 비JSON 본문 415, Origin 위조와 Origin·Referer 없는 쓰기 요청 403(enforce 이후). 기존 테스트 중 Origin 없이 POST하는 `test_client` 호출은 헤더 추가가 필요하다(공통 fixture 기본 헤더로 처리).
- **weeks**: 범위(1~52) 안의 보정 동작은 유지되고 응답에 `warnings`가 추가된다(하위 호환).
- **외부 클라이언트**: `/api/garmin/local-sync`는 면제. CF 서비스 토큰으로 Origin 없이 쓰기 호출하는 스크립트가 있으면 enforce 후 거부된다 — observe 기간 로그로 확인.
- **switch-user 링크**: v2 `MenuDrawer.svelte`가 `/switch-user`를 링크한다(production 차단 시 링크 숨김 필요). 그 밖의 레거시 v1 화면은 일몰 예정(V1-1).

## 5. 대안 비교
| | A안(채택): 전역 Origin 관문 + 라우트 경계 경량 스키마 | B안: CSRF 토큰(Flask-WTF 등) + pydantic 모델 |
|---|---|---|
| CSRF | 헤더 검사만, 프론트 변경 없음. Origin·Referer 누락은 거부(D1) | 토큰 이중 제출로 가장 강함. 모든 v2 fetch에 토큰 주입 필요, 세션 의존 증가 |
| 입력 검증 | 의존성 0, 150줄 내, 기존 `(clean, err)` 규약과 일치 | 표현력 높음. 신규 의존성, 오류 포맷을 엔벨로프로 다시 매핑해야 함 |
| 비용 | 소 (약 2~3 작업 단위) | 중~대 (프론트 전 쓰기 호출 수정) |
- A 채택 근거: CF Access가 앞단 인증을 하고, 같은 출처 SPA + JSON API 구조라 Origin 검사 + SameSite 쿠키로 대부분의 CSRF 경로를 막을 수 있으며, ADR-034 선례와 일관된다. B는 v1 제거 이후 위협 모델이 바뀌면 재검토.

## 6. 결정됨 (2026-10-11, `decisions-table.md` SRV-1~9)
- **D1 (SRV-1)** Origin·Referer 둘 다 없는 쓰기 요청 거부 — 브라우저 외 경로를 열어 두지 않는 가장 안전한 선택.
- **D2 (SRV-2)** `public_base_url()` + 개발용 허용 목록(localhost:5173 등) — 프록시 Host 헤더를 신뢰하지 않기 위해.
- **D3 (SRV-3)** SameSite `Lax` — 외부 링크 진입 시 CF 재식별 비용을 피하면서 교차 사이트 POST 차단.
- **D4 (SRV-4)** 2.2 상수 표의 제안 값으로 진행, 운영 데이터로 확인 후 조정.
- **D5 (SRV-5)** 비JSON 본문 415 Unsupported Media Type — 원인이 본문 형식임을 코드로 구분.
- **D6 (SRV-6)** 운영에서 `/switch-user` 차단 — 인가 문제를 입력 검증보다 앞서 제거. 운영 실사용 여부는 구현 전 확인.
- **D7 (SRV-7)** `min(weeks, 가능 주수)` 보정 유지 + 보정 경고 응답 반환 — 사용성 유지, 조용한 보정만 제거.
- **D8 (SRV-8)** 관찰 모드(로그만) 선행 후 enforce 전환, 기간 미정 — 정상 클라이언트 오차단 방지.
- **D9 (SRV-9)** 새 ADR로 기록(ADR-048 후보).

## 7. 범위 밖 메모
- E-01 보안 헤더(CSP·X-Frame-Options 등) — `security-headers.md`.
- `src/web/app.py` 1161줄 — 300줄 규칙 위반, 별도 분리 작업(이번엔 switch-user만 분리).
- 프론트에서 서버 `details`·`warnings`를 보여 주는 UX — product-architect 영역.

## 8. 변경 이력
- 초안 작성.
- 2026-10-11 설계서 동기화: D1~D9 결정(SRV-1~9) 반영 — 관찰→enforce 롤아웃, 면제 목록에 `/api/v1/csp-report` 추가, `input_limits` 상수 모듈, switch-user 운영 차단·분리, weeks 경고 반환.
- 2026-10-11 4차 동기화(V1-1): 레거시 v1 고려 제거 — 관문 대상 'v1 폼' 표기·4단계 'v1 폼 1회' 검증·호환성 v1 폼 25곳·v1 제거 시 정리 서술 삭제, 대안 B 'v1 폼' 언급 삭제.

## 9. 동기화 중 발견한 충돌/확인 필요
- ADR 번호: 이 문서 D9와 `security-headers.md` 4절 마지막 단계(초안 9절 참조)가 모두 ADR-048을 후보로 쓴다. 번호 배정이 필요하다.
- D3 결정은 SameSite만 명시한다. `SESSION_COOKIE_SECURE`(production 한정)·`HttpOnly`는 초안 설계값을 유지했으며 별도 결정 기록이 없다.
- D6 결정은 운영 차단만 정했다. 개발 환경 uid 허용 문자 집합(정규식)은 미정이며, 이 문서는 경로 이탈 차단 + escape만 설계한다.
- D7 `warnings` 필드는 기존 성공 응답 엔벨로프 규약에 정의가 없다. 구현 전 엔벨로프 형식 확인이 필요하다.
- `/api/v1/csp-report`는 브라우저가 `application/csp-report`/`application/reports+json`으로 보내므로 D5(415)를 적용하면 안 된다(`require_json=False` 또는 전용 파서).
- D6 production 차단 시 v2 `MenuDrawer.svelte`의 `/switch-user` 링크 처리(숨김)가 프론트 범위로 남는다.

## 10. 동기화 중 발견한 모호점
- (V1-1) E-02 `/switch-user`는 v1 HTML 라우트지만 SRV-6(운영 차단) 결정 대상인 보안 결함이고 v2 `MenuDrawer`가 링크하므로, 2.4 행·`views_switch_user.py`·`test_switch_user.py`·`db_setup.py` 행·5단계를 유지했다. 일몰 전 노출 기간의 보안 조치로 남길지, V1-1에 따라 범위 밖으로 뺄지 확인 필요.
- (V1-1) 2.1 거부 응답 '그 외 → text 403'과 5절 'B는 v1 제거 이후 위협 모델이 바뀌면 재검토'는 v1 호환 서술이 아니라고 보고 유지했다.
