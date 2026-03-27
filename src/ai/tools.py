"""AI Function Calling 도구 — DB 조회 함수 정의 + 실행기.

Gemini/Claude/OpenAI의 function calling에서 사용할 도구를 정의하고,
AI가 요청한 함수를 실행하여 결과를 반환한다.
"""
from __future__ import annotations

import json
import logging
import sqlite3
from datetime import date, timedelta
from typing import Any

from src.utils.pace import seconds_to_pace

log = logging.getLogger(__name__)

# ── 도구 선언 (Gemini function_declarations 형식) ─────────────────────

TOOL_DECLARATIONS = [
    {
        "name": "get_activity",
        "description": "특정 날짜의 러닝 활동 상세 데이터를 조회한다. 거리, 페이스, 심박, 메트릭, 운동 분류 포함.",
        "parameters": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "조회할 날짜 (YYYY-MM-DD)"},
            },
            "required": ["date"],
        },
    },
    {
        "name": "get_activities_range",
        "description": "기간 내 러닝 활동 목록을 조회한다. 날짜별 거리, 페이스, 심박 요약.",
        "parameters": {
            "type": "object",
            "properties": {
                "start_date": {"type": "string", "description": "시작일 (YYYY-MM-DD)"},
                "end_date": {"type": "string", "description": "종료일 (YYYY-MM-DD)"},
            },
            "required": ["start_date", "end_date"],
        },
    },
    {
        "name": "get_metrics",
        "description": "특정 날짜의 2차 메트릭(UTRS, CIRS, ACWR, DI 등)을 조회한다.",
        "parameters": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "날짜 (YYYY-MM-DD)"},
                "metric_names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "조회할 메트릭 이름 목록. 비어있으면 전체 조회.",
                },
            },
            "required": ["date"],
        },
    },
    {
        "name": "get_metrics_trend",
        "description": "메트릭의 기간별 추세를 조회한다. 시계열 데이터 반환.",
        "parameters": {
            "type": "object",
            "properties": {
                "metric_name": {"type": "string", "description": "메트릭 이름 (UTRS, CIRS, ACWR 등)"},
                "days": {"type": "integer", "description": "최근 N일 (기본 30)"},
            },
            "required": ["metric_name"],
        },
    },
    {
        "name": "get_wellness",
        "description": "기간 내 웰니스 데이터를 조회한다. 바디배터리, 수면, HRV, 스트레스, 안정심박.",
        "parameters": {
            "type": "object",
            "properties": {
                "start_date": {"type": "string", "description": "시작일 (YYYY-MM-DD)"},
                "end_date": {"type": "string", "description": "종료일 (YYYY-MM-DD)"},
            },
            "required": ["start_date", "end_date"],
        },
    },
    {
        "name": "get_fitness",
        "description": "CTL(만성훈련부하), ATL(급성훈련부하), TSB(신선도), VO2Max 추세를 조회한다.",
        "parameters": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "최근 N일 (기본 30)"},
            },
        },
    },
    {
        "name": "get_race_history",
        "description": "레이스(대회) 활동 이력을 조회한다. 거리, 완주 시간, 페이스 포함.",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "최대 결과 수 (기본 10)"},
            },
        },
    },
    {
        "name": "compare_periods",
        "description": "두 기간의 훈련 데이터를 비교한다. 볼륨, 메트릭, 페이스 등.",
        "parameters": {
            "type": "object",
            "properties": {
                "period_a_start": {"type": "string", "description": "기간A 시작일"},
                "period_a_end": {"type": "string", "description": "기간A 종료일"},
                "period_b_start": {"type": "string", "description": "기간B 시작일"},
                "period_b_end": {"type": "string", "description": "기간B 종료일"},
            },
            "required": ["period_a_start", "period_a_end", "period_b_start", "period_b_end"],
        },
    },
    {
        "name": "get_training_plan",
        "description": "훈련 계획을 조회한다. 이번 주 또는 특정 주의 계획.",
        "parameters": {
            "type": "object",
            "properties": {
                "week_offset": {"type": "integer", "description": "0=이번주, 1=다음주, -1=지난주"},
            },
        },
    },
    {
        "name": "get_runner_profile",
        "description": "러너의 전체 프로필 요약. 주간 평균, VO2Max, 목표, 수준.",
        "parameters": {"type": "object", "properties": {}},
    },
]


# ── 도구 실행기 ──────────────────────────────────────────────────────


def execute_tool(conn: sqlite3.Connection, name: str, args: dict) -> str:
    """AI가 호출한 도구를 실행하고 결과를 JSON 문자열로 반환."""
    _dispatch = {
        "get_activity": _exec_get_activity,
        "get_activities_range": _exec_get_activities_range,
        "get_metrics": _exec_get_metrics,
        "get_metrics_trend": _exec_get_metrics_trend,
        "get_wellness": _exec_get_wellness,
        "get_fitness": _exec_get_fitness,
        "get_race_history": _exec_get_race_history,
        "compare_periods": _exec_compare_periods,
        "get_training_plan": _exec_get_training_plan,
        "get_runner_profile": _exec_get_runner_profile,
    }
    fn = _dispatch.get(name)
    if not fn:
        return json.dumps({"error": f"알 수 없는 도구: {name}"}, ensure_ascii=False)
    try:
        result = fn(conn, args)
        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as exc:
        log.warning("도구 실행 실패 (%s): %s", name, exc)
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


