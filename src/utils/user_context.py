"""사용자 컨텍스트 — request context 없는 스레드/subprocess에서 user_id를 해석한다.

우선순위: 함수 인자 → threading.local(`set_current_user`) → Flask 세션 → "default".
요청 핸들러·서비스는 user_id를 인자로 넘기고, 깊은 공급자 코드만 스레드 로컬 폴백을 쓴다.
"""
from __future__ import annotations

import threading

_LOCAL = threading.local()


def set_current_user(user_id: str) -> None:
    """bg_sync 스레드·subprocess 시작 시 호출 — request context 없는 환경에서 user_id 설정."""
    _LOCAL.user_id = user_id


def resolve_user_id(user_id: str | None = None) -> str:
    """user_id 해석: 인자 → thread-local → Flask session → 'default'."""
    if user_id:
        return user_id
    uid = getattr(_LOCAL, "user_id", None)
    if uid:
        return uid
    try:
        from src.web.helpers import get_current_user_id
        return get_current_user_id()
    except Exception:
        return "default"
