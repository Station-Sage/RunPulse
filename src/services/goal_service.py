"""목표+대회 생성 (RC §2.3) — 대회를 A 로 만들거나 올린 뒤 add_goal(race_id=…). commit 은 호출자.

이전 활성 목표는 add_goal 이 취소하고, 이전 planned A 는 같은 트랜잭션에서 B·unasked·none 으로 강등한다(done A 는 그대로).
"""
from __future__ import annotations

import sqlite3

from src.services import race_calendar_query as q
from src.services import race_calendar_service as svc
from src.services import race_goal_sync as sync
from src.services.race_calendar_query import RaceError
from src.training import goals


def create_goal_with_race(conn: sqlite3.Connection, *, name: str, distance_km: float, race_date: str,
                          target_time_sec: int | None = None, race_id: int | None = None, **goal_kwargs) -> dict:
    """race_id 가 있으면 그 대회를 A 로 승격해 연결, 없으면 새 A 대회를 만든다. 반환 = 새 목표 dict."""
    if race_id is None:  # 같은 날짜·거리 planned 대회가 있으면 새로 만들지 않고 재사용
        same = conn.execute("SELECT id FROM race_calendar WHERE status='planned' AND race_date=? AND distance_km=?",
                            (race_date, distance_km)).fetchone()
        race_id = same[0] if same else None
    old = conn.execute("SELECT id, race_id FROM goals WHERE status='active'").fetchone()
    if old:
        conn.execute("UPDATE goals SET status='cancelled' WHERE id=?", (old[0],))
        prev = q.get(conn, old[1]) if old[1] else None
        if prev and prev["status"] == "planned" and prev["id"] != race_id:
            sync.demote_a(conn, prev["id"])
    if race_id is not None:
        race = q.require(conn, race_id)
        if race["status"] == "cancelled":
            raise RaceError("RACE_CANCELLED", "취소된 대회는 목표로 쓸 수 없습니다")
        other = q.find_other_a(conn, race_id)
        if other and other["status"] == "planned":
            sync.demote_a(conn, other["id"])
        race_date, distance_km = race["race_date"], race["distance_km"]
    else:
        other = q.find_other_a(conn)
        if other and other["status"] == "planned":
            sync.demote_a(conn, other["id"])
        race = svc.add(conn, {"name": name, "race_date": race_date, "distance_km": distance_km, "priority": "A",
                              "goal_type": "time" if target_time_sec else "finish", "goal_value": target_time_sec,
                              "origin": "goal"}, as_goal=True)
        race_id = race["id"]
    gid = goals.add_goal(conn, name, distance_km, race_date=None, target_time_sec=target_time_sec,
                         commit=False, race_id=race_id, **goal_kwargs)
    sync.link_goal(conn, gid, race_id)
    return goals.get_goal(conn, gid)
