"""LSI (Load Spike Index) — 갑작스러운 훈련 부하 급증 감지.

LSI = today_load / rolling_21day_avg_load

기준:
  < 0.8  : 훈련 부족
  0.8-1.3: 정상
  1.3-1.5: 주의
  > 1.5  : 위험

부하값: TRIMP > rTSS > distance_km 순서로 우선 사용.
Sprint 1에서는 distance_km 기반 부하 사용, Sprint 2에서 TRIMP로 교체 예정.
"""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from src.metrics.store import save_metric


def calc_lsi(today_load: float, rolling_loads: list[float]) -> float | None:
    """LSI 계산 (순수 함수).

    Args:
        today_load: 오늘 활동 총 부하.
        rolling_loads: 과거 21일 각 일별 부하 리스트.

    Returns:
        LSI 값 또는 None (부하 데이터 없음).
    """
    if today_load <= 0:
        return None
    valid = [v for v in rolling_loads if v > 0]
    if not valid:
        return None
    avg = sum(valid) / len(valid)
    if avg <= 0:
        return None
    return today_load / avg


def lsi_risk_level(lsi: float) -> str:
    """LSI 위험 수준 분류.

    Returns:
        'low' | 'normal' | 'caution' | 'danger'
    """
    if lsi < 0.8:
        return "low"
    if lsi <= 1.3:
        return "normal"
    if lsi <= 1.5:
        return "caution"
    return "danger"


def _get_daily_load(conn: sqlite3.Connection, target_date: str) -> float:
    """날짜별 총 부하 조회.

    우선순위: TRIMP 합계 > distance_km 합계.
    Sprint 2에서 TRIMP 도입 후 자동 전환.
    """
    # TRIMP가 computed_metrics에 있으면 사용
    row = conn.execute(
        """SELECT metric_value FROM computed_metrics
           WHERE date=? AND metric_name='TRIMP' AND activity_id IS NULL""",
        (target_date,),
    ).fetchone()
    if row and row[0] is not None:
        return float(row[0])

    # fallback: 해당 날짜 활동들의 distance_km 합
    row = conn.execute(
        """SELECT COALESCE(SUM(distance_km), 0)
           FROM v_canonical_activities
           WHERE DATE(start_time) = ? AND distance_km IS NOT NULL""",
        (target_date,),
    ).fetchone()
    return float(row[0]) if row and row[0] else 0.0


def calc_and_save_lsi(conn: sqlite3.Connection, target_date: str) -> float | None:
    """LSI 계산 후 computed_metrics에 저장.

    Args:
        conn: SQLite 커넥션.
        target_date: YYYY-MM-DD.

    Returns:
        LSI 값 또는 None.
    """
    today_load = _get_daily_load(conn, target_date)
    if today_load <= 0:
        return None

    # 과거 21일 부하
    td = date.fromisoformat(target_date)
    rolling_loads = []
    for i in range(1, 22):
        d = (td - timedelta(days=i)).isoformat()
        rolling_loads.append(_get_daily_load(conn, d))

    lsi = calc_lsi(today_load, rolling_loads)
    if lsi is not None:
        save_metric(
            conn,
            date=target_date,
            metric_name="LSI",
            value=lsi,
            extra_json={"risk": lsi_risk_level(lsi), "today_load": today_load},
        )
    return lsi
