"""RRI (Race Readiness Index) — 레이스 준비도 종합 지수.

공식: RRI = VDOT진행률 × CTL충족률 × DI계수 × 안전계수 × 100
- VDOT진행률: 현재 VDOT / 목표 VDOT (목표 레이스 페이스에서 역산)
- CTL충족률: 현재 CTL / 권장 CTL (거리별 기준)
- DI계수: min(1.0, DI / 70) — 내구성 70 이상이면 만점
- 안전계수: (100 - CIRS) / 100 — 부상 위험 반영

0~100 스케일. 80+ 레이스 준비 완료, 60~80 보통, 60 미만 부족.
저장: computed_metrics (date, 'RRI', value, extra_json)
"""
from __future__ import annotations

import sqlite3
from datetime import date

from src.metrics.store import save_metric


# 거리별 권장 CTL 기준 (최소한의 체력)
_TARGET_CTL: dict[str, float] = {
    "5k": 25, "10k": 35, "half": 45, "full": 55,
}


def calc_rri(
    vdot_current: float,
    vdot_target: float,
    ctl: float,
    target_ctl: float,
    di: float | None,
    cirs: float | None,
) -> float:
    """RRI 계산 (순수 함수).

    Returns:
        0~100 레이스 준비도 점수.
    """
    # VDOT 진행률
    vdot_pct = min(1.0, vdot_current / vdot_target) if vdot_target > 0 else 0.5

    # CTL 충족률
    ctl_pct = min(1.0, ctl / target_ctl) if target_ctl > 0 else 0.5

    # DI 계수 (70 이상이면 1.0)
    # DI < 2이면 구 비율값(0.8~1.2) → 0~100 스케일로 변환
    di_val = di or 50
    if di_val < 2.0:
        di_val = max(0, min(100, 70 + (di_val - 1.0) * 300))
    di_factor = min(1.0, di_val / 70)

    # 안전 계수 (CIRS 낮을수록 좋음)
    safety = (100 - min(100, cirs or 0)) / 100

    rri = vdot_pct * ctl_pct * di_factor * safety * 100
    return round(min(100, max(0, rri)), 1)


def calc_and_save_rri(conn: sqlite3.Connection, target_date: str) -> float | None:
    """RRI 계산 후 저장.

    Returns:
        RRI 값 (0~100) 또는 None.
    """
    # VDOT
    vdot_row = conn.execute(
        "SELECT metric_value FROM computed_metrics WHERE metric_name='VDOT' "
        "AND activity_id IS NULL AND date<=? AND metric_value IS NOT NULL "
        "ORDER BY date DESC LIMIT 1",
        (target_date,),
    ).fetchone()
    if not vdot_row:
        return None
    vdot = float(vdot_row[0])

    # CTL
    ctl_row = conn.execute(
        "SELECT ctl FROM daily_fitness WHERE date<=? AND ctl IS NOT NULL ORDER BY date DESC LIMIT 1",
        (target_date,),
    ).fetchone()
    ctl = float(ctl_row[0]) if ctl_row else 0.0

    # 목표 거리 (활성 목표에서)
    goal_row = conn.execute(
        "SELECT distance_km, target_pace_sec_km FROM goals WHERE status='active' "
        "ORDER BY created_at DESC LIMIT 1"
    ).fetchone()

    if goal_row and goal_row[0]:
        goal_dist = float(goal_row[0])
        # 거리별 기준 CTL
        if goal_dist >= 40:
            target_ctl = _TARGET_CTL["full"]
        elif goal_dist >= 18:
            target_ctl = _TARGET_CTL["half"]
        elif goal_dist >= 8:
            target_ctl = _TARGET_CTL["10k"]
        else:
            target_ctl = _TARGET_CTL["5k"]

        # 목표 VDOT (목표 페이스에서 역산, 없으면 현재 VDOT 기준)
        target_pace = goal_row[1]
        if target_pace and target_pace > 0:
            from src.metrics.vdot import estimate_vdot
            vdot_target = estimate_vdot(goal_dist * 1000, target_pace * goal_dist) or vdot
        else:
            vdot_target = vdot * 1.05  # 현재 대비 5% 향상 목표
    else:
        # 목표 없으면 하프마라톤 기준
        target_ctl = _TARGET_CTL["half"]
        vdot_target = vdot * 1.05

    # DI
    di_row = conn.execute(
        "SELECT metric_value FROM computed_metrics WHERE metric_name='DI' "
        "AND activity_id IS NULL AND date<=? AND metric_value IS NOT NULL "
        "ORDER BY date DESC LIMIT 1",
        (target_date,),
    ).fetchone()
    di = float(di_row[0]) if di_row else None

    # CIRS
    cirs_row = conn.execute(
        "SELECT metric_value FROM computed_metrics WHERE metric_name='CIRS' "
        "AND activity_id IS NULL AND date<=? AND metric_value IS NOT NULL "
        "ORDER BY date DESC LIMIT 1",
        (target_date,),
    ).fetchone()
    cirs = float(cirs_row[0]) if cirs_row else None

    rri = calc_rri(vdot, vdot_target, ctl, target_ctl, di, cirs)
    save_metric(conn, target_date, "RRI", rri, extra_json={
        "vdot": round(vdot, 1),
        "vdot_target": round(vdot_target, 1),
        "ctl": round(ctl, 1),
        "target_ctl": target_ctl,
        "di": round(di, 1) if di else None,
        "cirs": round(cirs, 1) if cirs else None,
    })
    return rri