def _exec_get_activity(conn: sqlite3.Connection, args: dict) -> dict:
    d = args.get("date", date.today().isoformat())
    acts = conn.execute(
        "SELECT id, distance_km, duration_sec, avg_pace_sec_km, avg_hr, max_hr, "
        "elevation_gain_m, calories, name FROM v_canonical_activities "
        "WHERE activity_type='running' AND date(start_time)=? ORDER BY start_time",
        (d,),
    ).fetchall()
    if not acts:
        return {"date": d, "activities": [], "message": "해당 날짜에 활동이 없습니다"}

    result = []
    for a in acts:
        aid, km, sec, pace, avg_hr, max_hr, elev, cal, name = a
        detail: dict[str, Any] = {
            "name": name,
            "distance_km": round(float(km), 1) if km else None,
            "duration_sec": round(float(sec)) if sec else None,
            "pace": seconds_to_pace(int(pace)) if pace else None,
            "avg_hr": round(float(avg_hr)) if avg_hr else None,
            "max_hr": round(float(max_hr)) if max_hr else None,
            "elevation_m": round(float(elev)) if elev else None,
            "calories": round(float(cal)) if cal else None,
        }
        # 메트릭
        metrics = conn.execute(
            "SELECT metric_name, metric_value FROM computed_metrics "
            "WHERE activity_id=? AND metric_value IS NOT NULL", (aid,),
        ).fetchall()
        detail["metrics"] = {r[0]: round(float(r[1]), 2) for r in metrics}
        # 분류
        cls = conn.execute(
            "SELECT metric_value FROM computed_metrics "
            "WHERE metric_name='workout_type' AND activity_id=?", (aid,),
        ).fetchone()
        if cls:
            detail["workout_type"] = cls[0]
        result.append(detail)
    return {"date": d, "activities": result}


def _exec_get_activities_range(conn: sqlite3.Connection, args: dict) -> dict:
    s, e = args["start_date"], args["end_date"]
    rows = conn.execute(
        "SELECT date(start_time), distance_km, duration_sec, avg_pace_sec_km, "
        "avg_hr, name FROM v_canonical_activities "
        "WHERE activity_type='running' AND start_time>=? AND start_time<=? || 'T99' "
        "ORDER BY start_time", (s, e),
    ).fetchall()
    return {
        "period": f"{s} ~ {e}",
        "count": len(rows),
        "activities": [
            {"date": r[0], "km": round(float(r[1]), 1) if r[1] else None,
             "sec": round(float(r[2])) if r[2] else None,
             "pace": seconds_to_pace(int(r[3])) if r[3] else None,
             "hr": round(float(r[4])) if r[4] else None, "name": r[5]}
            for r in rows
        ],
    }


def _exec_get_metrics(conn: sqlite3.Connection, args: dict) -> dict:
    d = args.get("date", date.today().isoformat())
    names = args.get("metric_names", [])
    if names:
        placeholders = ",".join("?" for _ in names)
        rows = conn.execute(
            f"SELECT metric_name, metric_value FROM computed_metrics "
            f"WHERE date=? AND activity_id IS NULL AND metric_name IN ({placeholders})",
            [d] + names,
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT metric_name, metric_value FROM computed_metrics "
            "WHERE date=? AND activity_id IS NULL AND metric_value IS NOT NULL",
            (d,),
        ).fetchall()
    return {"date": d, "metrics": {r[0]: round(float(r[1]), 2) for r in rows if r[1]}}


def _exec_get_metrics_trend(conn: sqlite3.Connection, args: dict) -> dict:
    name = args["metric_name"]
    days = args.get("days", 30)
    start = (date.today() - timedelta(days=days)).isoformat()
    rows = conn.execute(
        "SELECT date, metric_value FROM computed_metrics "
        "WHERE metric_name=? AND activity_id IS NULL AND date>=? ORDER BY date",
        (name, start),
    ).fetchall()
    return {
        "metric": name, "days": days,
        "data": [{"date": r[0], "value": round(float(r[1]), 2)} for r in rows if r[1]],
    }


def _exec_get_wellness(conn: sqlite3.Connection, args: dict) -> dict:
    s, e = args["start_date"], args["end_date"]
    rows = conn.execute(
        "SELECT date, body_battery, sleep_score, sleep_hours, hrv_value, "
        "stress_avg, resting_hr FROM daily_wellness "
        "WHERE source='garmin' AND date BETWEEN ? AND ? ORDER BY date", (s, e),
    ).fetchall()
    return {
        "period": f"{s} ~ {e}",
        "data": [
            {"date": r[0], "body_battery": r[1], "sleep_score": r[2],
             "sleep_hours": r[3], "hrv": r[4], "stress": r[5], "resting_hr": r[6]}
            for r in rows
        ],
    }


