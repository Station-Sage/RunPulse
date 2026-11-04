"""초대코드 — 발급(해시만 저장)·소비(원자적 사용 횟수 증가)·반납."""
from __future__ import annotations

import hashlib
import secrets
import uuid


class InviteError(Exception):
    """코드 없음/만료/소진 — 사유를 구분하지 않고 한 코드로 응답한다(코드 추측 단서 차단)."""


def _hash(code: str) -> str:
    return hashlib.sha256((code or "").strip().upper().encode()).hexdigest()


def issue(conn, *, max_uses: int = 1, expires_days: int | None = 14, note: str | None = None) -> tuple[str, str]:
    """(평문 코드, invite_id). 평문은 이 반환값으로만 볼 수 있다."""
    code = secrets.token_urlsafe(9).replace("-", "A").replace("_", "B").upper()[:12]
    invite_id = uuid.uuid4().hex[:12]
    exp = f"+{int(expires_days)} days" if expires_days else None
    with conn:
        conn.execute(
            "INSERT INTO invites (invite_id, code_hash, max_uses, expires_at, note) "
            "VALUES (?,?,?, CASE WHEN ? IS NULL THEN NULL ELSE datetime('now', ?) END, ?)",
            (invite_id, _hash(code), max_uses, exp, exp, note))
    return code, invite_id


def consume(conn, code: str) -> str:
    """유효하면 uses 를 1 올리고 invite_id 반환, 아니면 InviteError."""
    h = _hash(code)
    with conn:
        cur = conn.execute(
            "UPDATE invites SET uses = uses + 1 WHERE code_hash=? AND uses < max_uses "
            "AND (expires_at IS NULL OR expires_at > datetime('now'))", (h,))
    if cur.rowcount != 1:
        raise InviteError("invalid")
    return conn.execute("SELECT invite_id FROM invites WHERE code_hash=?", (h,)).fetchone()["invite_id"]


def release(conn, invite_id: str) -> None:
    with conn:
        conn.execute("UPDATE invites SET uses = MAX(uses - 1, 0) WHERE invite_id=?", (invite_id,))


def list_invites(conn) -> list[dict]:
    return [dict(r) for r in conn.execute(
        "SELECT invite_id, max_uses, uses, expires_at, created_at, note FROM invites ORDER BY created_at DESC")]
