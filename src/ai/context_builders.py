"""탭별 컨텍스트 빌더 — AI 프롬프트에 필요한 데이터를 탭별로 조합.

각 탭의 AI 해석에 필요한 현재값 + 시계열 + 관련 지표를 수집.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date, timedelta
from typing import Any


def build_dashboard_context(conn: sqlite3.Connection, today: str) -> dict:
    """대시보드 AI 프롬프트용 컨텍스트."""
    ctx: dict[str, Any] = {"date": today}

    # 주요 메트릭 현재값
    for name in ["UTRS", "CIRS", "ACWR", "RTTI", "Monotony", "LSI", "Strain", "DI", "REC", "RRI"]:
        row = conn.execute(
            "SELECT metric_value FROM computed_metrics WHERE metric_name=? "
            "AND activity_id IS NULL AND date<=? ORDER BY date DESC LIMIT 1",
            (name, today),
        ).fetchone()
        ctx[name.lower()] = float(row[0]) if row and row[0] is not None else None

    # 7일 시계열
    start_7d = (date.fromisoformat(today) - timedelta(days=6)).isoformat()
    for name in ["UTRS", "CIRS", "ACWR"]:
        rows = conn.execute(
            "SELECT date, metric_value FROM computed_metrics WHERE metric_name=? "
            "AND activity_id IS NULL AND date BETWEEN ? AND ? ORDER BY date",
            (name, start_7d, today),
        ).fetchall()
        ctx[f"{name.lower()}_7d"] = [{"d": r[0], "v": round(float(r[1]), 2)} for r in rows if r[1]]

    # TSB 7일
    tsb_rows = conn.execute(
        "SELECT date, tsb FROM daily_fitness WHERE date BETWEEN ? AND ? ORDER BY date",
        (start_7d, today),
    ).fetchall()
    ctx["tsb_7d"] = [{"d": r[0], "v": round(float(r[1]), 1)} for r in tsb_rows if r[1] is not None]
    ctx["tsb"] = float(tsb_rows[-1][1]) if tsb_rows and tsb_rows[-1][1] is not None else None

    # 웰니스 오늘
    well = conn.execute(
        "SELECT body_battery, sleep_score, hrv_value, stress_avg, resting_hr "
        "FROM daily_wellness WHERE source='garmin' AND date=? LIMIT 1",
        (today,),
    ).fetchone()
    if well:
        ctx["wellness"] = {
            "bb": well[0], "sleep": well[1], "hrv": well[2],
            "stress": well[3], "rhr": well[4],
        }

    # 주간 볼륨
    monday = date.fromisoformat(today) - timedelta(days=date.fromisoformat(today).weekday())
    vol = conn.execute(
        "SELECT COUNT(*), COALESCE(SUM(distance_km),0) FROM v_canonical_activities "
        "WHERE activity_type='running' AND start_time>=? AND start_time<=?",
        (monday.isoformat(), today + "T23:59:59"),
    ).fetchone()
    ctx["weekly"] = {"count": int(vol[0]), "km": round(float(vol[1]), 1)}

    return ctx


def build_training_context(conn: sqlite3.Connection, today: str,
                           week_offset: int = 0) -> dict:
    """훈련탭 AI 프롬프트용 컨텍스트."""
    from src.training.planner import get_planned_workouts
    from src.training.goals import get_active_goal

    ctx: dict[str, Any] = {"date": today}
    td = date.fromisoformat(today)

    # 목표
    goal = get_active_goal(conn)
    if goal:
        ctx["goal"] = {
            "name": goal.get("name"), "distance_km": goal.get("distance_km"),
            "race_date": goal.get("race_date"),
        }
        if goal.get("race_date"):
            try:
                ctx["d_day"] = (date.fromisoformat(goal["race_date"]) - td).days
            except ValueError:
                pass

    # 이번 주 워크아웃 + 이행률
    ws = td - timedelta(days=td.weekday()) + timedelta(weeks=week_offset)
    workouts = get_planned_workouts(conn, ws)
    if workouts:
        total = len([w for w in workouts if w.get("workout_type") != "rest"])
        completed = len([w for w in workouts if w.get("completed") and w.get("workout_type") != "rest"])
        total_km = sum(w.get("distance_km") or 0 for w in workouts)
        ctx["this_week"] = {
            "total": total, "completed": completed,
            "completion_pct": round(completed / total * 100) if total else 0,
            "total_km": round(total_km, 1),
            "workouts": [
                {"date": w["date"], "type": w["workout_type"],
                 "km": w.get("distance_km"), "done": bool(w.get("completed"))}
                for w in workouts
            ],
        }

    # 4주 볼륨 추세
    vol_4w = []
    for w in range(4):
        w_start = td - timedelta(days=td.weekday()) - timedelta(weeks=w)
        w_end = w_start + timedelta(days=6)
        row = conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(distance_km),0) FROM v_canonical_activities "
            "WHERE activity_type='running' AND DATE(start_time) BETWEEN ? AND ?",
            (w_start.isoformat(), w_end.isoformat()),
        ).fetchone()
        vol_4w.append({"week": w_start.isoformat(), "count": int(row[0]), "km": round(float(row[1]), 1)})
    ctx["volume_4w"] = list(reversed(vol_4w))

    # 현재 지표
    for name in ["UTRS", "CIRS", "ACWR"]:
        row = conn.execute(
            "SELECT metric_value FROM computed_metrics WHERE metric_name=? "
            "AND activity_id IS NULL AND date<=? ORDER BY date DESC LIMIT 1",
            (name, today),
        ).fetchone()
        ctx[name.lower()] = float(row[0]) if row and row[0] is not None else None

    # 웰니스
    well = conn.execute(
        "SELECT body_battery, sleep_score, hrv_value FROM daily_wellness "
        "WHERE source='garmin' AND date=? LIMIT 1", (today,),
    ).fetchone()
    if well:
        ctx["wellness"] = {"bb": well[0], "sleep": well[1], "hrv": well[2]}

    # 훈련 단계
    if goal and goal.get("race_date"):
        try:
            wl = max(0, (date.fromisoformat(goal["race_date"]) - td).days // 7)
            if wl > 16: ctx["phase"] = "base"
            elif wl > 8: ctx["phase"] = "build"
            elif wl > 3: ctx["phase"] = "peak"
            else: ctx["phase"] = "taper"
            ctx["weeks_left"] = wl
        except ValueError:
            pass

    # 오늘 활동
    act = conn.execute(
        "SELECT distance_km, duration_sec, avg_pace_sec_km, avg_hr FROM v_canonical_activities "
        "WHERE activity_type='running' AND DATE(start_time)=? LIMIT 1",
        (today,),
    ).fetchone()
    if act:
        ctx["today_activity"] = {
            "km": act[0], "sec": act[1], "pace": act[2], "hr": act[3],
        }

    return ctx


def build_report_context(conn: sqlite3.Connection, start_date: str,
                         end_date: str) -> dict:
    """레포트 AI 프롬프트용 컨텍스트 (선택 기간)."""
    ctx: dict[str, Any] = {"period": f"{start_date} ~ {end_date}"}

    # 기간 통계
    row = conn.execute(
        "SELECT COUNT(*), COALESCE(SUM(distance_km),0), COALESCE(SUM(duration_sec),0) "
        "FROM v_canonical_activities WHERE activity_type='running' "
        "AND start_time BETWEEN ? AND ?",
        (start_date, end_date + "T23:59:59"),
    ).fetchone()
    ctx["stats"] = {"count": int(row[0]), "km": round(float(row[1]), 1), "sec": int(row[2])}

    # 메트릭 시계열 (주별 요약)
    for name in ["UTRS", "CIRS", "ACWR"]:
        rows = conn.execute(
            "SELECT date, metric_value FROM computed_metrics WHERE metric_name=? "
            "AND activity_id IS NULL AND date BETWEEN ? AND ? ORDER BY date",
            (name, start_date, end_date),
        ).fetchall()
        vals = [float(r[1]) for r in rows if r[1] is not None]
        ctx[f"{name.lower()}_avg"] = round(sum(vals) / len(vals), 1) if vals else None
        ctx[f"{name.lower()}_trend"] = "↑" if len(vals) > 1 and vals[-1] > vals[0] else "↓" if len(vals) > 1 and vals[-1] < vals[0] else "→"

    return ctx


def build_race_context(conn: sqlite3.Connection, today: str) -> dict:
    """레이스 예측 AI 프롬프트용 컨텍스트."""
    from src.training.goals import get_active_goal
    ctx: dict[str, Any] = {"date": today}

    goal = get_active_goal(conn)
    if goal:
        ctx["goal"] = {
            "name": goal.get("name"), "distance_km": goal.get("distance_km"),
            "race_date": goal.get("race_date"),
        }

    # VDOT 12주 추세
    start_12w = (date.fromisoformat(today) - timedelta(weeks=12)).isoformat()
    rows = conn.execute(
        "SELECT date, metric_value FROM computed_metrics WHERE metric_name='VDOT' "
        "AND activity_id IS NULL AND date BETWEEN ? AND ? ORDER BY date",
        (start_12w, today),
    ).fetchall()
    ctx["vdot_12w"] = [{"d": r[0], "v": round(float(r[1]), 1)} for r in rows if r[1]]
    ctx["vdot"] = float(rows[-1][1]) if rows and rows[-1][1] else None

    # DI, CTL, Marathon Shape
    for name in ["DI", "MarathonShape", "RRI"]:
        row = conn.execute(
            "SELECT metric_value FROM computed_metrics WHERE metric_name=? "
            "AND activity_id IS NULL AND date<=? ORDER BY date DESC LIMIT 1",
            (name, today),
        ).fetchone()
        ctx[name.lower()] = float(row[0]) if row and row[0] is not None else None

    ctl_row = conn.execute(
        "SELECT ctl FROM daily_fitness WHERE date<=? AND ctl IS NOT NULL ORDER BY date DESC LIMIT 1",
        (today,),
    ).fetchone()
    ctx["ctl"] = float(ctl_row[0]) if ctl_row else None

    return ctx


def build_wellness_context(conn: sqlite3.Connection, today: str) -> dict:
    """웰니스 AI 프롬프트용 컨텍스트."""
    ctx: dict[str, Any] = {"date": today}
    start_14d = (date.fromisoformat(today) - timedelta(days=13)).isoformat()

    # 14일 웰니스 시계열
    rows = conn.execute(
        "SELECT date, body_battery, sleep_score, hrv_value, stress_avg, resting_hr "
        "FROM daily_wellness WHERE source='garmin' AND date BETWEEN ? AND ? ORDER BY date",
        (start_14d, today),
    ).fetchall()
    ctx["wellness_14d"] = [
        {"d": r[0], "bb": r[1], "sleep": r[2], "hrv": r[3], "stress": r[4], "rhr": r[5]}
        for r in rows
    ]

    # 오늘
    if rows:
        last = rows[-1]
        ctx["today"] = {"bb": last[1], "sleep": last[2], "hrv": last[3], "stress": last[4], "rhr": last[5]}

    # 14일 평균
    for key, idx in [("bb", 1), ("sleep", 2), ("hrv", 3)]:
        vals = [r[idx] for r in rows if r[idx] is not None]
        ctx[f"{key}_avg"] = round(sum(vals) / len(vals), 1) if vals else None

    return ctx


def build_activity_context(conn: sqlite3.Connection, activity_id: int) -> dict:
    """활동 심층분석 AI 프롬프트용 컨텍스트."""
    ctx: dict[str, Any] = {"activity_id": activity_id}

    # 활동 기본 데이터
    row = conn.execute(
        "SELECT name, distance_km, duration_sec, avg_pace_sec_km, avg_hr, max_hr, "
        "start_time, activity_type FROM activity_summaries WHERE id=?",
        (activity_id,),
    ).fetchone()
    if row:
        ctx["activity"] = {
            "name": row[0], "km": row[1], "sec": row[2], "pace": row[3],
            "hr": row[4], "max_hr": row[5], "date": str(row[6])[:10], "type": row[7],
        }

    # 활동별 메트릭
    metrics = conn.execute(
        "SELECT metric_name, metric_value FROM computed_metrics WHERE activity_id=?",
        (activity_id,),
    ).fetchall()
    ctx["metrics"] = {r[0]: round(float(r[1]), 2) for r in metrics if r[1] is not None}

    # 최근 10회 유사 활동 (거리 ±30%)
    if row and row[1]:
        dist = float(row[1])
        recent = conn.execute(
            "SELECT distance_km, avg_pace_sec_km, avg_hr FROM v_canonical_activities "
            "WHERE activity_type='running' AND distance_km BETWEEN ? AND ? "
            "AND id != ? ORDER BY start_time DESC LIMIT 10",
            (dist * 0.7, dist * 1.3, activity_id),
        ).fetchall()
        ctx["similar_recent"] = [
            {"km": r[0], "pace": r[1], "hr": r[2]} for r in recent
        ]

    return ctx


def format_context_compact(ctx: dict) -> str:
    """컨텍스트 dict를 프롬프트용 compact 텍스트로 변환."""
    parts = []
    for k, v in ctx.items():
        if v is None:
            continue
        if isinstance(v, list):
            if not v:
                continue
            # 시계열은 축약
            if len(v) > 10:
                v = v[-7:]  # 최근 7개만
            parts.append(f"{k}: {json.dumps(v, ensure_ascii=False)}")
        elif isinstance(v, dict):
            parts.append(f"{k}: {json.dumps(v, ensure_ascii=False)}")
        else:
            parts.append(f"{k}: {v}")
    return "\n".join(parts)
