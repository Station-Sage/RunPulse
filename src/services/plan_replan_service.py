"""안전한 재계획 서비스 — preview / apply / undo (ADR-035 부록 R).

같은 목표를 유지한 채 다음 월요일(anchor)부터 대회 주까지만 새 시작 부하로 다시 만든다.
이력 행은 지킨다(plan_replace). preview 는 apply 와 같은 경로를 SAVEPOINT 안에서 돌린 뒤 되돌려 쓰기가 없다.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date, timedelta

from src.training.goals import get_active_goal
from src.training.plan_replace import replace_range
from src.training.planner import generate_weekly_plan
from src.training.planner_rules import plan_start_monday, resolve_distance_label
from src.training import personalize as P
from src.training.planner_schedule import COLD_WEEK_KM, cold_start_km, recent_avg_km, recent_load, recent_long_max


class ReplanError(Exception):
    """code: NO_GOAL(404) / RACE_WEEK·CONFLICT·REPLAN_LOCKED(409)."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def next_monday(today: date) -> date:
    return today + timedelta(days=7 - today.weekday())


def _weekly_km(conn: sqlite3.Connection, start: str, end: str) -> list[dict]:
    """주별 {week_start, planned_km, long_km}. long_km 은 그 주 long·long_mp 세션 중 최대 거리(없으면 0)."""
    rows = conn.execute(
        "SELECT date, COALESCE(distance_km, 0), workout_type FROM planned_workouts WHERE source='planner'"
        " AND date>=? AND date<=? AND workout_type != 'rest' ORDER BY date", (start, end)).fetchall()
    out: dict[str, list[float]] = {}
    for d, km, wt in rows:
        dd = date.fromisoformat(d)
        w = out.setdefault((dd - timedelta(days=dd.weekday())).isoformat(), [0.0, 0.0])
        w[0] += float(km)
        if wt in ("long", "long_mp"):
            w[1] = max(w[1], float(km))
    return [{"week_start": k, "planned_km": round(v[0], 1), "long_km": round(v[1], 1)} for k, v in sorted(out.items())]


def _goal_and_anchor(conn: sqlite3.Connection, today: date) -> tuple[dict, date, date]:
    goal = get_active_goal(conn)
    if goal is None or not goal.get("race_date") or plan_start_monday(goal["race_date"], goal.get("plan_weeks")) is None:
        raise ReplanError("NO_GOAL", "대회일이 있는 활성 목표가 없습니다")
    race = date.fromisoformat(goal["race_date"])
    anchor = next_monday(today)
    if anchor > race:
        raise ReplanError("RACE_WEEK", "대회 주에는 재계획할 수 없습니다")
    return goal, anchor, race


def _start_km(conn: sqlite3.Connection, goal: dict, today: date, user_km: float | None) -> tuple[float, str, dict]:
    """(시작 km, 출처, 근거). 출처: history(km4≥12) / floor(0<km4<12, 12km) / user·avg16·default(km4=0)."""
    dlabel = resolve_distance_label(goal["distance_km"], goal.get("distance_label"))
    km4, long6 = recent_load(conn, today)
    avg16, long12 = recent_avg_km(conn, today, 16), recent_long_max(conn, today, 12)
    km, cold_src = cold_start_km(dlabel, km4, avg16, user_km)
    src = "history" if km4 >= COLD_WEEK_KM else "floor" if km4 > 0 else cold_src
    return km, src, {"km4": km4, "avg16": avg16, "long6": long6, "long12": long12}


