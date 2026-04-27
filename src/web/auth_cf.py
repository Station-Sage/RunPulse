"""Cloudflare Zero Trust 헤더 기반 사용자 식별 미들웨어.

Cloudflare Zero Trust가 외부 인증(GitHub/Google 로그인)을 담당하고,
인증된 요청에 CF-Access-Authenticated-User-Email 헤더를 추가한다.
Flask는 이 헤더를 읽어 session["user_id"]를 세팅하는 역할만 수행한다.

APP_ENV:
  - "production": CF 헤더 필수. 헤더 없으면 401 반환. KEY 없으면 앱 시작 거부.
  - "development" (기본값): CF 헤더 없으면 DEV_USER_ID 환경변수 또는 "default" 사용.
"""

from __future__ import annotations

import logging
import os

from flask import Flask, Response, request, session

log = logging.getLogger(__name__)

_CF_EMAIL_HEADER = "CF-Access-Authenticated-User-Email"
_SESSION_KEY = "user_id"
_APP_ENV = os.environ.get("APP_ENV", "development").lower()
_IS_PRODUCTION = _APP_ENV == "production"


def _get_dev_user_id() -> str:
    """개발 환경 fallback user_id. DEV_USER_ID 환경변수 우선, 없으면 'default'."""
    return os.environ.get("DEV_USER_ID", "default")


def _load_svc_token() -> tuple[str, str, str]:
    """루트 config에서 CF 서비스 토큰 자격증명을 읽어 반환 (요청별 동적 로딩)."""
    try:
        from src.utils.config import load_config
        cfg = load_config(user_id="default")
        cf = cfg.get("cf", {})
        svc_user = cfg.get("garmin", {}).get("email", "service")
        return cf.get("service_client_id", ""), cf.get("service_client_secret", ""), svc_user
    except Exception:
        return "", "", "service"


def init_cf_auth(app: Flask, config: dict | None = None) -> None:
    """Flask 앱에 CF 헤더 기반 사용자 식별 before_request 훅 등록.

    CF 서비스 토큰은 요청마다 루트 config에서 동적으로 로드하므로
    설정 변경 후 서버 재시작이 불필요하다.

    Args:
        app: Flask 앱 인스턴스.
        config: 사용하지 않음 (하위 호환 유지용).
    """
    if _IS_PRODUCTION:
        log.info("[auth_cf] production 모드: CF 헤더 필수 (서비스 토큰 동적 로딩)")
    else:
        fallback = _get_dev_user_id()
        log.warning(
            "[auth_cf] development 모드: CF 헤더 없으면 '%s' 사용 (로컬 개발 전용)",
            fallback,
        )

    @app.before_request
    def _identify_user() -> Response | None:
        """CF 헤더에서 이메일을 읽어 session["user_id"] 세팅."""
        # 이미 세션에 user_id가 있으면 매 요청마다 헤더 재파싱 불필요
        if _SESSION_KEY in session:
            return None

        email = request.headers.get(_CF_EMAIL_HEADER, "").strip()
        if email:
            session.permanent = True
            session[_SESSION_KEY] = email
            log.debug("[auth_cf] 사용자 식별: %s", email)
            return None

        # CF Zero Trust는 서비스 토큰 헤더를 엣지에서 검증 후 제거하고 전달한다.
        # /api/garmin/local-sync는 body의 sync_key로 2차 인증하므로 여기서 건너뜀.
        if request.path == "/api/garmin/local-sync" and request.method == "POST":
            log.debug("[auth_cf] /api/garmin/local-sync — sync_key 인증으로 위임")
            return None

        # CF 서비스 토큰 바이패스 (localhost 직접 호출 등 CF 미경유 경로용)
        svc_id, svc_secret, svc_user = _load_svc_token()
        if svc_id:
            req_id = request.headers.get("CF-Access-Client-Id", "")
            req_secret = request.headers.get("CF-Access-Client-Secret", "")
            if req_id == svc_id and req_secret == svc_secret:
                session.permanent = True
                session[_SESSION_KEY] = svc_user
                log.debug("[auth_cf] 서비스 토큰 인증 성공 (user=%s)", svc_user)
                return None

        if _IS_PRODUCTION:
            log.warning(
                "[auth_cf] production 환경에서 CF 헤더 없음 (path=%s). 401 반환.",
                request.path,
            )
            return Response(
                "Unauthorized: Cloudflare Access 인증이 필요합니다.",
                status=401,
                mimetype="text/plain",
            )

        # 개발 환경 fallback
        fallback = _get_dev_user_id()
        session.permanent = True
        session[_SESSION_KEY] = fallback
        return None


def get_current_user_email() -> str | None:
    """현재 요청의 CF 인증 이메일 반환. 없으면 None."""
    return request.headers.get(_CF_EMAIL_HEADER, "").strip() or None
