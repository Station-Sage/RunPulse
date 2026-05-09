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
        "SELECT id, date(start_time), distance_m / 1000.0 AS distance_km, duration_sec, avg_pace_sec_km, "
        "avg_hr, max_hr, elevation_gain, name FROM v_canonical_activities "
        "WHERE activity_type='running' AND start_time>=? ORDER BY start_time",
        (start_30d,),
    ).fetchall()
    ctx["activities_30d"] = [
        {"id": r[0], "date": r[1], "km": r[2], "sec": r[3],
         "pace": seconds_to_pace(r[4]) if r[4] else None,
         "avg_hr": r[5], "max_hr": r[6], "elev": r[7], "name": r[8]}
        for r in acts
    ]

    key_metrics = ["utrs", "cirs", "acwr", "di", "rtti", "rec", "rri",
                   "monotony", "lsi", "training_strain", "sapi", "teroi"]
    metric_rows = conn.execute(
        "SELECT scope_id, metric_name, numeric_value FROM metric_store"
        " WHERE scope_type='daily' AND is_primary=1"
        "   AND metric_name IN ({}) AND scope_id>=?"
        " ORDER BY scope_id".format(",".join(f"'{m}'" for m in key_metrics)),
        (start_30d,),
    ).fetchall()
    daily_metrics: dict[str, dict] = {}
    for d, name, val in metric_rows:
        if val is None:
            continue
        daily_metrics.setdefault(d, {})[name] = round(float(val), 2)
    ctx["daily_metrics_30d"] = daily_metrics

    well_rows = conn.execute(
        "SELECT date, body_battery_high, sleep_score, hrv_last_night, avg_stress, resting_hr "
        "FROM daily_wellness WHERE date>=? ORDER BY date",
        (start_30d,),
    ).fetchall()
    ctx["wellness_30d"] = [
        {"date": r[0], "bb": r[1], "sleep": r[2], "hrv": r[3],
         "stress": r[4], "rhr": r[5]}
        for r in well_rows
    ]

    ms_rows = conn.execute(
        "SELECT scope_id, metric_name, numeric_value FROM metric_store"
        " WHERE scope_type='daily' AND metric_name IN ('ctl','atl','tsb') AND is_primary=1"
        "   AND scope_id>=? AND numeric_value IS NOT NULL ORDER BY scope_id",
        (start_30d,),
    ).fetchall()
    fitness_by_date: dict[str, dict] = {}
    for _d, _name, _val in ms_rows:
        fitness_by_date.setdefault(_d, {})[_name] = round(float(_val), 1)
    ctx["fitness_30d"] = [
        {"date": _d, "ctl": _v.get("ctl"), "atl": _v.get("atl"), "tsb": _v.get("tsb")}
        for _d, _v in sorted(fitness_by_date.items())
    ]

    ctx["runner_profile"] = _build_runner_profile(conn, today)

    race_acts = conn.execute(
        "SELECT a.id, a.start_time, a.distance_m / 1000.0 AS distance_km, a.duration_sec, a.avg_pace_sec_km, a.avg_hr, a.name "
        "FROM v_canonical_activities a "
        "LEFT JOIN metric_store c ON c.scope_id=CAST(a.id AS TEXT)"
        "    AND c.scope_type='activity' AND c.metric_name='workout_type_classified' "
        "WHERE a.activity_type='running' AND (c.numeric_value='race' OR a.name LIKE '%레이스%' "
        "OR a.name LIKE '%대회%' OR a.name LIKE '%Race%') "
        "ORDER BY a.start_time DESC LIMIT 10",
    ).fetchall()
    if race_acts:
        ctx["race_history"] = [
            {"id": r[0], "date": str(r[1])[:10], "km": r[2], "sec": r[3],
             "pace": seconds_to_pace(r[4]) if r[4] else None,
             "hr": r[5], "name": r[6]}
            for r in race_acts
        ]

    today_type = conn.execute(
        "SELECT c.numeric_value FROM v_canonical_activities a "
        "JOIN metric_store c ON c.scope_id=CAST(a.id AS TEXT)"
        "    AND c.scope_type='activity' AND c.metric_name='workout_type_classified' "
        "WHERE a.activity_type='running' AND date(a.start_time)=? "
        "ORDER BY a.start_time DESC LIMIT 1", (today,),
    ).fetchone()
    if today_type and today_type[0]:
        wtype = today_type[0]
        similar = conn.execute(
            "SELECT a.id, date(a.start_time), a.distance_m / 1000.0 AS distance_km, a.avg_pace_sec_km, a.avg_hr "
            "FROM v_canonical_activities a "
            "JOIN metric_store c ON c.scope_id=CAST(a.id AS TEXT)"
            "    AND c.scope_type='activity' AND c.metric_name='workout_type_classified' "
            "WHERE c.numeric_value=? AND a.activity_type='running' AND date(a.start_time)<? "
            "ORDER BY a.start_time DESC LIMIT 5", (wtype, today),
        ).fetchall()
        if similar:
            ctx["similar_activities"] = {
                "type": wtype,
                "history": [
                    {"id": r[0], "date": r[1], "km": r[2],
                     "pace": seconds_to_pace(r[3]) if r[3] else None, "hr": r[4]}
                    for r in similar
                ],
            }


def _add_mid_14d_context(conn: sqlite3.Connection, ctx: dict, today: str) -> None:
    """Claude/OpenAI용 14일 데이터."""
    start_14d = (date.fromisoformat(today) - timedelta(days=14)).isoformat()

    acts = conn.execute(
        "SELECT date(start_time), distance_m / 1000.0 AS distance_km, duration_sec, avg_pace_sec_km, "
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
        "SELECT date, body_battery_high, sleep_score, hrv_last_night, avg_stress "
        "FROM daily_wellness WHERE date>=? ORDER BY date",
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
        "SELECT COUNT(*), COALESCE(SUM(distance_m) / 1000.0, 0), COALESCE(AVG(avg_pace_sec_km),0) "
        "FROM v_canonical_activities WHERE activity_type='running' AND start_time>=?",
        (start_4w,),
    ).fetchone()
    if vol and vol[0]:
        profile["weekly_avg_runs"] = round(vol[0] / 4, 1)
        profile["weekly_avg_km"] = round(float(vol[1]) / 4, 1)
        profile["avg_pace"] = seconds_to_pace(vol[2]) if vol[2] else None

    for name in ["VDOT_ADJ", "DI"]:
        row = conn.execute(
            "SELECT numeric_value FROM metric_store"
            " WHERE metric_name=? AND scope_type='daily' AND is_primary=1"
            "   AND scope_id<=? AND numeric_value IS NOT NULL ORDER BY scope_id DESC LIMIT 1",
            (name, today),
        ).fetchone()
        if row and row[0]:
            profile[name.lower()] = round(float(row[0]), 1)

    fit = conn.execute(
        "SELECT numeric_value FROM metric_store"
        " WHERE scope_type='daily' AND metric_name='vo2max' AND is_primary=1"
        "   AND scope_id<=? AND numeric_value IS NOT NULL ORDER BY scope_id DESC LIMIT 1",
        (today,),
    ).fetchone()
    if fit:
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
