---
> **후속 문서 (IP 차단 대응 설계)**
> - MIGRATION-01-01-IP-BLOCK-RESEARCH.md — 근본 원인 분석 + 방안 비교
> - MIGRATION-01-02-A-DESIGN.md — A안 상세 설계 (로컬 토큰 발급 + VPS sync, **채택**)
> - MIGRATION-01-03-B-DESIGN.md — B안 개요 (SSH 역방향 터널, **보류**)
---

설계서 구성
전수조사를 바탕으로 설계서를 4개 문서로 나눌게:
문서 1 (AUTH): garmin_auth.py와 views_settings_garmin.py의 garth 의존 지점 8+8=16곳 전수 식별, garminconnect 0.3.x 코드로 1:1 대응 설계 완료.
📄 문서 1: MIGRATION-01-AUTH.md — 인증 모듈 재작성
Garmin 인증 마이그레이션 상세설계 — garmin_auth.py + views_settings_garmin.py
작성일: 2026-04-09 | 브랜치: renew/data-architecture선행 조건: garminconnect 0.3.1+, curl_cffi, ua-generator 설치
1. 현행 분석 — garmin_auth.py
1.1 garth 의존 지점 (전수)
| 라인 | 코드 | 용도 ||------|------|------|| import | from garminconnect import Garmin | 현행 0.2.x Garmin 클래스 || import | GarminConnectTooManyRequestsError | 429 예외 (fallback placeholder 포함) || _tokenstore_path() | ~/.garth/{safe_uid} 하드코딩 | 토큰 디렉터리 || _tokenstore_path() | oauth2_token.json 존재 체크 | garth 토큰 파일명 || _login() | Garmin().login(tokenstore=str(tokenstore)) | 토큰 기반 로그인 || check_garmin_connection() | import garth as _garth | garth.Client 직접 사용 || check_garmin_connection() | _garth.Client().load(str(tokenstore)) | garth 토큰 로드 || check_garmin_connection() | g.oauth2_token | garth OAuth2Token 객체 || check_garmin_connection() | token.refresh_expired, token.expired | garth 전용 속성 |
1.2 garminconnect 0.3.x 대응 매핑
| 현행 (garth) | 신규 (garminconnect 0.3.x) | 비고 ||---|---|---|| /.garth/{user} | /.garminconnect/{user} | 디렉터리 변경 || oauth1_token.json + oauth2_token.json | garmin_tokens.json (단일 파일) | DI OAuth payload || garth.Client().load() | Garmin().login(tokenstore=path) | 토큰 로드+자동갱신 || token.refresh_expired | 직접 JSON 파싱 또는 login() 시도 후 예외 캐치 | 아래 상세 || token.expired | client._token_expires_soon() (내부) 또는 login 시도 | 아래 상세 || GarminConnectTooManyRequestsError | 동일 클래스 존재 (garminconnect.exceptions) | 호환 |
1.3 신규 garmin_auth.py 설계python"""Garmin Connect 인증 — garminconnect 0.3.x 네이티브 DI OAuth."""from future import annotationsfrom pathlib import Pathimport json, logging
log = logging.getLogger(name)
try:    from garminconnect import Garmin    from garminconnect.exceptions import (        GarminConnectTooManyRequestsError,        GarminConnectAuthenticationError,        GarminConnectConnectionError,    )except ImportError:    Garmin = None    class GarminConnectTooManyRequestsError(Exception): pass    class GarminConnectAuthenticationError(Exception): pass    class GarminConnectConnectionError(Exception): pass

class GarminAuthRequired(Exception):    """Garmin 토큰이 없거나 만료되어 웹 UI에서 재인증이 필요할 때."""    pass

def _tokenstore_path(config: dict) -> Path:    """멀티유저 토큰 디렉터리 결정."""    garmin_cfg = config.get("garmin", {})    explicit = garmin_cfg.get("tokenstore", "")    if explicit:        return Path(explicit).expanduser()    user_id = garmin_cfg.get("user_id", "")    if user_id:        safe_uid = user_id.replace("/", "").replace("@", "_at")        return Path(f"~/.garminconnect/{safe_uid}").expanduser()    return Path("~/.garminconnect").expanduser()

