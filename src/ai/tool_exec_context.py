"""일별/기간 단위 도구 실행기 — 메트릭, 웰니스, 피트니스, 날씨, 기간 비교, 프로필."""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from src.ai.tool_format import (
    DEFAULT_WEEK_START, columnar, num, resolve_granularity, span_days,
    weekly_last, weekly_mean,
)
from src.utils.pace import seconds_to_pace


def _exec_get_metrics(conn: sqlite3.Connection, args: dict) -> dict:
    d = args.get("date", date.today().isoformat())
    names = args.get("metric_names", [])
    if names:
        placeholders = ",".join("?" for _ in names)
        rows = conn.execute(
            f"SELECT metric_name, numeric_value FROM metric_store"
            f" WHERE scope_type='daily' AND scope_id=? AND is_primary=1"
            f"   AND metric_name IN ({placeholders})",
            [d] + names,
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT metric_name, numeric_value FROM metric_store"
            " WHERE scope_type='daily' AND scope_id=? AND is_primary=1 AND numeric_value IS NOT NULL",
            (d,),
        ).fetchall()
    return {"date": d, "metrics": {r[0]: round(float(r[1]), 2) for r in rows if r[1]}}


def _exec_get_metrics_trend(conn: sqlite3.Connection, args: dict) -> dict:
    name = args["metric_name"]
    days = int(args.get("days", 30))
    first = args.get("week_start", DEFAULT_WEEK_START)
    gran, note = resolve_granularity(args.get("granularity"), days)
    start = (date.today() - timedelta(days=days)).isoformat()
    rows = conn.execute(
        "SELECT scope_id, numeric_value FROM metric_store"
        " WHERE metric_name=? AND scope_type='daily' AND is_primary=1"
        "   AND scope_id>=? AND numeric_value IS NOT NULL ORDER BY scope_id",
        (name, start),
    ).fetchall()
    out: dict = {"metric": name, "days": days, "granularity": gran}
    if note:
        out["note"] = note
    if gran == "week":
        out["unit"] = f"week({'Mon' if first == 'mon' else 'Sun'}-start)"
        out.update(columnar(["week", "n", "value"],
                            weekly_mean([[r[0], r[1]] for r in rows], [2], first)))
    else:
        out.update(columnar(["date", "value"], [[r[0], num(r[1], 2)] for r in rows]))
    return out



def _exec_get_wellness(conn: sqlite3.Connection, args: dict) -> dict:
    s, e = args["start_date"], args["end_date"]
    first = args.get("week_start", DEFAULT_WEEK_START)
    gran, note = resolve_granularity(args.get("granularity"), span_days(s, e))
    rows = conn.execute(
        "SELECT date, body_battery_high, sleep_score, sleep_duration_sec, hrv_last_night, "
        "avg_stress, resting_hr FROM daily_wellness "
        "WHERE date BETWEEN ? AND ? ORDER BY date", (s, e),
    ).fetchall()
    fields = ["bb", "sleep_score", "sleep_h", "hrv", "stress", "rhr"]
    daily = [[r[0], r[1], r[2], r[3] / 3600.0 if r[3] else None, r[4], r[5], r[6]] for r in rows]
    out: dict = {"period": f"{s} ~ {e}", "granularity": gran}
    if note:
        out["note"] = note
    if gran == "week":
        out["unit"] = f"week({'Mon' if first == 'mon' else 'Sun'}-start) 평균"
        out.update(columnar(["week", "n", *fields], weekly_mean(daily, [0, 0, 1, 0, 0, 0], first)))
    else:
        digits = [0, 0, 1, 0, 0, 0]
        out.update(columnar(["date", *fields], [
            [r[0], *[num(v, nd) for v, nd in zip(r[1:], digits)]] for r in daily]))
    return out



def fitness_rows(conn: sqlite3.Connection, start: str, end: str | None = None) -> list[list]:
    """[date, ctl, atl, tsb, vo2max] 일별 (primary 값, 날짜 오름차순)."""
    sql = ("SELECT scope_id, metric_name, numeric_value FROM metric_store"
           " WHERE scope_type='daily' AND is_primary=1"
           "   AND metric_name IN ('ctl','atl','tsb','vo2max')"
           "   AND scope_id>=? AND numeric_value IS NOT NULL")
    params: list = [start]
    if end:
        sql += " AND scope_id<=?"
        params.append(end)
    by_date: dict = {}
    for d, mname, val in conn.execute(sql + " ORDER BY scope_id", params).fetchall():
        by_date.setdefault(d, {})[mname] = val
    return [[d, *[num(v[m], 1) if m in v else None for m in ("ctl", "atl", "tsb", "vo2max")]]
            for d, v in sorted(by_date.items())]


