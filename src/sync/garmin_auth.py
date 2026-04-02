from __future__ import annotations

"""Garmin Connect 인증 함수."""

from pathlib import Path

try:
    from garminconnect import Garmin
    try:
        from garminconnect import GarminConnectTooManyRequestsError
    except ImportError:
        class GarminConnectTooManyRequestsError(Exception):
            """garminconnect 미설치 시 placeholder — 어떤 예외도 매칭되지 않음."""
            pass
except ImportError:
    Garmin = None
    class GarminConnectTooManyRequestsError(Exception):
        """garminconnect 미설치 시 placeholder."""
        pass


class GarminAuthRequired(Exception):
    """Garmin 토큰이 없거나 만료되어 웹 UI에서 재인증이 필요할 때."""
    pass


def _tokenstore_path(config: dict) -> Path:
    garmin_cfg = config.get("garmin", {})
    # 1) 명시적 경로
    explicit = garmin_cfg.get("tokenstore", "")
    if explicit:
        return Path(explicit).expanduser()
    # 2) user_id(이메일)로 서브폴더
    user_id = garmin_cfg.get("user_id", "")
    if user_id:
        safe_uid = user_id.replace("/", "_")
        return Path(f"~/.garth/{safe_uid}").expanduser()
    # 3) 기본
    return Path("~/.garth").expanduser()


def _login(config: dict) -> "Garmin":
    """Garmin Connect 인증 — 토큰 기반만 허용.

    토큰이 없거나 복구 실패 시 GarminAuthRequired 발생.
    429 발생 시 GarminConnectTooManyRequestsError 그대로 전파.
    비밀번호 로그인은 웹 UI(/connect/garmin)에서만 처리.
    """
    if Garmin is None:
        raise ImportError("garminconnect 패키지가 필요합니다: pip install garminconnect")

    tokenstore = _tokenstore_path(config)

    if not tokenstore.exists():
        raise GarminAuthRequired(
            "Garmin 토큰 없음. /connect/garmin에서 로그인하세요."
        )

    oauth2_file = tokenstore / "oauth2_token.json"
    if not oauth2_file.exists():
        raise GarminAuthRequired(
            "Garmin 토큰 파일 없음. /connect/garmin에서 로그인하세요."
        )

    try:
        client = Garmin()
        client.login(tokenstore=str(tokenstore))
        return client
    except GarminConnectTooManyRequestsError:
        raise  # 429는 그대로 전파 — GarminAuthRequired로 감싸지 않음
    except Exception as e:
        raise GarminAuthRequired(
            f"Garmin 토큰 복구 실패: {e}. /connect/garmin에서 재로그인하세요."
        ) from e


def check_garmin_connection(config: dict) -> dict:
    """Garmin 연결 상태 확인 — garth 토큰 만료 여부까지 검사.

    Returns:
        {"ok": bool, "status": str, "detail": str}
    """
    tokenstore = _tokenstore_path(config)
    oauth2_file = tokenstore / "oauth2_token.json"

    if oauth2_file.exists():
        try:
            import garth as _garth
            g = _garth.Client()
            g.load(str(tokenstore))
            token = g.oauth2_token
            if token is None:
                raise ValueError("oauth2_token 없음")
            if token.refresh_expired:
                return {
                    "ok": False,
                    "status": "토큰 만료 (재로그인 필요)",
                    "detail": "refresh_token 만료. /connect/garmin에서 재로그인하세요.",
                }
            if token.expired:
                return {
                    "ok": True,
                    "status": "토큰 갱신 필요",
                    "detail": "access_token 만료, refresh_token 유효. 다음 sync 시 자동 갱신됩니다.",
                }
            return {
                "ok": True,
                "status": "연결됨",
                "detail": f"토큰 유효. tokenstore: {tokenstore}",
            }
        except Exception as e:
            return {
                "ok": False,
                "status": "토큰 손상",
                "detail": f"토큰 파일 읽기 실패: {e}. 재로그인 필요.",
            }

    if tokenstore.exists() and not oauth2_file.exists():
        return {
            "ok": False,
            "status": "토큰 없음",
            "detail": f"{tokenstore} 디렉터리만 존재. /connect/garmin에서 로그인하세요.",
        }

    return {
        "ok": False,
        "status": "미설정",
        "detail": "토큰 없음. /connect/garmin에서 연동하세요.",
    }
