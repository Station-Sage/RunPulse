from __future__ import annotations

"""Garmin Connect 인증 함수."""

from pathlib import Path

try:
    from garminconnect import Garmin
    try:
        from garminconnect import GarminConnectTooManyRequestsError
    except ImportError:
        GarminConnectTooManyRequestsError = Exception
except ImportError:  # 선택 의존성 — 테스트/Termux 환경 대응
    Garmin = None
    GarminConnectTooManyRequestsError = Exception


def _tokenstore_path(config: dict) -> Path:
    """garth 토큰 저장소 경로 반환. 기본: ~/.garth"""
    path_str = config.get("garmin", {}).get("tokenstore", "~/.garth")
    return Path(path_str).expanduser()


def _login(config: dict) -> "Garmin":
    """Garmin Connect 인증.

    순서:
    1. garth 토큰 저장소에서 세션 복구 시도
    2. 실패 시 이메일/패스워드 로그인 + 토큰 저장
    """
    if Garmin is None:
        raise ImportError("garminconnect 패키지가 필요합니다: pip install garminconnect")

    garmin_cfg = config.get("garmin", {})
    tokenstore = _tokenstore_path(config)

    if tokenstore.exists():
        try:
            client = Garmin()
            client.login(tokenstore=str(tokenstore))
            return client
        except Exception as e:
            print(f"[garmin] 토큰 복구 실패, 이메일/패스워드 로그인 시도: {e}")

    email = garmin_cfg.get("email", "")
    password = garmin_cfg.get("password", "")
    if not email or not password:
        raise ValueError(
            "Garmin 이메일/패스워드 미설정. config.json에 garmin.email/password를 입력하거나 "
            "웹 UI(/settings)에서 연동하세요."
        )

    client = Garmin(email, password)
    client.login()

    try:
        tokenstore.mkdir(parents=True, exist_ok=True)
        client.garth.dump(str(tokenstore))
        print(f"[garmin] 토큰 저장 완료: {tokenstore}")
    except Exception as e:
        print(f"[garmin] 토큰 저장 실패 (동기화는 계속됨): {e}")

    return client


def check_garmin_connection(config: dict) -> dict:
    """Garmin 연결 상태 확인 — garth 토큰 만료 여부까지 검사.

    Returns:
        {"ok": bool, "status": str, "detail": str}
    """
    tokenstore = _tokenstore_path(config)
    garmin_cfg = config.get("garmin", {})
    has_email = bool(garmin_cfg.get("email"))
    has_password = bool(garmin_cfg.get("password"))

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
                    "detail": "refresh_token 만료. /connect/garmin 에서 재로그인하세요.",
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
            "detail": f"{tokenstore} 디렉터리만 존재. /connect/garmin 에서 로그인하세요.",
        }

    if has_email and has_password:
        return {
            "ok": False,
            "status": "미로그인",
            "detail": "이메일/패스워드 설정됨. /connect/garmin 에서 '저장 + 연결 테스트'로 로그인하세요.",
        }
    return {
        "ok": False,
        "status": "미설정",
        "detail": "이메일/패스워드 미설정 및 토큰 없음. /connect/garmin 에서 연동하세요.",
    }
