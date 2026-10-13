"""요청 경계 보호 — Origin 관문·봉투 경로 규칙·403 응답 (SRV 2.1, ADR-048). 앱 셸(`src/web/`) 전용.

- 상태 변경 메서드(POST/PUT/PATCH/DELETE)는 `Origin`(없으면 `Referer` 의 출처)이 허용 출처여야 한다.
  둘 다 없으면 거부한다(D1). 허용 출처 = `public_base_url()` + (개발 환경 한정) `DEV_ALLOWED_ORIGINS`.
  프록시 뒤 `Host` 헤더는 기준이 아니다 — 운영은 `PUBLIC_BASE_URL` 설정이 전제다(없으면 요청 `url_root` 로 폴백,
  개발 편의용). 비교는 소문자·기본 포트 생략으로 정규화하며 userinfo 포함·http(s) 외 스킴·`null` 은 허용되지 않는다.
- 모드 `ORIGIN_GUARD_MODE` 환경변수: `observe`(기본, 로그만 남기고 통과) / `enforce`(403).
  인증(auth_cf)이 먼저 실행되므로 인증 실패 요청은 여기까지 오지 않는다 → 위반 로그는 인증 통과 요청만 집계된다(Q5).
- 면제(`EXEMPT_PATHS`)는 자체 인증이 있거나 읽기 전용인 경로다. `/api/context-episodes` 는 면제가 아니다(NEW-40).
- 보안 로그(`runpulse.security`)에는 Origin 과 Referer(쿼리·프래그먼트 제거, 200자 제한)만 남긴다.
- `same_origin()` 은 `/mcp`(ADR-034)도 재사용한다. 거기서는 Origin 헤더가 없는 비브라우저 클라이언트를 허용한다
  (비교 기준이 요청 Host 에서 허용 출처 목록으로 바뀜 — S3-5 ④).
"""
from __future__ import annotations

import logging
import os
from urllib.parse import urlsplit

from flask import Flask, Response, jsonify, request

security_log = logging.getLogger("runpulse.security")

# `{error:{code,message}}` 봉투로 응답하는 경로(NEW-40). `/api/v1` 밖에 봉투 API 를 두면 여기에 추가한다.
ENVELOPE_PATH_PREFIXES = ("/api/v1/", "/api/context-episodes")

STATE_CHANGING_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})

# Origin 관문 면제 — `/`로 끝나면 접두, 아니면 정확히 그 경로(와 하위).
EXEMPT_PATHS = (
    "/mcp",                      # 자체 Origin·Bearer 검사 (ADR-034)
    "/api/garmin/local-sync",    # sync_key 2차 인증, 로컬 스크립트
    "/feeds/cal/",               # GET 전용 공개 피드
    "/api/v1/csp-report",        # 브라우저 CSP 보고(로그 전용, security-headers D6)
)

# 개발 서버(vite) 등 — development 환경(APP_ENV != production)에서만 허용 출처에 더해진다.
DEV_ALLOWED_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)

_MODES = ("observe", "enforce")
_DEFAULT_MODE = "observe"


def is_envelope_path(path: str) -> bool:
    return path.startswith(ENVELOPE_PATH_PREFIXES)


def forbidden_response(code: str, message: str) -> Response:
    """403 — 봉투 경로는 `{error:{code,message}}` JSON, 그 외는 text/plain (S3-2)."""
    if is_envelope_path(request.path):
        resp = jsonify({"error": {"code": code, "message": message}})
        resp.status_code = 403
        return resp
    return Response(message, status=403, mimetype="text/plain")


def _is_production() -> bool:
    return os.environ.get("APP_ENV", "development").lower() == "production"


def guard_mode() -> str:
    """`ORIGIN_GUARD_MODE` — 알 수 없는 값은 observe 로 처리한다(오설정이 서비스를 막지 않게)."""
    raw = os.environ.get("ORIGIN_GUARD_MODE", _DEFAULT_MODE).strip().lower()
    if raw not in _MODES:
        security_log.warning("[origin_guard] ORIGIN_GUARD_MODE=%r 은 알 수 없는 값 — observe 로 처리", raw[:20])
        return _DEFAULT_MODE
    return raw


