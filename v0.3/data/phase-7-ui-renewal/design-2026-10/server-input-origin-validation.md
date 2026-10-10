# 설계: 쓰기 API 서버 입력 검증·Origin 검증

- 대상 ID: T-15, P-04, P-05, D-22, E-02, C-02 (참고 동일 원인: P-17, C-18)
- 상태: 설계 초안 (구현 전, 사용자 결정 필요 항목 있음)
- 관련 ADR: ADR-034 (원격 MCP의 Origin 불일치 거부 — `views_mcp_remote._origin_ok`가 이미 있는 선례)

## 1. 근본 원인

**RC-1. 서버에 "요청 경계 계약"이 없다.** `/api/v1` 쓰기 라우트 38개는 모두 `request.get_json(silent=True) or {}`로 본문을 받는다.
- JSON이 아닌 본문(text/plain, 깨진 JSON)도 조용히 `{}`가 되어 선택 필드만 있는 라우트는 그대로 실행된다(D-22: 캘린더 피드 생성 201·삭제 204).
- 필드 타입·범위 검증은 라우트마다 따로 하거나(`_reported_km`, `_message_input`, `validate_patch` 3종) 아예 없다. 체크인(T-15)은 `save_checkin`에 원시값을 그대로 넘기고, 플랜 생성(P-05)은 `int(weeks)`·`float(distance_km)` 캐스팅만 하며, 서비스가 `max(1, min(weeks, avail))`로 조용히 보정한다. 템플릿 비교 GET(P-04)도 과거 날짜·범위 밖 목표 시간을 검증하지 않는다.
- 예상 못 한 타입이면 예외가 그대로 올라가는데 `api_bp`에 오류 처리기가 없어 HTML 500이 나간다(C-02 `initial_message: 123` → `.strip()` AttributeError, P-05 `distance_km:"abc"`). 엔벨로프 계약 `{error:{code,message}}` 위반.

**RC-2. 상태 변경 요청의 출처를 확인하는 앱 전역 관문이 없다.** 신원은 CF Access 헤더 → Flask 세션 쿠키로만 잡히고(`auth_cf._identify_user`), 쓰기 요청이 같은 출처에서 왔는지 아무도 보지 않는다. 세션 쿠키에 `SameSite`/`Secure`를 명시하지 않았다(`app.py`에 `SESSION_COOKIE_*` 설정 없음). Origin 검사는 `/mcp`에만 있다. v1 `/switch-user`(E-02)는 폼 입력 uid를 검증 없이 `init_db(uid)` → `get_db_path`가 `data/users/<uid>`를 `mkdir`하므로 `../` 등 경로 이탈 입력도 디렉터리를 만들 수 있고, `<option value>`가 이스케이프되지 않는다.

## 2. 설계안 (추천: A안)

### 2.1 Origin 관문 — `src/web/request_guard.py` (신규)
- 앱 전역 `before_request` 1개. 대상: 메서드가 POST/PUT/PATCH/DELETE인 모든 요청(v1 폼 + `/api/v1`).
- 판정: `Origin` 헤더가 있으면 `netloc == request.host` 또는 허용 목록(결정 필요 D2)에 속할 때만 통과. 없으면 `Referer`로 대체 판정, 둘 다 없을 때 처리는 결정 필요 D1.
- 면제 목록(명시적 상수): `/mcp`(자체 Origin·Bearer 검사, ADR-034), `/api/garmin/local-sync`(sync_key 2차 인증, 로컬 스크립트), `/feeds/cal/`(GET 전용 공개 피드).
- 거부 응답: `/api/v1/*` → `api_error("FORBIDDEN_ORIGIN", ..., 403)`, 그 외 → text 403. 거부 시 path·Origin 로그.
- `_origin_ok` 로직은 이 모듈의 `same_origin(request) -> bool`로 옮기고 `views_mcp_remote`가 재사용한다(중복 제거).
- 세션 쿠키: `SESSION_COOKIE_SAMESITE`, `SESSION_COOKIE_SECURE`(production만), `SESSION_COOKIE_HTTPONLY`를 `create_app`에서 명시(값은 결정 필요 D3).
- 프록시 뒤 `request.host`가 공개 호스트와 다를 수 있으므로 비교 기준(Host 헤더 vs `public_base_url()`)을 결정 필요 D2에서 함께 정한다.

