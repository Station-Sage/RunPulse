"""레포트 — 신규 데이터 로더 (UI 재설계용).

훈련 질 시계열, 리스크 시계열, 폼/바이오 시계열, 웰니스 시계열,
이전 기간 비교 통계, 주간 TIDS 시리즈.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date, timedelta


def load_prev_period_stats(conn: sqlite3.Connection, start: str, end: str) -> dict:
    """이전 동일 기간 통계 (델타 비교용)."""
    sd = date.fromisoformat(start)
    ed = date.fromisoformat(end)
    span = (ed - sd).days or 1
    prev_end = (sd - timedelta(days=1)).isoformat()
    prev_start = (sd - timedelta(days=span + 1)).isoformat()
    row = conn.execute(
        """SELECT COUNT(*), COALESCE(SUM(distance_km), 0), COALESCE(SUM(duration_sec), 0)
           FROM v_canonical_activities
           WHERE activity_type = 'running' AND start_time BETWEEN ? AND ?""",
        (prev_start, prev_end + "T23:59:59"),
    ).fetchone()
    return {"count": int(row[0]), "total_km": float(row[1]), "total_sec": int(row[2])}


def load_training_quality_series(conn: sqlite3.Connection, start: str, end: str) -> dict:
    """EF / Decoupling / VO2Max 기간 내 시계열."""
    # EF, Decoupling (활동별)
    rows = conn.execute(
        """SELECT date, metric_name, metric_value FROM computed_metrics
           WHERE metric_name IN ('EF', 'AerobicDecoupling')
             AND activity_id IS NOT NULL AND date BETWEEN ? AND ?
           ORDER BY date""",
        (start, end),
    ).fetchall()
    ef_dates, ef_vals = [], []
    dec_dates, dec_vals = [], []
    for d, name, val in rows:
        if val is None:
            continue
        if name == "EF":
            ef_dates.append(d)
            ef_vals.append(round(float(val), 4))
        elif name == "AerobicDecoupling":
            dec_dates.append(d)
            dec_vals.append(round(float(val), 1))

    # VO2Max (daily_fitness)
    vo2_rows = conn.execute(
        """SELECT date, garmin_vo2max FROM daily_fitness
           WHERE garmin_vo2max IS NOT NULL AND date BETWEEN ? AND ?
           ORDER BY date""",
        (start, end),
    ).fetchall()
    vo2_dates = [r[0] for r in vo2_rows]
    vo2_vals = [round(float(r[1]), 1) for r in vo2_rows]

    return {
        "ef_dates": ef_dates, "ef_values": ef_vals,
        "dec_dates": dec_dates, "dec_values": dec_vals,
        "vo2_dates": vo2_dates, "vo2_values": vo2_vals,
    }


def load_risk_trend_series(conn: sqlite3.Connection, start: str, end: str) -> dict:
    """ACWR / Monotony / Strain 기간 내 일별 시계열."""
    rows = conn.execute(
        """SELECT date, metric_name, metric_value FROM computed_metrics
           WHERE metric_name IN ('ACWR', 'Monotony', 'Strain')
             AND activity_id IS NULL AND date BETWEEN ? AND ?
           ORDER BY date""",
        (start, end),
    ).fetchall()
    by_date: dict[str, dict] = {}
    for d, name, val in rows:
        by_date.setdefault(d, {})[name] = float(val) if val is not None else None
    dates = sorted(by_date.keys())
    return {
        "dates": dates,
        "acwr": [by_date[d].get("ACWR") for d in dates],
        "monotony": [by_date[d].get("Monotony") for d in dates],
        "strain": [by_date[d].get("Strain") for d in dates],
    }


def load_form_trend_series(conn: sqlite3.Connection, start: str, end: str) -> dict:
    """RMR 시작/끝 비교 + GCT/수직비율/보폭 시계열."""
    # RMR 기간 시작 vs 끝
    rmr_start = conn.execute(
        """SELECT metric_json FROM computed_metrics
           WHERE metric_name='RMR' AND activity_id IS NULL AND date >= ?
           ORDER BY date ASC LIMIT 1""",
        (start,),
    ).fetchone()
    rmr_end = conn.execute(
        """SELECT metric_json FROM computed_metrics
           WHERE metric_name='RMR' AND activity_id IS NULL AND date <= ?
           ORDER BY date DESC LIMIT 1""",
        (end,),
    ).fetchone()

    def _parse_rmr(row) -> dict:
        if row and row[0]:
            try:
                return json.loads(row[0])
            except Exception:
                pass
        return {}

    rmr_start_json = _parse_rmr(rmr_start)
    rmr_end_json = _parse_rmr(rmr_end)

    # GCT / 수직비율 / 보폭 (activity_detail_metrics)
    bio_rows = conn.execute(
        """SELECT a.start_time, m.metric_name, m.metric_value
           FROM activity_detail_metrics m
           JOIN activity_summaries a ON a.id = m.activity_id
           WHERE m.metric_name IN ('avg_ground_contact_time_ms', 'avg_vertical_ratio_pct', 'avg_stride_length_cm')
             AND a.start_time BETWEEN ? AND ?
           ORDER BY a.start_time""",
        (start, end + "T23:59:59"),
    ).fetchall()
    bio: dict[str, dict[str, list]] = {}
    for st, name, val in bio_rows:
        d = str(st)[:10]
        bio.setdefault(name, {"dates": [], "values": []})
        bio[name]["dates"].append(d)
        bio[name]["values"].append(round(float(val), 1) if val is not None else None)

    return {
        "rmr_start": rmr_start_json,
        "rmr_end": rmr_end_json,
        "gct": bio.get("avg_ground_contact_time_ms", {"dates": [], "values": []}),
        "vertical_ratio": bio.get("avg_vertical_ratio_pct", {"dates": [], "values": []}),
        "stride": bio.get("avg_stride_length_cm", {"dates": [], "values": []}),
    }


def load_wellness_trend_series(conn: sqlite3.Connection, start: str, end: str) -> dict:
    """HRV / 수면 / BB / 스트레스 / 안정심박 기간 내 시계열."""
    rows = conn.execute(
        """SELECT date, hrv_value, sleep_score, body_battery, stress_avg, resting_hr
           FROM daily_wellness WHERE source='garmin' AND date BETWEEN ? AND ?
           ORDER BY date""",
        (start, end),
    ).fetchall()
    dates = [r[0] for r in rows]
    return {
        "dates": dates,
        "hrv": [r[1] for r in rows],
        "sleep": [r[2] for r in rows],
        "bb": [r[3] for r in rows],
        "stress": [r[4] for r in rows],
        "rhr": [r[5] for r in rows],
    }


def load_tids_weekly_series(conn: sqlite3.Connection, start: str, end: str) -> dict:
    """주간 TIDS z12/z3/z45 시리즈."""
    rows = conn.execute(
        """SELECT date, metric_json FROM computed_metrics
           WHERE metric_name='TIDS' AND activity_id IS NULL
             AND date BETWEEN ? AND ?
           ORDER BY date""",
        (start, end),
    ).fetchall()
    weeks, z12, z3, z45 = [], [], [], []
    for d, mj_raw in rows:
        mj = json.loads(mj_raw) if isinstance(mj_raw, str) else (mj_raw or {})
        if not mj:
            continue
        weeks.append(d[5:])
        z12.append(round(float(mj.get("z12", 0)), 1))
        z3.append(round(float(mj.get("z3", 0)), 1))
        z45.append(round(float(mj.get("z45", 0)), 1))
    return {"weeks": weeks, "z12": z12, "z3": z3, "z45": z45}
