"""스키마 v39 — goals.race_id 추가 + goals→race_calendar 백필(RC-21·43·49·50·54), 단일 트랜잭션·멱등."""
from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timedelta

from src.utils.reference_day import reference_offset

log = logging.getLogger(__name__)

NOTE_CREATED_DATE = "[v39] 목표 생성일 기준 생성"
_DIST_TOL = 0.01
_INACTIVE_STATUS = {"completed": "done", "cancelled": "cancelled"}


def _main_db_path(conn: sqlite3.Connection) -> str | None:
    for _, name, path in conn.execute("PRAGMA database_list"):
        if name == "main":
            return path or None
    return None


def _backup(conn: sqlite3.Connection, path: str) -> str:
    dest = f"{path}.pre-v39-{datetime.now():%Y%m%d%H%M%S}"
    dst = sqlite3.connect(dest)
    try:
        conn.backup(dst)
    finally:
        dst.close()
    return dest


def _has_col(conn: sqlite3.Connection, table: str, col: str) -> bool:
    return any(r[1] == col for r in conn.execute(f"PRAGMA table_info({table})"))


def dry_run(conn: sqlite3.Connection) -> dict:
    """적용 전 상태 요약(쓰기 없음)."""
    if not _has_col(conn, "goals", "race_id"):
        n = conn.execute("SELECT COUNT(*) FROM goals").fetchone()[0]
        return {"needs_column": True, "goals": n}
    return {"needs_column": False,
            "unlinked": conn.execute("SELECT COUNT(*) FROM goals WHERE race_id IS NULL").fetchone()[0]}


def _local_date(conn: sqlite3.Connection, created_at: str, off: int | None) -> str:
    if off is None:
        return conn.execute("SELECT date(?, 'localtime')", (created_at,)).fetchone()[0]
    dt = datetime.strptime(created_at[:19].replace("T", " "), "%Y-%m-%d %H:%M:%S")
    return (dt + timedelta(seconds=off)).strftime("%Y-%m-%d")


def _find_race(conn, race_date: str, dist: float, status: str):
    return conn.execute(
        "SELECT id, priority, name FROM race_calendar WHERE race_date=? AND status=?"
        " AND ABS(distance_km-?)<=? ORDER BY id LIMIT 1",
        (race_date, status, dist, _DIST_TOL)).fetchone()


def _plan_state(conn, g) -> str:
    start = (g["created_at"] or "")[:10] or g["race_date"]
    n = conn.execute(
        "SELECT COUNT(*) FROM planned_workouts WHERE source='planner' AND date BETWEEN ? AND ?",
        (start, g["race_date"])).fetchone()[0]
    return "applied" if n else "none"


def _link_goal(conn, g, race_date: str, report: dict, *, created_date: bool) -> None:
    active = g["status"] == "active"
    rstatus = "planned" if active else _INACTIVE_STATUS[g["status"]]
    race = _find_race(conn, race_date, g["distance_km"], rstatus)
    if race:
        rid = race["id"]
        report["reused"] += 1
        if race["priority"] != "A":
            conn.execute("UPDATE race_calendar SET priority='A', updated_at=datetime('now') WHERE id=?", (rid,))
            if rstatus == "done":
                report["promotions"].append({"race_id": rid, "name": race["name"], "date": race_date,
                                             "prev_priority": race["priority"], "goal_id": g["id"]})
    else:
        tt = g["target_time_sec"]
        adapt = "adapt" if (active or rstatus == "done") else "unasked"
        plan = _plan_state(conn, g) if active else ("applied" if rstatus == "done" else "none")
        cur = conn.execute(
            "INSERT INTO race_calendar (name, race_date, distance_km, priority, goal_type, goal_value,"
            " adapt_choice, plan_state, status, origin, note) VALUES (?,?,?,?,?,?,?,?,?,'goal',?)",
            (g["name"], race_date, g["distance_km"], "A", "time" if tt else "finish", tt,
             adapt, plan, rstatus, NOTE_CREATED_DATE if created_date else None))
        rid = cur.lastrowid
        report["created"] += 1
    conn.execute("UPDATE goals SET race_id=? WHERE id=?", (rid, g["id"]))
    if report["future_completed"] is not None and g["status"] == "completed" and race_date > report["today"]:
        report["future_completed"] += 1


