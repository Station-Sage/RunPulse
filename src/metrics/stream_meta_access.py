"""스트림 시간축 meta 조회(U18c) — CalcContext.get_stream_meta 의 구현. meta 테이블이 없거나 행이 없으면 None."""
from __future__ import annotations

import sqlite3

from src.utils.canonical import group_activity_ids

TRUSTED_BASES = ("measured", "derived", "scaled")


def load_stream_meta(conn: sqlite3.Connection, activity_id: int, group: bool = True) -> dict | None:
    """activity(없으면 같은 그룹 사본 순서대로)의 meta 한 행. 소스가 여럿이면 stored_count 가 큰 쪽."""
    ids = group_activity_ids(conn, activity_id) if group else [activity_id]
    for aid in ids:
        try:
            cur = conn.execute(
                "SELECT * FROM activity_stream_meta WHERE activity_id=? ORDER BY stored_count DESC LIMIT 1", [aid])
        except sqlite3.OperationalError:
            return None
        row = cur.fetchone()
        if row:
            return dict(zip([d[0] for d in cur.description], row))
    return None


def is_trusted(meta: dict | None) -> bool:
    """meta 가 있고 시간축 출처가 확정(measured/derived/scaled)이면 휴리스틱 없이 그대로 쓴다."""
    return bool(meta) and meta.get("time_basis") in TRUSTED_BASES
