"""사용자 컨텍스트 — request context 없는 스레드/subprocess에서 user_id를 해석한다.

우선순위: 함수 인자 → threading.local(`set_current_user`) → Flask 세션 → "default".
공용 3함수(`project_root`·`get_current_user_id`·`db_path`)도 여기에 둔다(V1S-2 — `src/web/helpers.py` 에서 이관).
요청 핸들러·서비스는 user_id를 인자로 넘기고, 깊은 공급자 코드만 스레드 로컬 폴백을 쓴다.
"""
from __future__ import annotations

import logging
import re
import threading
from pathlib import Path

_LOCAL = threading.local()
_UID_RE = re.compile(r"[A-Za-z0-9._%+@-]{1,254}")  # fullmatch 로만 쓴다 — `$` 는 끝의 개행 1개를 허용
_security_log = logging.getLogger("runpulse.security")


class InvalidUserId(ValueError):
    """uid 허용 규칙(SRV-13) 위반. 메시지·속성에 원문을 싣지 않는다(`masked` 만) — 로그·응답 유출 방지."""

    def __init__(self, masked: str):
        super().__init__("invalid user id")
        self.masked = masked


def mask_uid(value: object) -> str:
    """보안 로그용 마스킹 — 앞 2자 + 길이만 남긴다(S3-2). 이메일 원문·경로 조각을 기록하지 않는다."""
    text = value if isinstance(value, str) else repr(value)
    return f"{text[:2]}***(len={len(text)})"


def validate_uid(uid: object) -> str:
    """사용자 ID 허용 규칙(SRV-13, 2.6): 이메일 호환 문자만 1~254자.

    값 `.`·`..`, 경로 구분자(`/`·`\\`), 선행 `.` 은 거부한다. 기존 형식(CF 이메일, `default`)은 통과한다.
    통과하면 입력을 그대로 돌려주고(정규화·공백 제거 없음), 위반하면 `InvalidUserId`(ValueError).
    Flask 무의존 순수 함수.
    """
    if not isinstance(uid, str) or not _UID_RE.fullmatch(uid) or uid.startswith("."):
        raise InvalidUserId(mask_uid(uid))
    return uid


def users_root() -> Path:
    """사용자 데이터 루트 `data/users`."""
    return project_root() / "data" / "users"


def list_user_ids(*, log_skipped: bool = True) -> list[str]:
    """`data/users` 하위 디렉터리 중 uid 규칙에 맞는 이름을 정렬해 반환한다(없으면 빈 목록).

    규칙 위반 디렉터리는 건너뛰고 마스킹해 `runpulse.security` 로그에 남긴다 — 하나가 있다고 시작 루프 전체가
    중단되지 않게 한다(S3-1: 운영 디렉터리 점검은 `scripts/check_user_dirs.py`).
    """
    root = users_root()
    if not root.is_dir():
        return []
    out: list[str] = []
    for d in sorted(root.iterdir()):
        if not d.is_dir():
            continue
        try:
            out.append(validate_uid(d.name))
        except InvalidUserId as exc:
            if log_skipped:
                _security_log.warning("[uid] 규칙 위반 사용자 디렉터리 건너뜀: %s", exc.masked)
    return out


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
    return get_db_path(uid)  # uid 규칙 위반이면 InvalidUserId
