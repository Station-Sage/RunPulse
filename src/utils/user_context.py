"""사용자 컨텍스트 — request context 없는 스레드/subprocess에서 user_id를 해석한다.

우선순위: 함수 인자 → threading.local(`set_current_user`) → Flask 세션 → "default".
공용 3함수(`project_root`·`get_current_user_id`·`db_path`)도 여기에 둔다(V1S-2 — `src/web/helpers.py` 에서 이관).
요청 핸들러·서비스는 user_id를 인자로 넘기고, 깊은 공급자 코드만 스레드 로컬 폴백을 쓴다.
"""
from __future__ import annotations

import threading
from pathlib import Path

_LOCAL = threading.local()


def set_current_user(user_id: str) -> None:
    """bg_sync 스레드·subprocess 시작 시 호출 — request context 없는 환경에서 user_id 설정."""
    _LOCAL.user_id = user_id


def set_current_job(job_id: str | None) -> None:
    """현재 스레드가 처리 중인 원장 작업 id — 게이트 기록 등에서 job_id 연결용."""
    _LOCAL.job_id = job_id


def current_job() -> str | None:
    return getattr(_LOCAL, "job_id", None)


def resolve_user_id(user_id: str | None = None) -> str:
    """user_id 해석: 인자 → thread-local → Flask session → 'default'."""
    if user_id:
        return user_id
    uid = getattr(_LOCAL, "user_id", None)
    if uid:
        return uid
    try:
        return get_current_user_id()
    except ImportError:  # flask 미설치 환경(CLI·분석 스크립트)
        return "default"


def project_root() -> Path:
    """저장소 루트 경로."""
    return Path(__file__).resolve().parent.parent.parent


def get_current_user_id() -> str:
    """현재 Flask 요청의 사용자 ID를 반환. 세션 없으면 'default'."""
    try:
        from flask import session
        return session.get("user_id", "default")
    except RuntimeError:
        # Flask 앱 컨텍스트 밖 (CLI 등)
        return "default"


def db_path(user_id: str | None = None) -> Path:
    """사용자별 running.db 경로. user_id 미지정 시 Flask 세션에서 추출."""
    from src.db_setup import get_db_path
    uid = user_id or get_current_user_id()
    return get_db_path(uid)
