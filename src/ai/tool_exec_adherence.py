"""get_plan_adherence 도구 실행기 — 주별 계획 이행 수치(최대 8주)."""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from src.ai.tool_format import columnar


def _exec_get_plan_adherence(conn: sqlite3.Connection, args: dict) -> dict:
    from src.services import plan_service as ps
    from src.services.adherence_review import scope_key
    from src.training import week_compliance
    from src.training.goals import get_active_goal
    weeks = max(1, min(int(args.get("weeks", 4) or 4), 8))
    goal = get_active_goal(conn)
    if not goal:
        return {"weeks": [], "note": "활성 목표 없음"}
    this_monday = date.today() - timedelta(days=date.today().weekday())
    rows, sessions = [], []
    for i in range(weeks, -1, -1):
        ws = this_monday - timedelta(weeks=i)
        wk = week_compliance.compute(conn, ws, ws + timedelta(days=6), ps._effective_start(goal),
                                     goal_id=goal["id"])
        c = wk["compliance"]
        rows.append([scope_key(ws), c["sessions"]["done"], c["sessions"]["total"],
                     c["volume"]["actual_km"], c["volume"]["planned_km"], c["volume"]["pct"],
                     c["quality"]["done"], c["quality"]["total"]])
        for d in wk["days"]:
            eff = d.get("effective") or {}
            if d["state"] in ("pre_plan", "rest") or not eff:
                continue
            sessions.append([d["date"], d["state"], eff.get("workout_type"), d.get("planned_km"),
                             d.get("actual_km"), d.get("reason")])
    out = columnar(["week", "sess_done", "sess_total", "km_actual", "km_planned", "vol_pct",
                    "quality_done", "quality_total"], rows)
    out["sessions"] = columnar(["date", "state", "planned_type", "planned_km", "actual_km", "reason"], sessions)
    return out
