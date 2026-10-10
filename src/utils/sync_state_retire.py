"""sync_state.json 퇴역 이관 — 미래의 retry_after만 sync_gates로 옮긴다 (--restore: 이름 원복)."""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

RENAME_ENABLED = True  # sync_state.py 삭제(R5) 후 구 코드는 파일을 쓰지 않는다


def _users_dir() -> Path:
    from src.db_setup import _PROJECT_ROOT
    return _PROJECT_ROOT / "data" / "users"


def _migrate_gates(user_id: str, state: dict) -> int:
    from src.utils.sync_gates import gate, _put
    moved = 0
    now = datetime.now()
    for service, st in state.items():
        ra = st.get("retry_after") if isinstance(st, dict) else None
        if not ra:
            continue
        try:
            remain = int((datetime.fromisoformat(ra) - now).total_seconds())
        except ValueError:
            continue
        if remain > 0 and gate(service, user_id) is None:
            _put(service, remain, "rate_limited", user_id)
            moved += 1
    return moved


def retire_all_users() -> int:
    """모든 사용자의 sync_state.json에서 활성 게이트를 이관. 이관 건수 반환. 멱등."""
    root = _users_dir()
    if not root.is_dir():
        return 0
    total = 0
    for d in sorted(root.iterdir()):
        f = d / "sync_state.json"
        if not f.is_file():
            continue
        try:
            total += _migrate_gates(d.name, json.loads(f.read_text(encoding="utf-8")))
            if RENAME_ENABLED:
                f.rename(d / f"sync_state.json.retired-{datetime.now():%Y%m%d}")
        except Exception:
            continue
    return total


def restore_all_users() -> int:
    """이름 바꾼 sync_state.json.retired-* 를 원복. 원복 건수 반환."""
    root = _users_dir()
    if not root.is_dir():
        return 0
    n = 0
    for d in sorted(root.iterdir()):
        target = d / "sync_state.json"
        olds = sorted(d.glob("sync_state.json.retired-*"))
        if olds and not target.exists():
            olds[-1].rename(target)
            n += 1
    return n


if __name__ == "__main__":
    print(restore_all_users() if "--restore" in sys.argv else retire_all_users())
