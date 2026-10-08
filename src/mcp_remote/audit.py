"""원격 MCP 호출 감사(mcp_audit) 기록·정리·조회, IP 해시. 토큰·원문 IP는 저장하지 않는다."""
from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
import threading
import time

from src.mcp_remote.token_index import connect

RETENTION_DAYS = 90
ARGS_MAX = 500
_SALT = secrets.token_hex(8)  # 프로세스 수명 동안만 상관 가능(재시작 시 변경)
_lock = threading.Lock()
_last_purge_day = ""


def ip_hash(ip: str) -> str:
    return hashlib.sha256(f"{_SALT}|{ip}".encode()).hexdigest()[:16]


def record(*, token_id: str | None, user_id: str | None, method: str | None, tool: str | None,
           args: dict | None, status: str, latency_ms: int = 0, resp_bytes: int = 0,
           ip: str = "") -> None:
    """한 요청 1행. 실패해도 요청 처리를 막지 않는다."""
    args_json = None
    if args:
        args_json = json.dumps(args, ensure_ascii=False, default=str)[:ARGS_MAX]
    try:
        conn = connect()
        try:
            with conn:
                conn.execute(
                    "INSERT INTO mcp_audit (token_id,user_id,method,tool,args_json,status,"
                    "latency_ms,resp_bytes,ip_hash) VALUES (?,?,?,?,?,?,?,?,?)",
                    (token_id, user_id, method, tool, args_json, status, latency_ms,
                     resp_bytes, ip_hash(ip) if ip else None))
        finally:
            conn.close()
    except sqlite3.Error:
        pass
    _purge_daily()


def purge(days: int = RETENTION_DAYS) -> int:
    conn = connect()
    try:
        with conn:
            return conn.execute(
                "DELETE FROM mcp_audit WHERE ts < datetime('now', ?)", (f"-{int(days)} days",)).rowcount
    finally:
        conn.close()


def _purge_daily() -> None:
    global _last_purge_day
    today = time.strftime("%Y-%m-%d")
    with _lock:
        if _last_purge_day == today:
            return
        _last_purge_day = today
    try:
        purge()
    except sqlite3.Error:
        pass


def query(user_id: str | None = None, since: str | None = None, limit: int = 50) -> list[dict]:
    sql, args = "SELECT * FROM mcp_audit WHERE 1=1", []
    if user_id:
        sql += " AND user_id=?"
        args.append(user_id)
    if since:
        sql += " AND ts >= ?"
        args.append(since)
    conn = connect()
    try:
        rows = conn.execute(sql + " ORDER BY id DESC LIMIT ?", (*args, int(limit))).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]
