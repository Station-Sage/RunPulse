"""Coach 채팅용 컨디션 판정 — Today 브리핑·계획 다운그레이드와 같은 `readiness_decision`을 쓴다.

채팅(규칙 fallback·프롬프트 컨텍스트)이 회복 등급·TSB 임계값을 따로 해석해 Today와 다른 권고를 내던 문제를
막는다. 판정은 fatigue 모듈, 세션 조정은 adjuster가 하고 여기서는 ctx에 붙이고 문장으로 옮기기만 한다.
"""
from __future__ import annotations

import sqlite3

from src.training.adjuster import adjust_todays_plan
from src.training.fatigue import readiness_decision
from src.utils.format_ko import fmt_distance, workout_ko


def attach_readiness(conn: sqlite3.Connection, ctx: dict, date_str: str) -> None:
    """ctx에 readiness_decision(판정)과 plan_adjustment(오늘 계획 조정 결과, 없으면 None)를 추가."""
    try:
        ctx["readiness_decision"] = readiness_decision(conn, date=date_str)
    except Exception:
        ctx["readiness_decision"] = None
    try:
        ctx["plan_adjustment"] = adjust_todays_plan(conn, date=date_str)
    except Exception:
        ctx["plan_adjustment"] = None


def decision_lines(ctx: dict) -> list[str]:
    """판정 헤드라인 + 근거 한 줄씩. 판정이 없으면 빈 리스트."""
    d = ctx.get("readiness_decision")
    if not d:
        return []
    lines = [d["headline"]]
    lines += [f"- {e['label']}" for e in d.get("evidence", [])]
    return lines


def plan_line(ctx: dict) -> str | None:
    """오늘 계획 한 줄 — 조정이 걸렸으면 원래 계획과 조정 결과·사유를 함께 적는다."""
    adj = ctx.get("plan_adjustment")
    plan = ctx.get("plan_today")
    if adj and adj.get("adjusted"):
        dist = f" {fmt_distance(adj['distance_km'])}" if adj.get("distance_km") else ""
        return (f"오늘 계획: {workout_ko(adj['original_type'])}{dist} → 조정: {workout_ko(adj['adjusted_type'])} "
                f"({adj.get('adjustment_reason')})")
    if plan:
        dist = f" {fmt_distance(plan['distance_km'])}" if plan.get("distance_km") else ""
        return f"오늘 계획: {workout_ko(plan.get('workout_type', ''))}{dist}"
    return None
