"""Intervals.icu API 인증 및 연결 상태 확인."""

from src.utils import api


def base_url(config: dict) -> str:
    """Intervals.icu API base URL 반환."""
    athlete_id = config["intervals"]["athlete_id"]
    return f"https://intervals.icu/api/v1/athlete/{athlete_id}"


def auth(config: dict) -> tuple[str, str]:
    """Basic Auth 튜플 반환."""
    return ("API_KEY", config["intervals"]["api_key"])


def check_intervals_connection(config: dict) -> dict:
    """Intervals.icu 연결 상태를 실제 API 호출로 확인.

    Returns:
        {"ok": bool, "status": str, "detail": str}
    """
    intervals_cfg = config.get("intervals", {})
    athlete_id = intervals_cfg.get("athlete_id", "")
    api_key = intervals_cfg.get("api_key", "")

    if not athlete_id or not api_key:
        missing = []
        if not athlete_id:
            missing.append("athlete_id")
        if not api_key:
            missing.append("api_key")
        return {
            "ok": False,
            "status": "설정 누락",
            "detail": f"{', '.join(missing)} 미설정. /settings에서 입력하세요.",
        }

    try:
        result = api.get(
            f"https://intervals.icu/api/v1/athlete/{athlete_id}",
            auth=("API_KEY", api_key),
            timeout=10,
        )
        name = result.get("name") or result.get("username") or athlete_id
        return {
            "ok": True,
            "status": "연결됨",
            "detail": f"athlete: {name} ({athlete_id})",
        }
    except api.ApiError as e:
        if e.status_code == 401:
            return {"ok": False, "status": "잘못된 API 키", "detail": "인증 실패 (401). API 키를 확인하세요."}
        if e.status_code == 404:
            return {"ok": False, "status": "잘못된 athlete_id", "detail": f"athlete_id '{athlete_id}'를 찾을 수 없습니다 (404)."}
        return {"ok": False, "status": "연결 실패", "detail": str(e)}
    except Exception as e:
        return {"ok": False, "status": "연결 오류", "detail": str(e)}
