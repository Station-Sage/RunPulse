"""목표 대회 역산 주간 목표 조회 — 최근 훈련량(DB)을 읽어 periodization.build_schedule 에 넣는다.

계획 시작 직전 4주의 주평균 거리와 최근 6주 최장 러닝이 출발점이라, 같은 계획을 언제 다시 만들어도 같은 결과가 나온다.
"""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from . import long_run_rules as LR
from . import marathon_rules as MR
from .goals import get_rules_version
from .periodization import WeekTarget, build_schedule
from .planner_config import DISTANCE_LABEL_KM, LONG_RUN_BASE, load_prefs
from .planner_rules import get_paces_from_vdot, plan_start_monday
from .week_structure import feasible_week_km
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


def recent_long_max(conn: sqlite3.Connection, as_of: date, weeks: int = 12) -> float:
    """as_of 직전 weeks 주 최장 러닝 km(롱런 basis·게이트 공용). 없으면 0."""
    r = conn.execute(
        f"SELECT MAX(distance_m) FROM v_canonical_activities WHERE activity_type IN {_RUN} "
        "AND DATE(start_time) >= ? AND DATE(start_time) < ?",
        ((as_of - timedelta(weeks=weeks)).isoformat(), as_of.isoformat())).fetchone()
    return round(float(r[0] or 0.0) / 1000.0, 1)


def _rules_version(conn: sqlite3.Connection, goal: dict) -> int:
    return get_rules_version(conn, goal["id"]) if goal.get("id") is not None else 1


def _long_pace_fn(goal: dict, dlabel: str, vdot: float | None):
    """대회까지 남은 주 → 그 주 처방 MP 기반 롱런 페이스(planner_v2.apply_for_goal 과 같은 정의)."""
    secs = goal.get("target_time_sec")
    mp_goal = goal.get("target_pace_sec_km") or (secs / 42.195 if secs and dlabel == "full" else None)
    mp_now = get_paces_from_vdot(vdot, None).get("M")

    def pace(to_race: int) -> float:
        mp = MR.prescribed_mp(mp_now, mp_goal, max(0, 16 - to_race))
        return MR.long_run_pace(mp) if mp else LR.DEFAULT_LONG_PACE
    return pace


def _long_cap_fn(dlabel: str, pace, n_days: int, long6: float, long12: float):
    """v2 주기화용 롱런 공유 상한(long_run_rules.long_cap_km, 진행 상한 포함)."""
    def cap(phase: str, to_race: int, week_km: float, sched: float, prev: float) -> float:
        return LR.long_cap_km(LR.LongCtx(dlabel, phase, to_race, week_km, n_days, pace(to_race), sched, long6, long12,
                                         prev_long_km=prev))
    return cap


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
    rv = _rules_version(conn, goal)
    cap, long_cap = None, None
    if rv >= 2:
        n_days = 7 - bin(load_prefs(conn).get("rest_weekdays_mask", 0) & 0x7F).count("1")
        pace = _long_pace_fn(goal, dlabel, vdot)
        cap = feasible_week_km(n_days, pace(2), dlabel)      # D-LR-8(B): 피크 롱런 공유 상한과 결합
        long_cap = _long_cap_fn(dlabel, pace, n_days, start_long, recent_long_max(conn, min(start, today), 12))
    return build_schedule(int(goal["plan_weeks"]), start_km, start_long, max(peak, start_km),
                          LONG_RUN_BASE.get(dlabel, 14.0), _LONG_CAP.get(dlabel, 0.40),
                          get_taper_weeks(DISTANCE_LABEL_KM.get(dlabel, goal["distance_km"])),
                          rv, cap, long_cap)


def week_target(conn: sqlite3.Connection, goal: dict, week_start: date, dlabel: str, vdot: float | None,
                as_of: date | None = None) -> WeekTarget | None:
    """week_start 가 계획 범위 안이면 그 주 목표, 밖이면 None. as_of 는 시작 부하를 읽는 기준일(백테스트용)."""
    start = plan_start_monday(goal.get("race_date"), goal.get("plan_weeks"))
    if start is None:
        return None
    idx = (week_start - start).days // 7
    sched = schedule_for_goal(conn, goal, dlabel, vdot, as_of)
    return sched[idx] if 0 <= idx < len(sched) else None
