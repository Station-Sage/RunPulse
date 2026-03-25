"""Monotony & Training Strain (Banister).

monotony = mean(trimp_7d) / std(trimp_7d)
strain   = monotony * sum(trimp_7d)

높은 monotony (>2.0): 매일 비슷한 강도로 훈련 → 부상/과훈련 위험
strain: 누적 부담 (monotony × 총 부하)

CIRS Monotony_risk 기준:
  > 2.0 : 100 (위험)
  > 1.5 : 60  (경고)
  ≤ 1.5 : 0   (안전)
"""
from __future__ import annotations

import math
import sqlite3
from datetime import date, timedelta

from src.metrics.store import save_metric
from src.metrics.trimp import get_trimp_series


def calc_monotony(trimp_7d: list[float]) -> float | None:
    """Monotony 계산 (순수 함수).

    Args:
        trimp_7d: 최근 7일 일별 TRIMP 리스트 (0 포함).

    Returns:
        Monotony 값 또는 None (std=0 또는 데이터 없음).
    """
    if len(trimp_7d) < 2:
        return None

    n = len(trimp_7d)
    mean_v = sum(trimp_7d) / n
    variance = sum((x - mean_v) ** 2 for x in trimp_7d) / n
    std_v = math.sqrt(variance)

    if std_v <= 0:
        return None  # 완전히 동일한 훈련 → 무한대 방지

    return mean_v / std_v


def calc_strain(monotony: float, trimp_7d: list[float]) -> float:
    """Training Strain 계산.

    Args:
        monotony: calc_monotony() 결과.
        trimp_7d: 최근 7일 일별 TRIMP 리스트.

    Returns:
        Strain 값.
    """
    return monotony * sum(trimp_7d)


def calc_and_save_monotony(conn: sqlite3.Connection, target_date: str) -> dict | None:
    """Monotony + Strain 계산 후 저장.

    Args:
        conn: SQLite 커넥션.
        target_date: YYYY-MM-DD.

    Returns:
        {'monotony': ..., 'strain': ...} 또는 None.
    """
    td = date.fromisoformat(target_date)
    start_date = (td - timedelta(days=6)).isoformat()
    trimp_7d = get_trimp_series(conn, start_date, target_date)

    monotony = calc_monotony(trimp_7d)
    if monotony is None:
        return None

    strain = calc_strain(monotony, trimp_7d)

    save_metric(
        conn,
        date=target_date,
        metric_name="Monotony",
        value=monotony,
        extra_json={"strain": strain, "trimp_sum": sum(trimp_7d)},
    )
    save_metric(conn, date=target_date, metric_name="Strain", value=strain)
    return {"monotony": monotony, "strain": strain}


def get_monotony(conn: sqlite3.Connection, target_date: str) -> float | None:
    """저장된 Monotony 값 조회."""
    row = conn.execute(
        """SELECT metric_value FROM computed_metrics
           WHERE date=? AND metric_name='Monotony' AND activity_id IS NULL""",
        (target_date,),
    ).fetchone()
    return float(row[0]) if row and row[0] is not None else None
