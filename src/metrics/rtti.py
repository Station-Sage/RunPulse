"""RTTI (Running Tolerance Training Index) — 달리기 내성 훈련 지수.

Garmin의 running_tolerance_load / optimal_max_load * 100.
100이면 권장 한계에 딱 맞는 훈련량, 100 초과 시 과부하.

없는 날은 None 반환.
저장: computed_metrics (date, 'RTTI', value, extra_json)
"""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from src.metrics.store import save_metric


def calc_rtti(load: float, optimal_max: float) -> float:
    """RTTI 계산 (순수 함수).

    Args:
        load: 실제 훈련 부하.
        optimal_max: 권장 최대 부하.

    Returns:
        RTTI 값 (%). 100 = 최대 권장치.
    """
    if optimal_max <= 0:
        return 0.0
    return round(load / optimal_max * 100, 1)


def calc_and_save_rtti(conn: sqlite3.Connection, target_date: str) -> float | None:
    """당일 또는 최근 7일 running_tolerance_* → RTTI 계산 후 저장.

    Args:
        conn: SQLite 커넥션.
        target_date: YYYY-MM-DD.

    Returns:
        RTTI 값 또는 None.
    """
    td = date.fromisoformat(target_date)
    # 당일부터 최대 7일 이전까지 가장 최근 데이터 탐색
    for delta in range(8):
        check_date = (td - timedelta(days=delta)).isoformat()
        row = conn.execute(
            """SELECT metric_name, metric_value FROM daily_detail_metrics
               WHERE date=? AND metric_name IN (
                 'running_tolerance_load',
                 'running_tolerance_optimal_max',
                 'running_tolerance_score'
               )""",
            (check_date,),
        ).fetchall()
        if not row:
            continue
        m = {r[0]: r[1] for r in row if r[1] is not None}
        load = m.get("running_tolerance_load")
        opt_max = m.get("running_tolerance_optimal_max")
        if load is not None and opt_max is not None and opt_max > 0:
            rtti = calc_rtti(float(load), float(opt_max))
            extra = {
                "load": float(load),
                "optimal_max": float(opt_max),
                "score": m.get("running_tolerance_score"),
                "source_date": check_date,
            }
            save_metric(conn, date=target_date, metric_name="RTTI", value=rtti, extra_json=extra)
            return rtti
    return None