### 2.2 요청 스키마 계층 — `src/api/validation.py` (신규)
- 라우트 경계에서 쓰는 작은 선언형 검증기. 외부 의존성(pydantic 등) 없이 순수 함수로 만든다.
  ```python
  Field = int_field(lo, hi) | float_field(lo, hi) | enum_field(values)
        | date_field(min_date=None, max_date=None) | str_field(max_len, required)
  def parse_body(schema: dict[str, Field], *, require_json: bool = True)
      -> tuple[dict, ApiErrorResponse | None]
  def parse_args(schema) -> tuple[dict, ApiErrorResponse | None]   # GET 쿼리(P-04 templates)
  ```
- 규칙: 형식이 틀리거나 범위 밖이면 **조용히 보정하지 않고** `400 INVALID_PARAM` + `details={field: reason}`로 거부한다. 타입 강제 변환은 문자열 숫자("5")처럼 손실 없는 경우만 허용, `5.5`→int, `True`→int는 거부.
- `require_json=True`일 때 `request.is_json`이 아니거나 JSON 파싱 실패면 `415/400`(코드 결정 필요 D5). 본문 없는 DELETE·multipart(`/data/import/preview`)는 `require_json=False`.
- 도메인 값의 SSOT: 범위·열거값은 서비스 쪽 상수로 두고(예: `today_service.FATIGUE_RANGE`, `PAIN_LEVELS`, `plan_template_service.WEEKS_RANGE`) 스키마가 그것을 참조한다. 서비스 함수는 내부 호출(MCP·CLI)을 위해 같은 상수로 최소 불변식(assert 수준이 아닌 `ValueError`)을 유지한다.
- 기존 `_reported_km`, `_message_input`, `validate_patch`/`validate_auto_patch`/`validate_changes`는 1차 적용 범위 밖이지만, 형태를 맞춰 점진 이관할 수 있게 `(clean, err)` 반환 규약을 그대로 따른다.

### 2.3 엔벨로프 보장 — `src/api/__init__.py` (수정)
- `@api_bp.errorhandler(HTTPException)` → 같은 상태코드의 `api_error`, `@api_bp.errorhandler(Exception)` → 로그 + `api_error("INTERNAL", ..., 500)`. 입력 검증이 빠진 라우트가 남아도 HTML 500은 나가지 않는다(안전망이지 검증 대체가 아님).

### 2.4 1차 적용 라우트
| 증상 | 라우트 | 스키마 요지 (범위 값은 D4에서 확정) |
|---|---|---|
| T-15 | POST `/today/checkin` | fatigue int(UI 1~10), pain enum(`none/mild/moderate/severe`, 프론트 `PainLevel`), note str(max_len) |
| P-05 | POST `/coach/plan` | distance_km float(>0, 상한), weeks int(범위, 보정 대신 거부), race_date date(>=오늘), target_time_sec int(>0, 상한), name str |
| P-04 | GET `/coach/plan/templates` | 위와 같은 race_date·target_time_sec·distance_km 규칙(`parse_args`) |
| C-02 | POST `/coach/threads`, `/threads/<id>/messages` | initial_message/text str(max_len), chip_id enum(`CHIP_TEXT`) — `_message_input`을 스키마 위로 재작성 |
| E-02 | v1 POST `/switch-user` | uid 정규식(결정 필요 D6) + `get_db_path` 경로 이탈 차단(`resolve()`가 `data/users` 하위인지), option 값 `html.escape` |

