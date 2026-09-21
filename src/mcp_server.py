"""RunPulse MCP 서버 — Claude Desktop/CLI 등 MCP 클라이언트에서 러닝 데이터 조회 (stdio, 읽기 전용).

사용법:
  RUNPULSE_USER_ID=<user_id> python3 -m src.mcp_server   # 프로젝트 루트에서 실행

Claude Code/Desktop 설정 예:
  {"mcpServers": {"runpulse": {
      "command": "python3", "args": ["-m", "src.mcp_server"], "cwd": "/path/to/RunPulse",
      "env": {"RUNPULSE_USER_ID": "<user_id>"}}}}

- RUNPULSE_USER_ID 필수. 미지정 시 시작하지 않는다 (과거에는 활동 0건인 default DB를
  조용히 열어 빈 결과만 돌려줬다).
- DB는 읽기 전용(mode=ro)으로 연다.
- 프레임: MCP stdio 사양대로 줄바꿈으로 구분된 JSON 한 줄 = 메시지 하나.
- 도구 목록은 TOOL_DECLARATIONS, 호출 규칙은 tool_guide.USAGE_GUIDE (initialize instructions).
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
import sys
from pathlib import Path

from src.utils.log_config import setup_logging
setup_logging(stderr=True)  # stdout은 MCP JSON-RPC 프로토콜 전용
log = logging.getLogger("runpulse-mcp")

_PROTOCOL_VERSION = "2024-11-05"


def resolve_db_path(user_id: str | None = None) -> Path:
    """RUNPULSE_USER_ID(또는 인자)로 유저 DB 경로를 결정. 없으면 명확한 오류."""
    from src.db_setup import get_db_path

    uid = (user_id if user_id is not None else os.environ.get("RUNPULSE_USER_ID", "")).strip()
    if not uid:
        raise RuntimeError("RUNPULSE_USER_ID 환경변수가 필요합니다 (data/users/ 아래 유저 ID).")
    if Path(uid).name != uid:
        raise RuntimeError(f"잘못된 RUNPULSE_USER_ID: {uid!r}")
    path = get_db_path(uid, create=False)
    if not path.exists():
        raise FileNotFoundError(f"DB not found: {path}")
    return path


def _get_conn(db_path: Path) -> sqlite3.Connection:
    """읽기 전용 연결. 도구는 조회만 하므로 쓰기 시도는 즉시 실패해야 한다."""
    return sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)


def _read_message() -> dict | None:
    """stdin에서 JSON-RPC 메시지 한 줄 읽기. EOF면 None."""
    while True:
        line = sys.stdin.readline()
        if not line:
            return None
        if line.strip():
            return json.loads(line)


def _write_message(msg: dict) -> None:
    """stdout으로 JSON-RPC 메시지 한 줄 쓰기 (메시지 내부 개행 금지)."""
    sys.stdout.write(json.dumps(msg, ensure_ascii=False, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def _handle_initialize(req: dict) -> dict:
    from src.ai.tool_guide import USAGE_GUIDE

    return {
        "jsonrpc": "2.0",
        "id": req["id"],
        "result": {
            "protocolVersion": _PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "runpulse", "version": "1.1.0"},
            "instructions": USAGE_GUIDE,
        },
    }


def _handle_tools_list(req: dict) -> dict:
    from src.ai.tools import TOOL_DECLARATIONS

    tools = [
        {"name": d["name"], "description": d["description"], "inputSchema": d["parameters"]}
        for d in TOOL_DECLARATIONS
    ]
    return {"jsonrpc": "2.0", "id": req["id"], "result": {"tools": tools}}


def _handle_tools_call(req: dict, db_path: Path) -> dict:
    from src.ai.tools import execute_tool

    params = req.get("params", {})
    name = params.get("name", "")
    args = params.get("arguments") or {}

    is_error = False
    try:
        conn = _get_conn(db_path)
        try:
            text = execute_tool(conn, name, args)
        finally:
            conn.close()
        is_error = text.startswith('{"error":')
    except Exception as exc:
        text = json.dumps({"error": str(exc)}, ensure_ascii=False)
        is_error = True

    return {
        "jsonrpc": "2.0",
        "id": req["id"],
        "result": {"content": [{"type": "text", "text": text}], "isError": is_error},
    }


def handle_request(msg: dict, db_path: Path) -> dict | None:
    """메시지 하나 처리. 알림(notification)이면 None."""
    method = msg.get("method", "")
    if method == "initialize":
        return _handle_initialize(msg)
    if method == "tools/list":
        return _handle_tools_list(msg)
    if method == "tools/call":
        return _handle_tools_call(msg, db_path)
    if method == "ping":
        return {"jsonrpc": "2.0", "id": msg["id"], "result": {}}
    if "id" not in msg:  # notifications/initialized, notifications/cancelled 등
        return None
    return {"jsonrpc": "2.0", "id": msg["id"],
            "error": {"code": -32601, "message": f"Unknown method: {method}"}}


def main() -> None:
    """MCP 서버 메인 루프 (stdio)."""
    try:
        db_path = resolve_db_path()
    except (RuntimeError, FileNotFoundError) as exc:
        log.error("%s", exc)
        sys.exit(2)
    log.info("RunPulse MCP 서버 시작 (DB: %s, read-only)", db_path)

    while True:
        try:
            msg = _read_message()
        except (KeyboardInterrupt, json.JSONDecodeError) as exc:
            if isinstance(exc, KeyboardInterrupt):
                break
            log.warning("잘못된 JSON 무시: %s", exc)
            continue
        if msg is None:
            break
        log.info("← %s (id=%s)", msg.get("method", ""), msg.get("id"))
        resp = handle_request(msg, db_path)
        if resp is not None:
            _write_message(resp)


if __name__ == "__main__":
    main()
