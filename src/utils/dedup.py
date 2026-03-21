"""중복 활동 매칭 유틸리티 (timestamp ±5분, distance ±3%)."""

import sqlite3
import uuid
from datetime import datetime, timedelta


# 매칭 허용 오차
_TIME_TOLERANCE = timedelta(minutes=5)
_DISTANCE_TOLERANCE = 0.03  # 3%


def is_duplicate(
    start_time1: str,
    distance1: float,
    start_time2: str,
    distance2: float,
) -> bool:
    """두 활동이 중복인지 판별.

    Args:
        start_time1: 첫 번째 활동 시작 시간 (ISO 형식).
        distance1: 첫 번째 활동 거리 (km).
        start_time2: 두 번째 활동 시작 시간 (ISO 형식).
        distance2: 두 번째 활동 거리 (km).

    Returns:
        중복이면 True.
    """
    t1 = datetime.fromisoformat(start_time1).replace(tzinfo=None)
    t2 = datetime.fromisoformat(start_time2).replace(tzinfo=None)

    if abs(t1 - t2) > _TIME_TOLERANCE:
        return False

    # 거리가 둘 다 0이면 중복으로 판정
    if distance1 == 0 and distance2 == 0:
        return True

    max_dist = max(distance1, distance2)
    if max_dist == 0:
        return False

    distance_diff = abs(distance1 - distance2) / max_dist
    return distance_diff <= _DISTANCE_TOLERANCE


def find_duplicates(activities: list[dict]) -> list[list[dict]]:
    """활동 목록에서 중복 그룹 찾기.

    Args:
        activities: [{"start_time": str, "distance_km": float, ...}, ...] 리스트.

    Returns:
        중복 그룹 리스트. 각 그룹은 2개 이상의 활동 dict 리스트.
    """
    n = len(activities)
    visited: set[int] = set()
    groups: list[list[dict]] = []

    for i in range(n):
        if i in visited:
            continue
        group = [activities[i]]
        for j in range(i + 1, n):
            if j in visited:
                continue
            if is_duplicate(
                activities[i]["start_time"],
                activities[i]["distance_km"],
                activities[j]["start_time"],
                activities[j]["distance_km"],
            ):
                group.append(activities[j])
                visited.add(j)
        if len(group) > 1:
            visited.add(i)
            groups.append(group)

    return groups


def assign_group_id(conn: sqlite3.Connection, activity_id: int) -> str | None:
    """새 활동에 대해 기존 활동과 매칭하여 group_id 할당.

    Args:
        conn: SQLite 연결.
        activity_id: 매칭할 활동 ID.

    Returns:
        할당된 group_id 또는 매칭 없으면 None.
    """
    row = conn.execute(
        "SELECT start_time, distance_km FROM activity_summaries WHERE id = ?",
        (activity_id,),
    ).fetchone()
    if not row:
        return None

    start_time, distance_km = row
    t = datetime.fromisoformat(start_time).replace(tzinfo=None)
    time_min = (t - _TIME_TOLERANCE).isoformat()
    time_max = (t + _TIME_TOLERANCE).isoformat()

    candidates = conn.execute(
        """SELECT id, start_time, distance_km, matched_group_id
           FROM activity_summaries
           WHERE id != ? AND start_time BETWEEN ? AND ?""",
        (activity_id, time_min, time_max),
    ).fetchall()

    for cand_id, cand_time, cand_dist, cand_group in candidates:
        if is_duplicate(start_time, distance_km or 0, cand_time, cand_dist or 0):
            # 기존 그룹이 있으면 재사용, 없으면 새 그룹 생성
            group_id = cand_group or str(uuid.uuid4())[:8]
            conn.execute(
                "UPDATE activity_summaries SET matched_group_id = ? WHERE id IN (?, ?)",
                (group_id, activity_id, cand_id),
            )
            return group_id

    return None
