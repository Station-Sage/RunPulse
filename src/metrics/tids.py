"""TIDS (Training Intensity Distribution Score) — 훈련 강도 분포 점수.

심박존별 훈련 시간 분포와 목표 모델 편차 계산.

목표 모델:
    폴라리제드: Zone1-2 80%, Zone3 5%, Zone4-5 15%
    피라미드:   Zone1-2 70%, Zone3 20%, Zone4-5 10%
    건강유지:   Zone1-2 60%, Zone3 30%, Zone4-5 10%

저장: computed_metrics (date, 'TIDS', JSON {z12, z3, z45, polar_dev, pyramid_dev, health_dev, dominant_model})
"""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from src.metrics.store import save_metric

# 목표 모델 정의 (z12%, z3%, z45%)
_MODELS = {
    "polarized": (80.0, 5.0, 15.0),
    "pyramid": (70.0, 20.0, 10.0),
    "health": (60.0, 30.0, 10.0),
}


def calc_tids(zone_minutes: list[float]) -> dict:
    """TIDS 계산 (순수 함수).

    Args:
        zone_minutes: [z1_min, z2_min, z3_min, z4_min, z5_min] 각 존별 분.
                      5개 값 필요; 데이터 부족 존은 0으로 처리.

    Returns:
        {z12, z3, z45, polar_dev, pyramid_dev, health_dev, dominant_model}
    """
    zm = (list(zone_minutes) + [0.0] * 5)[:5]
    total = sum(zm)

    if total <= 0:
        return {
            "z12": 0.0, "z3": 0.0, "z45": 0.0,
            "polar_dev": 100.0, "pyramid_dev": 100.0, "health_dev": 100.0,
            "dominant_model": None,
        }

    z12 = (zm[0] + zm[1]) / total * 100
    z3 = zm[2] / total * 100
    z45 = (zm[3] + zm[4]) / total * 100

    deviations = {}
    for model, (t12, t3, t45) in _MODELS.items():
        dev = abs(z12 - t12) + abs(z3 - t3) + abs(z45 - t45)
        deviations[model] = round(dev, 1)

    dominant = min(deviations, key=lambda m: deviations[m])

    return {
        "z12": round(z12, 1),
        "z3": round(z3, 1),
        "z45": round(z45, 1),
        "polar_dev": deviations["polarized"],
        "pyramid_dev": deviations["pyramid"],
        "health_dev": deviations["health"],
        "dominant_model": dominant,
    }


def _get_zone_minutes_from_db(
    conn: sqlite3.Connection,
    start_date: str,
    end_date: str,
) -> list[float]:
    """DB에서 기간 내 HR존 시간 집계.

    우선순위:
    1. hr_zone_{N}_sec  (Garmin sync_activity_hr_zones — 초 단위)
    2. heartrate_zone_{N}_sec  (Strava _sync_activity_zones — 초 단위)
    3. hr_zone_time_{N}  (구형 저장 형식 — 초 단위)

    Args:
        conn: SQLite 커넥션.
        start_date: YYYY-MM-DD.
        end_date: YYYY-MM-DD.

    Returns:
        [z1_min, z2_min, z3_min, z4_min, z5_min] 단위: 분
    """
    # 소스별 메트릭 이름 후보 (우선순위 순)
    _NAME_PATTERNS = [
        "hr_zone_{}_sec",
        "heartrate_zone_{}_sec",
        "hr_zone_time_{}",
    ]

    zone_totals = [0.0] * 5
    for zone_idx in range(1, 6):
        for pattern in _NAME_PATTERNS:
            metric_name = pattern.format(zone_idx)
            row = conn.execute(
                """SELECT COALESCE(SUM(m.metric_value), 0)
                   FROM activity_detail_metrics m
                   JOIN activity_summaries a ON a.id = m.activity_id
                   WHERE m.metric_name = ?
                     AND DATE(a.start_time) BETWEEN ? AND ?""",
                (metric_name, start_date, end_date),
            ).fetchone()
            total_sec = float(row[0]) if row and row[0] else 0.0
            if total_sec > 0:
                zone_totals[zone_idx - 1] = total_sec / 60.0  # 초 → 분
                break  # 이 존은 찾았으니 다음 존으로
    return zone_totals


def calc_and_save_tids(conn: sqlite3.Connection, target_date: str) -> dict | None:
    """TIDS 계산 후 computed_metrics에 저장.

    최근 4주 HR존 분포 집계.

    Args:
        conn: SQLite 커넥션.
        target_date: YYYY-MM-DD.

    Returns:
        TIDS 딕셔너리 또는 None (데이터 없음).
    """
    td = date.fromisoformat(target_date)
    start_date = (td - timedelta(weeks=4)).isoformat()

    zone_minutes = _get_zone_minutes_from_db(conn, start_date, target_date)
    total = sum(zone_minutes)

    if total <= 0:
        return None

    result = calc_tids(zone_minutes)
    # 요약 단일 값: polar_dev (낮을수록 폴라리제드에 가까움)
    save_metric(
        conn,
        date=target_date,
        metric_name="TIDS",
        value=result["polar_dev"],
        extra_json=result,
    )
    return result
