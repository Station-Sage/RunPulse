"""재계획(v1 계획 중간 anchor 에서 v2 로 전환) 백테스트 — 전환 이후 주(꼬리)를 게이트로 판정한다 (PLAN-ENGINE E7).

앞 구간은 v1 규칙, anchor 주부터는 plan_replans.rules_version=2 가 적용된 일정이다. 꼬리의 첫 주는 anchor 의 start_km 에서 시작하므로
G6(주간 증가율)은 꼬리 안에서만 본다. 메모리 DB 에서만 동작한다.
"""
from __future__ import annotations

import sqlite3
from datetime import timedelta

from . import plan_gates as G
from . import plan_backtest as B
from .goals import add_goal
from .marathon_rules import mp_now_from_prediction
from .planner import generate_weekly_plan, upsert_user_training_prefs


def engine_replan(scn: B.Scenario, conn: sqlite3.Connection, anchor_k: int) -> tuple[list[G.WeekPlan], dict]:
    """전체 일정을 만들되 anchor_k 주부터 v2. 반환 weeks 는 꼬리(index 0 = anchor 주)만."""
    gid = add_goal(conn, f"bt-rp-{scn.race_date}", B.DIST_KM[scn.distance], scn.race_date, scn.goal_sec, rules_version=1)
    conn.execute("UPDATE goals SET plan_weeks=?, distance_label=? WHERE id=?", (scn.plan_weeks, scn.distance, gid))
    upsert_user_training_prefs(conn, rest_weekdays_mask=B.rest_mask(scn.days))
    start = scn.start_monday
    anchor = start + timedelta(weeks=anchor_k)
    km = max(12.0, float(scn.start_km))
    conn.execute("INSERT INTO plan_replans(goal_id, anchor_monday, start_km, start_source, status, rules_version)"
                 " VALUES (?, ?, ?, 'user', 'applied', 2)", (gid, anchor.isoformat(), km))
    weeks = []
    for k in range(anchor_k, scn.plan_weeks):
        rows = generate_weekly_plan(conn, gid, week_start=start + timedelta(weeks=k), as_of=anchor)
        weeks.append(B._plan_from_rows(k - anchor_k, scn.plan_weeks - 1 - k, rows))
    conn.execute("DELETE FROM plan_replans WHERE goal_id=?", (gid,))
    conn.execute("DELETE FROM goals WHERE id=?", (gid,))
    return weeks, {"anchor_km": km}


def run_replan_scenario(scn: B.Scenario, anchor_k: int) -> dict:
    """합성 시나리오 하나를 anchor_k 주에서 v1→v2 전환해 판정(하드 게이트 G*). 기록 없는(start_km=0) v1 계획은 존재할 수 없어 호출 대상이 아니다."""
    def once() -> tuple[list[G.WeekPlan], dict, sqlite3.Connection]:
        from src.db_setup import create_tables
        mem = sqlite3.connect(":memory:")
        mem.row_factory = sqlite3.Row
        create_tables(mem)
        B.seed_grid_history(mem, scn)
        weeks, aux = engine_replan(scn, mem, anchor_k)
        return weeks, aux, mem

    weeks, aux, mem = once()
    try:
        le = scn.aux["long_eff"]
        inputs = {"start_km": aux["anchor_km"], "start_long": le, "long_max_12w": le, "peak_week_16w": scn.start_km}
        mp = mp_now_from_prediction(mem, None)
        tail_scn = B.Scenario(**{**scn.__dict__, "plan_weeks": len(weeks), "aux": {}})
        gates = B.judge(tail_scn, weeks, inputs, lambda: once()[0], mp_now=(lambda w: mp) if mp else None)
    finally:
        mem.close()
    return {"scenario": {k: v for k, v in scn.__dict__.items() if k != "aux"}, "anchor_k": anchor_k,
            "gates": {k: {"violations": r.violations, "worst": r.worst} for k, r in gates.items()},
            "pass": all(r.ok for k, r in gates.items() if k.startswith("G"))}


MIN_TAIL_WEEKS = 5      # 남은 주가 이보다 짧으면 12km 하한이 테이퍼 비율을 깨므로 격자에서 제외(재계획 진입은 대회 12일 전까지만 막는다)


def replan_grid() -> list[tuple[B.Scenario, int]]:
    """합성 격자(기록 있는 시작 부하) × anchor 위치(계획의 1/3·1/2 지점, 꼬리 ≥ MIN_TAIL_WEEKS)."""
    out = []
    for s in B.grid_scenarios():
        if s.start_km <= 0:
            continue
        for k in sorted({s.plan_weeks // 3, s.plan_weeks // 2}):
            if s.plan_weeks - k >= MIN_TAIL_WEEKS:
                out.append((s, k))
    return out


def run_replan_grid(distance: str | None = None, limit: int = 0) -> dict:
    items = [(s, k) for s, k in replan_grid() if not distance or s.distance == distance]
    if limit:
        items = items[:limit]
    res = [run_replan_scenario(B.Scenario(**{**s.__dict__, "aux": {}}), k) for s, k in items]
    return {"total": len(res), "passed": sum(r["pass"] for r in res), "failed": [r for r in res if not r["pass"]][:10]}
