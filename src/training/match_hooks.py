"""동기화 후 계획↔활동 매칭 훅 — 신규 활동이 있을 때만 최근 N주를 재매칭하고 결과를 반환한다(HSR-5 b, HSR-9).

매칭 실패는 동기화를 중단시키지 않고 {"error": ...} 로 돌려준다(흔적 없이 삼키지 않는다).
"""
from __future__ import annotations

import logging
import sqlite3
from datetime import date, timedelta

log = logging.getLogger(__name__)


def count_canonical(db_path: str) -> int:
    """동기화 전후 비교용 canonical 활동 수(신규 활동 집계 기준, HSR-10)."""
    from src.services.activity_counts import activity_counts
    with sqlite3.connect(db_path, timeout=30) as conn:
        return activity_counts(conn)["canonical_total"]


def run_post_sync_match(db_path: str, new_activities: int, weeks: int = 4,
                        today: date | None = None) -> dict:
    """{weeks, matched} | {skipped: 사유} | {error: 메시지}. new_activities=0 이면 실행하지 않는다."""
    if new_activities <= 0:
        return {"skipped": "no_new_activities"}
    try:
        from src.training.matcher import match_week_activities
        today = today or date.today()
        this_week = today - timedelta(days=today.weekday())
        matched = 0
        with sqlite3.connect(db_path, timeout=30) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            for w in range(weeks):
                matched += match_week_activities(conn, this_week - timedelta(weeks=w)) or 0
            conn.commit()
        return {"weeks": weeks, "matched": matched}
    except Exception as exc:  # noqa: BLE001 — 동기화는 계속
        log.warning("동기화 후 매칭 실패: %s", exc)
        return {"error": str(exc)[:150]}