def is_exempt(path: str) -> bool:
    for p in EXEMPT_PATHS:
        if p.endswith("/"):
            if path.startswith(p):
                return True
        elif path == p or path.startswith(p + "/"):
            return True
    return False


_DEFAULT_PORTS = {"http": 80, "https": 443}


def _origin_of(url: str) -> str | None:
    """`scheme://host[:port]` (소문자, 기본 포트 생략). 출처로 볼 수 없으면 None.

    None 대상: `null`·상대경로·스킴 없음·http(s) 외 스킴·userinfo 포함(브라우저는 보내지 않음)·잘못된 포트.
    """
    try:
        parts = urlsplit(url.strip())
        host, port = parts.hostname, parts.port
    except ValueError:
        return None
    scheme = parts.scheme.lower()
    if scheme not in _DEFAULT_PORTS or not host or parts.username is not None or parts.password is not None:
        return None
    host = f"[{host}]" if ":" in host else host  # IPv6 리터럴
    if port is None or port == _DEFAULT_PORTS[scheme]:
        return f"{scheme}://{host}"
    return f"{scheme}://{host}:{port}"


def _loggable(value: str | None, *, strip_query: bool = False, limit: int = 200) -> str | None:
    """보안 로그용 — Referer 의 쿼리·프래그먼트(토큰 가능성)를 떼고 길이를 제한한다. repr 은 호출 측 `%r`."""
    if value is None:
        return None
    if strip_query:
        value = value.split("#", 1)[0].split("?", 1)[0]
    return value[:limit]


def allowed_origins() -> set[str]:
    from src.utils.public_url import public_base_url
    out: set[str] = set()
    base = _origin_of(public_base_url())
    if base:
        out.add(base)
    if not _is_production():
        out.update(o.lower() for o in DEV_ALLOWED_ORIGINS)
    return out


def request_origin(req=None) -> str | None:
    """요청이 주장하는 출처 — `Origin` 우선, 없으면 `Referer` 의 출처.

    둘 다 없으면 None. 헤더는 있으나 출처로 해석할 수 없으면(`null`·빈 값·상대경로 등) 빈 문자열 —
    허용 목록에 없으므로 `same_origin` 이 거부한다.
    """
    req = req or request
    origin = req.headers.get("Origin")
    if origin is not None:
        return _origin_of(origin) or ""
    referer = req.headers.get("Referer")
    if referer:
        return _origin_of(referer) or ""
    return None


def same_origin(req=None, *, allow_missing: bool = False) -> bool:
    """요청 출처가 허용 출처인가. 출처 정보(Origin·Referer)가 없으면 `allow_missing` 값."""
    claimed = request_origin(req)
    if claimed is None:
        return allow_missing
    return claimed in allowed_origins()


def _check() -> Response | None:
    if request.method not in STATE_CHANGING_METHODS or is_exempt(request.path):
        return None
    if same_origin(request):
        return None
    mode = guard_mode()
    security_log.warning(
        "[origin_guard] 거부 대상 (mode=%s, method=%s, path=%s, origin=%r, referer=%r)",
        mode, request.method, request.path,
        _loggable(request.headers.get("Origin")),
        _loggable(request.headers.get("Referer"), strip_query=True),
    )
    if mode != "enforce":
        return None
    return forbidden_response("FORBIDDEN_ORIGIN", "허용되지 않는 요청 출처입니다.")


def init_request_guard(app: Flask) -> None:
    """Origin 관문 `before_request` 등록. `init_cf_auth` 뒤에 호출한다(인증 통과 요청만 검사·집계)."""
    configured = os.environ.get("PUBLIC_BASE_URL", "").strip()
    if _is_production() and not configured:
        security_log.warning(
            "[origin_guard] production 인데 PUBLIC_BASE_URL 미설정 — 프록시 뒤에서는 정상 요청이 거부 대상으로 집계된다"
        )
    elif configured and _origin_of(configured) is None:
        security_log.warning(
            "[origin_guard] PUBLIC_BASE_URL 이 http(s)://호스트 형식이 아니다 — 모든 쓰기 요청이 거부 대상으로 집계된다"
        )
    app.before_request(_check)