## 3. 변경 파일 표
| 파일 | 신규/수정 | 내용 | 예상 줄 |
|---|---|---|---|
| `src/web/request_guard.py` | 신규 | `same_origin`, 면제 목록, `init_request_guard(app)` | ~80 |
| `src/api/validation.py` | 신규 | Field 생성자, `parse_body`, `parse_args` | ~150 |
| `src/api/__init__.py` | 수정 | errorhandler 2개 | +20 |
| `src/web/app.py` | 수정 | guard 등록, 쿠키 설정, `/switch-user` uid 검증·escape | +15 (이미 1161줄 — 300줄 규칙 위반 상태, 이번에 늘리지 않으려면 switch-user를 `views_switch_user.py`로 분리 +40/-30) |
| `src/web/views_mcp_remote.py` | 수정 | `_origin_ok` → `request_guard.same_origin` | -3/+2 |
| `src/db_setup.py` | 수정 | `get_db_path` uid 경로 이탈 거부(ValueError) | +6 |
| `src/api/routes_today.py` | 수정 | 체크인 스키마 | +12 |
| `src/api/routes_plan.py` | 수정 | create/templates 스키마, `_reported_km` 이관 | +15/-15 |
| `src/api/routes_coach.py` | 수정 | `_message_input` 스키마화 | ±10 |
| `src/services/today_service.py`, `plan_template_service.py` | 수정 | 범위·열거 상수, 조용한 weeks 보정 제거 여부(D7) | +10 |
| `tests/test_request_guard.py` | 신규 | 동일/위조/누락 Origin, Referer 대체, 면제 경로, 쿠키 속성 | ~120 |
| `tests/test_api_validation.py` | 신규 | Field별 경계값, 비JSON 본문, details 형태 | ~150 |
| `tests/test_api_input_contracts.py` | 신규 | T-15·P-04·P-05·C-02 재현 케이스(리뷰 문서 값 그대로) → 400 JSON, errorhandler → JSON 500 | ~120 |
| `tests/test_switch_user.py` | 신규 | `../`·빈 값·특수문자 uid 거부, escape | ~50 |
| `frontend/src/lib/api/*` | 수정 가능 | `details`를 폼 필드 오류로 표시하는 처리(UI 범위는 product 영역) | 범위 밖 |

합계: 신규 약 670줄(테스트 440 포함), 수정 약 100줄.

## 4. 적용 순서·검증
1. **errorhandler (2.3)** — 가장 안전, 단독 배포 가능. 검증: C-02·`distance_km:"abc"` 재현 시 JSON 500/400, `pytest tests/test_api_*.py` 전체 통과.
2. **validation.py + 4개 라우트 (2.2/2.4)** — 검증: 리뷰 표의 재현 값(fatigue 0·11·5.5·"x", pain "bogus", weeks 0/-3/500, race_date "garbage"·2020-01-01, 99:99:99) 전부 400 + `details`. 정상 값 회귀 테스트. 브라우저(사본 DB): 오늘 체크인 저장, `/v2/coach/plan/new` 정상 생성·과거 날짜 오류 표시.
3. **Origin 관문 + 쿠키 (2.1)** — 먼저 "로그만 남기고 통과" 모드로 배포해 거부될 요청을 관찰한 뒤 차단 모드로 전환(전환 여부·기간 D8). 검증: `curl -X POST -H 'Origin: http://evil.example'` → 403, 같은 출처 → 정상, `/mcp`·`/api/garmin/local-sync` 면제 확인, `curl -i /v2/today`의 `Set-Cookie` 속성. 브라우저: v2 전 화면 쓰기 동작(체크인·코치·플랜·데이터 설정·가져오기 업로드·캘린더 피드 삭제) 1회씩, v1 폼 1회.
4. **switch-user / get_db_path** — 검증: 경로 이탈 uid 거부, 기존 사용자 전환 정상.
5. 완료 체크리스트: `pytest tests/`, `scripts/check_docs.py`, decisions.md에 새 ADR(ADR-048 후보: "쓰기 요청은 Origin 관문 + 경계 스키마") 기록 — 기록 여부는 사용자 결정.