def _run(conn: sqlite3.Connection, today: date, p: dict, write: bool) -> dict:
    goal, anchor, race = _goal_and_anchor(conn, today)
    user_km, user_long, target = p.get("recent_weekly_km"), p.get("recent_long_km"), p.get("target_time_sec")
    start_km, start_source, basis = _start_km(conn, goal, today, user_km)
    if not user_long:
        user_long = P.start_long_km(basis["long6"], basis["long12"]) or None
    end = (race - timedelta(days=race.weekday()) + timedelta(days=6)).isoformat()
    a_iso = anchor.isoformat()
    conn.execute("SAVEPOINT replan")
    try:
        before = _weekly_km(conn, a_iso, end)
        conn.execute(
            "INSERT INTO plan_replans(goal_id, anchor_monday, start_km, start_long_km, start_source, target_time_sec)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (goal["id"], a_iso, start_km, user_long, start_source, target))
        replan_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        plan, ws = [], anchor
        while ws <= race:
            plan += generate_weekly_plan(conn, goal_id=goal["id"], week_start=ws)
            ws += timedelta(weeks=1)
        res = replace_range(conn, plan, a_iso, end)
        after = _weekly_km(conn, a_iso, end)
        if write:
            conn.execute("UPDATE plan_replans SET replaced_json=? WHERE id=?", (json.dumps(
                {"deleted": res["snapshot"], "inserted": res["inserted"]}, ensure_ascii=False), replan_id))
        else:
            conn.execute("ROLLBACK TO replan")
        conn.execute("RELEASE replan")
    except Exception:
        conn.execute("ROLLBACK TO replan")
        conn.execute("RELEASE replan")
        raise
    if write:
        conn.commit()
    return {"replan_id": replan_id if write else None, "anchor_monday": a_iso, "start_km": start_km,
            "start_source": start_source, "basis": basis, "goal_target_time_sec": goal.get("target_time_sec"),
            "start_long_km": user_long, "target_time_sec": target, "before": before, "after": after,
            "deleted_count": len(res["deleted"]), "preserved": res["preserved"], "external": res["external"],
            "skipped_dates": res["skipped_dates"]}


def preview(conn: sqlite3.Connection, params: dict, today: date | None = None) -> dict:
    """쓰기 없이 재계획 결과 요약(주별 거리 전/후, 보존·외부 항목)."""
    return _run(conn, today or date.today(), params, write=False)


def apply(conn: sqlite3.Connection, params: dict, today: date | None = None) -> dict:
    """재계획 적용. params['expect_anchor'] 가 오늘 기준 anchor 와 다르면 CONFLICT."""
    today = today or date.today()
    if params.get("expect_anchor") != next_monday(today).isoformat():
        raise ReplanError("CONFLICT", "기준일이 바뀌었습니다. 미리보기를 다시 확인하세요")
    return _run(conn, today, params, write=True)


def last_undoable(conn: sqlite3.Connection, today: date | None = None) -> dict | None:
    """활성 목표의 마지막 applied 재계획이 아직 시작 전이면 {replan_id, anchor_monday, undo_until}, 아니면 None."""
    today = today or date.today()
    goal = get_active_goal(conn)
    if goal is None:
        return None
    row = conn.execute("SELECT id, anchor_monday FROM plan_replans WHERE goal_id=? AND status='applied' "
                       "ORDER BY anchor_monday DESC, id DESC LIMIT 1", (goal["id"],)).fetchone()
    if row is None or today >= date.fromisoformat(row[1]):
        return None
    return {"replan_id": row[0], "anchor_monday": row[1],
            "undo_until": (date.fromisoformat(row[1]) - timedelta(days=1)).isoformat()}


def undo(conn: sqlite3.Connection, replan_id: int, today: date | None = None) -> dict:
    """마지막으로 적용된 anchor 를 시작 전에만 되돌린다. 조건 위반은 REPLAN_LOCKED."""
    today = today or date.today()
    row = conn.execute("SELECT goal_id, anchor_monday, status, replaced_json FROM plan_replans WHERE id=?",
                       (replan_id,)).fetchone()
    if row is None:
        raise ReplanError("NO_GOAL", "재계획 기록이 없습니다")
    goal_id, a_iso, status, blob = row
    last = conn.execute("SELECT id FROM plan_replans WHERE goal_id=? AND status='applied' "
                        "ORDER BY anchor_monday DESC, id DESC LIMIT 1", (goal_id,)).fetchone()
    if status != "applied" or last is None or last[0] != replan_id:
        raise ReplanError("REPLAN_LOCKED", "마지막 재계획만 되돌릴 수 있습니다")
    if today >= date.fromisoformat(a_iso):
        raise ReplanError("REPLAN_LOCKED", "이미 시작된 재계획은 되돌릴 수 없습니다")
    saved = json.loads(blob or "{}")
    ins = saved.get("inserted", [])
    if ins and conn.execute(
            f"SELECT 1 FROM planned_workouts w WHERE w.id IN ({','.join('?' * len(ins))}) AND (w.completed=1 "
            "OR w.matched_activity_id IS NOT NULL OR EXISTS (SELECT 1 FROM session_outcomes o WHERE o.planned_id=w.id) "
            "OR EXISTS (SELECT 1 FROM plan_adjustments a WHERE a.workout_id=w.id AND a.decision='accepted')) LIMIT 1",
            ins).fetchone():
        raise ReplanError("REPLAN_LOCKED", "새 계획 행에 이력이 생겨 되돌릴 수 없습니다")
    conn.execute("SAVEPOINT undo")
    try:
        if ins:
            ph = ",".join("?" * len(ins))
            conn.execute(f"DELETE FROM plan_adjustments WHERE workout_id IN ({ph}) AND decision != 'accepted'", ins)
            conn.execute(f"DELETE FROM planned_workouts WHERE id IN ({ph})", ins)
        for d in saved.get("deleted", []):
            cols = list(d)
            conn.execute(f"INSERT INTO planned_workouts({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
                         [d[c] for c in cols])
        conn.execute("UPDATE plan_replans SET status='undone', undone_at=datetime('now') WHERE id=?", (replan_id,))
        conn.execute("RELEASE undo")
    except Exception:
        conn.execute("ROLLBACK TO undo")
        conn.execute("RELEASE undo")
        raise
    conn.commit()
    return {"replan_id": replan_id, "restored": len(saved.get("deleted", [])), "removed": len(ins)}
