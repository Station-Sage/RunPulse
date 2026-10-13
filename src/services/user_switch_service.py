"""개발용 사용자 전환 서비스 — v1 `/switch-user` 이관 (SRV 2.5, V1-3 (b)·V1-8·V1-9).

- 사용자 목록: `data/users` 하위 디렉터리 중 uid 규칙(SRV-13)에 맞는 이름.
- 전환: `validate_uid` → `init_db(uid)` 성공 후에만 세션을 바꾼다(v1 은 세션을 먼저 바꿔 DB 초기화가
  실패하면 깨진 사용자로 남을 수 있었다). 규칙 위반은 `InvalidUserId`(호출 측이 400 으로 변환).
- 운영 차단: production(`APP_ENV == "production"`)에서는 사용할 수 없다(`dev_switch_enabled`) — 라우트가 404.
Flask 무의존: 세션은 매핑 인자로 받는다.
"""
from __future__ import annotations

import os
from collections.abc import MutableMapping

from src.utils.user_context import list_user_ids, validate_uid

SESSION_KEY = "user_id"


def dev_switch_enabled() -> bool:
    """production 이 아닐 때만 사용자 전환을 허용한다(호출 시점의 `APP_ENV` 판정)."""
    return os.environ.get("APP_ENV", "development").lower() != "production"


def list_users() -> list[str]:
    """전환 가능한 사용자 목록(정렬). `data/users` 가 비어 있으면 `default` 하나."""
    return list_user_ids(log_skipped=False) or ["default"]


def switch_user(uid: str, session: MutableMapping) -> str:
    """`uid` 로 전환한다 — 규칙 검증 → DB 초기화 → 세션 기록. 반환은 검증된 uid.

    새 uid 면 `data/users/<uid>` 가 만들어진다(v1 과 같은 동작). 어느 단계든 실패하면 세션은 그대로다.
    """
    from src.db_setup import init_db
    validate_uid(uid)
    init_db(uid)
    session[SESSION_KEY] = uid
    return uid