def _exec_get_fitness(conn: sqlite3.Connection, args: dict) -> dict:
    days = args.get("days", 30)
    start = (date.today() - timedelta(days=days)).isoformat()
    rows = conn.execute(
        "SELECT date, ctl, atl, tsb, garmin_vo2max FROM daily_fitness "
        "WHERE date>=? ORDER BY date", (start,),
    ).fetchall()
    return {
        "days": days,
        "data": [
            {"date": r[0], "ctl": round(float(r[1]), 1) if r[1] else None,
             "atl": round(float(r[2]), 1) if r[2] else None,
             "tsb": round(float(r[3]), 1) if r[3] else None,
             "vo2max": round(float(r[4]), 1) if r[4] else None}
            for r in rows
        ],
    }


def _exec_get_race_history(conn: sqlite3.Connection, args: dict) -> dict:
    limit = args.get("limit", 10)
    rows = conn.execute(
        "SELECT a.start_time, a.distance_km, a.duration_sec, a.avg_pace_sec_km, "
        "a.avg_hr, a.name FROM v_canonical_activities a "
        "LEFT JOIN computed_metrics c ON c.activity_id=a.id AND c.metric_name='workout_type' "
        "WHERE a.activity_type='running' AND (c.metric_value='race' OR a.name LIKE '%레이스%' "
        "OR a.name LIKE '%대회%' OR a.name LIKE '%Race%') "
        "ORDER BY a.start_time DESC LIMIT ?", (limit,),
    ).fetchall()
    return {
        "races": [
            {"date": str(r[0])[:10], "km": r[1], "duration": r[2],
             "pace": seconds_to_pace(int(r[3])) if r[3] else None,
             "hr": r[4], "name": r[5]}
            for r in rows
        ],
    }


def _exec_compare_periods(conn: sqlite3.Connection, args: dict) -> dict:
    def _period_stats(s: str, e: str) -> dict:
        rows = conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(distance_km),0), "
            "COALESCE(AVG(avg_pace_sec_km),0), COALESCE(AVG(avg_hr),0) "
            "FROM v_canonical_activities "
            "WHERE activity_type='running' AND start_time>=? AND start_time<=? || 'T99'",
            (s, e),
        ).fetchone()
        # 메트릭 평균
        metrics = {}
        for m in ["UTRS", "CIRS", "ACWR", "DI"]:
            mr = conn.execute(
                "SELECT AVG(metric_value) FROM computed_metrics "
                "WHERE metric_name=? AND activity_id IS NULL AND date BETWEEN ? AND ?",
                (m, s, e),
            ).fetchone()
            if mr and mr[0]:
                metrics[m] = round(float(mr[0]), 2)
        return {
            "period": f"{s}~{e}", "runs": rows[0],
            "total_km": round(float(rows[1]), 1),
            "avg_pace": seconds_to_pace(int(rows[2])) if rows[2] else None,
            "avg_hr": round(float(rows[3]), 1) if rows[3] else None,
            "metrics": metrics,
        }

    a = _period_stats(args["period_a_start"], args["period_a_end"])
    b = _period_stats(args["period_b_start"], args["period_b_end"])
    return {"period_a": a, "period_b": b}


def _exec_get_training_plan(conn: sqlite3.Connection, args: dict) -> dict:
    offset = args.get("week_offset", 0)
    today = date.today()
    monday = today - timedelta(days=today.weekday()) + timedelta(weeks=offset)
    sunday = monday + timedelta(days=6)
    try:
        from src.training.planner import get_planned_workouts
        plans = get_planned_workouts(conn)
        week = [p for p in plans if monday.isoformat() <= p["date"] <= sunday.isoformat()]
        return {"week": f"{monday} ~ {sunday}", "workouts": week}
    except Exception:
        return {"week": f"{monday} ~ {sunday}", "workouts": [], "message": "계획 없음"}


def _exec_get_runner_profile(conn: sqlite3.Connection, args: dict) -> dict:
    from src.ai.chat_context import _build_runner_profile
    profile = _build_runner_profile(conn, date.today().isoformat())
    # Daniels 훈련 페이스 추가
    vdot_row = conn.execute(
        "SELECT metric_value FROM computed_metrics WHERE metric_name='VDOT' "
        "AND metric_value IS NOT NULL ORDER BY date DESC LIMIT 1",
    ).fetchone()
    if vdot_row and vdot_row[0]:
        from src.metrics.daniels_table import get_training_paces
        paces = get_training_paces(float(vdot_row[0]))
        profile["training_paces"] = {
            k: f"{v // 60}:{v % 60:02d}/km" for k, v in paces.items()
            if k != "R_400m"
        }
        if "R_400m" in paces:
            profile["training_paces"]["R_400m"] = f"{paces['R_400m']}초"
    return profile
