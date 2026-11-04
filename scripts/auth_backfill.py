"""기존 data/users 디렉터리를 계정 레지스트리(data/auth.db)에 active 로 등록한다. 기본은 dry-run.

사용: python3 scripts/auth_backfill.py [--apply] [--exclude uid ...]
이메일 형태가 아니거나 @example.* 인 디렉터리는 건너뛰고, email_norm 충돌은 보고만 한다.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.auth import registry  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="실제로 기록(기본 dry-run)")
    ap.add_argument("--exclude", nargs="*", default=[], help="제외할 uid")
    a = ap.parse_args()
    conn = registry.connect()
    try:
        r = registry.backfill(conn, apply=a.apply, exclude=tuple(a.exclude))
    finally:
        conn.close()
    print(f"[{'APPLY' if a.apply else 'DRY-RUN'}] 등록 {len(r['backfilled'])} / 건너뜀 {len(r['skipped'])} / 충돌 {len(r['collided'])}")
    for k in ("backfilled", "skipped", "collided"):
        for uid in r[k]:
            print(f"  {k}: {uid}")
    return 1 if r["collided"] else 0


if __name__ == "__main__":
    sys.exit(main())
