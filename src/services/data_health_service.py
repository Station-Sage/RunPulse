"""데이터 건강 — 부하(TRIMP) 커버리지 등, 지표를 믿어도 되는지 알려주는 읽기 전용 진단."""
from __future__ import annotations

import sqlite3
from datetime import date as _date, timedelta


def get_load_coverage(conn: sqlite3.Connection, days: int = 90, today: str | None = None) -> dict:
    """최근 N일 러닝(캐노니컬, HR·시간 있는 것) 중 primary TRIMP가 없는 활동 비율.

    PMC(CTL/ATL/TSB)는 캐노니컬 활동의 TRIMP 합으로 계산되므로 누락이 많으면 체력·폼이 낮게 나온다.
    반환: {"window_days", "runs", "missing", "missing_ratio"}
    """
    end = _date.fromisoformat(today) if today else _date.today()
    start = (end - timedelta(days=days)).isoformat()
    row = conn.execute(
        "SELECT COUNT(*) AS n, SUM(CASE WHEN NOT EXISTS ("
        "   SELECT 1 FROM metric_store m WHERE m.scope_type = 'activity' AND m.scope_id = CAST(a.id AS TEXT)"
        "   AND m.metric_name = 'trimp' AND m.is_primary = 1) THEN 1 ELSE 0 END) AS miss"
        " FROM v_canonical_activities a"
        " WHERE a.activity_type LIKE '%running%' AND a.avg_hr > 0 AND a.duration_sec > 0"
        "   AND substr(a.start_time, 1, 10) > ? AND substr(a.start_time, 1, 10) <= ?",
        (start, end.isoformat()),
    ).fetchone()
    runs = int(row[0] or 0)
    missing = int(row[1] or 0)
    return {
        "window_days": days,
        "runs": runs,
        "missing": missing,
        "missing_ratio": round(missing / runs, 2) if runs else 0.0,
    }
