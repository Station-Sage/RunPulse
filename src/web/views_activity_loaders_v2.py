"""활동 상세 — 신규 데이터 로더 (UI 재설계용).

EF/Decoupling 시계열, 과훈련 위험 시리즈, TIDS 주간 추세, DARP 값.
"""
from __future__ import annotations

import json
import sqlite3


def load_ef_decoupling_series(conn: sqlite3.Connection, target_date: str, days: int = 30) -> dict:
    """EF·Decoupling 30일 활동별 시계열."""
    rows = conn.execute(
        """SELECT scope_id AS date, metric_name, numeric_value
           FROM metric_store
           WHERE metric_name IN ('efficiency_factor_rp', 'aerobic_decoupling_rp')
             AND scope_type='activity' AND is_primary=1
             AND scope_id >= date(?, '-' || ? || ' days')
             AND scope_id <= ?
           ORDER BY scope_id""",
        (target_date, days, target_date),
    ).fetchall()
    dates_ef, vals_ef = [], []
    dates_dec, vals_dec = [], []
    for d, name, val in rows:
        if val is None:
            continue
        if name == "efficiency_factor_rp":
            dates_ef.append(d)
            vals_ef.append(round(float(val), 4))
        elif name == "aerobic_decoupling_rp":
            dates_dec.append(d)
            vals_dec.append(round(float(val), 1))
    return {
        "ef": {"dates": dates_ef, "values": vals_ef},
        "decoupling": {"dates": dates_dec, "values": vals_dec},
    }


def load_risk_series(conn: sqlite3.Connection, target_date: str, days: int = 60) -> dict:
    """ACWR·Monotony·Strain·LSI 일별 시계열 (60일)."""
    rows = conn.execute(
        """SELECT scope_id AS date, metric_name, numeric_value
           FROM metric_store
           WHERE metric_name IN ('acwr', 'monotony', 'training_strain', 'lsi')
             AND scope_type='daily' AND is_primary=1
             AND scope_id >= date(?, '-' || ? || ' days')
             AND scope_id <= ?
           ORDER BY scope_id""",
        (target_date, days, target_date),
    ).fetchall()
    by_date: dict[str, dict] = {}
    for d, name, val in rows:
        by_date.setdefault(d, {})[name] = float(val) if val is not None else None
    dates = sorted(by_date.keys())
    return {
        "dates": dates,
        "acwr": [by_date[d].get("acwr") for d in dates],
        "monotony": [by_date[d].get("monotony") for d in dates],
        "strain": [by_date[d].get("training_strain") for d in dates],
        "lsi": [by_date[d].get("lsi") for d in dates],
    }


def load_tids_weekly_series(conn: sqlite3.Connection, target_date: str, weeks: int = 8) -> dict:
    """TIDS 주간 z12/z3/z45 시리즈 (8주)."""
    days = weeks * 7
    rows = conn.execute(
        """SELECT scope_id AS date, json_value
           FROM metric_store
           WHERE metric_name = 'tids'
             AND scope_type='daily' AND is_primary=1
             AND scope_id >= date(?, '-' || ? || ' days')
             AND scope_id <= ?
           ORDER BY scope_id""",
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
        """SELECT metric_name, json_value
           FROM metric_store
           WHERE metric_name IN ('race_pred_5k_sec', 'race_pred_10k_sec', 'race_pred_half_sec', 'race_pred_marathon_sec')
             AND scope_type='daily' AND is_primary=1
             AND scope_id = ?""",
        (target_date,),
    ).fetchall()
    result = {}
    for name, mj_raw in rows:
        mj = json.loads(mj_raw) if isinstance(mj_raw, str) else (mj_raw or {})
        result[name] = mj
    return result
