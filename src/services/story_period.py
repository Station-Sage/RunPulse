"""Story 기간 파싱 — 월/주/블록 문자열 → 날짜 범위 (story_service 하위 모듈)."""
from __future__ import annotations

import calendar
import sqlite3
from datetime import date, timedelta
from typing import Any


def _parse_period(period: str) -> dict[str, Any]:
    """기간 문자열 파싱 — 2026-09 | 2026-W39 | b-<planId>-<phase>.

    Returns: {scope, year?, month?, week?, plan_id?, phase?}
    또는 ValueError 발생.
    """
    if period.startswith("b-"):
        parts = period[2:].split("-", 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid block period: {period}")
        return {"scope": "block", "plan_id": parts[0], "phase": parts[1]}

    if "-W" in period:
        parts = period.split("-W")
        if len(parts) != 2:
            raise ValueError(f"Invalid week period: {period}")
        try:
            year = int(parts[0])
            week = int(parts[1])
            if not 1 <= week <= 53:
                raise ValueError("week out of range")
            return {"scope": "week", "year": year, "week": week}
        except ValueError:
            raise ValueError(f"Invalid week period: {period}")

    if len(period) == 7 and period[4] == "-":
        try:
            year = int(period[:4])
            month = int(period[5:7])
            if not 1 <= month <= 12:
                raise ValueError("month out of range")
            return {"scope": "month", "year": year, "month": month}
        except ValueError:
            raise ValueError(f"Invalid month period: {period}")

    raise ValueError(f"Invalid period format: {period}")


def _month_date_range(year: int, month: int) -> tuple[str, str]:
    """월 범위 계산 — 시작일, 종료일.

    현재 달이면 오늘까지, 과거 달이면 말일까지.
    """
    month_start = f"{year}-{month:02d}-01"
    today = date.today()
    if year == today.year and month == today.month:
        return month_start, today.isoformat()
    last_day = calendar.monthrange(year, month)[1]
    return month_start, f"{year}-{month:02d}-{last_day:02d}"


def _week_date_range(year: int, week: int) -> tuple[str, str]:
    """ISO주차 범위 계산 — 일요일 시작으로 조정.

    Returns: (일요일, 토요일)
    """
    from datetime import datetime, timedelta
    jan_4 = date(year, 1, 4)
    week_1_start = jan_4 - timedelta(days=jan_4.isoweekday() - 1)
    target_start = week_1_start + timedelta(weeks=week - 1)
    target_start_sunday = target_start - timedelta(days=(target_start.weekday() + 1) % 7)
    target_end_saturday = target_start_sunday + timedelta(days=6)
    return target_start_sunday.isoformat(), target_end_saturday.isoformat()


def _get_block_dates(conn: sqlite3.Connection, plan_id: str, phase: str) -> tuple[str, str]:
    """활성 계획 phase 경계 조회 — 블록 단위 기간.

    현재 구현: plan_id는 미사용(향후 다중 계획 지원용). phase별로 활성 계획에서
    해당 phase의 시작/종료 주(월요일~토요일)를 찾는다.
    """
    from src.training.goals import get_active_goal
    from src.training.planner_schedule import schedule_for_goal
    from src.training.planner_rules import resolve_distance_label, plan_start_monday
    from src.training.planner_config import get_vdot_adj

    goal = get_active_goal(conn)
    if goal is None:
        raise ValueError(f"No active plan for block scope: {phase}")

    dlabel = resolve_distance_label(goal.get("distance_km", 10.0), goal.get("distance_label"))
    vdot = get_vdot_adj(conn)

    # schedule_for_goal는 전체 계획 주차 목록을 반환 (각 WeekTarget이 phase를 가짐)
    sched = schedule_for_goal(conn, goal, dlabel, vdot)
    plan_start = plan_start_monday(goal.get("race_date"), goal.get("plan_weeks"))

    if plan_start is None:
        raise ValueError("Cannot determine plan start date")

    # 요청한 phase의 첫 주(index)와 마지막 주(index)를 찾는다
    matching_indices = [i for i, w in enumerate(sched) if w.phase == phase]
    if not matching_indices:
        raise ValueError(f"Phase not found in active plan: {phase}")

    first_idx = matching_indices[0]
    last_idx = matching_indices[-1]

    # plan_start로부터 역산 (schedule은 race_date 역산이므로 시작이 index 0)
    start_week_date = plan_start + timedelta(weeks=first_idx)
    end_week_date = plan_start + timedelta(weeks=last_idx + 1) - timedelta(days=1)  # 토요일

    return start_week_date.isoformat(), end_week_date.isoformat()
