"""AI 채팅 컨텍스트 — 기본 + 의도별 빌더.

chat_context.py에서 분리 (2026-03-29).
"""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from typing import Any

from .chat_context_utils import _r1, _ri, seconds_to_pace


# ── 기본 컨텍스트 (항상 포함) ──────────────────────────────────────────


def _build_base_context(conn: sqlite3.Connection, today: str) -> dict[str, Any]:
    """기본 컨텍스트: 주요 메트릭 + 웰니스 + 피트니스 + 최근 활동 3개."""
    ctx: dict[str, Any] = {"date": today}

    for name in ["UTRS", "CIRS", "ACWR", "DI", "RTTI"]:
        row = conn.execute(
            "SELECT metric_value FROM computed_metrics WHERE metric_name=? "
            "AND activity_id IS NULL AND date<=? ORDER BY date DESC LIMIT 1",
            (name, today),
        ).fetchone()
        ctx[name] = round(float(row[0]), 2) if row and row[0] is not None else None

    fit = conn.execute(
        "SELECT ctl, atl, tsb, garmin_vo2max FROM daily_fitness "
        "WHERE date<=? ORDER BY date DESC LIMIT 1", (today,),
    ).fetchone()
    if fit:
        ctx["ctl"] = round(float(fit[0]), 1) if fit[0] else None
        ctx["atl"] = round(float(fit[1]), 1) if fit[1] else None
        ctx["tsb"] = round(float(fit[2]), 1) if fit[2] else None
        ctx["vo2max"] = round(float(fit[3]), 1) if fit[3] else None

    well = conn.execute(
        "SELECT body_battery, sleep_score, hrv_value, stress_avg, resting_hr "
        "FROM daily_wellness WHERE source='garmin' AND date=? LIMIT 1",
        (today,),
    ).fetchone()
    if well:
        ctx["wellness"] = {"bb": well[0], "sleep": well[1], "hrv": well[2],
                           "stress": well[3], "rhr": well[4]}

    acts = conn.execute(
        "SELECT start_time, distance_km, duration_sec, avg_pace_sec_km, avg_hr "
        "FROM v_canonical_activities WHERE activity_type='running' "
        "ORDER BY start_time DESC LIMIT 3",
    ).fetchall()
    ctx["recent_activities"] = [
        {"date": str(r[0])[:10], "km": _r1(r[1]), "sec": _ri(r[2]), "pace": r[3], "hr": _ri(r[4])}
        for r in acts
    ]

    return ctx


# ── 의도별 추가 컨텍스트 ──────────────────────────────────────────────


def _add_today_context(conn: sqlite3.Connection, ctx: dict, today: str) -> None:
    """오늘 활동 상세 — 메트릭, HR존, 분류, 컨디션."""
    act = conn.execute(
        "SELECT id, distance_km, duration_sec, avg_pace_sec_km, avg_hr, max_hr, "
        "elevation_gain_m, calories FROM v_canonical_activities "
        "WHERE activity_type='running' AND date(start_time)=? "
        "ORDER BY start_time DESC LIMIT 1", (today,),
    ).fetchone()
    if not act:
        ctx["today_detail"] = None
        return

    aid = act[0]
    detail = {
        "distance_km": act[1], "duration_sec": act[2],
        "pace": seconds_to_pace(act[3]) if act[3] else None,
        "avg_hr": act[4], "max_hr": act[5],
        "elevation": act[6], "calories": act[7],
    }

    metrics = conn.execute(
        "SELECT metric_name, metric_value FROM computed_metrics "
        "WHERE activity_id=? AND metric_value IS NOT NULL", (aid,),
    ).fetchall()
    detail["metrics"] = {r[0]: round(float(r[1]), 2) for r in metrics}

    cls = conn.execute(
        "SELECT metric_value, metric_json FROM computed_metrics "
        "WHERE metric_name='workout_type' AND activity_id=?", (aid,),
    ).fetchone()
    if cls:
        detail["workout_type"] = cls[0]

    ctx["today_detail"] = detail


