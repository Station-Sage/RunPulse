"""RunPulse MCP 서버 — Claude Desktop/CLI에서 러닝 데이터 직접 조회.

사용법:
  python src/mcp_server.py

Claude Desktop 설정 (claude_desktop_config.json):
  {
    "mcpServers": {
      "runpulse": {
        "command": "python",
        "args": ["src/mcp_server.py"],
        "cwd": "/path/to/RunPulse"
      }
    }
  }

제공 도구 10개: tools.py의 TOOL_DECLARATIONS와 동일.
"""
from __future__ import annotations

import json
import logging
import sqlite3
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
log = logging.getLogger("runpulse-mcp")

# DB 경로
_DB_PATH = Path(__file__).parent.parent / "data" / "users" / "default" / "running.db"


def _get_conn() -> sqlite3.Connection:
    """DB 연결."""
    if not _DB_PATH.exists():
        raise FileNotFoundError(f"DB not found: {_DB_PATH}")
    return sqlite3.connect(str(_DB_PATH))


def _read_message() -> dict | None:
    """stdin에서 JSON-RPC 메시지 읽기 (Content-Length 헤더)."""
    headers = {}
    while True:
        line = sys.stdin.readline()
        if not line or line.strip() == "":
            break
        if ":" in line:
            key, val = line.split(":", 1)
            headers[key.strip().lower()] = val.strip()

    length = int(headers.get("content-length", 0))
    if length == 0:
        return None
    body = sys.stdin.read(length)
    return json.loads(body)


def _write_message(msg: dict) -> None:
    """stdout으로 JSON-RPC 메시지 쓰기."""
    body = json.dumps(msg, ensure_ascii=False)
    sys.stdout.write(f"Content-Length: {len(body.encode())}\r\n\r\n{body}")
    sys.stdout.flush()


def _handle_initialize(req: dict) -> dict:
    """MCP initialize."""
    return {
        "jsonrpc": "2.0",
        "id": req["id"],
        "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {
                "name": "runpulse",
                "version": "1.0.0",
            },
        },
    }


def _handle_tools_list(req: dict) -> dict:
    """도구 목록 반환."""
    from src.ai.tools import TOOL_DECLARATIONS

    tools = []
    for decl in TOOL_DECLARATIONS:
        tools.append({
            "name": decl["name"],
            "description": decl["description"],
            "inputSchema": decl["parameters"],
        })
    return {
        "jsonrpc": "2.0",
        "id": req["id"],
        "result": {"tools": tools},
    }


def _handle_tools_call(req: dict) -> dict:
    """도구 실행."""
    from src.ai.tools import execute_tool

    params = req.get("params", {})
    name = params.get("name", "")
    args = params.get("arguments", {})

    try:
        conn = _get_conn()
        try:
            result_json = execute_tool(conn, name, args)
        finally:
            conn.close()
    except Exception as exc:
        result_json = json.dumps({"error": str(exc)}, ensure_ascii=False)

    return {
        "jsonrpc": "2.0",
        "id": req["id"],
        "result": {
            "content": [{"type": "text", "text": result_json}],
        },
    }


def main() -> None:
    """MCP 서버 메인 루프 (stdio)."""
    log.info("RunPulse MCP 서버 시작 (DB: %s)", _DB_PATH)

    while True:
        try:
            msg = _read_message()
        except (EOFError, KeyboardInterrupt):
            break
        if msg is None:
            break

        method = msg.get("method", "")
        log.info("← %s (id=%s)", method, msg.get("id"))

        if method == "initialize":
            resp = _handle_initialize(msg)
        elif method == "initialized":
            continue  # notification, no response
        elif method == "tools/list":
            resp = _handle_tools_list(msg)
        elif method == "tools/call":
            resp = _handle_tools_call(msg)
        elif method == "notifications/cancelled":
            continue
        else:
            resp = {
                "jsonrpc": "2.0",
                "id": msg.get("id"),
                "error": {"code": -32601, "message": f"Unknown method: {method}"},
            }

        _write_message(resp)
        log.info("→ response sent")


if __name__ == "__main__":
    main()
