"""대회 확인(race_results, P7-PRED-53) — 사용자가 대회 여부·전력 여부·공식 기록을 확정한다.

예측(P7-PRED-51)은 확정된 effort 가 'allout' 인 대회만 앵커로 쓰고, 공식 기록이 있으면 기기 기록 대신 쓴다.
미확정 대회는 기존 규칙(이름·event_type + 평균 HR ≥ 0.84·HRmax)으로 추정한다.
"""
from __future__ import annotations

import re
import sqlite3

EFFORTS = ("allout", "paced", "fun", "dnf")
_RACE_NAME = re.compile(r"대회|마라톤|marathon|half|하프|10k|10km|race|레이스", re.I)
_NOT_RACE = re.compile(r"TT|템포|tempo", re.I)


def confirm(conn: sqlite3.Connection, activity_id: int, effort: str, official_time_sec: int | None = None,
            race_name: str | None = None, distance_m: float | None = None, note: str | None = None) -> dict:
    if effort not in EFFORTS:
        raise ValueError(f"effort must be one of {EFFORTS}")
    if official_time_sec is not None and not 600 <= official_time_sec <= 8 * 3600:
        raise ValueError("official_time_sec out of range")
    row = conn.execute("SELECT distance_m FROM activity_summaries WHERE id=?", (activity_id,)).fetchone()
    if row is None:
        raise LookupError("activity not found")
    distance_m = distance_m or row[0]              # 미입력 시 기기 거리
    conn.execute(
        "INSERT INTO race_results (activity_id, race_name, distance_m, official_time_sec, effort, note, confirmed_at) "
        "VALUES (?,?,?,?,?,?, datetime('now')) ON CONFLICT(activity_id) DO UPDATE SET race_name=excluded.race_name, "
        "distance_m=excluded.distance_m, official_time_sec=excluded.official_time_sec, effort=excluded.effort, "
        "note=excluded.note, confirmed_at=excluded.confirmed_at",
        (activity_id, race_name, distance_m, official_time_sec, effort, note))
    conn.commit()
    return get(conn, activity_id)


def remove(conn: sqlite3.Connection, activity_id: int) -> bool:
    n = conn.execute("DELETE FROM race_results WHERE activity_id=?", (activity_id,)).rowcount
    conn.commit()
    return n > 0


def get(conn: sqlite3.Connection, activity_id: int) -> dict | None:
    r = conn.execute("SELECT activity_id, race_name, distance_m, official_time_sec, effort, note, confirmed_at "
                     "FROM race_results WHERE activity_id=?", (activity_id,)).fetchone()
    keys = ("activity_id", "race_name", "distance_m", "official_time_sec", "effort", "note", "confirmed_at")
    return dict(zip(keys, r)) if r else None


def candidates(conn: sqlite3.Connection, since: str) -> list[dict]:
    """확인이 필요한 대회 후보(since 이후, canonical 러닝, 이름 또는 event_type 으로 대회로 보이는 것) — 최신순."""
    rows = conn.execute(
        "SELECT v.id, substr(v.start_time,1,10), v.name, v.distance_m, COALESCE(v.elapsed_time_sec, v.duration_sec), "
        "v.event_type, r.effort FROM v_canonical_activities v LEFT JOIN race_results r ON r.activity_id = v.id "
        "WHERE v.start_time >= ? AND v.activity_type IN ('running','trail_running') ORDER BY v.start_time DESC",
        (since,)).fetchall()
    out = []
    for aid, d, name, dist, t, ev, eff in rows:
        looks = ev == "race" or (bool(_RACE_NAME.search(name or "")) and not _NOT_RACE.search(name or ""))
        if looks or eff:
            out.append({"activity_id": aid, "date": d, "name": name, "distance_m": dist, "time_sec": t,
                        "confirmed_effort": eff})
    return out
