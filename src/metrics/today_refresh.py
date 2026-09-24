"""달력 오늘의 일별 메트릭을 "현 시각 기준"으로 유지하는 지연 갱신.

오늘 행(PMC·UTRS·CIRS…)은 하루가 끝나기 전엔 잠정값이다 — PMC는 하루 중 경과 비율만큼만
휴식 감쇠를 적용한다(pmc.elapsed_day_fraction). 그래서 마지막 계산이 오래됐으면 조회 시점에
오늘 하루치만 다시 계산한다. sync를 안 돌려도 아침부터 저녁까지 값이 시각에 맞게 따라간다.
실패해도 조회는 막지 않는다(로그만).
"""
from __future__ import annotations

import logging
import sqlite3
import threading
from datetime import date

log = logging.getLogger(__name__)

_lock = threading.Lock()


def refresh_today_if_stale(conn: sqlite3.Connection, max_age_min: int = 30) -> bool:
    """오늘 tsb 행이 없거나 max_age_min분보다 오래됐으면 오늘만 재계산. 갱신했으면 True."""
    today = date.today().isoformat()  # 서버 로컬 날짜 (SQLite date('now')는 UTC라 쓰지 않는다)
    with _lock:
        try:
            fresh = conn.execute(
                "SELECT 1 FROM metric_store WHERE scope_type = 'daily' AND scope_id = ?"
                " AND metric_name = 'tsb' AND is_primary = 1"
                " AND updated_at >= datetime('now', ?)",
                (today, f"-{int(max_age_min)} minutes"),
            ).fetchone()
            if fresh:
                return False
            from src.metrics import engine

            engine.compute_for_dates(conn, [today])
            conn.commit()
            return True
        except Exception:  # noqa: BLE001 — 조회를 막지 않는다
            log.warning("today 메트릭 갱신 실패", exc_info=True)
            return False
