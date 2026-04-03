"""활동 중복 감지 — 5분 / 3% 규칙.

서로 다른 소스에서 온 같은 실제 활동을 matched_group_id로 묶습니다.
"""

from __future__ import annotations

import logging
import sqlite3
import uuid
from datetime import datetime

log = logging.getLogger(__name__)

TIME_THRESHOLD_SEC = 300
DISTANCE_THRESHOLD = 0.03


def run(conn: sqlite3.Connection) -> int:
    """전체 activity_summaries에 대해 dedup 실행.

    Returns: 새로 묶인 그룹 수.
    """
    rows = conn.execute(
        "SELECT id, source, source_id, start_time, distance_m, matched_group_id "
        "FROM activity_summaries ORDER BY start_time"
    ).fetchall()

    col_names = ["id", "source", "source_id", "start_time", "distance_m", "matched_group_id"]
    activities = [dict(zip(col_names, r)) for r in rows]

    new_groups = 0

    for i, a in enumerate(activities):
        if a["matched_group_id"]:
            continue

        group_id = str(uuid.uuid4())
        members = [a]

        for j in range(i + 1, len(activities)):
            b = activities[j]
            if b["matched_group_id"]:
                continue
            if b["source"] == a["source"]:
                continue
            if _is_match(a, b):
                members.append(b)

        if len(members) > 1:
            for m in members:
                conn.execute(
                    "UPDATE activity_summaries SET matched_group_id = ? WHERE id = ?",
                    (group_id, m["id"]),
                )
                m["matched_group_id"] = group_id
            new_groups += 1
            log.info(
                "[dedup] Group %s: %s",
                group_id[:8],
                ", ".join(f"{m['source']}:{m['source_id']}" for m in members),
            )

    if new_groups:
        conn.commit()
    log.info("[dedup] %d new groups created", new_groups)
    return new_groups


def _is_match(a: dict, b: dict) -> bool:
    try:
        ta = datetime.fromisoformat(a["start_time"].replace("Z", "+00:00"))
        tb = datetime.fromisoformat(b["start_time"].replace("Z", "+00:00"))
        if abs((ta - tb).total_seconds()) > TIME_THRESHOLD_SEC:
            return False
    except (ValueError, TypeError, AttributeError):
        return False

    da = a.get("distance_m") or 0
    db = b.get("distance_m") or 0
    if da == 0 and db == 0:
        return True
    if da == 0 or db == 0:
        return True
    return abs(da - db) / max(da, db) <= DISTANCE_THRESHOLD