def _add_race_context(conn: sqlite3.Connection, ctx: dict, today: str) -> None:
    """레이스 준비도 — DARP/VDOT 12주 추세 + 목표 + 최근 레이스."""
    import json
    start_12w = (date.fromisoformat(today) - timedelta(weeks=12)).isoformat()
    darp_rows = conn.execute(
        "SELECT date, metric_value, metric_json FROM computed_metrics "
        "WHERE metric_name='DARP_half' AND activity_id IS NULL "
        "AND date>=? ORDER BY date", (start_12w,),
    ).fetchall()
    ctx["darp_trend"] = []
    for r in darp_rows:
        mj = json.loads(r[2]) if r[2] else {}
        ctx["darp_trend"].append({
            "date": r[0], "time_sec": mj.get("time_sec"), "vdot": mj.get("vdot"),
        })

    di_rows = conn.execute(
        "SELECT date, metric_value FROM computed_metrics "
        "WHERE metric_name='DI' AND activity_id IS NULL AND date>=? ORDER BY date",
        (start_12w,),
    ).fetchall()
    ctx["di_trend"] = [{"date": r[0], "value": round(float(r[1]), 1)} for r in di_rows if r[1]]

    try:
        from src.training.goals import get_active_goal
        ctx["goal"] = get_active_goal(conn)
    except Exception:
        ctx["goal"] = None


def _add_compare_context(conn: sqlite3.Connection, ctx: dict, today: str) -> None:
    """장기 비교 — 3/6/12개월 전 메트릭 스냅샷 + 레이스 이력."""
    snapshots = {}
    for label, months in [("3개월전", 3), ("6개월전", 6), ("12개월전", 12)]:
        ref = (date.fromisoformat(today) - timedelta(days=months * 30)).isoformat()
        snap = {}
        for name in ["UTRS", "CIRS", "ACWR", "DI"]:
            row = conn.execute(
                "SELECT metric_value FROM computed_metrics "
                "WHERE metric_name=? AND activity_id IS NULL "
                "AND date BETWEEN ? AND date(?, '+7 days') ORDER BY date LIMIT 1",
                (name, ref, ref),
            ).fetchone()
            snap[name] = round(float(row[0]), 2) if row and row[0] is not None else None
        fit = conn.execute(
            "SELECT ctl, garmin_vo2max FROM daily_fitness "
            "WHERE date BETWEEN ? AND date(?, '+7 days') ORDER BY date LIMIT 1",
            (ref, ref),
        ).fetchone()
        if fit:
            snap["ctl"] = round(float(fit[0]), 1) if fit[0] else None
            snap["vo2max"] = round(float(fit[1]), 1) if fit[1] else None

        vol = conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(distance_km),0), "
            "COALESCE(AVG(avg_pace_sec_km),0) FROM v_canonical_activities "
            "WHERE activity_type='running' "
            "AND start_time BETWEEN ? AND date(?, '+7 days')",
            (ref, ref),
        ).fetchone()
        if vol:
            snap["weekly_runs"] = vol[0]
            snap["weekly_km"] = round(float(vol[1]), 1)
            snap["avg_pace"] = seconds_to_pace(vol[2]) if vol[2] else None

        snapshots[label] = snap

    ctx["past_snapshots"] = snapshots


def _add_plan_context(conn: sqlite3.Connection, ctx: dict, today: str) -> None:
    """훈련 계획 — 이번 주 계획 + 웰니스 3일 추세."""
    try:
        from src.training.planner import get_planned_workouts
        plans = get_planned_workouts(conn)
        monday = date.fromisoformat(today) - timedelta(days=date.fromisoformat(today).weekday())
        sunday = monday + timedelta(days=6)
        ctx["week_plan"] = [
            p for p in plans
            if monday.isoformat() <= p["date"] <= sunday.isoformat()
        ]
    except Exception:
        ctx["week_plan"] = []

    rows = conn.execute(
        "SELECT date, body_battery, sleep_score, hrv_value, stress_avg "
        "FROM daily_wellness WHERE source='garmin' AND date<=? "
        "ORDER BY date DESC LIMIT 3", (today,),
    ).fetchall()
    ctx["wellness_3d"] = [
        {"date": r[0], "bb": r[1], "sleep": r[2], "hrv": r[3], "stress": r[4]}
        for r in reversed(rows)
    ]


