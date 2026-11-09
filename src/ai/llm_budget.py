"""LLM 예산 — 사용자·전역 일 상한, 분당 상한, 동시 실행 상한을 `_post` 한 지점에서 계량한다(multiuser-sync §4, T7).

호출부(coach·narrative·warm·test)는 `scope(uid, feature)`로 감싸고, `chat_engine_providers._post`만 admit→호출→settle 한다.
scope 밖 호출은 feature="unscoped"로 계측만 하고 막지 않는다(누락 탐지 경고). 판정은 검사 후 기록(예약 없음) —
초과분 1회는 허용한다. 일 경계는 00:00 Asia/Seoul. 상수는 LIMITS, env `LLM_LIMITS_JSON`으로 덮어쓴다.
"""
from __future__ import annotations

import contextvars
import json
import logging
import os
import threading
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from .provider_common import ProviderError

log = logging.getLogger("runpulse.llm")

KST = ZoneInfo("Asia/Seoul")
LIMITS = {
    "user_calls": 200, "user_tokens": 300_000, "user_per_min": 10,
    "global_calls": 4000, "global_tokens": 8_000_000,
    "concurrent": 3, "acquire_wait_sec": 2.0, "warn_ratio": 0.8, "warm_stop_ratio": 0.8,
}
QUOTA_REASONS = ("quota_user", "quota_global")
BUDGET_REASONS = (*QUOTA_REASONS, "busy")

_SCOPE: contextvars.ContextVar["Scope | None"] = contextvars.ContextVar("llm_scope", default=None)
_sem_lock = threading.Lock()
_sem: tuple[int, threading.BoundedSemaphore] | None = None
_warned: set[tuple[str, str]] = set()


def now_kst() -> datetime:
    """일 경계 판정용 시각 — 테스트는 monkeypatch 로 바꾼다."""
    return datetime.now(KST)


def limits() -> dict:
    raw = os.environ.get("LLM_LIMITS_JSON", "").strip()
    if not raw:
        return dict(LIMITS)
    try:
        over = json.loads(raw)
        return {**LIMITS, **{k: v for k, v in over.items() if k in LIMITS}}
    except (ValueError, AttributeError):
        log.warning("LLM_LIMITS_JSON 해석 실패 — 기본값 사용")
        return dict(LIMITS)


def _store():
    from src.ops.store import default_store
    return default_store()


def _semaphore(n: int) -> threading.BoundedSemaphore:
    global _sem
    with _sem_lock:
        if _sem is None or _sem[0] != n:
            _sem = (n, threading.BoundedSemaphore(n))
        return _sem[1]


def day_of(dt: datetime) -> str:
    return dt.astimezone(KST).date().isoformat()


def resets_at(now: datetime | None = None) -> str:
    """다음 00:00 KST — 예: 2026-11-07T00:00+09:00."""
    d = (now or now_kst()).astimezone(KST)
    nxt = datetime(d.year, d.month, d.day, tzinfo=KST) + timedelta(days=1)
    return nxt.isoformat(timespec="minutes")


@dataclass
class Scope:
    uid: str
    feature: str
    refused: str | None = None      # 마지막 거부 사유(quota_user|quota_global|busy)


@dataclass
class Ticket:
    uid: str
    feature: str
    day: str
    provider: str
    held: bool = False
    metered: bool = True


@contextmanager
def scope(uid: str | None, feature: str):
    """호출부 컨텍스트. uid=None 이면 resolve_user_id()."""
    if uid is None:
        from src.utils.user_context import resolve_user_id
        uid = resolve_user_id()
    sc = Scope(uid, feature)
    token = _SCOPE.set(sc)
    try:
        yield sc
    finally:
        _SCOPE.reset(token)


def ensure_scope(feature: str, uid: str | None = None):
    """이미 scope 안이면 그대로(예: warm → narrative), 아니면 새 scope."""
    cur = _SCOPE.get()
    return nullcontext(cur) if cur is not None else scope(uid, feature)


def uid_from_db(db_path) -> str | None:
    """`data/users/<uid>/running.db` → uid. 형식이 아니면 None(호출자가 resolve_user_id 폴백)."""
    from pathlib import Path
    p = Path(str(db_path))
    return p.parent.name if p.parent.parent.name == "users" else None


def current() -> Scope | None:
    return _SCOPE.get()


def _refuse(sc: Scope, day: str, reason: str) -> None:
    sc.refused = reason
    try:
        _store().add_usage(day, sc.uid, sc.feature, refused=1)
    except Exception:  # noqa: BLE001
        log.warning("거부 기록 실패", exc_info=True)
    from src.utils.user_context import mask_uid
    log.info("refuse uid=%s feature=%s reason=%s", mask_uid(sc.uid), sc.feature, reason)
    raise ProviderError(reason, None, "llm budget")


