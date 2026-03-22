"""중복 활동 매칭 유틸리티 (timestamp ±5분, distance ±3%)."""

import sqlite3
import uuid
from datetime import datetime, timedelta


# 매칭 허용 오차
# - 시간: Garmin은 GPS lock 즉시, Strava는 약간 늦게 시작 → 7분으로 여유
# - 거리: Strava/Garmin/intervals.icu GPS 알고리즘 차이로 같은 활동도 5~16% 편차 발생
#         크로스 소스 매칭 허용 (동일 소스 내 중복은 source 체크로 별도 관리)
_TIME_TOLERANCE = timedelta(minutes=7)
_DISTANCE_TOLERANCE = 0.15  # 15%


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


def auto_group_all(conn: sqlite3.Connection) -> dict[str, int]:
    """모든 활동을 대상으로 cross-source 중복 매칭을 재실행.

    ±5분 AND ±3% 거리 조건을 만족하는 활동 쌍에
    matched_group_id를 일괄 할당한다.
    단일 소스 내 중복은 무시 (source가 다른 쌍만 묶음).

    Returns:
        {"groups_created": n, "activities_grouped": n}
    """
    rows = conn.execute(
        "SELECT id, source, start_time, distance_km, matched_group_id "
        "FROM activity_summaries ORDER BY start_time"
    ).fetchall()

    # id → 현재 group_id (메모리에서 관리)
    group_map: dict[int, str | None] = {r[0]: r[4] for r in rows}
    acts = [
        {"id": r[0], "source": r[1], "start_time": r[2], "distance_km": r[3]}
        for r in rows
    ]

    grouped_ids: set[int] = set()

    for i in range(len(acts)):
        a = acts[i]
        if not a["start_time"]:
            continue
        ta = datetime.fromisoformat(a["start_time"]).replace(tzinfo=None)
        time_max = (ta + _TIME_TOLERANCE).isoformat()

        for j in range(i + 1, len(acts)):
            b = acts[j]
            if not b["start_time"]:
                continue
            # 시간 범위를 벗어나면 이후 활동도 모두 벗어남
            if b["start_time"] > time_max:
                break
            # 같은 소스는 묶지 않음
            if a["source"] == b["source"]:
                continue
            if not is_duplicate(
                a["start_time"], a["distance_km"] or 0,
                b["start_time"], b["distance_km"] or 0,
            ):
                continue

            # 기존 group_id 재사용 또는 새로 생성
            gid_a = group_map.get(a["id"])
            gid_b = group_map.get(b["id"])
            gid = gid_a or gid_b or str(uuid.uuid4())[:8]
            # 그룹 병합: 패배 그룹의 모든 멤버를 승리 그룹으로 이전
            losing_gid = gid_b if gid_a else None
            if losing_gid and losing_gid != gid:
                for k in group_map:
                    if group_map[k] == losing_gid:
                        group_map[k] = gid
            group_map[a["id"]] = gid
            group_map[b["id"]] = gid
            grouped_ids.add(a["id"])
            grouped_ids.add(b["id"])

    # 변경된 행만 DB 업데이트
    new_groups = 0
    for act_id, gid in group_map.items():
        if gid is None:
            continue
        original = next((r[4] for r in rows if r[0] == act_id), None)
        if gid != original:
            conn.execute(
                "UPDATE activity_summaries SET matched_group_id = ? WHERE id = ?",
                (gid, act_id),
            )
            if original is None:
                new_groups += 1

    conn.commit()
    return {
        "groups_created": new_groups // 2 + new_groups % 2,
        "activities_grouped": len(grouped_ids),
    }
