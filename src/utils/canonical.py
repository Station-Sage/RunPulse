"""캐노니컬 활동 — 같은 활동의 소스 사본(Garmin·Intervals·Strava·Runalyze) 중 대표 1개(`v_canonical_activities`).

RunPulse activity-scope 계산은 대표에만 저장한다(UX 리뷰 21 design §7.3 C3, DECISIONS D10).
"""
from __future__ import annotations

import sqlite3

_SAME_GROUP = "COALESCE(c.matched_group_id, 'solo_'||c.id) = COALESCE(a.matched_group_id, 'solo_'||a.id)"


def canonical_activity_id(conn: sqlite3.Connection, activity_id: int) -> int:
    """활동 id → 같은 그룹의 현재 canonical 활동 id. 그룹이 재편돼 저장된 id 가 낡아도 같은 활동으로 취급한다."""
    row = conn.execute(
        f"SELECT c.id FROM activity_summaries a JOIN v_canonical_activities c ON {_SAME_GROUP} "
        "WHERE a.id=? LIMIT 1", (activity_id,)).fetchone()
    return row[0] if row else activity_id


def group_activity_ids(conn: sqlite3.Connection, activity_id: int) -> list[int]:
    """같은 그룹의 활동 id(자기 자신 먼저, 이후 id 순). 그룹이 없으면 [자기]."""
    rows = conn.execute(
        "SELECT c.id FROM activity_summaries a JOIN activity_summaries c ON "
        f"{_SAME_GROUP} WHERE a.id=? ORDER BY c.id != ?, c.id", (activity_id, activity_id)).fetchall()
    return [r[0] for r in rows] or [activity_id]
