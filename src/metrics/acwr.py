"""ACWR (Acute:Chronic Workload Ratio) — 급성/만성 부하 비율.

ACWR = sum(trimp_7d) / mean(trimp_28d_daily)

기준:
  < 0.8 : 훈련 부족 (Undertraining)
  0.8-1.3: 최적 훈련 구간 (Sweet Spot)
  1.3-1.5: 주의 (Danger Zone 진입)
  > 1.5 : 부상 위험 (Danger Zone)
"""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from src.metrics.store import save_metric
from src.metrics.trimp import get_daily_trimp, get_trimp_series


def calc_acwr(trimp_7d: list[float], trimp_28d: list[float]) -> float | None:
    """ACWR 계산 (표준 공식).

    ACWR = (7일 합계 / 7) / (28일 합계 / 28)
    휴식일(TRIMP=0)도 포함하여 평균 계산.

    Args:
        trimp_7d: 최근 7일 일별 TRIMP 리스트.
        trimp_28d: 최근 28일 일별 TRIMP 리스트.

    Returns:
        ACWR 값 또는 None (만성 부하 = 0).
    """
    if not trimp_28d:
        return None
    acute_avg = sum(trimp_7d) / 7
    chronic_avg = sum(trimp_28d) / 28
    if chronic_avg <= 0:
        return None
    return round(acute_avg / chronic_avg, 2)


def acwr_risk_level(acwr: float) -> str:
    """ACWR 위험 수준.

    Returns:
        'undertraining' | 'optimal' | 'caution' | 'danger'
    """
    if acwr < 0.8:
        return "undertraining"
    if acwr <= 1.3:
        return "optimal"
    if acwr <= 1.5:
        return "caution"
    return "danger"


def calc_and_save_acwr(conn: sqlite3.Connection, target_date: str) -> float | None:
    """ACWR 계산 후 computed_metrics에 저장.

    Args:
        conn: SQLite 커넥션.
        target_date: YYYY-MM-DD.

    Returns:
        ACWR 값 또는 None.
    """
    td = date.fromisoformat(target_date)

    # 7일 TRIMP (오늘 포함)
    start_7 = (td - timedelta(days=6)).isoformat()
    trimp_7d = get_trimp_series(conn, start_7, target_date)

    # 28일 TRIMP
    start_28 = (td - timedelta(days=27)).isoformat()
    trimp_28d = get_trimp_series(conn, start_28, target_date)

    acwr = calc_acwr(trimp_7d, trimp_28d)
    if acwr is not None:
        save_metric(
            conn,
            date=target_date,
            metric_name="ACWR",
            value=acwr,
            extra_json={
                "risk": acwr_risk_level(acwr),
                "status": acwr_risk_level(acwr),
                "acute_avg": round(sum(trimp_7d) / 7, 1),
                "chronic_avg": round(sum(trimp_28d) / 28, 1),
                "acute_trimp": round(sum(trimp_7d), 1),
            },
        )
    return acwr
