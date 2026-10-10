"""주간 적응 서비스 — 지난주 이행도·CRS·ACWR를 읽어 weekly_adapt 규칙으로 이번 주 계획 행을 조정한다(v2 목표만)."""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from src.training import weekly_adapt as WA

CRS_RED_SCORE = 20.0      # crs 점수 범위 rest=[0,20)


def _metric_series(conn: sqlite3.Connection, name: str, start: date, end: date) -> list[float]:
    try:
        rows = conn.execute(
            "SELECT numeric_value FROM metric_store WHERE scope_type='daily' AND metric_name=? AND is_primary=1"
            " AND scope_id >= ? AND scope_id < ? AND numeric_value IS NOT NULL",
            (name, start.isoformat(), end.isoformat())).fetchall()
    except sqlite3.OperationalError:
        return []
    return [float(r[0]) for r in rows]


def load_input(conn: sqlite3.Connection, goal: dict, week_start: date, dlabel: str, vdot: float | None,
               injury_flag: bool = False) -> WA.AdaptInput | None:
    from src.training.planner_schedule import week_target
    from src.training.week_compliance import compute
    prev = week_start - timedelta(days=7)
    this_t, next_t = week_target(conn, goal, prev, dlabel, vdot), week_target(conn, goal, week_start, dlabel, vdot)
    if next_t is None:
        return None
    vol = compute(conn, prev, week_start - timedelta(days=1), prev, week_start)["compliance"]
    pct = vol["volume"].get("pct")
    qual = vol["quality"]
    acwr = _metric_series(conn, "acwr", week_start - timedelta(days=1), week_start)
    red = sum(1 for v in _metric_series(conn, "crs", prev, week_start) if v < CRS_RED_SCORE)
    return WA.AdaptInput(
        volume_pct=None if pct is None else pct / 100.0,
        quality_pct=(qual["done"] / qual["total"]) if qual.get("total") else None,
        last_actual_km=float(vol["volume"].get("actual_km") or 0.0),
        this_target_km=this_t.weekly_km if this_t else next_t.weekly_km,
        sched_next_km=next_t.weekly_km, acwr=acwr[-1] if acwr else None, crs_red_days=red,
        injury_flag=injury_flag, next_phase=next_t.phase)


def adapt_plan(conn: sqlite3.Connection, goal: dict | None, rows: list[dict], week_start: date,
               dlabel: str, vdot: float | None, injury_flag: bool = False) -> list[dict]:
    """v2 목표이고 지난주 이행 데이터가 있으면 조정된 행을, 아니면 입력을 그대로 돌려준다."""
    from src.training.goals import effective_rules_version
    if not goal or effective_rules_version(conn, goal["id"], week_start) < 2:
        return rows
    x = load_input(conn, goal, week_start, dlabel, vdot, injury_flag)
    if x is None:
        return rows
    d = WA.decide(x)
    if d.rule in ("no_data", "proceed"):
        return rows
    return WA.apply_to_rows(rows, d, x.sched_next_km)
