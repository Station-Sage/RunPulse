"""소스 연결·테스트·해제 쓰기 — 키 방식(Intervals·Runalyze)과 Strava OAuth 시작. 설계: 40 design §2.4·§3.1·§7.3.

자격 증명 원문은 응답에 싣지 않는다. 데이터 삭제 해제는 파급(파생 지표 재계산)이 커서 아직 지원하지 않는다.
"""
from __future__ import annotations

import urllib.parse

from src.sync.intervals_auth import check_intervals_connection
from src.sync.runalyze import check_runalyze_connection
from src.utils.config import load_config, update_service_config

_RETURN_PREFIXES = ("/v2/data/sources/", "/v2/welcome")
_CRED_FIELDS = {
    "intervals": {"athlete_id": "", "api_key": ""},
    "runalyze": {"token": ""},
    "strava": {"access_token": "", "refresh_token": "", "expires_at": 0},
}
_CHECKS = {"intervals": check_intervals_connection, "runalyze": check_runalyze_connection}


def safe_return_to(value: str | None) -> str | None:
    """OAuth 복귀 경로 허용 목록 검사 — 같은 사이트의 v2 Data/환영 화면만 허용."""
    if not value or not value.startswith("/") or value.startswith("//") or "\\" in value or ".." in value:
        return None
    path = urllib.parse.urlsplit(value).path
    if any(path == p.rstrip("/") or path.startswith(p) for p in _RETURN_PREFIXES):
        return value
    return None


def _result(ok: bool, message_ko: str, **extra) -> dict:
    return {"ok": ok, "message_ko": message_ko, **extra}


def _verdict(provider: str, config: dict) -> dict:
    res = _CHECKS[provider](config)
    if res.get("ok"):
        return _result(True, "연결됐어요")
    return _result(False, f"연결하지 못했어요 ({res.get('status', '확인 실패')})")


def test_connection(provider: str, config: dict) -> dict:
    if provider in _CHECKS:
        return _verdict(provider, config)
    from src.sync.garmin_auth import check_garmin_connection
    from src.sync.strava_auth import check_strava_connection

    res = (check_garmin_connection if provider == "garmin" else check_strava_connection)(config)
    return _result(bool(res.get("ok")), "연결돼 있어요" if res.get("ok") else f"연결 확인 필요 ({res.get('status', '확인 실패')})")


def connect(provider: str, user_id: str, body: dict) -> tuple[dict | None, str | None]:
    """연결 시작. 반환 (payload, error_code). error_code 있으면 payload는 사용자 메시지를 담는다."""
    config = load_config(user_id=user_id)
    if provider == "garmin":
        return {"message_ko": "Garmin은 아직 이 화면에서 연결할 수 없어요"}, "UNSUPPORTED"
    if provider == "strava":
        sc = config.get("strava", {})
        if not (sc.get("client_id") and sc.get("client_secret")):
            return {"message_ko": "Strava 앱 정보(Client ID/Secret)를 먼저 저장해 주세요"}, "NEEDS_APP"
        ret = safe_return_to(body.get("return_to")) or "/v2/data/sources/strava?connected=1"
        return {"redirect_url": "/connect/strava/oauth-start?" + urllib.parse.urlencode({"return_to": ret})}, None
    key = str(body.get("api_key") or "").strip()
    if not key:
        return {"message_ko": "API 키를 입력해 주세요"}, "INVALID_PARAM"
    if provider == "intervals":
        aid = str(body.get("athlete_id") or config.get("intervals", {}).get("athlete_id", "")).strip()
        if not aid:
            return {"message_ko": "Athlete ID를 입력해 주세요"}, "INVALID_PARAM"
        updates = {"athlete_id": aid, "api_key": key}
    else:
        updates = {"token": key}
    previous = {k: config.get(provider, {}).get(k, "") for k in updates}
    cfg = update_service_config(provider, updates, user_id=user_id)
    verdict = _verdict(provider, cfg)
    if not verdict["ok"]:
        update_service_config(provider, previous, user_id=user_id)
    return verdict, None


def disconnect(provider: str, user_id: str) -> dict:
    """자격 증명만 지운다. 가져온 데이터는 그대로 둔다."""
    update_service_config(provider, _CRED_FIELDS.get(provider, {}), user_id=user_id)
    return {"provider": provider, "keep_data": True}
