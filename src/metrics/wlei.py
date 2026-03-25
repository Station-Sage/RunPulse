"""WLEI (Weather-Loaded Effort Index) — 날씨 가중 노력 지수.

TRIMP에 날씨 스트레스 계수를 곱해 실제 신체 부담을 반영.

공식:
    temp_stress    = 1 + max(0, temp_c - 20) * 0.025   (20°C 초과 시 추가)
                   + max(0, 5 - temp_c)   * 0.015       (5°C 미만 시 추가)
    humidity_stress = 1 + max(0, humidity_pct - 60) * 0.008
    WLEI = TRIMP * temp_stress * humidity_stress

저장: computed_metrics (date, 'WLEI', value, activity_id, extra_json)
"""
from __future__ import annotations

import sqlite3

from src.metrics.store import save_metric


def calc_wlei(
    trimp: float,
    temp_c: float = 20.0,
    humidity_pct: float = 60.0,
) -> float:
    """WLEI 계산 (순수 함수).

    Args:
        trimp: TRIMP 값.
        temp_c: 기온 (°C).
        humidity_pct: 습도 (%).

    Returns:
        WLEI 값.
    """
    temp_stress = (
        1.0
        + max(0.0, temp_c - 20.0) * 0.025
        + max(0.0, 5.0 - temp_c) * 0.015
    )
    humidity_stress = 1.0 + max(0.0, humidity_pct - 60.0) * 0.008
    return round(trimp * temp_stress * humidity_stress, 2)


def calc_and_save_wlei(conn: sqlite3.Connection, activity_id: int) -> float | None:
    """활동 ID로 WLEI 계산 후 저장.

    TRIMP은 computed_metrics에서, 날씨는 activity_detail_metrics → activity_summaries
    lat/lon → 없으면 기본값(20°C, 60%)으로 계산.

    Args:
        conn: SQLite 커넥션.
        activity_id: activity_summaries.id.

    Returns:
        WLEI 값 또는 None.
    """
    # TRIMP 조회
    trimp_row = conn.execute(
        """SELECT metric_value FROM computed_metrics
           WHERE activity_id=? AND metric_name='TRIMP'
           ORDER BY computed_at DESC LIMIT 1""",
        (activity_id,),
    ).fetchone()
    if trimp_row is None or trimp_row[0] is None:
        return None
    trimp = float(trimp_row[0])

    # 날씨 데이터 조회 (activity_detail_metrics 우선)
    weather_rows = conn.execute(
        """SELECT metric_name, metric_value FROM activity_detail_metrics
           WHERE activity_id=? AND metric_name IN ('weather_temp_c','weather_humidity_pct')""",
        (activity_id,),
    ).fetchall()
    weather_map = {r[0]: r[1] for r in weather_rows if r[1] is not None}

    temp_c = float(weather_map.get("weather_temp_c", 20.0))
    humidity_pct = float(weather_map.get("weather_humidity_pct", 60.0))

    wlei = calc_wlei(trimp, temp_c, humidity_pct)

    # 활동 날짜 조회
    date_row = conn.execute(
        "SELECT start_time FROM activity_summaries WHERE id=?", (activity_id,)
    ).fetchone()
    if date_row is None:
        return None

    activity_date = date_row[0][:10]
    save_metric(
        conn,
        date=activity_date,
        metric_name="WLEI",
        value=wlei,
        activity_id=activity_id,
        extra_json={
            "trimp": trimp,
            "temp_c": temp_c,
            "humidity_pct": humidity_pct,
        },
    )
    return wlei
