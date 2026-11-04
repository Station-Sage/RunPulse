"""초대코드 발급·조회 CLI — `python3 scripts/auth_invite.py issue [--uses N] [--days D] [--note ..]` / `list`."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.auth import invites, registry  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("issue")
    p.add_argument("--uses", type=int, default=1)
    p.add_argument("--days", type=int, default=14)
    p.add_argument("--note")
    sub.add_parser("list")
    a = ap.parse_args(argv)
    conn = registry.connect()
    if a.cmd == "issue":
        code, iid = invites.issue(conn, max_uses=a.uses, expires_days=a.days or None, note=a.note)
        print(f"코드: {code}  (id={iid}, 사용 {a.uses}회, {a.days}일) — 평문은 지금만 확인 가능")
    else:
        for r in invites.list_invites(conn):
            print(r)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
