"""신규 계정 프로비저닝 — 사용자 디렉터리·DB·빈 config 를 멱등하게 만든다(pending→active 전환 직전 1회)."""
from __future__ import annotations


def provision(uid: str) -> None:
    """디렉터리 + `init_db` + 기본 config. 이미 있으면 덮어쓰지 않는다. 실패는 호출자가 롤백한다."""
    from src.db_setup import init_db
    from src.utils.config import _default_config, get_config_path, save_config

    init_db(uid)
    if not get_config_path(uid).exists():
        save_config(_default_config(), user_id=uid)