def resync_cache(conn: sqlite3.Connection) -> list[dict]:
    """연결된 목표의 race_date·distance 캐시가 레이스와 다르면 goals 값을 레이스에 반영(RC-21, 예외행 제외)."""
    diffs = []
    prev, conn.row_factory = conn.row_factory, sqlite3.Row
    rows = conn.execute(
        "SELECT g.id gid, g.race_date, g.distance_km, r.id rid, r.race_date rdate, r.distance_km rdist"
        " FROM goals g JOIN race_calendar r ON r.id=g.race_id WHERE g.race_date IS NOT NULL").fetchall()
    conn.row_factory = prev
    for r in rows:
        if r["race_date"] != r["rdate"] or abs(r["distance_km"] - r["rdist"]) > _DIST_TOL:
            conn.execute("UPDATE race_calendar SET race_date=?, distance_km=?, updated_at=datetime('now') WHERE id=?",
                         (r["race_date"], r["distance_km"], r["rid"]))
            diffs.append({"goal_id": r["gid"], "race_id": r["rid"], "from": [r["rdate"], r["rdist"]],
                          "to": [r["race_date"], r["distance_km"]]})
    return diffs


def _backfill(conn: sqlite3.Connection) -> dict:
    off = reference_offset(conn)
    today = conn.execute("SELECT date('now','localtime')").fetchone()[0]
    report = {"goals": 0, "reused": 0, "created": 0, "no_date_active": 0, "no_date_inactive": 0,
              "promotions": [], "cache_diffs": [], "future_completed": 0, "today": today}
    goals = conn.execute("SELECT * FROM goals WHERE race_id IS NULL ORDER BY id").fetchall()
    report["goals"] = len(goals)
    for g in goals:
        if g["race_date"]:
            _link_goal(conn, g, g["race_date"], report, created_date=False)
        elif g["status"] == "active":
            report["no_date_active"] += 1
        else:
            report["no_date_inactive"] += 1
            _link_goal(conn, g, _local_date(conn, g["created_at"], off), report, created_date=True)
    report["cache_diffs"] = resync_cache(conn)
    return report


def _check_invariant3(conn: sqlite3.Connection) -> None:
    bad = conn.execute(
        "SELECT g.id FROM goals g JOIN race_calendar r ON r.id=g.race_id"
        " WHERE g.status='active' AND NOT (r.priority='A' AND r.status IN ('planned','done'))").fetchall()
    if bad:
        raise RuntimeError(f"v39 불변식 3 위반 목표: {[b[0] for b in bad]}")


def ensure_v39(conn: sqlite3.Connection, *, backup: bool = True) -> dict:
    """goals.race_id 추가·백필·ux_goals_race 생성. 실패 시 롤백하고 예외(user_version 미갱신)."""
    prev_factory = conn.row_factory
    conn.row_factory = sqlite3.Row
    try:
        path = _main_db_path(conn)
        uv = conn.execute("PRAGMA user_version").fetchone()[0]
        n_goals = conn.execute("SELECT COUNT(*) FROM goals").fetchone()[0]
        if backup and path and uv < 39 and n_goals:
            dest = _backup(conn, path)
            log.info("v39 백업: %s", dest)
        conn.commit()
        conn.execute("SAVEPOINT v39")
        try:
            if not _has_col(conn, "goals", "race_id"):
                conn.execute("ALTER TABLE goals ADD COLUMN race_id INTEGER REFERENCES race_calendar(id)")
            report = _backfill(conn)
            _check_invariant3(conn)
            conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_goals_race ON goals(race_id)"
                         " WHERE race_id IS NOT NULL AND status='active'")
            conn.execute("RELEASE v39")
        except Exception:
            conn.execute("ROLLBACK TO v39")
            conn.execute("RELEASE v39")
            raise
        return report
    finally:
        conn.row_factory = prev_factory
