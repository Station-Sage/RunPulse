"""MCP JSON-RPC 처리 코어 — 전송(stdio/HTTP)과 무관. 연결 팩토리·허용 도구 집합을 주입받는다."""
from __future__ import annotations

import json
import logging
import sqlite3
from typing import Callable, Iterable

log = logging.getLogger("runpulse-mcp")

SUPPORTED_VERSIONS = ("2025-06-18", "2025-03-26", "2024-11-05")
GENERIC_TOOL_ERROR = json.dumps({"error": "도구 실행 실패"}, ensure_ascii=False)

ConnFactory = Callable[[], sqlite3.Connection]


def negotiate_version(requested: str | None) -> str:
    """클라이언트 요청 버전이 지원 목록에 있으면 그대로, 아니면 서버 최신."""
    return requested if requested in SUPPORTED_VERSIONS else SUPPORTED_VERSIONS[0]


def _ok(req: dict, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": req["id"], "result": result}


def _declarations(allowed: frozenset[str] | None) -> list[dict]:
    from src.ai.tools import TOOL_DECLARATIONS

    return [d for d in TOOL_DECLARATIONS if allowed is None or d["name"] in allowed]


def _initialize(req: dict) -> dict:
    from src.ai.tool_guide import USAGE_GUIDE

    version = negotiate_version((req.get("params") or {}).get("protocolVersion"))
    return _ok(req, {
        "protocolVersion": version,
        "capabilities": {"tools": {}},
        "serverInfo": {"name": "runpulse", "version": "1.1.0"},
        "instructions": USAGE_GUIDE,
    })


def _tools_list(req: dict, allowed: frozenset[str] | None) -> dict:
    tools = [{"name": d["name"], "description": d["description"], "inputSchema": d["parameters"]}
             for d in _declarations(allowed)]
    return _ok(req, {"tools": tools})


def _tools_call(req: dict, connect: ConnFactory, allowed: frozenset[str] | None,
                generic_errors: bool) -> dict:
    from src.ai.tools import execute_tool

    params = req.get("params") or {}
    name = params.get("name", "")
    args = params.get("arguments") or {}
    if allowed is not None and name not in allowed:
        text = json.dumps({"error": f"알 수 없는 도구: {name}"}, ensure_ascii=False)
        return _ok(req, {"content": [{"type": "text", "text": text}], "isError": True})
    try:
        conn = connect()
        try:
            text = execute_tool(conn, name, args)
        finally:
            conn.close()
        is_error = text.startswith('{"error":')
        if is_error and generic_errors:
            text = GENERIC_TOOL_ERROR
    except Exception as exc:
        log.warning("도구 호출 실패 (%s): %s", name, exc)
        text = GENERIC_TOOL_ERROR if generic_errors else json.dumps({"error": str(exc)}, ensure_ascii=False)
        is_error = True
    return _ok(req, {"content": [{"type": "text", "text": text}], "isError": is_error})


def handle_message(msg: dict, connect: ConnFactory, *, allowed: Iterable[str] | None = None,
                   generic_errors: bool = False) -> dict | None:
    """메시지 하나 처리. 알림(id 없음)이면 None."""
    allowed_set = None if allowed is None else frozenset(allowed)
    method = msg.get("method", "")
    if method == "initialize":
        return _initialize(msg)
    if method == "tools/list":
        return _tools_list(msg, allowed_set)
    if method == "tools/call":
        return _tools_call(msg, connect, allowed_set, generic_errors)
    if method == "ping":
        return _ok(msg, {})
    if "id" not in msg:
        return None
    return {"jsonrpc": "2.0", "id": msg["id"],
            "error": {"code": -32601, "message": f"Unknown method: {method}"}}
