"""원격 MCP 토큰 관리 CLI — 컨테이너 안에서 실행: docker compose exec runpulse python scripts/mcp_token.py ...

issue --user <id> --label <name> [--days 90] | list --user <id> [--all] | revoke <token_id> | revoke --user <id> --all | audit [--user <id>] [--since YYYY-MM-DD] [--limit N]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.mcp_remote import audit, token_index as ti  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("issue")
    p.add_argument("--user", required=True)
    p.add_argument("--label", required=True)
    p.add_argument("--days", type=int, default=ti.DEFAULT_DAYS)
    p = sub.add_parser("list")
    p.add_argument("--user", required=True)
    p.add_argument("--all", action="store_true", help="폐기·만료 포함")
    p = sub.add_parser("revoke")
    p.add_argument("token_id", nargs="?")
    p.add_argument("--user")
    p.add_argument("--all", action="store_true")
    p = sub.add_parser("audit")
    p.add_argument("--user")
    p.add_argument("--since")
    p.add_argument("--limit", type=int, default=50)
    a = ap.parse_args(argv)

    if a.cmd == "audit":
        for r in audit.query(a.user, a.since, a.limit):
            print(f"{r['ts']}  {r['user_id']}  {r['token_id']}  {r['method']}  {r['tool'] or '-'}  "
                  f"{r['status']}  {r['latency_ms']}ms  {r['resp_bytes']}B  {r['ip_hash']}")
        return 0

    if a.cmd == "issue":
        try:
            token, meta = ti.issue(a.user, a.label, a.days)
        except ti.TokenError as e:
            print(f"오류: {e}", file=sys.stderr)
            return 1
        print(f"{meta['token_id']}  만료 {meta['expires_at']}  (아래 토큰은 다시 볼 수 없습니다)")
        print(token)
        return 0
    if a.cmd == "list":
        for t in ti.list_tokens(a.user, a.all):
            state = "폐기" if t["revoked_at"] else "활성"
            print(f"{t['token_id']}  {state}  {t['label']}  ••••{t['last4']}  "
                  f"만료 {t['expires_at']}  최근 {t['last_used_at']}")
        return 0
    if a.all and a.user:
        print(f"{ti.revoke_all(a.user)}개 폐기")
        return 0
    if a.token_id and not a.all:
        ok = ti.revoke(a.token_id)
        print("폐기됨" if ok else "대상 없음")
        return 0 if ok else 1
    print("revoke <token_id> 또는 revoke --user <id> --all", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
