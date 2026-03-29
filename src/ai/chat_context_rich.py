"""AI 채팅 컨텍스트 — 풍부한 컨텍스트 빌더 (Gemini/Claude용).

chat_context.py에서 분리 (2026-03-29).
"""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from typing import Any

from .chat_context_utils import seconds_to_pace


def _add_rich_30d_context(conn: sqlite3.Connection, ctx: dict, today: str) -> None:
    """Gemini용 30일 풀 데이터 — 활동/메트릭/웰니스/피트니스 전체."""
    start_30d = (date.fromisoformat(today) - timedelta(days=30)).isoformat()

    acts = conn.execute(
        "SELECT date(start_time), distance_km, duration_sec, avg_pace_sec_km, "
        "avg_hr, max_hr, elevation_gain_m, name FROM v_canonical_activities "
        "WHERE activity_type='running' AND start_time>=? ORDER BY start_time",
        (start_30d,),
    ).fetchall()
    ctx["activities_30d"] = [
        {"date": r[0], "km": r[1], "sec": r[2],
         "pace": seconds_to_pace(r[3]) if r[3] else None,
         "avg_hr": r[4], "max_hr": r[5], "elev": r[6], "name": r[7]}
        for r in acts
    ]

    key_metrics = ["UTRS", "CIRS", "ACWR", "DI", "RTTI", "REC", "RRI",
                   "Monotony", "LSI", "Strain", "SAPI", "TEROI"]
    metric_rows = conn.execute(
        "SELECT date, metric_name, metric_value FROM computed_metrics "
        "WHERE activity_id IS NULL AND metric_name IN ({}) AND date>=? "
        "ORDER BY date".format(",".join(f"'{m}'" for m in key_metrics)),
        (start_30d,),
    ).fetchall()
    daily_metrics: dict[str, dict] = {}
    for d, name, val in metric_rows:
        if val is None:
            continue
        daily_metrics.setdefault(d, {})[name] = round(float(val), 2)
    ctx["daily_metrics_30d"] = daily_metrics

    well_rows = conn.execute(
        "SELECT date, body_battery, sleep_score, hrv_value, stress_avg, resting_hr "
        "FROM daily_wellness WHERE source='garmin' AND date>=? ORDER BY date",
        (start_30d,),
    ).fetchall()
    ctx["wellness_30d"] = [
        {"date": r[0], "bb": r[1], "sleep": r[2], "hrv": r[3],
         "stress": r[4], "rhr": r[5]}
        for r in well_rows
    ]

    fit_rows = conn.execute(
        "SELECT date, ctl, atl, tsb FROM daily_fitness "
        "WHERE date>=? ORDER BY date", (start_30d,),
    ).fetchall()
    ctx["fitness_30d"] = [
        {"date": r[0], "ctl": round(float(r[1]), 1) if r[1] else None,
         "atl": round(float(r[2]), 1) if r[2] else None,
         "tsb": round(float(r[3]), 1) if r[3] else None}
        for r in fit_rows
    ]

    ctx["runner_profile"] = _build_runner_profile(conn, today)

    race_acts = conn.execute(
        "SELECT a.start_time, a.distance_km, a.duration_sec, a.avg_pace_sec_km, a.avg_hr, a.name "
        "FROM v_canonical_activities a "
        "LEFT JOIN computed_metrics c ON c.activity_id=a.id AND c.metric_name='workout_type' "
        "WHERE a.activity_type='running' AND (c.metric_value='race' OR a.name LIKE '%레이스%' "
        "OR a.name LIKE '%대회%' OR a.name LIKE '%Race%') "
        "ORDER BY a.start_time DESC LIMIT 10",
    ).fetchall()
    if race_acts:
        ctx["race_history"] = [
            {"date": str(r[0])[:10], "km": r[1], "sec": r[2],
             "pace": seconds_to_pace(r[3]) if r[3] else None,
             "hr": r[4], "name": r[5]}
            for r in race_acts
        ]

    today_type = conn.execute(
        "SELECT c.metric_value FROM v_canonical_activities a "
        "JOIN computed_metrics c ON c.activity_id=a.id AND c.metric_name='workout_type' "
        "WHERE a.activity_type='running' AND date(a.start_time)=? "
        "ORDER BY a.start_time DESC LIMIT 1", (today,),
    ).fetchone()
    if today_type and today_type[0]:
        wtype = today_type[0]
        similar = conn.execute(
            "SELECT date(a.start_time), a.distance_km, a.avg_pace_sec_km, a.avg_hr "
            "FROM v_canonical_activities a "
            "JOIN computed_metrics c ON c.activity_id=a.id AND c.metric_name='workout_type' "
            "WHERE c.metric_value=? AND a.activity_type='running' AND date(a.start_time)<? "
            "ORDER BY a.start_time DESC LIMIT 5", (wtype, today),
        ).fetchall()
        if similar:
            ctx["similar_activities"] = {
                "type": wtype,
                "history": [
                    {"date": r[0], "km": r[1],
                     "pace": seconds_to_pace(r[2]) if r[2] else None, "hr": r[3]}
                    for r in similar
                ],
            }


