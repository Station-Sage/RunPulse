"""sync 패키지 — 소스별 동기화 함수 + 공용 SOURCES/병렬 헬퍼."""
from __future__ import annotations

import sqlite3
import sys

from src.sync.garmin import sync_activities as garmin_act, sync_wellness as garmin_well
from src.sync.strava import sync_activities as strava_act
from src.sync.intervals import sync_activities as intervals_act, sync_wellness as intervals_well
from src.sync.runalyze import sync_activities as runalyze_act


# (sync_activities, sync_wellness or None)
SOURCES: dict[str, tuple] = {
    "garmin": (garmin_act, garmin_well),
    "strava": (strava_act, None),
    "intervals": (intervals_act, intervals_well),
    "runalyze": (runalyze_act, None),
}


def _sync_source(source: str, config: dict, db_path, days: int) -> dict:
    """단일 소스 동기화 (독립 DB 커넥션).

    Returns:
        {"activities": int, "wellness": int, "errors": list[str]}
    """
    result: dict = {"activities": 0, "wellness": 0, "errors": []}
    sync_act_fn, sync_well_fn = SOURCES[source]

    with sqlite3.connect(str(db_path)) as conn:
        conn.execute("PRAGMA busy_timeout=5000")
        try:
            count = sync_act_fn(config, conn, days)
            result["activities"] = count
        except Exception as e:
            result["errors"].append(f"활동 동기화 실패: {e}")

        if sync_well_fn:
            try:
                count = sync_well_fn(config, conn, days)
                result["wellness"] = count
            except Exception as e:
                result["errors"].append(f"웰니스 동기화 실패: {e}")

    return result
