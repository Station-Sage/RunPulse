"""VDOT_ADJ (VDOT Adjusted) — HR-페이스 회귀 + EF 추세 기반 VDOT 보정.

기존 VDOT (Jack Daniels / Garmin VO2Max)에 추가 보정:
1. HR-페이스 회귀: 최근 활동들의 (HR, pace) 쌍으로 HR 80%에서의 예상 페이스 → VDOT 역산
2. EF 추세: EF 7일 평균 변화율로 체력 변화 반영

VDOT_ADJ = VDOT_base × (1 + ef_trend) × hr_pace_correction
저장: computed_metrics (date, 'VDOT_ADJ', value, extra_json)
"""
from __future__ import annotations

import math
import sqlite3
from datetime import date, timedelta

from src.metrics.store import save_metric


def _linear_regression(x: list[float], y: list[float]) -> tuple[float, float]:
    """단순 선형 회귀. Returns (slope, intercept)."""
    n = len(x)
    if n < 2:
        return 0.0, 0.0
    sx = sum(x)
    sy = sum(y)
    sxx = sum(xi * xi for xi in x)
    sxy = sum(xi * yi for xi, yi in zip(x, y))
    denom = n * sxx - sx * sx
    if abs(denom) < 1e-10:
        return 0.0, sy / n if n > 0 else 0.0
    slope = (n * sxy - sx * sy) / denom
    intercept = (sy - slope * sx) / n
    return slope, intercept


def calc_and_save_vdot_adj(conn: sqlite3.Connection, target_date: str) -> float | None:
    """VDOT 보정 계산 후 저장.

    Returns:
        보정된 VDOT 또는 None.
    """
    td = date.fromisoformat(target_date)

    # 기본 VDOT
    base_row = conn.execute(
        "SELECT metric_value FROM computed_metrics WHERE metric_name='VDOT' "
        "AND activity_id IS NULL AND date<=? AND metric_value IS NOT NULL "
        "ORDER BY date DESC LIMIT 1",
        (target_date,),
    ).fetchone()
    if not base_row:
        return None
    vdot_base = float(base_row[0])

    # 1. HR-페이스 회귀
    start_12w = (td - timedelta(weeks=12)).isoformat()
    rows = conn.execute(
        "SELECT avg_hr, avg_pace_sec_km FROM v_canonical_activities "
        "WHERE activity_type='running' AND avg_hr IS NOT NULL AND avg_hr > 100 "
        "AND avg_pace_sec_km IS NOT NULL AND avg_pace_sec_km > 0 "
        "AND distance_km >= 3 AND DATE(start_time) BETWEEN ? AND ?",
        (start_12w, target_date),
    ).fetchall()

    hr_pace_correction = 1.0
    if len(rows) >= 5:
        hrs = [float(r[0]) for r in rows]
        paces = [float(r[1]) for r in rows]
        slope, intercept = _linear_regression(hrs, paces)

        # HR 80%에서의 예상 페이스
        hr_max_row = conn.execute(
            "SELECT MAX(max_hr) FROM activity_summaries WHERE max_hr IS NOT NULL"
        ).fetchone()
        hr_max = float(hr_max_row[0]) if hr_max_row and hr_max_row[0] else 190.0
        hr_80pct = hr_max * 0.8
        predicted_pace = slope * hr_80pct + intercept

        if predicted_pace > 0:
            from src.metrics.vdot import estimate_vdot
            hr_vdot = estimate_vdot(10000, predicted_pace * 10)  # 10km 환산
            if hr_vdot and hr_vdot > 0:
                hr_pace_correction = hr_vdot / vdot_base
                # 보정 범위 제한 (±15%)
                hr_pace_correction = max(0.85, min(1.15, hr_pace_correction))

    # 2. EF 추세 (28일)
    start_28d = (td - timedelta(days=28)).isoformat()
    mid_date = (td - timedelta(days=14)).isoformat()

    ef_first = conn.execute(
        "SELECT AVG(metric_value) FROM computed_metrics WHERE metric_name='EF' "
        "AND activity_id IS NOT NULL AND date BETWEEN ? AND ? AND metric_value IS NOT NULL",
        (start_28d, mid_date),
    ).fetchone()
    ef_second = conn.execute(
        "SELECT AVG(metric_value) FROM computed_metrics WHERE metric_name='EF' "
        "AND activity_id IS NOT NULL AND date BETWEEN ? AND ? AND metric_value IS NOT NULL",
        (mid_date, target_date),
    ).fetchone()

    ef_trend = 0.0
    if ef_first and ef_second and ef_first[0] and ef_second[0]:
        ef1 = float(ef_first[0])
        ef2 = float(ef_second[0])
        if ef1 > 0:
            ef_trend = (ef2 - ef1) / ef1  # 변화율
            ef_trend = max(-0.1, min(0.1, ef_trend))  # ±10% 범위 제한

    # 보정 VDOT
    vdot_adj = round(vdot_base * hr_pace_correction * (1 + ef_trend), 1)
    # 합리적 범위
    if vdot_adj < 15 or vdot_adj > 90:
        vdot_adj = vdot_base

    save_metric(conn, target_date, "VDOT_ADJ", vdot_adj, extra_json={
        "vdot_base": vdot_base,
        "hr_pace_correction": round(hr_pace_correction, 4),
        "ef_trend": round(ef_trend, 4),
        "sample_count": len(rows),
    })
    return vdot_adj
