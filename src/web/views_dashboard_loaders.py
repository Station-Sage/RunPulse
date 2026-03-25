"""대시보드 — 신규 데이터 로더 (UI 재설계용).

웰니스 미니, 주간 훈련 요약, Monotony/Strain/EF 추세 시리즈.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date, timedelta


def load_wellness_mini(conn: sqlite3.Connection, target_date: str) -> dict:
    """오늘의 웰니스 미니 데이터 (BB, 수면, HRV)."""
    row = conn.execute(
        "SELECT body_battery, sleep_score, hrv_value, resting_hr "
        "FROM daily_wellness WHERE source='garmin' AND date=? LIMIT 1",
        (target_date,),
    ).fetchone()
    if not row:
        return {}
    return {
        "body_battery": row[0],
        "sleep_score": row[1],
        "hrv": row[2],
        "resting_hr": row[3],
    }


def load_weekly_summary(conn: sqlite3.Connection, target_date: str) -> dict:
    """이번 주 훈련 요약 (거리, 시간, 활동 수, TIDS 존 분포)."""
    td = date.fromisoformat(target_date)
    # 이번 주 월요일 ~ 오늘
    monday = td - timedelta(days=td.weekday())
    row = conn.execute(
        """SELECT COUNT(*), COALESCE(SUM(distance_km), 0), COALESCE(SUM(duration_sec), 0)
           FROM v_canonical_activities
           WHERE activity_type = 'running'
             AND start_time >= ? AND start_time <= ?""",
        (monday.isoformat(), target_date + "T23:59:59"),
    ).fetchone()
    count, dist_km, dur_sec = int(row[0]), round(float(row[1]), 1), int(row[2])

    # TIDS 최신 (이번 주 내)
    tids_row = conn.execute(
        """SELECT metric_json FROM computed_metrics
           WHERE metric_name='TIDS' AND activity_id IS NULL
             AND date >= ? AND date <= ?
           ORDER BY date DESC LIMIT 1""",
        (monday.isoformat(), target_date),
    ).fetchone()
    tids = {}
    if tids_row and tids_row[0]:
        try:
            tids = json.loads(tids_row[0])
        except Exception:
            pass

    return {
        "count": count,
        "distance_km": dist_km,
        "duration_sec": dur_sec,
        "tids_z12": tids.get("z12"),
        "tids_z3": tids.get("z3"),
        "tids_z45": tids.get("z45"),
    }


def load_fitness_trends(conn: sqlite3.Connection, target_date: str, days: int = 60) -> dict:
    """Monotony/Strain/EF 추세 시계열 (60일)."""
    start = (date.fromisoformat(target_date) - timedelta(days=days - 1)).isoformat()

    # Monotony + Strain (일별)
    rows = conn.execute(
        """SELECT date, metric_name, metric_value FROM computed_metrics
           WHERE metric_name IN ('Monotony', 'Strain')
             AND activity_id IS NULL AND date BETWEEN ? AND ?
           ORDER BY date""",
        (start, target_date),
    ).fetchall()
    by_date: dict[str, dict] = {}
    for d, name, val in rows:
        by_date.setdefault(d, {})[name] = float(val) if val is not None else None
    dates = sorted(by_date.keys())

    # EF (활동별)
    ef_rows = conn.execute(
        """SELECT date, metric_value FROM computed_metrics
           WHERE metric_name = 'EF' AND activity_id IS NOT NULL
             AND date BETWEEN ? AND ?
           ORDER BY date""",
        (start, target_date),
    ).fetchall()
    ef_dates = [r[0] for r in ef_rows if r[1] is not None]
    ef_vals = [round(float(r[1]), 4) for r in ef_rows if r[1] is not None]

    return {
        "dates": dates,
        "monotony": [by_date[d].get("Monotony") for d in dates],
        "strain": [by_date[d].get("Strain") for d in dates],
        "ef_dates": ef_dates,
        "ef_values": ef_vals,
    }


def load_risk_7day_trends(conn: sqlite3.Connection, target_date: str) -> dict:
    """ACWR/LSI/Monotony/Strain/TSB 7일 미니 추세."""
    start = (date.fromisoformat(target_date) - timedelta(days=6)).isoformat()
    rows = conn.execute(
        """SELECT date, metric_name, metric_value FROM computed_metrics
           WHERE metric_name IN ('ACWR', 'LSI', 'Monotony', 'Strain')
             AND activity_id IS NULL AND date BETWEEN ? AND ?
           ORDER BY date""",
        (start, target_date),
    ).fetchall()
    series: dict[str, list] = {"ACWR": [], "LSI": [], "Monotony": [], "Strain": []}
    for _, name, val in rows:
        if name in series:
            series[name].append(float(val) if val is not None else None)

    # TSB from daily_fitness
    tsb_rows = conn.execute(
        "SELECT tsb FROM daily_fitness WHERE date BETWEEN ? AND ? ORDER BY date",
        (start, target_date),
    ).fetchall()
    series["TSB"] = [float(r[0]) if r[0] is not None else None for r in tsb_rows]

    return series
