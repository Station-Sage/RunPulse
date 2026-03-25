"""활동 상세 — 신규 데이터 로더 (UI 재설계용).

EF/Decoupling 시계열, 과훈련 위험 시리즈, TIDS 주간 추세, DARP 값.
"""
from __future__ import annotations

import json
import sqlite3


def load_ef_decoupling_series(conn: sqlite3.Connection, target_date: str, days: int = 30) -> dict:
    """EF·Decoupling 30일 활동별 시계열."""
    rows = conn.execute(
        """SELECT date, metric_name, metric_value
           FROM computed_metrics
           WHERE metric_name IN ('EF', 'AerobicDecoupling')
             AND activity_id IS NOT NULL
             AND date >= date(?, '-' || ? || ' days')
             AND date <= ?
           ORDER BY date""",
        (target_date, days, target_date),
    ).fetchall()
    dates_ef, vals_ef = [], []
    dates_dec, vals_dec = [], []
    for d, name, val in rows:
        if val is None:
            continue
        if name == "EF":
            dates_ef.append(d)
            vals_ef.append(round(float(val), 4))
        elif name == "AerobicDecoupling":
            dates_dec.append(d)
            vals_dec.append(round(float(val), 1))
    return {
        "ef": {"dates": dates_ef, "values": vals_ef},
        "decoupling": {"dates": dates_dec, "values": vals_dec},
    }


def load_risk_series(conn: sqlite3.Connection, target_date: str, days: int = 60) -> dict:
    """ACWR·Monotony·Strain·LSI 일별 시계열 (60일)."""
    rows = conn.execute(
        """SELECT date, metric_name, metric_value
           FROM computed_metrics
           WHERE metric_name IN ('ACWR', 'Monotony', 'Strain', 'LSI')
             AND activity_id IS NULL
             AND date >= date(?, '-' || ? || ' days')
             AND date <= ?
           ORDER BY date""",
        (target_date, days, target_date),
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
        "lsi": [by_date[d].get("LSI") for d in dates],
    }


def load_tids_weekly_series(conn: sqlite3.Connection, target_date: str, weeks: int = 8) -> dict:
    """TIDS 주간 z12/z3/z45 시리즈 (8주)."""
    days = weeks * 7
    rows = conn.execute(
        """SELECT date, metric_json
           FROM computed_metrics
           WHERE metric_name = 'TIDS'
             AND activity_id IS NULL
             AND date >= date(?, '-' || ? || ' days')
             AND date <= ?
           ORDER BY date""",
        (target_date, days, target_date),
    ).fetchall()
    week_labels, z12_vals, z3_vals, z45_vals = [], [], [], []
    for d, mj_raw in rows:
        mj = json.loads(mj_raw) if isinstance(mj_raw, str) else (mj_raw or {})
        if not mj:
            continue
        week_labels.append(d[5:])
        z12_vals.append(round(float(mj.get("z12", 0)), 1))
        z3_vals.append(round(float(mj.get("z3", 0)), 1))
        z45_vals.append(round(float(mj.get("z45", 0)), 1))
    return {"weeks": week_labels, "z12": z12_vals, "z3": z3_vals, "z45": z45_vals}


def load_darp_values(conn: sqlite3.Connection, target_date: str) -> dict:
    """DARP 레이스 예측 값 (5k/10k/half/full)."""
    rows = conn.execute(
        """SELECT metric_name, metric_json
           FROM computed_metrics
           WHERE metric_name IN ('DARP_5k', 'DARP_10k', 'DARP_half', 'DARP_full')
             AND activity_id IS NULL
             AND date = ?""",
        (target_date,),
    ).fetchall()
    result = {}
    for name, mj_raw in rows:
        mj = json.loads(mj_raw) if isinstance(mj_raw, str) else (mj_raw or {})
        result[name] = mj
    return result
