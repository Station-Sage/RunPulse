"""Strava OAuth2 토큰 관리 및 연결 상태 확인."""

import time

from src.utils import api
from src.utils.config import update_service_config

_BASE_URL = "https://www.strava.com/api/v3"
_TOKEN_URL = "https://www.strava.com/oauth/token"


def refresh_token(config: dict) -> str:
    """access_token 만료 시 갱신. config dict 업데이트.

    Args:
        config: 전체 설정 딕셔너리.

    Returns:
        유효한 access_token.
    """
    strava = config["strava"]
    if strava.get("expires_at", 0) > time.time():
        return strava["access_token"]

    result = api.post(
        _TOKEN_URL,
        data={
            "client_id": strava["client_id"],
            "client_secret": strava["client_secret"],
            "refresh_token": strava["refresh_token"],
            "grant_type": "refresh_token",
        },
    )

    strava["access_token"] = result["access_token"]
    strava["refresh_token"] = result["refresh_token"]
    strava["expires_at"] = result["expires_at"]

    try:
        update_service_config("strava", {
            "access_token": strava["access_token"],
            "refresh_token": strava["refresh_token"],
            "expires_at": strava["expires_at"],
        })
    except Exception as e:
        print(f"[strava] 토큰 저장 실패 (동기화는 계속됨): {e}")

    return strava["access_token"]


def check_strava_connection(config: dict) -> dict:
    """Strava 연결 상태 확인.

    Returns:
        {"ok": bool, "status": str, "detail": str}
    """
    strava = config.get("strava", {})
    has_client = bool(strava.get("client_id") and strava.get("client_secret"))
    has_refresh = bool(strava.get("refresh_token"))
    access_token = strava.get("access_token")
    expires_at = strava.get("expires_at", 0)

    if not has_client:
        return {
            "ok": False,
            "status": "설정 누락",
            "detail": "client_id / client_secret 미설정. /settings에서 연동하세요.",
        }
    if not has_refresh:
        return {
            "ok": False,
            "status": "재연동 필요",
            "detail": "refresh_token 없음. /connect/strava에서 OAuth 연동을 완료하세요.",
        }
    if not access_token:
        return {
            "ok": True,
            "status": "갱신 필요",
            "detail": "access_token 없음. 다음 sync 시 자동 갱신됩니다.",
        }
    if expires_at and expires_at < time.time():
        return {
            "ok": True,
            "status": "토큰 만료",
            "detail": "access_token 만료. 다음 sync 시 자동 갱신됩니다.",
        }
    return {
        "ok": True,
        "status": "연결됨",
        "detail": f"토큰 유효. 만료: {expires_at}",
    }