def _token_file(config: dict) -> Path:    return _tokenstore_path(config) / "garmin_tokens.json"

def _login(config: dict) -> "Garmin":    """토큰 기반 로그인. 실패 시 GarminAuthRequired."""    if Garmin is None:        raise ImportError("garminconnect 패키지 필요: pip install garminconnect curl_cffi ua-generator")
    tokenstore = _tokenstore_path(config)    token_file = tokenstore / "garmin_tokens.json"
    if not token_file.exists():        raise GarminAuthRequired(            "Garmin 토큰 없음. /connect/garmin에서 로그인하세요."        )
    try:        client = Garmin()        client.login(tokenstore=str(tokenstore))로그인 성공 시 갱신된 토큰 자동 저장        try:            client.client.dump(str(tokenstore))        except Exception:            pass        return client    except GarminConnectTooManyRequestsError:        raise    except (GarminConnectAuthenticationError, GarminConnectConnectionError) as e:        raise GarminAuthRequired(f"Garmin 토큰 복구 실패: {e}") from e    except Exception as e:        raise GarminAuthRequired(f"Garmin 토큰 복구 실패: {e}") from e

def check_garmin_connection(config: dict) -> dict:    """Garmin 연결 상태 확인 — garmin_tokens.json 기반."""    tokenstore = _tokenstore_path(config)    token_file = tokenstore / "garmin_tokens.json"
    if not token_file.exists():        if tokenstore.exists():디렉터리는 있지만 토큰 없음 — 마이그레이션 안내 포함            old_oauth2 = tokenstore / "oauth2_token.json"            if old_oauth2.exists():                return {                    "ok": False,                    "status": "garth 토큰 감지 (마이그레이션 필요)",                    "detail": "이전 garth 토큰이 존재합니다. /connect/garmin에서 재로그인하세요.",                }            return {                "ok": False,                "status": "토큰 없음",                "detail": f"{tokenstore} 디렉터리만 존재. /connect/garmin에서 로그인하세요.",            }        return {            "ok": False,            "status": "미설정",            "detail": "토큰 없음. /connect/garmin에서 연동하세요.",        }
