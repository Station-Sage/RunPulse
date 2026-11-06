"""Garmin 연결 쓰기 — 비밀번호 로그인·MFA 완료·토큰 붙여넣기·해제, 예외→오류코드 매핑. 설계: garmin-connect.md §3.

비밀번호는 요청 본문 → 지역 변수 → 라이브러리 호출로만 흐른다(config·로그·응답·대기 상태에 남기지 않음).
예외 원문은 응답에 싣지 않고 로그에는 예외 클래스명만 남긴다. 토큰 경로는 서버가 uid 로 계산한다
(`data/users/<uid>/.garminconnect`, default 는 루트 — `garmin_auth._tokenstore_path` 규칙 ②·③).
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path

from src.services import garmin_mfa_store as store
from src.utils import rate_window
from src.utils.config import load_config, update_service_config
from src.utils.user_context import validate_uid

log = logging.getLogger(__name__)

COOLDOWN_S = 900
EMAIL_MAX, PASSWORD_MAX, TOKEN_MAX = 254, 256, 16 * 1024
_CODE_RE = re.compile(r"\d{6,8}")
_TOKEN_KEYS = ("di_token", "di_refresh_token", "di_client_id")
MSG = {
    "connected": "연결됐어요",
    "auth": "이메일 또는 비밀번호가 맞지 않아요",
    "token_auth": "토큰으로 로그인하지 못했어요. 새로 발급한 토큰인지 확인해 주세요",
    "mfa_invalid": "인증 코드가 맞지 않아요. 다시 입력해 주세요",
    "mfa_expired": "시간이 지났어요. 다시 로그인해 주세요",
    "mfa_unavailable": "지금은 인증 코드 단계를 처리할 수 없어요. 관리자에게 알려 주세요",
    "rate_upstream": "Garmin이 잠시 막았어요. 15분 뒤 다시 시도해 주세요",
    "upstream": "Garmin에 연결하지 못했어요. 잠시 후 다시 시도해 주세요",
    "internal": "토큰을 저장하지 못했어요. 잠시 후 다시 시도해 주세요",
}


@dataclass
class Fail:
    code: str
    status: int
    message: str
    details: dict | None = None
    retry_after: int | None = None


def mask_email(email: str) -> str:
    """로그용 `a***@domain`."""
    local, _, domain = (email or "").partition("@")
    return f"{local[:1]}***@{domain}" if domain else "***"


def token_dir(user_id: str) -> Path:
    """사용자 토큰 디렉터리 — 요청 값이 아니라 검증된 uid 로만 계산한다(R6)."""
    from src.sync.garmin_auth import _tokenstore_path

    return _tokenstore_path({"garmin": {"user_id": validate_uid(user_id)}})


def _garmin_cls():
    """garminconnect.Garmin 지연 import — 미설치면 ImportError. 테스트는 이 함수를 교체한다."""
    from garminconnect import Garmin

    return Garmin


def _errors():
    from src.sync import garmin_auth as ga

    return ga.GarminConnectTooManyRequestsError, ga.GarminConnectAuthenticationError


def _cooldown_key(user_id: str) -> str:
    return f"garmin:cooldown:{user_id}"


def in_cooldown(user_id: str) -> bool:
    return rate_window.count(_cooldown_key(user_id), COOLDOWN_S) > 0


def _rate_fail(user_id: str, record: bool = True) -> Fail:
    if record and not in_cooldown(user_id):
        rate_window.hit(_cooldown_key(user_id), 1, COOLDOWN_S)
    return Fail("GARMIN_RATE_LIMITED", 503, MSG["rate_upstream"], retry_after=COOLDOWN_S)


def _map_exc(exc: Exception, user_id: str, where: str, auth_msg: str = MSG["auth"]) -> Fail:
    too_many, auth = _errors()
    log.warning("[garmin_connect] %s 실패: %s", where, type(exc).__name__)
    if isinstance(exc, too_many):
        return _rate_fail(user_id)
    if isinstance(exc, auth):
        return Fail("GARMIN_AUTH_FAILED", 401, auth_msg)
    return Fail("GARMIN_UPSTREAM", 502, MSG["upstream"])


def _new_client(*args, **kwargs):
    try:
        return _garmin_cls()(*args, **kwargs), None
    except ImportError:
        log.error("[garmin_connect] garminconnect 패키지 없음")
        return None, Fail("GARMIN_UPSTREAM", 503, MSG["upstream"])


def _persist(user_id: str, client, email: str | None) -> tuple[dict | None, Fail | None]:
    """토큰을 사용자 경로에 원자 저장(dump) 후 config 의 명시 tokenstore·과거 비밀번호를 비운다."""
    path = token_dir(user_id)
    try:
        client.client.dump(str(path))
    except OSError as exc:
        log.error("[garmin_connect] 토큰 저장 실패: %s", type(exc).__name__)
        return None, Fail("INTERNAL", 500, MSG["internal"])
    updates = {"tokenstore": "", "password": ""}
    if email:
        updates["email"] = email
    update_service_config("garmin", updates, user_id=user_id)
    return {"status": "connected", "message_ko": MSG["connected"]}, None


def _invalid(msg: str) -> Fail:
    return Fail("INVALID_PARAM", 400, msg)


def start_login(user_id: str, email: object, password: object) -> tuple[dict | None, Fail | None]:
    """비밀번호 로그인. 성공이면 토큰 저장, MFA 필요면 ticket 발급. 실패 시 기존 토큰·config 불변."""
    if not isinstance(email, str) or not email.strip() or len(email.strip()) > EMAIL_MAX:
        return None, _invalid("이메일을 확인해 주세요")
    if not isinstance(password, str) or not password or len(password) > PASSWORD_MAX:
        return None, _invalid("비밀번호를 확인해 주세요")
    email = email.strip()
    if in_cooldown(user_id):
        return None, _rate_fail(user_id, record=False)
    store.discard(user_id)
    client, fail = _new_client(email, password, return_on_mfa=True)
    del password
    if fail:
        return None, fail
    try:
        status, _ = client.login(tokenstore=None)  # 기존 토큰을 읽지 않는 새 로그인(R5)
    except Exception as exc:  # noqa: BLE001 — 라이브러리 예외 전부 코드로 매핑
        return None, _map_exc(exc, user_id, "login")
    finally:
        client.password = None  # needs_mfa 경로에서는 라이브러리가 비우지 않는다
    if status == "needs_mfa":
        if not store.is_available():
            return None, Fail("MFA_UNAVAILABLE", 503, MSG["mfa_unavailable"])
        ticket = store.put(user_id, client, email)
        log.info("[garmin_connect] MFA 대기 %s", mask_email(email))
        return {"status": "needs_mfa", "mfa_ticket": ticket, "expires_in": store.TTL_S}, None
    log.info("[garmin_connect] 로그인 성공 %s", mask_email(email))
    return _persist(user_id, client, email)


def complete_mfa(user_id: str, ticket: object, code: object) -> tuple[dict | None, Fail | None]:
    """MFA 코드 제출. 오답·429 는 대기 유지, 상류 오류는 폐기."""
    if not isinstance(ticket, str) or not ticket or len(ticket) > 128:
        return None, _invalid("인증 단계를 처음부터 다시 시작해 주세요")
    if not isinstance(code, str) or not _CODE_RE.fullmatch(code.strip()):
        return None, _invalid("인증 코드는 6~8자리 숫자예요")
    if not store.is_available():
        return None, Fail("MFA_UNAVAILABLE", 503, MSG["mfa_unavailable"])
    pending = store.claim(user_id, ticket)
    if pending is None:
        return None, Fail("MFA_EXPIRED", 410, MSG["mfa_expired"])
    too_many, auth = _errors()
    try:
        pending.client.resume_login(None, code.strip())
    except auth as exc:
        log.warning("[garmin_connect] MFA 오답: %s", type(exc).__name__)
        left = store.record_failure(user_id)
        if left <= 0:
            return None, Fail("MFA_EXPIRED", 410, MSG["mfa_expired"])
        return None, Fail("MFA_INVALID", 422, MSG["mfa_invalid"], {"attempts_left": left})
    except too_many as exc:
        store.release(user_id)
        return None, _map_exc(exc, user_id, "mfa")
    except Exception as exc:  # noqa: BLE001
        store.discard(user_id)
        return None, _map_exc(exc, user_id, "mfa")
    store.discard(user_id)
    return _persist(user_id, pending.client, pending.email)


def cancel(user_id: str) -> dict:
    """대기 상태 폐기(멱등)."""
    store.discard(user_id)
    return {"status": "disconnected"}


def parse_token(raw: object) -> tuple[dict | None, str | None]:
    """붙여넣은 garmin_tokens.json 검증 — 16KB 상한, 허용 키만 남김, di_token/di_refresh_token 필수(R10)."""
    if not isinstance(raw, str) or not raw.strip():
        return None, "토큰 JSON을 붙여넣어 주세요"
    if len(raw.encode("utf-8")) > TOKEN_MAX:
        return None, "토큰 JSON이 너무 커요(16KB 이하)"
    try:
        data = json.loads(raw)
    except ValueError:
        return None, "올바른 JSON이 아니에요. garmin_tokens.json 내용을 그대로 붙여넣어 주세요"
    if not isinstance(data, dict):
        return None, "올바른 토큰 형식이 아니에요"
    kept = {k: data[k] for k in _TOKEN_KEYS if isinstance(data.get(k), str) and data[k]}
    if not (kept.get("di_token") or kept.get("di_refresh_token")):
        return None, "di_token 또는 di_refresh_token이 필요해요(이전 형식 토큰은 지원하지 않아요)"
    return kept, None


def submit_token(user_id: str, raw: object) -> tuple[dict | None, Fail | None]:
    """토큰 붙여넣기 — 검증 로그인(인라인 JSON)을 통과한 경우에만 사용자 경로에 저장한다."""
    token, err = parse_token(raw)
    if err:
        return None, _invalid(err)
    client, fail = _new_client()
    if fail:
        return None, fail
    try:
        client.login(tokenstore=json.dumps(token))
    except Exception as exc:  # noqa: BLE001
        return None, _map_exc(exc, user_id, "token", MSG["token_auth"])
    return _persist(user_id, client, None)


def remove_tokens(user_id: str, config: dict | None = None) -> int:
    """해제 — 현재 설정이 가리키는 토큰 파일과 규칙 ② 경로의 토큰 파일 삭제, 대기 상태 폐기. 지운 파일 수 반환."""
    from src.sync.garmin_auth import _token_file

    store.discard(user_id)
    cfg = config if config is not None else load_config(user_id=user_id)
    targets = {_token_file(cfg), token_dir(user_id) / "garmin_tokens.json"}
    removed = 0
    for f in targets:
        try:
            if f.is_file() and not f.is_symlink():
                f.unlink()
                removed += 1
        except OSError as exc:
            log.warning("[garmin_connect] 토큰 삭제 실패: %s", type(exc).__name__)
    return removed
