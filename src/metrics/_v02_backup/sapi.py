"""SAPI (Seasonal-Adjusted Performance Index) — 계절·날씨 성과 비교.

기온 구간별 FEARP 평균을 비교하여 계절 영향을 정량화.
기준 구간(10~15°C)의 FEARP 대비 현재 기온 구간의 FEARP 비율.

SAPI = (기준 FEARP / 현재 FEARP) × 100
- 100 = 기준과 동일 성능
- 100+ = 기준보다 좋은 성능 (추운 날씨 등)
- 100 미만 = 기준보다 낮은 성능 (더운 날씨 등)

저장: computed_metrics (date, 'SAPI', value, extra_json)
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date, timedelta

from src.metrics.store import save_metric

# 기온 구간 정의 (°C)
_TEMP_BINS = [
    ("극한 추위", -20, 0),
    ("추움", 0, 10),
    ("적정 (기준)", 10, 15),
    ("따뜻함", 15, 25),
    ("더움", 25, 35),
    ("극한 더위", 35, 50),
]


def calc_and_save_sapi(conn: sqlite3.Connection, target_date: str,
                       lookback_days: int = 90) -> float | None:
    """SAPI 계산 후 저장.

    최근 lookback_days 동안의 활동에서 기온 구간별 FEARP 평균 비교.

    Returns:
        SAPI 값 또는 None.
    """
    td = date.fromisoformat(target_date)
    start = (td - timedelta(days=lookback_days)).isoformat()

    # FEARP + 기온 데이터 수집
    rows = conn.execute(
        """SELECT cm.metric_value, cm.metric_json, cm.date
           FROM computed_metrics cm
           WHERE cm.metric_name='FEARP' AND cm.activity_id IS NOT NULL
             AND cm.date BETWEEN ? AND ? AND cm.metric_value IS NOT NULL""",
        (start, target_date),
    ).fetchall()

    if len(rows) < 3:
        return None

    # 기온 구간별 FEARP 집계
    bin_data: dict[str, list[float]] = {b[0]: [] for b in _TEMP_BINS}
    for fearp_val, mj_raw, dt in rows:
        temp = _extract_temp(mj_raw, conn, dt)
        if temp is None:
            continue
        for label, lo, hi in _TEMP_BINS:
            if lo <= temp < hi:
                bin_data[label].append(float(fearp_val))
                break

    # 기준 구간 (10~15°C) 평균
    ref_vals = bin_data.get("적정 (기준)", [])
    if not ref_vals:
        # 기준 구간 데이터 없으면 전체 평균을 기준으로
        all_vals = [v for vals in bin_data.values() for v in vals]
        if not all_vals:
            return None
        ref_avg = sum(all_vals) / len(all_vals)
    else:
        ref_avg = sum(ref_vals) / len(ref_vals)

    if ref_avg <= 0:
        return None

    # 최근 7일 평균 FEARP
    recent_start = (td - timedelta(days=7)).isoformat()
    recent_rows = conn.execute(
        "SELECT metric_value FROM computed_metrics WHERE metric_name='FEARP' "
        "AND activity_id IS NOT NULL AND date BETWEEN ? AND ? "
        "AND metric_value IS NOT NULL",
        (recent_start, target_date),
    ).fetchall()
    if not recent_rows:
        return None
    current_avg = sum(r[0] for r in recent_rows) / len(recent_rows)

    if current_avg <= 0:
        return None

    # SAPI = 기준/현재 × 100 (FEARP는 sec/km이므로 낮을수록 빠름)
    sapi = round(ref_avg / current_avg * 100, 1)

    # 구간별 통계 JSON
    bin_stats = {}
    for label, vals in bin_data.items():
        if vals:
            bin_stats[label] = {
                "avg_fearp": round(sum(vals) / len(vals), 1),
                "count": len(vals),
            }

    save_metric(conn, target_date, "SAPI", sapi, extra_json={
        "ref_avg_fearp": round(ref_avg, 1),
        "current_avg_fearp": round(current_avg, 1),
        "bins": bin_stats,
        "lookback_days": lookback_days,
    })
    return sapi


def _extract_temp(mj_raw: str | None, conn: sqlite3.Connection,
                  dt: str) -> float | None:
    """FEARP JSON 또는 날씨 데이터에서 기온 추출."""
    if mj_raw:
        try:
            mj = json.loads(mj_raw) if isinstance(mj_raw, str) else mj_raw
            temp = mj.get("temperature") or mj.get("temp_c")
            if temp is not None:
                return float(temp)
        except (json.JSONDecodeError, TypeError):
            pass

    # 날씨 테이블에서 조회
    try:
        row = conn.execute(
            "SELECT temperature FROM daily_weather WHERE date=? LIMIT 1",
            (dt,),
        ).fetchone()
        if row and row[0] is not None:
            return float(row[0])
    except Exception:
        pass

    return None
