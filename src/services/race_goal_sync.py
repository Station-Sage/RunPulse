"""목표↔대회 동기화 (RC §2.2·2.3) — goals 의 race_date·distance_km·target_time_sec 은 race_calendar 의 읽기 호환 캐시.

캐시는 이 모듈만 쓴다. RC-21 예외행(비활성 목표, race_id 있음, race_date NULL)은 날짜가 실제 입력될 때만 채운다.
트리거 없이 서비스가 불변식 3(활성 목표 대회는 A·planned/done)·4(캐시=대회)를 지키고, 검증은 check_data_consistency 가 한다.
commit 은 모두 호출자.
"""
from __future__ import annotations

import sqlite3

from src.services import race_calendar_query as q
from src.services.race_calendar_query import RaceError


def _plan_weeks(race_date: str) -> int | None:
    from src.training.goals import _plan_weeks
    return _plan_weeks(race_date)


def push_cache(conn: sqlite3.Connection, race_id: int, *, date_changed: bool = True) -> int:
    """race_id 를 가리키는 목표들의 캐시를 대회 값으로 맞춘다. 반환 = 갱신한 목표 수.

    race_date 는 date_changed 이거나 목표가 이미 날짜를 가진 경우만 쓴다(RC-24/26/34, 같은 날짜 재저장은 변경 아님).
    distance_km·target_time_sec 은 항상 동기화한다.
    """
    race = q.require(conn, race_id)
    tt = int(race["goal_value"]) if race["goal_type"] == "time" and race["goal_value"] else None
    n = 0
    for gid, gdate in conn.execute("SELECT id, race_date FROM goals WHERE race_id=?", (race_id,)).fetchall():
        if gdate is not None or date_changed:
            conn.execute("UPDATE goals SET race_date=?, plan_weeks=? WHERE id=?",
                         (race["race_date"], _plan_weeks(race["race_date"]), gid))
        conn.execute("UPDATE goals SET distance_km=?, target_time_sec=? WHERE id=?", (race["distance_km"], tt, gid))
        n += 1
    return n


def demote_a(conn: sqlite3.Connection, race_id: int) -> None:
    """A → B·unasked·none (RC-15). 활성 목표에 연결된 대회는 강등할 수 없다(불변식 3)."""
    if q.is_goal_race(conn, race_id):
        raise RaceError("GOAL_LINKED", "활성 목표에 연결된 대회는 B로 바꿀 수 없습니다")
    conn.execute("UPDATE race_calendar SET priority='B', adapt_choice='unasked', plan_state='none',"
                 " updated_at=datetime('now') WHERE id=?", (race_id,))


def promote_to_a(conn: sqlite3.Connection, race_id: int) -> None:
    """대회를 A 로 올리고 연결 목표용 값(adapt·applied 고정)으로 맞춘다. 다른 planned A 는 먼저 강등한다."""
    q.require(conn, race_id)
    other = q.find_other_a(conn, race_id)
    if other and other["status"] == "planned":
        demote_a(conn, other["id"])  # done 이던 이전 A 는 그대로 둔다(§2.2)
    conn.execute("UPDATE race_calendar SET priority='A', adapt_choice='adapt', plan_state='applied',"
                 " updated_at=datetime('now') WHERE id=?", (race_id,))


def link_goal(conn: sqlite3.Connection, goal_id: int, race_id: int) -> None:
    """활성 목표를 race_id 대회에 연결(복원·되돌리기 goal_link 경로). 대회는 A 가 되고 캐시를 맞춘다."""
    race = q.require(conn, race_id)
    if race["status"] == "cancelled":
        raise RaceError("RACE_CANCELLED", "취소된 대회에는 연결할 수 없습니다")
    g = conn.execute("SELECT status FROM goals WHERE id=?", (goal_id,)).fetchone()
    if not g or g[0] != "active":
        raise RaceError("GOAL_NOT_ACTIVE", "활성 목표가 아닙니다", http=404)
    promote_to_a(conn, race_id)
    conn.execute("UPDATE goals SET race_id=NULL WHERE race_id=? AND id != ? AND status='active'", (race_id, goal_id))
    conn.execute("UPDATE goals SET race_id=? WHERE id=?", (race_id, goal_id))
    push_cache(conn, race_id)


def attach_race(conn: sqlite3.Connection, goal_id: int, race_date: str, *, name: str | None = None) -> int:
    """날짜 없는 활성 목표에 날짜를 줄 때(RC-11 b): A 대회를 만들고 race_id·캐시를 한 번에 기록. 반환 = race id."""
    g = conn.execute("SELECT name, distance_km, target_time_sec, race_id FROM goals WHERE id=? AND status='active'",
                     (goal_id,)).fetchone()
    if not g:
        raise RaceError("GOAL_NOT_ACTIVE", "활성 목표가 아닙니다", http=404)
    if g[3] is not None:
        raise RaceError("ALREADY_LINKED", "이미 대회가 연결된 목표입니다")
    from src.services import race_calendar_service as svc
    race = svc.add(conn, {"name": name or g[0], "race_date": race_date, "distance_km": g[1], "priority": "A",
                          "goal_type": "time" if g[2] else "finish", "goal_value": g[2], "origin": "goal"},
                   as_goal=True)
    link_goal(conn, goal_id, race["id"])
    return race["id"]


def check_invariants(conn: sqlite3.Connection) -> list[str]:
    """불변식 3·4 위반 설명(빈 리스트면 정상). RC-21 예외행은 race_date 비교를 건너뛴다."""
    bad = [f"goal {r[0]}: active race_id={r[1]} is not A planned/done" for r in conn.execute(
        "SELECT g.id, g.race_id FROM goals g JOIN race_calendar r ON r.id=g.race_id"
        " WHERE g.status='active' AND NOT (r.priority='A' AND r.status IN ('planned','done'))")]
    for gid, gdate, gdist, rdate, rdist in conn.execute(
            "SELECT g.id, g.race_date, g.distance_km, r.race_date, r.distance_km FROM goals g"
            " JOIN race_calendar r ON r.id=g.race_id"):
        if gdate is not None and gdate != rdate:
            bad.append(f"goal {gid}: cache race_date {gdate} != race {rdate}")
        if abs((gdist or 0) - rdist) > 1e-6:
            bad.append(f"goal {gid}: cache distance {gdist} != race {rdist}")
    return bad
