"""Garmin MFA 대기 상태 보관 — 프로세스 메모리, 사용자당 1개, TTL 300초·오답 5회 폐기. 설계: garmin-connect.md §3.2.

라이브러리의 MFA 세션은 `Garmin` 인스턴스 메모리에만 있어 직렬화할 수 없다 — 단일 워커 전제.
키는 user_id(세션 인증 결과), ticket 은 2차 검증(sha256 해시만 보관, 원문은 응답으로 1회 전달).
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
import threading
import time
from dataclasses import dataclass
from typing import Any

TTL_S = 300
MAX_TRIES = 5

_lock = threading.Lock()
_items: dict[str, "PendingMfa"] = {}
_state = {"multi_worker": False}
_security_log = logging.getLogger("runpulse.security")


@dataclass
class PendingMfa:
    user_id: str
    ticket_hash: str
    client: Any  # MFA 세션을 쥔 Garmin 인스턴스(password 는 None 으로 비운 뒤 보관)
    email: str
    expires_at: float
    tries: int = 0
    busy: bool = False  # 처리 중(이중 제출 방지)


def _now(now: float | None) -> float:
    return time.monotonic() if now is None else now


def _hash(ticket: str) -> str:
    return hashlib.sha256(ticket.encode("utf-8")).hexdigest()


def _sweep_locked(t: float) -> int:
    dead = [uid for uid, p in _items.items() if p.expires_at <= t]
    for uid in dead:
        _items.pop(uid, None)
    return len(dead)


def sweep(now: float | None = None) -> int:
    """만료 항목 제거, 제거 수 반환."""
    with _lock:
        return _sweep_locked(_now(now))


def put(user_id: str, client: Any, email: str, now: float | None = None) -> str:
    """기존 항목을 폐기하고 저장. 원문 ticket 반환."""
    t = _now(now)
    ticket = secrets.token_urlsafe(32)
    with _lock:
        _sweep_locked(t)
        _items[user_id] = PendingMfa(user_id, _hash(ticket), client, email, t + TTL_S)
    return ticket


def _match_locked(user_id: str, ticket: str, t: float) -> PendingMfa | None:
    _sweep_locked(t)
    if not isinstance(ticket, str) or not ticket:
        return None
    h = _hash(ticket)
    p = _items.get(user_id)
    if p is not None and hmac.compare_digest(p.ticket_hash, h):
        return p
    if any(hmac.compare_digest(o.ticket_hash, h) for uid, o in _items.items() if uid != user_id):
        _security_log.warning("[garmin_mfa] 다른 사용자의 MFA ticket 사용 시도")
    return None


def get(user_id: str, ticket: str, now: float | None = None) -> PendingMfa | None:
    """uid 일치 + ticket 해시 일치 + 미만료일 때만 반환."""
    with _lock:
        return _match_locked(user_id, ticket, _now(now))


def claim(user_id: str, ticket: str, now: float | None = None) -> PendingMfa | None:
    """처리용으로 잡는다 — 이미 처리 중이면 None(이중 제출). 끝나면 release/discard 호출."""
    with _lock:
        p = _match_locked(user_id, ticket, _now(now))
        if p is None or p.busy:
            return None
        p.busy = True
        return p


def release(user_id: str) -> None:
    with _lock:
        p = _items.get(user_id)
        if p is not None:
            p.busy = False


def record_failure(user_id: str) -> int:
    """오답 1회 기록 후 남은 시도 수 반환. 0이면 폐기됨."""
    with _lock:
        p = _items.get(user_id)
        if p is None:
            return 0
        p.tries += 1
        p.busy = False
        left = MAX_TRIES - p.tries
        if left <= 0:
            _items.pop(user_id, None)
            return 0
        return left


def remaining_s(p: PendingMfa, now: float | None = None) -> int:
    return max(0, int(p.expires_at - _now(now)))


def discard(user_id: str) -> None:
    with _lock:
        _items.pop(user_id, None)


def reset() -> None:
    """테스트용 전체 비우기."""
    with _lock:
        _items.clear()


def set_multi_worker(flag: bool) -> None:
    _state["multi_worker"] = bool(flag)


def is_available() -> bool:
    """워커가 여러 개면 MFA 상태를 다른 프로세스가 못 보므로 비활성."""
    return not _state["multi_worker"]
