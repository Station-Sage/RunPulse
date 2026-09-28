"""분해 v2(`metrics_explain.py`/`metrics_explain_composite.py`) 공유 헬퍼.

파일당 300줄 규칙 때문에 explainer들을 여러 모듈로 나누면서, 양쪽이 쓰는
`sources` 근사 로직만 여기 둔다(순환 import 방지).
"""
from __future__ import annotations

import sqlite3


def daily_trimp_sum(conn: sqlite3.Connection, date_str: str) -> float:
    """그날 활동들의 TRIMP 합 — `CalcContext.get_daily_load()` 폴백 쿼리와 동일 패턴."""
    rows = conn.execute(
        "SELECT m.numeric_value FROM metric_store m "
        "JOIN v_canonical_activities a ON CAST(m.scope_id AS INTEGER)=a.id "
        "WHERE m.scope_type='activity' AND m.metric_name='trimp' AND m.is_primary=1 "
        "AND substr(a.start_time,1,10)=?",
        (date_str,),
    ).fetchall()
    return sum(r[0] or 0 for r in rows)


def top_activity_sources(conn: sqlite3.Connection, scope_id: str, window_days: int = 14, limit: int = 3) -> list[dict]:
    """최근 window_days 내 TRIMP 상위 활동(근사 — 정확한 EMA 기여 배분 아님)."""
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT a.id, a.name, m.numeric_value AS trimp FROM metric_store m "
        "JOIN v_canonical_activities a ON CAST(m.scope_id AS INTEGER)=a.id "
        "WHERE m.scope_type='activity' AND m.metric_name='trimp' AND m.is_primary=1 "
        "AND substr(a.start_time,1,10)<=? AND substr(a.start_time,1,10)>date(?, ?) "
        "ORDER BY m.numeric_value DESC LIMIT ?",
        (scope_id, scope_id, f"-{window_days} days", limit),
    ).fetchall()
    return [
        {
            "type": "activity",
            "id": r["id"],
            "label": r["name"] or "활동",
            "value": round(r["trimp"], 1) if r["trimp"] is not None else None,
            "unit": "TRIMP",
            "effect": f"부하 +{round(r['trimp'], 1)}" if r["trimp"] is not None else "",
        }
        for r in rows
    ]
