"""`/api/v1/data/sources/garmin/*` — Garmin 비밀번호 로그인·MFA·토큰 붙여넣기·로컬 동기화 키트. 설계: garmin-connect.md §3.4·§3.5.

모든 응답 `Cache-Control: no-store`. 요청 본문은 로깅하지 않는다. 해제·연결 테스트는 routes_data 공통 라우트를 쓴다.
"""
from __future__ import annotations

from pathlib import Path

from flask import make_response, request, send_file

from src.services import garmin_connect_service as svc
from src.utils import rate_window
from src.utils.config import load_config
from src.utils.user_context import get_current_user_id

from . import api_bp, api_error, api_ok

_WINDOW_LOGIN, _WINDOW_MFA = 900, 300
_LIMIT_MSG = "시도가 너무 많아요. 잠시 후 다시 시도해 주세요"
_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "garmin_local_sync.py"


def _no_store(resp):
    body, status = resp if isinstance(resp, tuple) else (resp, resp.status_code)
    body.headers["Cache-Control"] = "no-store"
    return body, status


def _client_ip() -> str:
    return (request.headers.get("CF-Connecting-IP") or request.remote_addr or "?").strip()


def _within(*limits: tuple[str, int, int]) -> bool:
    return all(rate_window.hit(key, n, window) for key, n, window in limits)


def _limited(window: int):
    resp, status = api_error("RATE_LIMITED", _LIMIT_MSG, 429)
    resp.headers["Retry-After"] = str(window)
    return _no_store((resp, status))


def _respond(data, fail):
    if fail is None:
        return _no_store(api_ok(data))
    resp, status = api_error(fail.code, fail.message, fail.status, fail.details)
    if fail.retry_after:
        resp.headers["Retry-After"] = str(fail.retry_after)
    return _no_store((resp, status))


def _body() -> dict:
    body = request.get_json(silent=True)
    return body if isinstance(body, dict) else {}


@api_bp.post("/data/sources/garmin/connect")
def garmin_connect():
    uid = get_current_user_id()
    if not _within((f"garmin:login:uid:{uid}", 5, _WINDOW_LOGIN), (f"garmin:login:ip:{_client_ip()}", 10, _WINDOW_LOGIN)):
        return _limited(_WINDOW_LOGIN)
    body = _body()
    return _respond(*svc.start_login(uid, body.get("email"), body.get("password")))


@api_bp.post("/data/sources/garmin/mfa")
def garmin_mfa():
    uid = get_current_user_id()
    if not _within((f"garmin:mfa:uid:{uid}", 10, _WINDOW_MFA)):
        return _limited(_WINDOW_MFA)
    body = _body()
    return _respond(*svc.complete_mfa(uid, body.get("mfa_ticket"), body.get("code")))


@api_bp.post("/data/sources/garmin/mfa/cancel")
def garmin_mfa_cancel():
    return _respond(svc.cancel(get_current_user_id()), None)


@api_bp.post("/data/sources/garmin/token")
def garmin_token():
    uid = get_current_user_id()
    if not _within((f"garmin:token:uid:{uid}", 10, _WINDOW_LOGIN)):
        return _limited(_WINDOW_LOGIN)
    return _respond(*svc.submit_token(uid, _body().get("token_json")))


@api_bp.get("/data/sources/garmin/local-kit/script")
def garmin_local_kit_script():
    resp = send_file(_SCRIPT, as_attachment=True, download_name="garmin_local_sync.py", mimetype="text/x-python")
    resp.headers["Cache-Control"] = "no-store"
    return resp


def local_env_text(user_id: str, email: str, cf_client_id: str) -> str:
    """로컬 동기화 `.env` — CF secret 은 빈칸(전역 비밀, R8). 비밀번호 줄은 주석."""
    lines = [
        "# Garmin 로컬 동기화 설정 — garmin_local_sync.py",
        f"RUNPULSE_USER_ID={user_id}",
        f"GARMIN_EMAIL={email or 'your@email.com'}",
        "# GARMIN_PASSWORD=  # 첫 실행 후 스크립트가 자동 저장 제안",
        "# GARMIN_TOKENSTORE=  # 기본값: 스크립트 위치/.garminconnect",
        f"CF_SERVICE_CLIENT_ID={cf_client_id}",
        "CF_SERVICE_CLIENT_SECRET=  # 운영자에게 받아 직접 입력",
        "# GARMIN_VPS_URL=  # 기본값: https://runpulse.stationsage.dev",
    ]
    return "\n".join(lines) + "\n"


@api_bp.get("/data/sources/garmin/local-kit/env")
def garmin_local_kit_env():
    uid = get_current_user_id()
    email = load_config(user_id=uid).get("garmin", {}).get("email", "")
    cf_id = load_config(user_id="default").get("cf", {}).get("service_client_id", "")
    resp = make_response(local_env_text(uid, email, cf_id))
    resp.headers["Content-Type"] = "text/plain; charset=utf-8"
    resp.headers["Content-Disposition"] = "attachment; filename=.env"
    resp.headers["Cache-Control"] = "no-store"
    return resp
