"""기존 계획 정정 도구 — 자동 매칭 재평가 + 대회일 기준 미래 주차 재생성.

  python3 -m src.training.rematch --db <running.db> [--replan]

- 재매칭: 자동 매칭된 planner 행(matched_activity_id 있음)만 초기화 후 새 규칙(match_select)으로 다시 매칭.
  수동 완료(matched_activity_id 없음)는 건드리지 않는다. 외부 계획 행은 결과 라벨만 다시 계산한다.
- --replan: 대회 역산 주기화로 계획을 다시 짠다 — plan_weeks 를 대회 주까지로 정정, 대회 이후 행 삭제,
  이번 주 남은 날부터 대회 주까지 재생성(지난 날·완료·연결된 행은 보존).
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import date, timedelta

from src.training.goals import get_active_goal
from src.training.matcher import match_week_activities
from src.training.matcher_context import canonical_activity_id
from src.training.outcome_store import update_outcome_v2
from src.training.plan_structure import structure_for_plan
from src.training.planner import generate_weekly_plan, save_weekly_plan


def _backfill_structure(conn: sqlite3.Connection, start: date, end: date) -> int:
    """structure_json 이 없는 planner 행에 세그먼트 구조를 채운다(세트·구간 페이스 분석의 기준)."""
    n = 0
    for pid, wt, km, pmin, pmax, rx in conn.execute(
            "SELECT id, workout_type, distance_km, target_pace_min, target_pace_max, interval_prescription "
            "FROM planned_workouts WHERE source='planner' AND structure_json IS NULL AND date BETWEEN ? AND ?",
            (start.isoformat(), end.isoformat())).fetchall():
        st = structure_for_plan(wt, km, pmin, pmax, rx)
        if st:
            conn.execute("UPDATE planned_workouts SET structure_json=? WHERE id=?", (json.dumps(st), pid))
            n += 1
    return n


def rematch(conn: sqlite3.Connection, start: date, end: date) -> dict:
    """[start, end] 의 자동 매칭을 새 규칙으로 다시 계산. 반환: {"reset", "matched", "external"}."""
    _backfill_structure(conn, start, end)
    rows = conn.execute(
        "SELECT id FROM planned_workouts WHERE source='planner' AND matched_activity_id IS NOT NULL "
        "AND date BETWEEN ? AND ?", (start.isoformat(), end.isoformat())).fetchall()
    for (pid,) in rows:
        conn.execute("DELETE FROM session_outcomes WHERE planned_id=?", (pid,))
        conn.execute("UPDATE planned_workouts SET completed=0, matched_activity_id=NULL WHERE id=?", (pid,))
    ext = conn.execute(
        "SELECT id, matched_activity_id FROM planned_workouts WHERE source!='planner' AND matched_activity_id IS NOT NULL "
        "AND date BETWEEN ? AND ?", (start.isoformat(), end.isoformat())).fetchall()
    for pid, aid in ext:
        cid = canonical_activity_id(conn, aid)       # 그룹 재편으로 낡은 id 를 현재 canonical 로 교정
        conn.execute("UPDATE planned_workouts SET matched_activity_id=? WHERE id=?", (cid, pid))
        conn.execute("UPDATE session_outcomes SET activity_id=? WHERE planned_id=?", (cid, pid))
        update_outcome_v2(conn, pid, cid)
    matched, ws = 0, start - timedelta(days=start.weekday())
    while ws <= end:
        matched += match_week_activities(conn, ws)
        ws += timedelta(weeks=1)
    conn.commit()
    return {"reset": len(rows), "matched": matched, "external": len(ext)}


def replan_future(conn: sqlite3.Connection, goal_id: int, today: date | None = None) -> dict:
    """대회 역산으로 계획을 다시 짠다: plan_weeks 를 만든 주~대회 주로 정정, 대회 이후 planner 행 삭제,
    이번 주 남은 날(오늘 이후·미완료)과 다음 주~대회 주를 재생성. 이미 지난 날·완료·연결된 행은 그대로 둔다."""
    today = today or date.today()
    g = conn.execute("SELECT race_date, created_at FROM goals WHERE id=?", (goal_id,)).fetchone()
    if not g or not g[0]:
        return {"weeks": None, "regenerated": 0, "deleted": 0}
    race = date.fromisoformat(g[0])
    race_mon = race - timedelta(days=race.weekday())
    created = date.fromisoformat(g[1][:10])
    start_mon = created - timedelta(days=created.weekday())
    weeks = (race_mon - start_mon).days // 7 + 1
    conn.execute("UPDATE goals SET plan_weeks=? WHERE id=?", (weeks, goal_id))
    deleted = conn.execute("DELETE FROM planned_workouts WHERE source='planner' AND date > ?",
                           (race.isoformat(),)).rowcount
    this_mon = today - timedelta(days=today.weekday())
    ws, n = this_mon, 0
    while ws <= race_mon:
        plan = generate_weekly_plan(conn, goal_id=goal_id, week_start=ws)
        if ws == this_mon:
            done = {r[0] for r in conn.execute(
                "SELECT date FROM planned_workouts WHERE source='planner' AND (completed=1 OR matched_activity_id IS NOT NULL)")}
            plan = [w for w in plan if w["date"] >= today.isoformat() and w["date"] not in done]
        save_weekly_plan(conn, plan)
        ws += timedelta(weeks=1)
        n += 1
    conn.commit()
    return {"weeks": weeks, "regenerated": n, "deleted": deleted}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", required=True)
    ap.add_argument("--replan", action="store_true")
    a = ap.parse_args()
    conn = sqlite3.connect(a.db)
    lo, hi = conn.execute("SELECT MIN(date), MAX(date) FROM planned_workouts WHERE source='planner'").fetchone()
    today = date.today()
    print("rematch", rematch(conn, date.fromisoformat(lo), min(date.fromisoformat(hi), today)))
    if a.replan:
        g = get_active_goal(conn)
        if g:
            print("replan", replan_future(conn, g["id"]))


if __name__ == "__main__":
    main()