def _add_recovery_context(conn: sqlite3.Connection, ctx: dict, today: str) -> None:
    """회복 상세 — 웰니스 7일 + HRV 기준선."""
    rows = conn.execute(
        "SELECT date, body_battery, sleep_score, hrv_value, stress_avg, resting_hr "
        "FROM daily_wellness WHERE source='garmin' AND date<=? "
        "ORDER BY date DESC LIMIT 7", (today,),
    ).fetchall()
    ctx["wellness_7d"] = [
        {"date": r[0], "bb": r[1], "sleep": r[2], "hrv": r[3], "stress": r[4], "rhr": r[5]}
        for r in reversed(rows)
    ]

    bl = conn.execute(
        "SELECT hrv_baseline_low, hrv_baseline_high FROM daily_detail_metrics "
        "WHERE metric_name='hrv_baseline_low' AND date<=? ORDER BY date DESC LIMIT 1",
        (today,),
    ).fetchone()
    if bl:
        ctx["hrv_baseline"] = {"low": bl[0], "high": bl[1]}

    cirs_rows = conn.execute(
        "SELECT date, metric_value FROM computed_metrics "
        "WHERE metric_name='CIRS' AND activity_id IS NULL AND date<=? "
        "ORDER BY date DESC LIMIT 7", (today,),
    ).fetchall()
    ctx["cirs_7d"] = [{"date": r[0], "value": round(float(r[1]), 1)}
                      for r in reversed(cirs_rows) if r[1]]


def _add_lookup_context(conn: sqlite3.Connection, ctx: dict, today: str) -> None:
    """특정 날짜 활동 조회 — 해당 날짜의 모든 활동 + 메트릭 + 웰니스."""
    target = ctx.get("_target_date", today)

    acts = conn.execute(
        "SELECT id, distance_km, duration_sec, avg_pace_sec_km, avg_hr, max_hr, "
        "elevation_gain_m, calories, name FROM v_canonical_activities "
        "WHERE activity_type='running' AND date(start_time)=? "
        "ORDER BY start_time", (target,),
    ).fetchall()

    lookup_acts = []
    for act in acts:
        aid = act[0]
        detail = {
            "distance_km": act[1], "duration_sec": act[2],
            "pace": seconds_to_pace(act[3]) if act[3] else None,
            "avg_hr": act[4], "max_hr": act[5],
            "elevation": act[6], "calories": act[7],
            "name": act[8],
        }
        metrics = conn.execute(
            "SELECT metric_name, metric_value FROM computed_metrics "
            "WHERE activity_id=? AND metric_value IS NOT NULL", (aid,),
        ).fetchall()
        detail["metrics"] = {r[0]: round(float(r[1]), 2) for r in metrics}

        cls = conn.execute(
            "SELECT metric_value FROM computed_metrics "
            "WHERE metric_name='workout_type' AND activity_id=?", (aid,),
        ).fetchone()
        if cls:
            detail["workout_type"] = cls[0]
        lookup_acts.append(detail)

    ctx["lookup_date"] = target
    ctx["lookup_activities"] = lookup_acts

    day_metrics = conn.execute(
        "SELECT metric_name, metric_value FROM computed_metrics "
        "WHERE date=? AND activity_id IS NULL AND metric_value IS NOT NULL",
        (target,),
    ).fetchall()
    ctx["lookup_day_metrics"] = {r[0]: round(float(r[1]), 2) for r in day_metrics}

    well = conn.execute(
        "SELECT body_battery, sleep_score, hrv_value, stress_avg, resting_hr "
        "FROM daily_wellness WHERE source='garmin' AND date=? LIMIT 1",
        (target,),
    ).fetchone()
    if well:
        ctx["lookup_wellness"] = {"bb": well[0], "sleep": well[1], "hrv": well[2],
                                   "stress": well[3], "rhr": well[4]}


INTENT_BUILDERS: dict = {
    "today": _add_today_context,
    "race": _add_race_context,
    "compare": _add_compare_context,
    "plan": _add_plan_context,
    "recovery": _add_recovery_context,
    "lookup": _add_lookup_context,
}
