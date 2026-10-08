"""원격 MCP Bearer 토큰 인덱스 (data/mcp_tokens.db) — 발급·목록·폐기·조회·사용 기록.

토큰 원문은 저장하지 않는다(sha256 해시만). 발급 시 1회만 반환.
설계: v0.3/data/phase-7-ui-renewal/ux-review-2026-09/DESIGN-MCP-REMOTE.md §2.2
"""
from __future__ import annotations

import hashlib
import re
import secrets
import sqlite3
from pathlib import Path

from src.db_setup import _PROJECT_ROOT, get_db_path

TOKEN_PREFIX = "rpmcp_"
TOKEN_RE = re.compile(r"^rpmcp_[A-Za-z0-9_-]{43}$")
MAX_ACTIVE_PER_USER = 5
DEFAULT_DAYS = 90
_TOUCH_INTERVAL_MIN = 10

_DDL = """
CREATE TABLE IF NOT EXISTS mcp_tokens (
    token_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, token_hash TEXT NOT NULL UNIQUE,
    label TEXT NOT NULL, scope TEXT NOT NULL DEFAULT 'read', last4 TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')), expires_at TEXT,
    revoked_at TEXT, last_used_at TEXT, last_client TEXT);
CREATE INDEX IF NOT EXISTS ix_mcp_tokens_user ON mcp_tokens(user_id);
CREATE TABLE IF NOT EXISTS mcp_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL DEFAULT (datetime('now')),
    token_id TEXT, user_id TEXT, method TEXT, tool TEXT, args_json TEXT,
    status TEXT NOT NULL, latency_ms INTEGER, resp_bytes INTEGER, ip_hash TEXT);
CREATE INDEX IF NOT EXISTS ix_mcp_audit_ts ON mcp_audit(ts);
"""


class TokenError(ValueError):
    """발급 거부(사용자 없음·상한 초과·잘못된 입력)."""


def index_path() -> Path:
    return _PROJECT_ROOT / "data" / "mcp_tokens.db"


def connect() -> sqlite3.Connection:
    p = index_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(p), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(_DDL)
    return conn


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _active_where() -> str:
    return "revoked_at IS NULL AND (expires_at IS NULL OR expires_at > datetime('now'))"


def issue(user_id: str, label: str, days: int | None = DEFAULT_DAYS) -> tuple[str, dict]:
    """토큰 발급 → (원문, 메타). 원문은 이후 복구 불가."""
    label = (label or "").strip()
    if not label or len(label) > 40:
        raise TokenError("라벨은 1~40자여야 합니다")
    if days is not None and not 1 <= days <= 365:
        raise TokenError("만료일은 1~365일이어야 합니다")
    if not get_db_path(user_id, create=False).exists():
        raise TokenError("존재하지 않는 사용자입니다")
    token = TOKEN_PREFIX + secrets.token_urlsafe(32)
    token_id = "mt_" + secrets.token_hex(6)
    conn = connect()
    try:
        with conn:
            conn.execute("BEGIN IMMEDIATE")
            n = conn.execute(
                f"SELECT COUNT(*) FROM mcp_tokens WHERE user_id=? AND {_active_where()}",
                (user_id,)).fetchone()[0]
            if n >= MAX_ACTIVE_PER_USER:
                raise TokenError(f"활성 토큰은 최대 {MAX_ACTIVE_PER_USER}개입니다")
            exp = f"datetime('now', '+{int(days)} days')" if days else "NULL"
            conn.execute(
                "INSERT INTO mcp_tokens (token_id,user_id,token_hash,label,last4,expires_at) "
                f"VALUES (?,?,?,?,?,{exp})",
                (token_id, user_id, hash_token(token), label, token[-4:]))
        row = conn.execute("SELECT * FROM mcp_tokens WHERE token_id=?", (token_id,)).fetchone()
    finally:
        conn.close()
    return token, _public(row)


def _public(r: sqlite3.Row) -> dict:
    return {k: r[k] for k in ("token_id", "label", "scope", "last4", "created_at",
                              "expires_at", "revoked_at", "last_used_at", "last_client")}


def list_tokens(user_id: str, include_inactive: bool = False) -> list[dict]:
    conn = connect()
    try:
        sql = "SELECT * FROM mcp_tokens WHERE user_id=?"
        if not include_inactive:
            sql += f" AND {_active_where()}"
        rows = conn.execute(sql + " ORDER BY created_at DESC, token_id", (user_id,)).fetchall()
    finally:
        conn.close()
    return [_public(r) for r in rows]


def revoke(token_id: str, user_id: str | None = None) -> bool:
    """폐기(즉시 효력). user_id 지정 시 해당 사용자 토큰만."""
    conn = connect()
    try:
        with conn:
            sql = "UPDATE mcp_tokens SET revoked_at=datetime('now') WHERE token_id=? AND revoked_at IS NULL"
            args: list = [token_id]
            if user_id is not None:
                sql += " AND user_id=?"
                args.append(user_id)
            return conn.execute(sql, args).rowcount > 0
    finally:
        conn.close()


def revoke_all(user_id: str) -> int:
    conn = connect()
    try:
        with conn:
            return conn.execute(
                "UPDATE mcp_tokens SET revoked_at=datetime('now') WHERE user_id=? AND revoked_at IS NULL",
                (user_id,)).rowcount
    finally:
        conn.close()


def lookup(token: str) -> dict | None:
    """Bearer → {token_id, user_id}. 형식·미존재·만료·폐기·사용자 DB 없음은 모두 None."""
    if not isinstance(token, str) or not TOKEN_RE.match(token):
        return None
    conn = connect()
    try:
        r = conn.execute(
            f"SELECT token_id, user_id FROM mcp_tokens WHERE token_hash=? AND {_active_where()}",
            (hash_token(token),)).fetchone()
    finally:
        conn.close()
    if not r or not get_db_path(r["user_id"], create=False).exists():
        return None
    return {"token_id": r["token_id"], "user_id": r["user_id"]}


def touch(token_id: str, client: str) -> None:
    """마지막 사용 시각·클라이언트 족 기록 (10분 단위로만 쓰기)."""
    conn = connect()
    try:
        with conn:
            conn.execute(
                "UPDATE mcp_tokens SET last_used_at=datetime('now'), last_client=? "
                "WHERE token_id=? AND (last_used_at IS NULL OR "
                f"last_used_at < datetime('now', '-{_TOUCH_INTERVAL_MIN} minutes'))",
                ((client or "")[:60], token_id))
    finally:
        conn.close()
