"""활동 건수 단일 정의 (HSR-12 (a), NRA SSOT) — canonical 전체·러닝 계열·소스별 수신.

러닝 판정은 `activity_types.family_clause("running")` 하나만 쓴다(LIKE '%running%' 금지).
"""
from __future__ import annotations

import sqlite3

from src.utils.activity_types import family_clause


def activity_counts(conn: sqlite3.Connection) -> dict:
    """{canonical_total, canonical_running, raw_by_source} — 읽기 전용."""
    total = conn.execute("SELECT COUNT(*) FROM v_canonical_activities").fetchone()[0] or 0
    clause, params = family_clause("running")
    running = conn.execute(
        f"SELECT COUNT(*) FROM v_canonical_activities WHERE {clause}", params).fetchone()[0] or 0
    raw = {src: int(n) for src, n in conn.execute(
        "SELECT source, COUNT(*) FROM activity_summaries GROUP BY source")}
    return {"canonical_total": int(total), "canonical_running": int(running), "raw_by_source": raw}
