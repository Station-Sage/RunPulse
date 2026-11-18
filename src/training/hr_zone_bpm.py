"""플랜 심박존 번호 → 러너 본인 LTHR 기준 bpm 구간 (Friel 5존, physio.zones_lthr)."""
from __future__ import annotations

import sqlite3

from src.metrics.prediction.physio import zones_lthr


def latest_lthr(conn: sqlite3.Connection) -> float | None:
    """가장 최근 daily lthr_self(대표값). 없으면 None."""
    row = conn.execute(
        "SELECT numeric_value FROM metric_store WHERE scope_type='daily' AND metric_name='lthr_self' "
        "AND numeric_value IS NOT NULL ORDER BY scope_id DESC, is_primary DESC LIMIT 1"
    ).fetchone()
    return float(row[0]) if row and row[0] else None


def zone_bpm(conn: sqlite3.Connection, zone) -> dict | None:
    """{"zone","lo","hi","lthr"} — 존이 1~5가 아니거나 LTHR 없으면 None. Z5 상한은 None(열림)."""
    try:
        z = int(str(zone).upper().lstrip("Z"))
    except (TypeError, ValueError):
        return None
    if not 1 <= z <= 5:
        return None
    lthr = latest_lthr(conn)
    if lthr is None:
        return None
    lo, hi = zones_lthr(lthr)[z - 1]
    return {"zone": z, "lo": round(lo), "hi": None if z == 5 else round(hi), "lthr": round(lthr)}
