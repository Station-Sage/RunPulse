"""계정 레지스트리 DB(data/auth.db) — accounts·identities·invites·auth_events. 초대코드는 sha256 해시만 저장."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from src.utils import user_context as uc
from src.utils.user_context import InvalidUserId, validate_uid

_DDL = """
CREATE TABLE IF NOT EXISTS accounts (
    uid TEXT PRIMARY KEY, email_norm TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL CHECK (status IN ('pending','active','disabled')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')), activated_at TEXT,
    invite_id TEXT, consent_version TEXT);
CREATE TABLE IF NOT EXISTS identities (
    provider TEXT NOT NULL, subject TEXT NOT NULL, uid TEXT NOT NULL REFERENCES accounts(uid),
    email_at_link TEXT, idp_type TEXT, first_seen TEXT NOT NULL DEFAULT (datetime('now')),
    last_seen TEXT NOT NULL DEFAULT (datetime('now')), PRIMARY KEY (provider, subject));
CREATE INDEX IF NOT EXISTS ix_identities_uid ON identities(uid);
CREATE TABLE IF NOT EXISTS invites (
    invite_id TEXT PRIMARY KEY, code_hash TEXT NOT NULL UNIQUE, max_uses INTEGER NOT NULL DEFAULT 1,
    uses INTEGER NOT NULL DEFAULT 0, expires_at TEXT, created_at TEXT NOT NULL DEFAULT (datetime('now')), note TEXT);
CREATE TABLE IF NOT EXISTS auth_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL DEFAULT (datetime('now')),
    event TEXT NOT NULL, uid TEXT, detail TEXT);
CREATE INDEX IF NOT EXISTS ix_auth_events_ts ON auth_events(ts);
"""
PROVIDER = "cf"


def db_path() -> Path:
    return uc.project_root() / "data" / "auth.db"


def connect() -> sqlite3.Connection:
    p = db_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(p), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(_DDL)
    return conn


def normalize_email(email: str) -> str:
    """strip + lower. Gmail 별칭(점·+tag) 접기는 하지 않는다(오병합 방지)."""
    return (email or "").strip().lower()


def record_event(conn: sqlite3.Connection, event: str, uid: str | None = None, detail: str | None = None) -> None:
    with conn:
        conn.execute("INSERT INTO auth_events (event, uid, detail) VALUES (?,?,?)", (event, uid, detail))


def account_by_identity(conn, subject: str, provider: str = PROVIDER):
    return conn.execute(
        "SELECT a.* FROM identities i JOIN accounts a ON a.uid = i.uid WHERE i.provider=? AND i.subject=?",
        (provider, subject)).fetchone()


def account_by_email(conn, email: str):
    return conn.execute("SELECT * FROM accounts WHERE email_norm=?", (normalize_email(email),)).fetchone()


def link_identity(conn, uid: str, subject: str, email: str, idp_type: str | None = None, provider: str = PROVIDER) -> None:
    with conn:
        conn.execute(
            "INSERT INTO identities (provider, subject, uid, email_at_link, idp_type) VALUES (?,?,?,?,?) "
            "ON CONFLICT(provider, subject) DO UPDATE SET last_seen=datetime('now')",
            (provider, subject, uid, normalize_email(email), idp_type))


def create_pending(conn, email: str) -> sqlite3.Row:
    """신규 계정(pending). uid = email_norm — uid 규칙 위반이면 `InvalidUserId`."""
    norm = normalize_email(email)
    validate_uid(norm)
    with conn:
        conn.execute("INSERT INTO accounts (uid, email_norm, status) VALUES (?,?, 'pending')", (norm, norm))
    return account_by_email(conn, norm)


def activate(conn, uid: str, invite_id: str | None = None, consent_version: str | None = None) -> None:
    with conn:
        conn.execute(
            "UPDATE accounts SET status='active', activated_at=datetime('now'), invite_id=COALESCE(?, invite_id), "
            "consent_version=COALESCE(?, consent_version) WHERE uid=? AND status='pending'",
            (invite_id, consent_version, uid))


def backfill(conn, *, apply: bool, exclude: tuple[str, ...] = ()) -> dict:
    """기존 `data/users` 디렉터리 → active 계정. 이메일 형태가 아니거나 예시 도메인·제외 목록이면 건너뛴다."""
    done, skipped, collided = [], [], []
    for uid in uc.list_user_ids(log_skipped=False):
        norm = normalize_email(uid)
        domain = norm.rsplit("@", 1)[-1] if "@" in norm else ""
        if uid in exclude or "@" not in norm or "." not in domain or domain.startswith("example."):
            skipped.append(uid)
            continue
        other = account_by_email(conn, norm)
        if other is not None and other["uid"] != uid:
            collided.append(uid)
            continue
        done.append(uid)
        if apply and other is None:
            with conn:
                conn.execute(
                    "INSERT INTO accounts (uid, email_norm, status, activated_at) VALUES (?,?, 'active', datetime('now'))",
                    (uid, norm))
    return {"backfilled": done, "skipped": skipped, "collided": collided}


__all__ = ["InvalidUserId", "PROVIDER", "connect", "normalize_email"]
