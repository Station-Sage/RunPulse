"""도구 CLI — `python -m src.ai.tool_cli <tool> '<json args>' [--user UID] [--db PATH]` (읽기 전용, 결과 JSON 출력)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.ai.tools import _DISPATCH, execute_tool


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="tool_cli", description=__doc__)
    ap.add_argument("tool", choices=sorted(_DISPATCH))
    ap.add_argument("args", nargs="?", default="{}")
    ap.add_argument("--user")
    ap.add_argument("--db")
    ns = ap.parse_args(argv)
    try:
        args = json.loads(ns.args)
    except ValueError as exc:
        print(json.dumps({"error": f"args JSON 오류: {exc}"}, ensure_ascii=False))
        return 2
    from src.mcp_remote.safe_conn import connect_readonly
    if ns.db:
        path = Path(ns.db)
    else:
        from src.mcp_server import resolve_db_path
        path = resolve_db_path(ns.user)
    conn = connect_readonly(path)
    try:
        print(execute_tool(conn, ns.tool, args))
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
