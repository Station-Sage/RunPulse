"""이번 달 Today 내러티브 사전 생성(워밍) — 동기화 직후 AI 문장을 캐시에 미리 채운다 (DESIGN-U17 §3).

동의·신선 캐시·일일 상한·동시 실행 가드(uid 별 락)·전역 LLM 사용량 80% 미만일 때만 LLM을 호출하고, 실패는 로그만 남긴다.
"""
from __future__ import annotations

import logging
import sqlite3
import threading
from datetime import datetime

from src.ai import ai_cache
from src.services._narrative import get_narrative_cache

logger = logging.getLogger(__name__)

WARM_DAILY_CAP = 3
_WARM_TAB = "today_narrative_warm"
_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


def _user_lock(user_id: str | None) -> threading.Lock:
    """uid 별 워밍 락 — 다른 사용자가 워밍 중이어도 막히지 않는다(multiuser-sync §4.2)."""
    key = user_id or "default"
    with _locks_guard:
        return _locks.setdefault(key, threading.Lock())


def _calls_today(conn: sqlite3.Connection, today: str) -> int:
    row = conn.execute(
        "SELECT content_json FROM ai_cache WHERE tab=? AND cache_key=?", (_WARM_TAB, today)
    ).fetchone()
    if not row:
        return 0
    try:
        import json
        return int(json.loads(row[0]).get("calls", 0))
    except (ValueError, TypeError, AttributeError):
        return 0


def _bump_calls(conn: sqlite3.Connection, today: str, calls: int) -> None:
    ai_cache._ensure_table(conn)
    conn.execute(
        "INSERT INTO ai_cache (tab, cache_key, content_json, generated_at) VALUES (?, ?, ?, ?)"
        " ON CONFLICT(tab, cache_key) DO UPDATE SET content_json=excluded.content_json,"
        " generated_at=excluded.generated_at",
        (_WARM_TAB, today, '{"calls": %d}' % calls, datetime.now().isoformat(timespec="seconds")),
    )
    conn.commit()


def warm_month_narrative(conn: sqlite3.Connection, today: str, *, consent_ok: bool,
                         config: dict | None = None, user_id: str | None = None) -> str:
    """반환: "warmed" | "fresh" | "no_consent" | "capped" | "failed"."""
    from src.ai import llm_budget
    if not consent_ok:
        return "no_consent"
    if llm_budget.global_ratio() >= llm_budget.limits()["warm_stop_ratio"]:
        return "capped"
    lock = _user_lock(user_id)
    if not lock.acquire(blocking=False):
        return "failed"
    try:
        month_start = today[:7] + "-01"
        if get_narrative_cache(conn, month_start, today) is not None:
            return "fresh"
        calls = _calls_today(conn, today)
        if calls >= WARM_DAILY_CAP:
            return "capped"
        _bump_calls(conn, today, calls + 1)
        try:
            from src.services import today_service
            with llm_budget.scope(user_id, "warm"):
                result = today_service.get_today_narrative(conn, date=today, config=config)
        except Exception as exc:  # noqa: BLE001
            logger.warning("내러티브 워밍 실패: %s", exc)
            return "failed"
        return "warmed" if result.get("source") == "ai" else "failed"
    finally:
        lock.release()


def warm_in_background(db_path: str, today: str, config: dict | None) -> None:
    """데몬 스레드로 워밍 실행 — 동기화 완료를 늦추지 않으며 예외는 전파하지 않는다."""
    def _run() -> None:
        try:
            from src.services import coach_consent
            with sqlite3.connect(db_path, timeout=30) as c:
                from src.ai.llm_budget import uid_from_db
                warm_month_narrative(c, today, consent_ok=coach_consent.get_consent(c) is not None,
                                     config=config, user_id=uid_from_db(db_path))
        except Exception as exc:  # noqa: BLE001
            logger.warning("내러티브 워밍 스레드 실패: %s", exc)
    threading.Thread(target=_run, daemon=True, name="narrative-warm").start()
