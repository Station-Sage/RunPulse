"""Garmin Connect 인증 — garminconnect 0.3.x 네이티브 DI OAuth."""
from __future__ import annotations

import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)

try:
    from garminconnect import Garmin
    try:
        from garminconnect.exceptions import (
            GarminConnectTooManyRequestsError,
            GarminConnectAuthenticationError,
            GarminConnectConnectionError,
        )
    except ImportError:
        class GarminConnectTooManyRequestsError(Exception):
            """garminconnect 미설치 시 placeholder."""
            pass
        class GarminConnectAuthenticationError(Exception):
            pass
        class GarminConnectConnectionError(Exception):
            pass
except ImportError:
    Garmin = None
    class GarminConnectTooManyRequestsError(Exception):
        """garminconnect 미설치 시 placeholder."""
        pass
    class GarminConnectAuthenticationError(Exception):
        pass
    class GarminConnectConnectionError(Exception):
        pass


class GarminAuthRequired(Exception):
    """Garmin 토큰이 없거나 만료되어 웹 UI에서 재인증이 필요할 때."""
    pass


def _tokenstore_path(config: dict) -> Path:
    """멀티유저 토큰 디렉터리 결정."""
    garmin_cfg = config.get("garmin", {})
    from src.utils.config import get_config_path

    # 1) 명시적 경로 — 항상 그대로 사용
    explicit = garmin_cfg.get("tokenstore", "")
    if explicit:
        return Path(explicit).expanduser()

    # 2) data/users/{user_id}/.garminconnect/
    user_id = garmin_cfg.get("user_id", "")
    if user_id:
        return get_config_path(user_id).parent / ".garminconnect"

    # 3) 기본 (default 사용자)
    return get_config_path().parent / ".garminconnect"


def _token_file(config: dict) -> Path:
    return _tokenstore_path(config) / "garmin_tokens.json"


def _login(config: dict) -> "Garmin":
    """Garmin Connect 인증 — 토큰 기반만 허용.

    토큰이 없거나 복구 실패 시 GarminAuthRequired 발생.
    429 발생 시 GarminConnectTooManyRequestsError 그대로 전파.
    비밀번호 로그인은 웹 UI(/connect/garmin)에서만 처리.
    """
    if Garmin is None:
        raise ImportError(
            "garminconnect 패키지 필요: pip install garminconnect curl_cffi ua-generator"
        )

    tokenstore = _tokenstore_path(config)
    token_file = tokenstore / "garmin_tokens.json"
    log.info("[garmin_auth] tokenstore=%s, token_file_exists=%s", tokenstore, token_file.exists())

    if not token_file.exists():
        log.warning("[garmin_auth] 토큰 파일 없음: %s", token_file)
        raise GarminAuthRequired(
            "Garmin 토큰 없음. /connect/garmin에서 로그인하세요."
        )

    # 토큰 파일 기본 유효성 체크
    try:
        import json as _json
        with open(token_file) as _f:
            _tok = _json.load(_f)
        _has_access = bool(
            _tok.get("access_token")
            or _tok.get("di_access_token")
            or (isinstance(_tok.get("oauth2_token"), dict) and _tok["oauth2_token"].get("access_token"))
        )
        log.info("[garmin_auth] 토큰 파일 읽기 OK — keys=%s, has_access_token=%s",
                 list(_tok.keys())[:6], _has_access)
    except Exception as _te:
        log.warning("[garmin_auth] 토큰 파일 파싱 실패: %s", _te)

    try:
        log.info("[garmin_auth] Garmin().login(tokenstore=%s) 시작", tokenstore)
        client = Garmin()
        client.login(tokenstore=str(tokenstore))
        log.info("[garmin_auth] 로그인 성공")
        # 로그인 성공 시 갱신된 토큰 자동 저장
        try:
            client.client.dump(str(tokenstore))
            log.debug("[garmin_auth] 갱신 토큰 저장 완료")
        except Exception as _de:
            log.debug("[garmin_auth] 토큰 dump 실패(무시): %s", _de)
        return client
    except GarminConnectTooManyRequestsError:
        log.warning("[garmin_auth] 로그인 중 429 발생")
        raise  # 429는 그대로 전파
    except (GarminConnectAuthenticationError, GarminConnectConnectionError) as e:
        log.error("[garmin_auth] 인증/연결 오류: %s", e)
        raise GarminAuthRequired(f"Garmin 토큰 복구 실패: {e}. /connect/garmin에서 재로그인하세요.") from e
    except Exception as e:
        log.error("[garmin_auth] 예상치 못한 오류: %s", e)
        raise GarminAuthRequired(
            f"Garmin 토큰 복구 실패: {e}. /connect/garmin에서 재로그인하세요."
        ) from e


def check_garmin_connection(config: dict) -> dict:
    """Garmin 연결 상태 확인 — garmin_tokens.json 기반.

    Returns:
        {"ok": bool, "status": str, "detail": str}
    """
    tokenstore = _tokenstore_path(config)
    token_file = tokenstore / "garmin_tokens.json"

    if not token_file.exists():
        if tokenstore.exists():
            # 구 garth 토큰 감지 — 마이그레이션 안내
            old_oauth2 = tokenstore / "oauth2_token.json"
            if old_oauth2.exists():
                return {
                    "ok": False,
                    "status": "garth 토큰 감지 (마이그레이션 필요)",
                    "detail": "이전 garth 토큰이 존재합니다. /connect/garmin에서 재로그인하세요.",
                }
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

    # 토큰 파일 존재 — JSON 파싱으로 기본 유효성 확인
    try:
        with open(token_file) as f:
            token_data = json.load(f)
        # garminconnect 0.3.x: di_token (DI OAuth) 또는 oauth2_token (레거시)
        has_oauth2 = bool(
            token_data.get("access_token")
            or token_data.get("di_access_token")
            or token_data.get("di_token")
            or (isinstance(token_data.get("oauth2_token"), dict) and token_data["oauth2_token"].get("access_token"))
        )
        if not has_oauth2:
            return {
                "ok": False,
                "status": "토큰 손상",
                "detail": "토큰 파일에 유효한 access_token 없음. 재로그인 필요.",
            }
        return {
            "ok": True,
            "status": "연결됨",
            "detail": f"토큰 유효. tokenstore: {tokenstore}",
        }
    except (json.JSONDecodeError, IOError) as e:
        return {
            "ok": False,
            "status": "토큰 손상",
            "detail": f"토큰 파일 읽기 실패: {e}. 재로그인 필요.",
        }
