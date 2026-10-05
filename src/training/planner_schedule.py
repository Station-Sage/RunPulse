"""목표 대회 역산 주간 목표 조회 — 최근 훈련량(DB)을 읽어 periodization.build_schedule 에 넣는다.

계획 시작 직전 4주의 주평균 거리와 최근 6주 최장 러닝이 출발점이라, 같은 계획을 언제 다시 만들어도 같은 결과가 나온다.
"""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from .goals import get_rules_version
from .periodization import WeekTarget, build_schedule
from .planner_config import DISTANCE_LABEL_KM, LONG_RUN_BASE
from .planner_rules import plan_start_monday
from .readiness import get_taper_weeks, recommend_weekly_km

_RUN = "('running','run','virtualrun','treadmill','highintensityintervaltraining')"
_LONG_CAP = {"full": 0.50, "half": 0.50}      # 그 외 0.40


def recent_load(conn: sqlite3.Connection, as_of: date) -> tuple[float, float]:
    """(as_of 직전 4주 주평균 km, 직전 6주 최장 러닝 km). 데이터가 없으면 (0, 0)."""
    def _sum(days: int, agg: str) -> float:
        r = conn.execute(
            f"SELECT {agg}(distance_m) FROM v_canonical_activities WHERE activity_type IN {_RUN} "
            "AND DATE(start_time) >= ? AND DATE(start_time) < ?",
            ((as_of - timedelta(days=days)).isoformat(), as_of.isoformat())).fetchone()
        return float(r[0] or 0.0) / 1000.0
    return round(_sum(28, "SUM") / 4, 1), round(_sum(42, "MAX"), 1)


def _rules_version(conn: sqlite3.Connection, goal: dict) -> int:
    return get_rules_version(conn, goal["id"]) if goal.get("id") is not None else 1


def schedule_for_goal(conn: sqlite3.Connection, goal: dict, dlabel: str, vdot: float | None,
                      today: date | None = None) -> list[WeekTarget]:
    """goal(race_date·plan_weeks 필요)의 주별 목표. 계획 정보가 부족하면 빈 리스트(호출부가 기존 규칙으로 폴백)."""
    start = plan_start_monday(goal.get("race_date"), goal.get("plan_weeks"))
    if start is None:
        return []
    today = today or date.today()
    start_km, start_long = recent_load(conn, min(start, today))
    if start_km <= 0:
        return []
    peak = recommend_weekly_km(vdot, dlabel, "peak", 0, goal["plan_weeks"]) if vdot else start_km * 1.3
    return build_schedule(int(goal["plan_weeks"]), start_km, start_long, max(peak, start_km),
                          LONG_RUN_BASE.get(dlabel, 14.0), _LONG_CAP.get(dlabel, 0.40),
                          get_taper_weeks(DISTANCE_LABEL_KM.get(dlabel, goal["distance_km"])),
                          _rules_version(conn, goal))


def week_target(conn: sqlite3.Connection, goal: dict, week_start: date, dlabel: str, vdot: float | None) -> WeekTarget | None:
    """week_start 가 계획 범위 안이면 그 주 목표, 밖이면 None."""
    start = plan_start_monday(goal.get("race_date"), goal.get("plan_weeks"))
    if start is None:
        return None
    idx = (week_start - start).days // 7
    sched = schedule_for_goal(conn, goal, dlabel, vdot)
    return sched[idx] if 0 <= idx < len(sched) else None
