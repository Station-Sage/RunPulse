"""Aerobic Decoupling + EF (Efficiency Factor) 계산.

Aerobic Decoupling (Intervals.icu 방식):
    mid = len(series) // 2
    ef1 = speed[:mid].mean() / hr[:mid].mean()
    ef2 = speed[mid:].mean() / hr[mid:].mean()
    decoupling_pct = (ef1 - ef2) / ef1 * 100

기준: <5% 양호, 5-10% 보통, >10% 낮은 유산소 피트니스

EF (Efficiency Factor) = NGP(m/min) / avg_hr
높을수록 같은 심박수에서 더 빠름 → 유산소 효율 좋음
"""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from src.metrics.gap import pace_to_speed
from src.metrics.store import load_metric_series, save_metric


def calc_decoupling(
    speeds_first_half: list[float],
    hrs_first_half: list[float],
    speeds_second_half: list[float],
    hrs_second_half: list[float],
) -> float | None:
    """Aerobic Decoupling 계산 (순수 함수).

    Args:
        speeds_first_half: 전반부 속도 (m/min) 리스트.
        hrs_first_half: 전반부 HR 리스트.
        speeds_second_half: 후반부 속도 리스트.
        hrs_second_half: 후반부 HR 리스트.

    Returns:
        Decoupling % 또는 None.
    """
    if not speeds_first_half or not hrs_first_half:
        return None
    if not speeds_second_half or not hrs_second_half:
        return None

    ef1 = (sum(speeds_first_half) / len(speeds_first_half)) / (sum(hrs_first_half) / len(hrs_first_half))
    ef2 = (sum(speeds_second_half) / len(speeds_second_half)) / (sum(hrs_second_half) / len(hrs_second_half))

    if ef1 <= 0:
        return None
    return (ef1 - ef2) / ef1 * 100.0


def calc_decoupling_from_laps(laps: list[dict]) -> float | None:
    """랩 데이터로 Aerobic Decoupling 계산.

    Args:
        laps: [{'avg_pace_sec_km': ..., 'avg_hr': ...}, ...] 랩 리스트.

    Returns:
        Decoupling % 또는 None.
    """
    valid = [
        lap for lap in laps
        if lap.get("avg_pace_sec_km") and lap.get("avg_hr") and lap["avg_pace_sec_km"] > 0
    ]
    if len(valid) < 2:
        return None

    mid = len(valid) // 2
    first = valid[:mid]
    second = valid[mid:]

    speeds1 = [pace_to_speed(lap["avg_pace_sec_km"]) for lap in first]
    hrs1 = [float(lap["avg_hr"]) for lap in first]
    speeds2 = [pace_to_speed(lap["avg_pace_sec_km"]) for lap in second]
    hrs2 = [float(lap["avg_hr"]) for lap in second]

    return calc_decoupling(speeds1, hrs1, speeds2, hrs2)


def calc_decoupling_from_halves(
    pace_first: float, hr_first: float,
    pace_second: float, hr_second: float,
) -> float | None:
    """전/후반 평균값으로 Aerobic Decoupling 근사.

    랩 데이터 없을 때 fallback.
    """
    if pace_first <= 0 or hr_first <= 0 or pace_second <= 0 or hr_second <= 0:
        return None
    ef1 = pace_to_speed(pace_first) / hr_first
    ef2 = pace_to_speed(pace_second) / hr_second
    if ef1 <= 0:
        return None
    return (ef1 - ef2) / ef1 * 100.0


def decoupling_grade(decoupling_pct: float) -> str:
    """Decoupling 등급."""
    if decoupling_pct < 5.0:
        return "good"
    if decoupling_pct < 10.0:
        return "moderate"
    return "poor"


def calc_ef(avg_speed_m_per_min: float, avg_hr: float) -> float | None:
    """EF (Efficiency Factor) 계산.

    Args:
        avg_speed_m_per_min: 평균 속도 (m/min).
        avg_hr: 평균 심박수.

    Returns:
        EF 값 (m/min/bpm) 또는 None.
    """
    if avg_hr <= 0 or avg_speed_m_per_min <= 0:
        return None
    return avg_speed_m_per_min / avg_hr


def calc_and_save_decoupling(conn: sqlite3.Connection, activity_id: int) -> float | None:
    """활동별 Aerobic Decoupling + EF 계산 후 저장.

    랩 데이터 우선, 없으면 전체 활동 단일 EF만 계산.

    Args:
        conn: SQLite 커넥션.
        activity_id: activity_summaries.id.

    Returns:
        Decoupling % 또는 None.
    """
    row = conn.execute(
        """SELECT start_time, avg_pace_sec_km, avg_hr, duration_sec
           FROM activity_summaries WHERE id=?""",
        (activity_id,),
    ).fetchone()
    if row is None:
        return None

    start_time, avg_pace, avg_hr, duration_sec = row
    if not avg_pace or not avg_hr:
        return None

    activity_date = start_time[:10]

    # 랩 데이터 조회
    laps = conn.execute(
        """SELECT avg_pace_sec_km, avg_hr FROM activity_laps
           WHERE activity_id=? ORDER BY lap_index ASC""",
        (activity_id,),
    ).fetchall()

    decoupling = None
    if len(laps) >= 2:
        lap_dicts = [{"avg_pace_sec_km": r[0], "avg_hr": r[1]} for r in laps]
        decoupling = calc_decoupling_from_laps(lap_dicts)

    # EF (전체 활동 기준)
    speed = pace_to_speed(float(avg_pace))
    ef = calc_ef(speed, float(avg_hr))

    if ef is not None:
        save_metric(
            conn, date=activity_date, metric_name="EF",
            value=ef, activity_id=activity_id,
        )

    if decoupling is not None:
        save_metric(
            conn,
            date=activity_date,
            metric_name="AerobicDecoupling",
            value=decoupling,
            activity_id=activity_id,
            extra_json={"grade": decoupling_grade(decoupling), "ef": ef},
        )

    return decoupling
