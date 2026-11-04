"""가입 관문 — SIGNUP_MODE(invite|allowlist|open)·일일 상한·프로비저닝 후 활성화."""
from __future__ import annotations

import os

from . import invites, provisioning, registry


class SignupError(Exception):
    def __init__(self, code: str, status: int):
        super().__init__(code)
        self.code, self.status = code, status


def signup_mode() -> str:
    m = os.environ.get("SIGNUP_MODE", "invite").strip().lower()
    return m if m in ("invite", "allowlist", "open") else "invite"


def daily_cap() -> int:
    try:
        return max(0, int(os.environ.get("SIGNUP_DAILY_CAP", "20")))
    except ValueError:
        return 20


def activated_today(conn) -> int:
    """오늘 신규 가입으로 활성화된 계정 수(백필 계정은 invite_id 가 NULL 이라 제외)."""
    return conn.execute(
        "SELECT COUNT(*) FROM accounts WHERE status='active' AND activated_at >= date('now') "
        "AND invite_id IS NOT NULL").fetchone()[0]


def _allowlisted(email: str) -> bool:
    raw = os.environ.get("SIGNUP_ALLOWLIST", "")
    return registry.normalize_email(email) in {registry.normalize_email(e) for e in raw.split(",") if e.strip()}


def activate_pending(conn, uid: str, code: str | None) -> None:
    """pending → active. 상한 → 모드별 자격 → 프로비저닝 → 활성화 순. 실패 시 사용 횟수를 되돌린다."""
    mode, invite_id = signup_mode(), None
    if mode != "allowlist" and activated_today(conn) >= daily_cap():
        raise SignupError("SIGNUP_CAP", 429)
    if mode == "invite":
        try:
            invite_id = invites.consume(conn, code or "")
        except invites.InviteError:
            raise SignupError("INVITE_INVALID", 400) from None
    elif mode == "allowlist" and not _allowlisted(uid):
        raise SignupError("NOT_ALLOWED", 403)
    try:
        provisioning.provision(uid)
    except Exception:
        if invite_id:
            invites.release(conn, invite_id)
        raise SignupError("PROVISION_FAILED", 503) from None
    registry.activate(conn, uid, invite_id=invite_id or f"{mode}")
