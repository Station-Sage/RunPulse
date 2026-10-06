"""이번 달 Today 내러티브 사전 생성(워밍) — 동기화 직후 AI 문장을 캐시에 미리 채운다 (DESIGN-U17 §3).

동의·신선 캐시·일일 상한·동시 실행 가드를 통과할 때만 LLM을 호출하고, 실패는 로그만 남긴다.
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
_lock = threading.Lock()


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
                         config: dict | None = None) -> str:
    """반환: "warmed" | "fresh" | "no_consent" | "capped" | "failed"."""
    if not consent_ok:
        return "no_consent"
    if not _lock.acquire(blocking=False):
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
            result = today_service.get_today_narrative(conn, date=today, config=config)
        except Exception as exc:  # noqa: BLE001
            logger.warning("내러티브 워밍 실패: %s", exc)
            return "failed"
        return "warmed" if result.get("source") == "ai" else "failed"
    finally:
        _lock.release()


def warm_in_background(db_path: str, today: str, config: dict | None) -> None:
    """데몬 스레드로 워밍 실행 — 동기화 완료를 늦추지 않으며 예외는 전파하지 않는다."""
    def _run() -> None:
        try:
            from src.services import coach_consent
            with sqlite3.connect(db_path, timeout=30) as c:
                warm_month_narrative(c, today, consent_ok=coach_consent.get_consent(c) is not None,
                                     config=config)
        except Exception as exc:  # noqa: BLE001
            logger.warning("내러티브 워밍 스레드 실패: %s", exc)
    threading.Thread(target=_run, daemon=True, name="narrative-warm").start()
