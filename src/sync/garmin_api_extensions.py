"""Garmin 활동 확장 API — gear, exercise_sets."""
from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING

from src.sync.garmin_helpers import _store_raw_payload

if TYPE_CHECKING:
    from garminconnect import Garmin


def sync_activity_gear(
    conn: sqlite3.Connection,
    client: "Garmin",
    activity_id: int,
    source_id: str,
) -> str | None:
    """Garmin 활동 장비 → gear 테이블 저장 및 activity_summaries 링크.

    Returns:
        저장된 gear_id (첫 번째), 없으면 None.
    """
    try:
        data = client.get_activity_gear(int(source_id))
    except Exception as e:
        print(f"[garmin] activity_gear 조회 실패 {source_id}: {e}")
        return None

    if not data:
        return None

    _store_raw_payload(conn, "activity_gear", source_id, {"gear": data}, activity_id=activity_id)

    gear_list = data if isinstance(data, list) else [data]
    first_gear_id = None

    for item in gear_list:
        g_id = str(item.get("gearPk") or item.get("uuid") or "")
        if not g_id:
            continue
        name = (
            item.get("customMakeModel") or item.get("displayName")
            or item.get("name") or ""
        )
        dist_km = item.get("totalDistanceInKilometers")
        dist_m = dist_km * 1000 if dist_km is not None else item.get("totalDistance")
        status = "inactive" if (item.get("gearStatusName") or "").lower() == "inactive" else "active"

        try:
            conn.execute(
                """INSERT INTO gear (source, source_gear_id, name, total_distance_m, status)
                   VALUES ('garmin', ?, ?, ?, ?)
                   ON CONFLICT(source, source_gear_id) DO UPDATE SET
                       name = COALESCE(excluded.name, name),
                       total_distance_m = excluded.total_distance_m,
                       status = excluded.status,
                       updated_at = datetime('now')""",
                (g_id, name, dist_m, status),
            )
        except sqlite3.Error as e:
            print(f"[garmin] gear 저장 실패 {g_id}: {e}")

        first_gear_id = first_gear_id or g_id

    if first_gear_id:
        conn.execute(
            "UPDATE activity_summaries SET gear_id = ? WHERE id = ?",
            (first_gear_id, activity_id),
        )
    return first_gear_id


def sync_activity_exercise_sets(
    conn: sqlite3.Connection,
    client: "Garmin",
    activity_id: int,
    source_id: str,
) -> int:
    """Garmin exerciseSets → activity_exercise_sets 저장 (근력/기타 전 종목).

    Returns:
        저장된 세트 수.
    """
    try:
        data = client.get_activity_exercise_sets(int(source_id))
    except Exception as e:
        print(f"[garmin] exercise_sets 조회 실패 {source_id}: {e}")
        return 0

    if not data:
        return 0

    sets = (
        data if isinstance(data, list)
        else data.get("exerciseSets") or data.get("sets") or []
    )
    if not sets:
        return 0

    _store_raw_payload(
        conn, "activity_exercise_sets", source_id, data, activity_id=activity_id
    )

    count = 0
    for i, s in enumerate(sets):
        etype = s.get("exerciseType") or {}
        exercise_name = (
            etype.get("typeKey") or etype.get("typeId") or s.get("exerciseName")
        )
        category = s.get("category") or etype.get("category")

        weight_raw = s.get("weight")
        weight_kg = None
        if weight_raw is not None:
            try:
                weight_kg = float(weight_raw)
            except (TypeError, ValueError):
                pass

        try:
            conn.execute(
                """INSERT INTO activity_exercise_sets
                   (activity_id, source, set_index, exercise_name, exercise_category,
                    set_type, reps, weight_kg, duration_sec, distance_m)
                   VALUES (?, 'garmin', ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(activity_id, source, set_index) DO UPDATE SET
                       exercise_name = excluded.exercise_name,
                       exercise_category = excluded.exercise_category,
                       set_type = excluded.set_type,
                       reps = excluded.reps,
                       weight_kg = excluded.weight_kg,
                       duration_sec = excluded.duration_sec,
                       distance_m = excluded.distance_m""",
                (
                    activity_id, s.get("setOrder", i), exercise_name, category,
                    s.get("setType"), s.get("reps"), weight_kg,
                    s.get("duration"), s.get("distance"),
                ),
            )
            count += 1
        except sqlite3.Error as e:
            print(f"[garmin] exercise_set 저장 실패 {source_id} idx {i}: {e}")

    return count
