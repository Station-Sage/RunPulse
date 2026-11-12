"""Strava OAuth2 시작·콜백 — `/connect/strava/oauth-start`·`/connect/strava/callback`.

v1 연동 화면(views_settings_integrations)에서 OAuth 두 라우트만 남겼다(S4-91, ADR-056). URL 은 불변 —
v2 `data_connect_service.connect` 가 oauth-start 로 보내고, Strava 앱 설정의 redirect URI 가 callback 이다.
결과는 `return_to`(state) 또는 v2 Strava 소스 화면으로 돌려보낸다(`connected=1` / `connect_error=1`).
"""
from __future__ import annotations

import logging
import urllib.parse

from flask import Blueprint, redirect, request

from src.utils.config import load_config, update_service_config
from src.utils.public_url import public_base_url

log = logging.getLogger(__name__)
strava_oauth_bp = Blueprint("strava_oauth", __name__)

_STRAVA_AUTH_URL = "https://www.strava.com/oauth/authorize"
_STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token"
_STRAVA_SCOPE = "read,activity:read_all"
_STRAVA_REDIRECT_PATH = "/connect/strava/callback"
_PUBLIC_BASE_URL = public_base_url("https://runpulse.stationsage.dev")
V2_STRAVA_PATH = "/v2/data/sources/strava"


def _fail(return_to: str | None, reason: str):
    """실패 — return_to(쿼리 제거) 또는 v2 Strava 화면에 connect_error=1."""
    log.warning("[strava_oauth] 실패: %s", reason)
    base = return_to.split("?")[0] if return_to else V2_STRAVA_PATH
    return redirect(base + "?connect_error=1")


@strava_oauth_bp.get("/connect/strava/oauth-start")
def strava_oauth_start():
    """Strava OAuth2 인증 시작."""
    from src.services.data_connect_service import safe_return_to

    return_to = safe_return_to(request.args.get("return_to"))
    client_id = load_config().get("strava", {}).get("client_id", "")
    if not client_id:
        return _fail(return_to, "client_id 미설정")
    params = {
        "client_id": client_id,
        "redirect_uri": f"{_PUBLIC_BASE_URL}{_STRAVA_REDIRECT_PATH}",
        "response_type": "code",
        "approval_prompt": "auto",
        "scope": _STRAVA_SCOPE,
    }
    if return_to:
        params["state"] = return_to
    return redirect(_STRAVA_AUTH_URL + "?" + urllib.parse.urlencode(params))


@strava_oauth_bp.get("/connect/strava/callback")
def strava_oauth_callback():
    """Strava OAuth2 콜백 — code → token 교환 → 저장."""
    import httpx
    from src.services.data_connect_service import safe_return_to

    return_to = safe_return_to(request.args.get("state"))
    error = request.args.get("error")
    if error:
        return _fail(return_to, f"OAuth 오류: {error}")
    code = request.args.get("code", "")
    if not code:
        return _fail(return_to, "인증 코드 없음")

    strava_cfg = load_config().get("strava", {})
    client_id = strava_cfg.get("client_id", "")
    client_secret = strava_cfg.get("client_secret", "")
    if not client_id or not client_secret:
        return _fail(return_to, "Client ID/Secret 미설정")

    try:
        with httpx.Client(timeout=15) as client:
            resp = client.post(_STRAVA_TOKEN_URL, data={
                "client_id": client_id, "client_secret": client_secret,
                "code": code, "grant_type": "authorization_code",
            })
            resp.raise_for_status()
            token_data = resp.json()
    except Exception as e:
        return _fail(return_to, f"토큰 교환 실패: {e}")

    update_service_config("strava", {
        "access_token": token_data.get("access_token", ""),
        "refresh_token": token_data.get("refresh_token", ""),
        "expires_at": token_data.get("expires_at", 0),
    })
    return redirect(return_to or V2_STRAVA_PATH + "?connected=1")