### 호환성·v1 의존
- **깨지는 동작**: 범위 밖 값이 보정 대신 400(P-05 weeks), 비JSON 본문 거부, Origin 위조·(D1에 따라) Origin 없는 쓰기 요청 거부. 기존 테스트 중 Origin 없이 POST하는 `test_client` 호출은 D1 결정에 따라 헤더 추가 필요.
- **외부 클라이언트**: `/api/garmin/local-sync` 로컬 스크립트, CF 서비스 토큰으로 localhost에서 쓰기 호출하는 스크립트가 있다면 Origin이 없다 → 면제 목록 또는 D1에서 처리.
- **v1 의존**: `/switch-user`는 v1 HTML 페이지이고 v2 `MenuDrawer.svelte`가 링크한다. v1 폼 POST 25곳도 같은 관문을 받는다(같은 출처 폼은 브라우저가 Origin을 보내므로 영향 없음 예상). v1 제거 시 면제·switch-user 처리도 함께 정리.

## 5. 대안 비교
| | A안(추천): 전역 Origin 관문 + 라우트 경계 경량 스키마 | B안: CSRF 토큰(Flask-WTF 등) + pydantic 모델 |
|---|---|---|
| CSRF | 헤더 검사만, 프론트 변경 없음. 구형 브라우저·Origin 누락 처리가 D1에 달림 | 토큰 이중 제출로 가장 강함. 모든 v2 fetch·v1 폼에 토큰 주입 필요, 세션 의존 증가 |
| 입력 검증 | 의존성 0, 150줄 내, 기존 `(clean, err)` 규약과 일치 | 표현력 높음. 신규 의존성, 오류 포맷을 엔벨로프로 다시 매핑해야 함 |
| 비용 | 소 (약 2~3 작업 단위) | 중~대 (프론트 전 쓰기 호출 수정) |
- 추천 A: 이미 CF Access가 앞단 인증을 하고, 같은 출처 SPA + JSON API 구조라 Origin 검사 + SameSite 쿠키로 대부분의 CSRF 경로를 막을 수 있으며, ADR-034 선례와 일관된다. B는 v1 제거 이후 위협 모델이 바뀌면 재검토.

## 6. 결정 필요
- **D1 Origin·Referer 둘 다 없는 쓰기 요청**: (a) 거부 — 가장 안전, curl·스크립트·일부 테스트 깨짐 / (b) 허용 — 호환성 높음, 브라우저 CSRF는 Origin을 보내므로 대부분 방어되나 예외 경로 남음 / (c) production만 거부.
- **D2 허용 출처 기준**: `request.host` 일치만 vs `public_base_url()` + 추가 허용 목록(dev 서버 `localhost:5173` 등). 프록시 Host 헤더 신뢰 여부 포함.
- **D3 쿠키 속성**: SameSite `Lax` vs `Strict`(외부 링크로 진입 시 세션 미전송 → CF 재식별 비용), Secure를 production 한정할지.
- **D4 범위·상한 값**: fatigue 범위, note·메시지 최대 길이, distance_km 상한, weeks 범위, target_time_sec 상한, race_date 하한(오늘/내일)·상한.
- **D5 비JSON 본문 응답 코드**: 415 vs 400.
- **D6 user_id 허용 형식**: 이메일 형태(CF 신원) 허용 문자 집합, 그리고 production에서 `/switch-user` 자체를 막을지(인가 문제, 아래 범위 밖 메모와 연결).
- **D7 weeks 조용한 보정**: 대회일 기준 `min(weeks, avail)` 보정을 유지(경고 반환)할지, 거부할지.
- **D8 Origin 관문 롤아웃**: 관찰 모드 선행 여부·기간.
- **D9 ADR 기록**: 새 ADR로 남길지.

## 7. 범위 밖 메모
- E-01 보안 헤더(CSP·X-Frame-Options 등) 부재 — 별도 패턴.
- `/switch-user`가 production에서 인증된 사용자가 임의 사용자로 전환 가능한 인가 문제 — 입력 검증과 별개, 별도 결정.
- `src/web/app.py` 1161줄 — 300줄 규칙 위반, 별도 분리 작업.
- 프론트에서 서버 `details`를 필드 오류로 보여 주는 UX — product-architect 영역.
