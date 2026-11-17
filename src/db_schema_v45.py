"""스키마 v45 — activity_laps.lap_kind(강도) 분리(REVIEW-10 A-5).

기존 lap_trigger 에는 intensityType(ACTIVE·REST…)이 들어 있었다. 강도는 lap_kind 로 옮기고
lap_trigger 는 랩 종료 원인(MANUAL·DISTANCE…) 전용으로 쓴다. 가산 ALTER + 기존 값 이관, 멱등.
"""
from __future__ import annotations

import sqlite3


def ensure_v45(conn: sqlite3.Connection) -> None:
    cols = {r[1] for r in conn.execute("PRAGMA table_info(activity_laps)")}
    if not cols:
        return
    if "lap_kind" not in cols:
        conn.execute("ALTER TABLE activity_laps ADD COLUMN lap_kind TEXT")
        conn.execute(
            "UPDATE activity_laps SET lap_kind = lap_trigger, lap_trigger = NULL "
            "WHERE lap_kind IS NULL AND lap_trigger IS NOT NULL"
        )
