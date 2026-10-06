"""주간 다이제스트 — 월간 내러티브의 주(週) 단위 근거 (DESIGN-U17 U17g).

월요일 시작 주 1개의 러닝 합계·CTL/TSB·수면·계획 이행을 모은다. 캐시하지 않는다(월간 캐시 키 불변).
데이터가 없으면 값은 None, flags 는 빈 리스트. 진행 중인 주는 partial=True.
"""
from __future__ import annotations

import datetime
import sqlite3

from src.utils.db_helpers import get_metric_history

TSB_LOW = -30.0
SLEEP_LOW = 60.0


def week_start_of(day: datetime.date) -> datetime.date:
    return day - datetime.timedelta(days=day.weekday())


def weeks_overlapping(month_start: str, date_end: str) -> list[str]:
    """[month_start, date_end] 와 겹치는 월요일 시작 주의 시작일(ISO) 목록."""
    cur = week_start_of(datetime.date.fromisoformat(month_start))
    end = datetime.date.fromisoformat(date_end)
    out: list[str] = []
    while cur <= end:
        out.append(cur.isoformat())
        cur += datetime.timedelta(days=7)
    return out


def _first_last(rows: list[dict]) -> tuple[float | None, float | None]:
    vals = [r["numeric_value"] for r in rows if r.get("numeric_value") is not None]
    return (float(vals[0]), float(vals[-1])) if vals else (None, None)


def week_digest(conn: sqlite3.Connection, week_start: str) -> dict:
    start = datetime.date.fromisoformat(week_start)
    end = start + datetime.timedelta(days=6)
    s, e = start.isoformat(), end.isoformat()
    partial = end >= datetime.date.today()

    row = conn.execute(
        "SELECT COUNT(*), COALESCE(SUM(distance_m), 0), COALESCE(MAX(distance_m), 0)"
        " FROM v_canonical_activities WHERE DATE(start_time) >= ? AND DATE(start_time) <= ?",
        (s, e),
    ).fetchone()
    run_count = int(row[0]) if row else 0
    dist = round(float(row[1]) / 1000.0, 1) if run_count else None
    long_km = round(float(row[2]) / 1000.0, 1) if run_count else None
    quality = conn.execute(
        "SELECT COUNT(*) FROM planned_workouts WHERE date >= ? AND date <= ?"
        " AND completed = 1 AND workout_type IN ('tempo','interval','marathon','threshold','long_mp')",
        (s, e),
    ).fetchone()[0]

    ctl_start, ctl_end = _first_last(get_metric_history(conn, "ctl", date_from=s, date_to=e))
    tsb_vals = [r["numeric_value"] for r in get_metric_history(conn, "tsb", date_from=s, date_to=e)
                if r.get("numeric_value") is not None]
    tsb_min = round(float(min(tsb_vals)), 1) if tsb_vals else None

    sl = conn.execute(
        "SELECT AVG(sleep_score) FROM daily_wellness WHERE date >= ? AND date <= ? AND sleep_score IS NOT NULL",
        (s, e),
    ).fetchone()
    sleep_avg = round(float(sl[0]), 0) if sl and sl[0] is not None else None

    plan = conn.execute(
        "SELECT COUNT(*), COALESCE(SUM(completed), 0) FROM planned_workouts"
        " WHERE date >= ? AND date <= ? AND workout_type NOT IN ('rest')",
        (s, e),
    ).fetchone()
    plan_total, plan_done = int(plan[0]), int(plan[1])

    flags: list[str] = []
    if tsb_min is not None and tsb_min < TSB_LOW:
        flags.append("tsb_low")
    if sleep_avg is not None and sleep_avg < SLEEP_LOW:
        flags.append("sleep_low")
    if plan_total and not partial and plan_done < plan_total:
        flags.append("plan_missed")
    return {
        "week_start": s, "week_end": e, "run_count": run_count, "distance_km": dist,
        "long_run_km": long_km, "quality_count": int(quality),
        "ctl_start": ctl_start, "ctl_end": ctl_end, "tsb_min": tsb_min, "sleep_avg": sleep_avg,
        "plan_done": plan_done, "plan_total": plan_total, "flags": flags, "partial": partial,
    }


def week_digests(conn: sqlite3.Connection, month_start: str, date_end: str) -> list[dict]:
    return [week_digest(conn, w) for w in weeks_overlapping(month_start, date_end)]


def digest_prompt_lines(weeks: list[dict]) -> list[str]:
    """프롬프트 W 블록 — 값 있는 항목만 나열."""
    out: list[str] = []
    for i, w in enumerate(weeks, 1):
        if not w["run_count"]:
            out.append(f"- W{i}({w['week_start']}~): 러닝 없음")
            continue
        parts = [f"{w['distance_km']}km", f"{w['run_count']}회", f"롱런 {w['long_run_km']}km"]
        if w["ctl_end"] is not None:
            parts.append(f"CTL {w['ctl_end']:.1f}")
        if w["tsb_min"] is not None:
            parts.append(f"최저 TSB {w['tsb_min']}")
        if w["partial"]:
            parts.append("진행 중")
        out.append(f"- W{i}({w['week_start']}~): " + ", ".join(parts))
    return out