토큰 파일 존재 — JSON 파싱으로 유효성 기본 확인    try:        with open(token_file) as f:            token_data = json.load(f)        if not token_data.get("access_token") and not token_data.get("di_access_token"):            return {                "ok": False,                "status": "토큰 손상",                "detail": "토큰 파일에 access_token 없음. 재로그인 필요.",            }실제 유효성은 API 호출로만 확인 가능여기서는 파일 존재 + 기본 구조만 검증        return {            "ok": True,            "status": "연결됨",            "detail": f"토큰 유효. tokenstore: {tokenstore}",        }    except (json.JSONDecodeError, IOError) as e:        return {            "ok": False,            "status": "토큰 손상",            "detail": f"토큰 파일 읽기 실패: {e}. 재로그인 필요.",        }1.4 핵심 변경 포인트 요약
- import garth → 완전 제거- 토큰 경로: /.garth/{user} → /.garminconnect/{user}- 토큰 파일: oauth1_token.json + oauth2_token.json → garmin_tokens.json- check_garmin_connection(): garth.Client 의존 제거, JSON 파싱 기반 검증으로 교체- _login(): Garmin().login(tokenstore=path) 패턴 유지, 로그인 후 토큰 자동 dump 추가- 예외 클래스: garminconnect 0.3.x exceptions 모듈에서 직접 import (호환됨)
2. 현행 분석 — views_settings_garmin.py
2.1 garth 의존 지점 (전수: 총 8개 위치)
| 위치 | garth 사용 | 영향 ||------|-----------|------|| _garmin_token_status_html() | import garth as _garth; _garth.Client().load(); tok.refresh_expired/expired | 토큰 상태 배지 생성 || garmin_connect_post() | import garth; from garth import sso; _sso.login(email, password, client=g, return_on_mfa=True) | 서버 직접 로그인 || garmin_connect_post() | g.oauth1_token = oauth1; g.oauth2_token = oauth2; g.dump(str(tokenstore)) | 토큰 저장 || garmin_mfa_submit() | from garth.sso import resume_login; _sso.resume_login(client_state, mfa_code) | MFA 완료 || garmin_mfa_submit() | g.dump(str(tokenstore)) | MFA 후 토큰 저장 || garmin_upload_token() | oauth2_token.json 파일명 하드코딩 | 토큰 업로드 || garmin_paste_token() | from garth.sso import get_oauth1_token, exchange | ticket 교환 || garmin_browser_login() | sso.garmin.com/sso/signin 리다이렉트 URL | 브라우저 SSO |
2.2 라우트별 재설계
GET /connect/garmin — 연동 폼- _garmin_token_status_html(): garth 제거, check_garmin_connection() 결과 사용- /.garth 표시 → /.garminconnect 표시- 토큰 파일명: oauth2_token.json → garmin_tokens.json- 브라우저 로그인 섹션: SSO embed URL은 garminconnect 0.3.x에서 미지원 → 섹션 제거 또는 안내 문구로 대체- 토큰 업로드 섹션: garmin_tokens.json 단일 파일 업로드로 변경
POST /connect/garmin — 서버 직접 로그인python현행: garth.sso.login(email, password, client=g, return_on_mfa=True)신규:garmin = Garmin(email, password, return_on_mfa=True)mfa_status, client_state = garmin.login(tokenstore=str(tokenstore))if mfa_status == "needs_mfa":    _pending_mfa[key] = {        "garmin_client": garmin,        "tokenstore": str(tokenstore),        "email": email,    }→ MFA 폼으로 리다이렉트else:로그인 성공 — 토큰 자동 저장됨    garmin.client.dump(str(tokenstore))POST /connect/garmin/mfa — MFA 제출python현행: garth.sso.resume_login(client_state, mfa_code)신규:garmin = pending["garmin_client"]garmin.resume_login(pending.get("client_state", {}), mfa_code)garmin.client.dump(str(pending["tokenstore"]))POST /connect/garmin/upload-token — 토큰 업로드python현행: oauth1_token.json (선택) + oauth2_token.json (필수)신규: garmin_tokens.json (단일 파일)token_file = request.files.get("token")token_data = json.loads(token_file.read())tokenstore = Path(f"~/.garminconnect/{safe_uid}").expanduser()tokenstore.mkdir(parents=True, exist_ok=True)with open(tokenstore / "garmin_tokens.json", "w") as f:    json.dump(token_data, f, indent=2)POST /connect/garmin/paste-token — 붙여넣기- ticket 교환 로직(garth.sso.get_oauth1_token, exchange): 제거  - garminconnect 0.3.x는 ticket → DI OAuth 변환을 내부에서 처리  - 외부에서 ticket만으로 토큰 발급 불가- JSON 직접 붙여넣기: garmin_tokens.json 형식으로 저장
GET /connect/garmin/browser-login — 브라우저 SSO- garminconnect 0.3.x는 브라우저 기반 SSO → 토큰 추출 경로 미지원- 제거 또는 "PC에서 CLI로 토큰 발급 후 업로드하세요" 안내로 대체
2.3 _pending_mfa 구조 변경python현행_pending_mfa[key] = {    "client_state": result[1],   # garth 내부 state    "garth_client": g,           # garth.Client 인스턴스    "tokenstore": str(tokenstore),    "email": email,}
신규_pending_mfa[key] = {    "garmin_client": garmin,     # garminconnect.Garmin 인스턴스    "client_state": client_state,# login() return_on_mfa=True의 두 번째 값    "tokenstore": str(tokenstore),    "email": email,}3. 예외 클래스 호환성 확인
garminconnect 0.3.x (garminconnect/exceptions.py) 정의:pythonclass GarminConnectConnectionError(Exception): ...class GarminConnectTooManyRequestsError(Exception): ...class GarminConnectAuthenticationError(Exception): ...class GarminConnectInvalidFileFormatError(Exception): ...현행 garmin_auth.py의 fallback placeholder와 동일 이름 → 호환 문제 없음.
garmin.py에서 re-export하는 GarminConnectTooManyRequestsError도 동일 클래스이므로 하위 모듈 수정 불필요.
