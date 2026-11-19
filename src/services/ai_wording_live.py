"""AI 다듬기 요청 경로 연결 (ADR-059) — 캐시를 읽어 응답하고, 낡았으면 기다리지 않고 백그라운드 생성을 예약한다.

요청 스레드는 `present_or_warm` 으로 캐시만 읽는다(LLM·큐를 기다리지 않음). 캐시 미스면 같은 항목을
쿨다운(기본 30분) 안에 한 번만 `ai_wording.warm_in_background` 로 보낸다 — 검증 실패로 저장이 안 된 항목이
화면을 열 때마다 다시 호출되지 않게 하기 위해서다. 동기화 직후 워밍(`warm_after_sync`)은 쿨다운 없이 표면별로 돈다.
"""
from __future__ import annotations

import logging
import sqlite3
import threading
import time
from typing import Callable

from src.services import ai_wording as aw

log = logging.getLogger(__name__)

COOLDOWN_SEC = 30 * 60
_MAX_RECENT = 2000
_recent: dict[tuple[str, str, str], tuple[str, float]] = {}
_recent_guard = threading.Lock()


def _db_path(conn: sqlite3.Connection) -> str | None:
    try:
        from src.ai import provider_claude_queue as pcq
        return pcq.db_path_of(conn) or None
    except sqlite3.Error:
        return None


def _should_schedule(db_path: str, surface: aw.Surface, item: aw.Item, now: float | None = None) -> bool:
    """같은 (DB, 표면, 항목, src_hash) 를 쿨다운 안에 다시 예약하지 않는다."""
    now = time.monotonic() if now is None else now
    key, h = (db_path, surface.name, item.scope_key), aw.src_hash(surface, item)
    with _recent_guard:
        prev = _recent.get(key)
        if prev and prev[0] == h and now - prev[1] < COOLDOWN_SEC:
            return False
        if len(_recent) >= _MAX_RECENT:
            _recent.clear()
        _recent[key] = (h, now)
    return True


def reset_cooldown() -> None:
    """테스트용 — 예약 기록을 비운다."""
    with _recent_guard:
        _recent.clear()


def present_or_warm(conn: sqlite3.Connection | None, config: dict | None, surface: aw.Surface,
                    item: aw.Item | None) -> dict | None:
    """화면 응답용 {text, source}. item 이 None 이면 None. 캐시가 낡았으면 백그라운드 생성을 예약(대기 없음)."""
    if item is None or not item.rule_text:
        return None
    view = aw.present(conn, surface, item.scope_key, item.rule_text, item.facts, item.basis)
    if conn is None or view["source"] == "ai" or aw.is_fresh(conn, surface, item):
        return view
    path = _db_path(conn)
    if path and _should_schedule(path, surface, item):
        try:
            aw.warm_in_background(path, config, surface, lambda _c: [item])
        except RuntimeError:  # 스레드 생성 실패 — 화면은 규칙 문구로 계속
            log.warning("ai wording schedule failed: %s", surface.name)
    return view


def _collectors() -> list[tuple[aw.Surface, Callable[[sqlite3.Connection], list[aw.Item]]]]:
    from src.services import activity_impact_wording, story_wording, today_reason_wording
    return [(today_reason_wording.SURFACE, today_reason_wording.collect),
            (story_wording.SURFACE, story_wording.collect),
            (activity_impact_wording.SURFACE, activity_impact_wording.collect)]


def warm_after_sync(db_path: str, config: dict | None) -> None:
    """동기화 직후 1단계 표면(Today 사유·Story·러닝의 의미)을 한 스레드에서 차례로 워밍. 예외는 표면별로 삼킨다."""
    def _run() -> None:
        try:
            with sqlite3.connect(db_path, timeout=30) as c:
                for surface, collect in _collectors():
                    try:
                        aw.warm(c, config, surface, collect(c))
                    except Exception:  # noqa: BLE001
                        log.warning("ai wording sync warm failed: %s", surface.name, exc_info=True)
        except Exception:  # noqa: BLE001
            log.warning("ai wording sync warm failed", exc_info=True)
    threading.Thread(target=_run, daemon=True, name="wording-sync-warm").start()