def _exec_get_fitness(conn: sqlite3.Connection, args: dict) -> dict:
    days = int(args.get("days", 30))
    first = args.get("week_start", DEFAULT_WEEK_START)
    gran, note = resolve_granularity(args.get("granularity"), days)
    rows = fitness_rows(conn, (date.today() - timedelta(days=days)).isoformat())
    out: dict = {"days": days, "granularity": gran}
    if note:
        out["note"] = note
    if gran == "week":
        out["unit"] = f"week({'Mon' if first == 'mon' else 'Sun'}-start) 주말 값"
        rows = weekly_last(rows, first)
        out.update(columnar(["week", "ctl", "atl", "tsb", "vo2max"], rows))
    else:
        out.update(columnar(["date", "ctl", "atl", "tsb", "vo2max"], rows))
    return out



def _exec_get_race_history(conn: sqlite3.Connection, args: dict) -> dict:
    limit = args.get("limit", 10)
    rows = conn.execute(
        "SELECT a.start_time, a.distance_m / 1000.0 AS distance_km, a.duration_sec, a.avg_pace_sec_km, "
        "a.avg_hr, a.name FROM v_canonical_activities a "
        "LEFT JOIN metric_store c ON c.scope_id=CAST(a.id AS TEXT)"
        "    AND c.scope_type='activity' AND c.metric_name='workout_type_classified' "
        "WHERE a.activity_type='running' AND (c.text_value='race' OR a.name LIKE '%레이스%' "
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


def _exec_get_weather(conn: sqlite3.Connection, args: dict) -> dict:
    date_str = args["date"]
    to_date = args.get("to_date", date_str)

    rows = conn.execute(
        "SELECT date, hour, temp_c, humidity_pct, wind_speed_ms, "
        "cloud_cover_pct, condition_text "
        "FROM weather_cache WHERE date BETWEEN ? AND ? ORDER BY date, hour",
        (date_str, to_date),
    ).fetchall()

    if not rows:
        return {"date": date_str, "rows": [], "message": "날씨 데이터 없음"}

    return {
        "date": date_str,
        "to_date": to_date,
        **columnar(
            ["date", "hour", "temp_c", "humidity", "wind_ms", "cloud", "condition"],
            [[r[0], r[1], num(r[2], 1), num(r[3]), num(r[4], 1), num(r[5]), r[6]] for r in rows],
        ),
    }


def _exec_compare_periods(conn: sqlite3.Connection, args: dict) -> dict:
    def _period_stats(s: str, e: str) -> dict:
        rows = conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(distance_m) / 1000.0, 0), "
            "COALESCE(AVG(avg_pace_sec_km),0), COALESCE(AVG(avg_hr),0) "
            "FROM v_canonical_activities "
            "WHERE activity_type='running' AND start_time>=? AND start_time<=? || 'T99'",
            (s, e),
        ).fetchone()
        # 메트릭 평균
        metrics = {}
        for m in ["UTRS", "CIRS", "ACWR", "DI"]:
            mr = conn.execute(
                "SELECT AVG(numeric_value) FROM metric_store"
                " WHERE metric_name=? AND scope_type='daily' AND is_primary=1"
                "   AND scope_id BETWEEN ? AND ?",
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
        "SELECT numeric_value FROM metric_store"
        " WHERE metric_name='vdot' AND scope_type='daily' AND is_primary=1"
        "   AND numeric_value IS NOT NULL ORDER BY scope_id DESC LIMIT 1",
    ).fetchone()
    if vdot_row and vdot_row[0]:
        from src.utils.daniels_table import get_training_paces
        paces = get_training_paces(float(vdot_row[0]))
        profile["training_paces"] = {
            k: f"{v // 60}:{v % 60:02d}/km" for k, v in paces.items()
            if k != "R_400m"
        }
        if "R_400m" in paces:
            profile["training_paces"]["R_400m"] = f"{paces['R_400m']}초"
    return profile


# ── 랩(세트) 조회 ────────────────────────────────────────────────────
#
# 토큰 비용을 줄이기 위해 랩은 키를 반복하는 dict 대신 `fields` 헤더 +
# 값 배열로 반환하고, 전부 NULL인 컬럼은 헤더에서 제외한다.
