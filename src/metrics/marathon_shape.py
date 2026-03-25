"""Marathon Shape (Runalyze 방식) — 마라톤 훈련 완성도.

공식:
    target_weekly_km = vdot * 0.8
    target_long_km   = vdot * 0.35
    weekly_shape   = min(1.0, weekly_km_avg / target_weekly_km)
    long_run_shape = min(1.0, longest_run_km / target_long_km)
    shape_pct = (weekly_shape * 2/3 + long_run_shape * 1/3) * 100

기준:
    < 40%:  훈련 부족 (레이스 준비 안 됨)
    40-60%: 기초 훈련
    60-80%: 훈련 진행 중
    80-90%: 충분한 준비
    > 90%:  최적 준비
"""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from src.metrics.store import save_metric


def calc_marathon_shape(
    weekly_km_avg: float,
    longest_run_km: float,
    vdot: float,
) -> float | None:
    """Marathon Shape 계산 (순수 함수).

    Args:
        weekly_km_avg: 최근 4주 평균 주간 거리 (km).
        longest_run_km: 최근 4주 최장 거리 (km).
        vdot: VDOT 값.

    Returns:
        Marathon Shape 퍼센트 (0~100) 또는 None (VDOT 없음).
    """
    if not vdot or vdot <= 0:
        return None

    target_weekly_km = vdot * 0.8
    target_long_km = vdot * 0.35

    if target_weekly_km <= 0 or target_long_km <= 0:
        return None

    weekly_shape = min(1.0, weekly_km_avg / target_weekly_km)
    long_run_shape = min(1.0, longest_run_km / target_long_km)
    shape_pct = (weekly_shape * 2 / 3 + long_run_shape * 1 / 3) * 100

    return round(shape_pct, 1)


def marathon_shape_label(shape_pct: float) -> str:
    """Marathon Shape 상태 레이블.

    Returns:
        'insufficient' | 'base' | 'building' | 'ready' | 'peak'
    """
    if shape_pct < 40:
        return "insufficient"
    if shape_pct < 60:
        return "base"
    if shape_pct < 80:
        return "building"
    if shape_pct < 90:
        return "ready"
    return "peak"


def _get_recent_running_data(
    conn: sqlite3.Connection, target_date: str, weeks: int = 4
) -> tuple[float, float]:
    """최근 n주 평균 주간 거리 + 최장 거리 조회.

    Returns:
        (weekly_km_avg, longest_run_km)
    """
    td = date.fromisoformat(target_date)
    start_date = (td - timedelta(weeks=weeks)).isoformat()

    # 최장 거리
    row = conn.execute(
        """SELECT COALESCE(MAX(distance_km), 0)
           FROM v_canonical_activities
           WHERE DATE(start_time) BETWEEN ? AND ?
             AND activity_type = 'running'
             AND distance_km IS NOT NULL""",
        (start_date, target_date),
    ).fetchone()
    longest_km = float(row[0]) if row and row[0] else 0.0

    # 주별 총 거리 → 평균
    row = conn.execute(
        """SELECT COALESCE(SUM(distance_km), 0)
           FROM v_canonical_activities
           WHERE DATE(start_time) BETWEEN ? AND ?
             AND activity_type = 'running'
             AND distance_km IS NOT NULL""",
        (start_date, target_date),
    ).fetchone()
    total_km = float(row[0]) if row and row[0] else 0.0
    weekly_avg = total_km / weeks if weeks > 0 else 0.0

    return weekly_avg, longest_km


def _get_vdot(conn: sqlite3.Connection, target_date: str) -> float | None:
    """가장 최신 VDOT 값 조회.

    우선순위: daily_fitness.runalyze_vdot > 직접 계산 예정.
    """
    row = conn.execute(
        """SELECT runalyze_vdot FROM daily_fitness
           WHERE runalyze_vdot IS NOT NULL AND date <= ?
           ORDER BY date DESC LIMIT 1""",
        (target_date,),
    ).fetchone()
    if row and row[0]:
        return float(row[0])

    # computed_metrics에 VDOT이 있으면 사용
    row = conn.execute(
        """SELECT metric_value FROM computed_metrics
           WHERE metric_name='VDOT' AND metric_value IS NOT NULL AND date <= ?
           ORDER BY date DESC LIMIT 1""",
        (target_date,),
    ).fetchone()
    return float(row[0]) if row and row[0] else None


def calc_and_save_marathon_shape(
    conn: sqlite3.Connection, target_date: str
) -> float | None:
    """Marathon Shape 계산 후 computed_metrics에 저장.

    Args:
        conn: SQLite 커넥션.
        target_date: YYYY-MM-DD.

    Returns:
        shape_pct 또는 None.
    """
    vdot = _get_vdot(conn, target_date)
    if vdot is None:
        return None

    weekly_km_avg, longest_km = _get_recent_running_data(conn, target_date)

    shape = calc_marathon_shape(weekly_km_avg, longest_km, vdot)
    if shape is not None:
        save_metric(
            conn,
            date=target_date,
            metric_name="MarathonShape",
            value=shape,
            extra_json={
                "label": marathon_shape_label(shape),
                "weekly_km_avg": round(weekly_km_avg, 1),
                "longest_run_km": round(longest_km, 1),
                "vdot": vdot,
                "target_weekly_km": round(vdot * 0.8, 1),
                "target_long_km": round(vdot * 0.35, 1),
            },
        )
    return shape