def _add_mid_14d_context(conn: sqlite3.Connection, ctx: dict, today: str) -> None:
    """Claude/OpenAI용 14일 데이터."""
    start_14d = (date.fromisoformat(today) - timedelta(days=14)).isoformat()

    acts = conn.execute(
        "SELECT date(start_time), distance_km, duration_sec, avg_pace_sec_km, "
        "avg_hr, name FROM v_canonical_activities "
        "WHERE activity_type='running' AND start_time>=? ORDER BY start_time",
        (start_14d,),
    ).fetchall()
    ctx["activities_14d"] = [
        {"date": r[0], "km": r[1], "sec": r[2],
         "pace": seconds_to_pace(r[3]) if r[3] else None,
         "avg_hr": r[4], "name": r[5]}
        for r in acts
    ]

    well_rows = conn.execute(
        "SELECT date, body_battery, sleep_score, hrv_value, stress_avg "
        "FROM daily_wellness WHERE source='garmin' AND date>=? ORDER BY date",
        (start_14d,),
    ).fetchall()
    ctx["wellness_14d"] = [
        {"date": r[0], "bb": r[1], "sleep": r[2], "hrv": r[3], "stress": r[4]}
        for r in well_rows
    ]

    ctx["runner_profile"] = _build_runner_profile(conn, today)


def _build_runner_profile(conn: sqlite3.Connection, today: str) -> dict[str, Any]:
    """러너 프로필 요약 — 주간 볼륨, 수준, 경향 등."""
    profile: dict[str, Any] = {}

    start_4w = (date.fromisoformat(today) - timedelta(weeks=4)).isoformat()
    vol = conn.execute(
        "SELECT COUNT(*), COALESCE(SUM(distance_km),0), COALESCE(AVG(avg_pace_sec_km),0) "
        "FROM v_canonical_activities WHERE activity_type='running' AND start_time>=?",
        (start_4w,),
    ).fetchone()
    if vol and vol[0]:
        profile["weekly_avg_runs"] = round(vol[0] / 4, 1)
        profile["weekly_avg_km"] = round(float(vol[1]) / 4, 1)
        profile["avg_pace"] = seconds_to_pace(vol[2]) if vol[2] else None

    for name in ["VDOT_ADJ", "DI"]:
        row = conn.execute(
            "SELECT metric_value FROM computed_metrics WHERE metric_name=? "
            "AND activity_id IS NULL AND date<=? ORDER BY date DESC LIMIT 1",
            (name, today),
        ).fetchone()
        if row and row[0]:
            profile[name.lower()] = round(float(row[0]), 1)

    fit = conn.execute(
        "SELECT garmin_vo2max FROM daily_fitness WHERE date<=? ORDER BY date DESC LIMIT 1",
        (today,),
    ).fetchone()
    if fit and fit[0]:
        profile["vo2max"] = round(float(fit[0]), 1)

    try:
        from src.training.goals import get_active_goal
        goal = get_active_goal(conn)
        if goal:
            profile["goal"] = goal.get("name")
            if goal.get("race_date"):
                try:
                    dl = (date.fromisoformat(goal["race_date"]) - date.fromisoformat(today)).days
                    profile["race_dday"] = dl
                except ValueError:
                    pass
    except Exception:
        pass

    return profile


# Provider별 컨텍스트 전략
RICH_PROVIDERS = {"gemini"}         # 1M 컨텍스트 → 30일 풀 데이터
MID_PROVIDERS = {"claude", "openai"}  # 200K → 14일 + 의도별
