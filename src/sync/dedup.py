"""활동 중복 감지 — 7분 / 15% 규칙.

서로 다른 소스에서 온 같은 실제 활동을 matched_group_id로 묶습니다.
Union-Find 알고리즘으로 3-way 이상 매칭을 지원하고, 기존 그룹을 보존합니다.
"""

from __future__ import annotations

import logging
import sqlite3
import uuid
from datetime import datetime

log = logging.getLogger(__name__)

TIME_THRESHOLD_SEC = 420   # 7분 (utils/dedup.py와 통일)
DISTANCE_THRESHOLD = 0.15  # 15% (GPS 소스 간 실측 오차 허용)


def run(conn: sqlite3.Connection) -> int:
    """전체 activity_summaries에 대해 dedup 실행.

    기존 matched_group_id는 유지하면서 신규 매칭을 추가합니다.
    Returns: 활성 그룹 총 수.
    """
    rows = conn.execute(
        "SELECT id, source, source_id, start_time, distance_m, matched_group_id "
        "FROM activity_summaries ORDER BY start_time"
    ).fetchall()

    col_names = ["id", "source", "source_id", "start_time", "distance_m", "matched_group_id"]
    activities = [dict(zip(col_names, r)) for r in rows]

    n = len(activities)
    parent: dict = {a["id"]: a["id"] for a in activities}

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]  # path compression
            x = parent[x]
        return x

    def union(x: int, y: int) -> None:
        px, py = find(x), find(y)
        if px != py:
            parent[py] = px

    # 기존 그룹을 Union-Find에 반영 (그룹 보존)
    group_seed: dict[str, int] = {}
    for a in activities:
        gid = a["matched_group_id"]
        if gid:
            if gid not in group_seed:
                group_seed[gid] = a["id"]
            else:
                union(a["id"], group_seed[gid])

    # 새 매칭 탐색 (시간순 정렬 + 조기 종료)
    for i in range(n):
        for j in range(i + 1, n):
            a, b = activities[i], activities[j]
            if a["source"] == b["source"]:
                continue
            if find(a["id"]) == find(b["id"]):
                continue  # 이미 같은 컴포넌트
            try:
                ta = datetime.fromisoformat(a["start_time"].replace("Z", ""))
                tb = datetime.fromisoformat(b["start_time"].replace("Z", ""))
                delta = (tb - ta).total_seconds()
                if delta > TIME_THRESHOLD_SEC:
                    break  # 이후 b는 더 늦음 (시간순 정렬)
            except (ValueError, TypeError, AttributeError):
                continue
            if _is_match(a, b):
                union(a["id"], b["id"])

    # 컴포넌트별 멤버 수집
    comp_members: dict = {}
    for a in activities:
        c = find(a["id"])
        comp_members.setdefault(c, []).append(a)

    # 그룹 ID 결정: 기존 ID 우선, 없으면 신규 발급
    comp_gid: dict = {}
    for comp, members in comp_members.items():
        if len(members) < 2:
            continue
        existing = [m["matched_group_id"] for m in members if m["matched_group_id"]]
        comp_gid[comp] = existing[0] if existing else str(uuid.uuid4())

    # DB 업데이트 (변경된 행만)
    updates: list[tuple] = []
    for a in activities:
        comp = find(a["id"])
        new_gid = comp_gid.get(comp)  # None = 단독 활동 → 기존 그룹 해제
        if new_gid != a["matched_group_id"]:
            updates.append((new_gid, a["id"]))

    if updates:
        conn.executemany(
            "UPDATE activity_summaries SET matched_group_id = ? WHERE id = ?",
            updates,
        )
        conn.commit()

    total = len(comp_gid)
    log.info("[dedup] %d groups, %d activities updated", total, len(updates))
    return total


def _is_match(a: dict, b: dict) -> bool:
    """거리 기준 매칭 여부. 시간 체크는 호출 전에 완료됨."""
    da = a.get("distance_m") or 0
    db = b.get("distance_m") or 0
    if da == 0 and db == 0:
        return True   # 둘 다 거리 없음 (실내 운동 등)
    if da == 0 or db == 0:
        return False  # 한쪽만 0 → 종목이 다를 가능성
    return abs(da - db) / max(da, db) <= DISTANCE_THRESHOLD
