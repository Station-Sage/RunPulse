"""캘린더 구독 토큰 전역 인덱스 (data/calendar_feeds.db) — 발급·재발급·해제·조회.

토큰 원문은 저장하지 않는다: 조회용 sha256 해시 + 재표시용 Fernet 암호문(키 없으면 NULL).
설계: v0.3/data/phase-7-ui-renewal/ux-review-2026-09/DESIGN-ICS-SUBSCRIBE.md §3
"""
from __future__ import annotations

import hashlib
import secrets
import sqlite3
from pathlib import Path

from src.db_setup import _PROJECT_ROOT
from src.utils.credential_store import decrypt_value, encrypt_value

TOKEN_PREFIX = "rpcal_"
_TOUCH_INTERVAL_MIN = 10
_DDL = """CREATE TABLE IF NOT EXISTS calendar_feeds (
    user_id TEXT PRIMARY KEY, token_hash TEXT NOT NULL UNIQUE, token_enc TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')), last_access_at TEXT, last_client TEXT)"""


def index_path() -> Path:
    return _PROJECT_ROOT / "data" / "calendar_feeds.db"


def _connect() -> sqlite3.Connection:
    p = index_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(p), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(_DDL)
    return conn


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def issue(user_id: str) -> str:
    """새 토큰 발급(이미 있으면 교체 — 구 토큰 즉시 무효). 토큰 원문 반환."""
    token = TOKEN_PREFIX + secrets.token_urlsafe(32)
    conn = _connect()
    try:
        with conn:
            conn.execute(
                "INSERT INTO calendar_feeds (user_id, token_hash, token_enc) VALUES (?,?,?) "
                "ON CONFLICT(user_id) DO UPDATE SET token_hash=excluded.token_hash, "
                "token_enc=excluded.token_enc, created_at=datetime('now'), "
                "last_access_at=NULL, last_client=NULL",
                (user_id, hash_token(token), encrypt_value(token)))
    finally:
        conn.close()
    return token


def get_status(user_id: str) -> dict | None:
    """없으면 None. token 은 복호화 가능할 때만(아니면 None → revealable=False)."""
    conn = _connect()
    try:
        r = conn.execute("SELECT * FROM calendar_feeds WHERE user_id=?", (user_id,)).fetchone()
    finally:
        conn.close()
    if not r:
        return None
    return {"token": decrypt_value(r["token_enc"]), "created_at": r["created_at"],
            "last_access_at": r["last_access_at"], "last_client": r["last_client"]}


def revoke(user_id: str) -> bool:
    conn = _connect()
    try:
        with conn:
            return conn.execute("DELETE FROM calendar_feeds WHERE user_id=?", (user_id,)).rowcount > 0
    finally:
        conn.close()


def lookup(token: str) -> tuple[str, str] | None:
    """토큰 → (user_id, token_hash). 형식이 틀리거나 없으면 None."""
    if not token.startswith(TOKEN_PREFIX) or len(token) > 80:
        return None
    h = hash_token(token)
    conn = _connect()
    try:
        r = conn.execute("SELECT user_id FROM calendar_feeds WHERE token_hash=?", (h,)).fetchone()
    finally:
        conn.close()
    return (r["user_id"], h) if r else None


def touch(token_hash: str, client: str) -> None:
    """접근 시각·클라이언트 족 기록 (10분 단위로만 쓰기)."""
    conn = _connect()
    try:
        with conn:
            conn.execute(
                "UPDATE calendar_feeds SET last_access_at=datetime('now'), last_client=? "
                "WHERE token_hash=? AND (last_access_at IS NULL OR "
                f"last_access_at < datetime('now', '-{_TOUCH_INTERVAL_MIN} minutes'))",
                (client, token_hash))
    finally:
        conn.close()
