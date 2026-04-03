"""TPDI (Trainer Physical Disparity Index) — 실내/실외 FEARP 격차 지수.

최근 N주 실외(trainer=0) 활동과 실내(trainer=1) 활동의 평균 FEARP 차이를
실외 FEARP 대비 비율로 표현.

공식:
    gap = fearp_outdoor_avg - fearp_indoor_avg
    TPDI = gap / fearp_outdoor_avg * 100  (%)

양수: 실외가 더 빠름 (실내 훈련 대비 실외 페이스 이득)
음수: 실내가 더 빠름 (의외로 실내 퍼포먼스가 우세)
데이터 없으면 None 반환.

저장: computed_metrics (date, 'TPDI', value, extra_json)
"""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from src.metrics.store import save_metric


def calc_tpdi(fearp_outdoor_avg: float, fearp_indoor_avg: float) -> float:
    """TPDI 계산 (순수 함수).

    Args:
        fearp_outdoor_avg: 실외 활동 평균 FEARP (초/km).
        fearp_indoor_avg: 실내 활동 평균 FEARP (초/km).

    Returns:
        TPDI (%). 양수 = 실외가 더 빠름.
    """
    if fearp_outdoor_avg <= 0:
        return 0.0
    gap = fearp_outdoor_avg - fearp_indoor_avg
    return round(gap / fearp_outdoor_avg * 100, 1)


def calc_and_save_tpdi(
    conn: sqlite3.Connection,
    target_date: str,
    weeks: int = 8,
) -> float | None:
    """최근 N주 실내/실외 FEARP 격차 → TPDI 계산 후 저장.

    Args:
        conn: SQLite 커넥션.
        target_date: YYYY-MM-DD 기준일.
        weeks: 집계 기간 (주).

    Returns:
        TPDI 값 또는 None.
    """
    td = date.fromisoformat(target_date)
    start_date = (td - timedelta(weeks=weeks)).isoformat()

    # 실내/실외 FEARP 평균
    row = conn.execute(
        """SELECT
               AVG(CASE WHEN a.trainer = 0 OR a.trainer IS NULL THEN cm.metric_value END) AS outdoor_avg,
               AVG(CASE WHEN a.trainer = 1 THEN cm.metric_value END) AS indoor_avg,
               COUNT(CASE WHEN a.trainer = 0 OR a.trainer IS NULL THEN 1 END) AS outdoor_cnt,
               COUNT(CASE WHEN a.trainer = 1 THEN 1 END) AS indoor_cnt
           FROM computed_metrics cm
           JOIN activity_summaries a ON a.id = cm.activity_id
           WHERE cm.metric_name = 'FEARP'
             AND DATE(a.start_time) BETWEEN ? AND ?
             AND a.activity_type IN ('run', 'trail_run', 'treadmill')
             AND cm.metric_value > 0""",
        (start_date, target_date),
    ).fetchone()

    if row is None:
        return None

    outdoor_avg, indoor_avg, outdoor_cnt, indoor_cnt = row

    # 실내·실외 모두 데이터 있어야 의미 있음
    if not outdoor_avg or not indoor_avg or outdoor_cnt < 2 or indoor_cnt < 2:
        return None

    tpdi = calc_tpdi(float(outdoor_avg), float(indoor_avg))
    save_metric(
        conn,
        date=target_date,
        metric_name="TPDI",
        value=tpdi,
        extra_json={
            "fearp_outdoor_avg": round(float(outdoor_avg), 1),
            "fearp_indoor_avg": round(float(indoor_avg), 1),
            "outdoor_cnt": int(outdoor_cnt),
            "indoor_cnt": int(indoor_cnt),
            "weeks": weeks,
        },
    )
    return tpdi