def _warn_global(day: str, used: dict, lim: dict) -> None:
    ratio = max(used["calls"] / lim["global_calls"], used["tokens"] / lim["global_tokens"])
    for level, name in ((1.0, "100%"), (lim["warn_ratio"], "80%")):
        if ratio >= level and (day, name) not in _warned:
            _warned.add((day, name))
            log.warning("global llm usage %s reached calls=%d tokens=%d", name, used["calls"], used["tokens"])
            break


def admit(provider: str) -> Ticket:
    """호출 직전 검사. 초과면 ProviderError(quota_user|quota_global|busy)."""
    sc = _SCOPE.get()
    day = day_of(now_kst())
    if sc is None:
        from src.utils.user_context import resolve_user_id
        try:
            uid = resolve_user_id()
        except Exception:  # noqa: BLE001
            uid = "default"
        log.warning("unscoped llm call provider=%s", provider)
        return Ticket(uid, "unscoped", day, provider)
    lim = limits()
    store = _store()
    mine = store.usage(day, sc.uid)
    if mine["calls"] >= lim["user_calls"] or mine["tokens"] >= lim["user_tokens"]:
        _refuse(sc, day, "quota_user")
    glob = store.usage(day)
    _warn_global(day, glob, lim)
    if glob["calls"] >= lim["global_calls"] or glob["tokens"] >= lim["global_tokens"]:
        _refuse(sc, day, "quota_global")
    from src.utils import rate_window
    if not rate_window.hit(f"llm:{sc.uid}", int(lim["user_per_min"]), 60.0):
        _refuse(sc, day, "busy")
    if not _semaphore(int(lim["concurrent"])).acquire(timeout=float(lim["acquire_wait_sec"])):
        _refuse(sc, day, "busy")
    return Ticket(sc.uid, sc.feature, day, provider, held=True)


def _tokens(resp_json) -> tuple[int, int] | None:
    usage = resp_json.get("usage") if isinstance(resp_json, dict) else None
    if not isinstance(usage, dict):
        return None
    tin = usage.get("prompt_tokens", usage.get("input_tokens"))
    tout = usage.get("completion_tokens", usage.get("output_tokens"))
    if tin is None and tout is None:
        return None
    return int(tin or 0), int(tout or 0)


def settle(ticket: Ticket, resp_json, prompt_chars: int, out_chars: int) -> None:
    """호출 후 기록 — usage 필드, 없으면 문자수/2 추정. 세마포어 반납."""
    try:
        tk = _tokens(resp_json) or (max(0, prompt_chars) // 2, max(0, out_chars) // 2)
        _store().add_usage(ticket.day, ticket.uid, ticket.feature, calls=1, tokens_in=tk[0], tokens_out=tk[1])
    except Exception:  # noqa: BLE001
        log.warning("사용량 기록 실패", exc_info=True)
    finally:
        if ticket.held:
            ticket.held = False
            try:
                _semaphore(int(limits()["concurrent"])).release()
            except ValueError:
                pass


def chars_of(obj) -> int:
    try:
        return len(json.dumps(obj, ensure_ascii=False)) if obj is not None else 0
    except (TypeError, ValueError):
        return 0


def usage_today(uid: str) -> dict:
    """설정 화면용 {calls, tokens, limit_calls, limit_tokens, resets_at}."""
    lim = limits()
    now = now_kst()
    try:
        used = _store().usage(day_of(now), uid)
    except Exception:  # noqa: BLE001
        used = {"calls": 0, "tokens": 0}
    return {"calls": used["calls"], "tokens": used["tokens"], "limit_calls": lim["user_calls"],
            "limit_tokens": lim["user_tokens"], "resets_at": resets_at(now)}


def global_ratio() -> float:
    """오늘 전역 사용률(호출·토큰 중 큰 쪽). 조회 실패는 0."""
    lim = limits()
    try:
        used = _store().usage(day_of(now_kst()))
    except Exception:  # noqa: BLE001
        return 0.0
    return max(used["calls"] / lim["global_calls"], used["tokens"] / lim["global_tokens"])


def reset_for_tests() -> None:
    """세마포어·경고 기록·분당 창(llm: 키)을 비운다."""
    global _sem
    with _sem_lock:
        _sem = None
    _warned.clear()
    from src.utils import rate_window
    with rate_window._lock:
        for k in [k for k in rate_window._hits if k.startswith("llm:")]:
            rate_window._hits.pop(k, None)
