"""TRIMP (TRIMPexp, Banister 1991) 및 HRSS 계산.

TRIMPexp:
    hr_ratio = (hr_avg - hr_rest) / (hr_max - hr_rest)
    y = 1.92  (남성) / 1.67 (여성)
    TRIMP = duration_min * hr_ratio * 0.64 * exp(y * hr_ratio)

HRSS (HR Stress Score, 기준: LTHR에서 1시간 = 100점):
    lthr_ratio = (hr_lthr - hr_rest) / (hr_max - hr_rest)
    trimp_ref  = 60 * lthr_ratio * 0.64 * exp(y * lthr_ratio)
    HRSS = (TRIMP / trimp_ref) * 100

일별 TRIMP 합산은 computed_metrics (date, NULL, 'TRIMP')에 저장.
활동별 TRIMP는 computed_metrics (date, activity_id, 'TRIMP')에 저장.
"""
from __future__ import annotations

import math
import sqlite3
from datetime import date, timedelta

from src.metrics.store import estimate_max_hr, save_metric

# 기본 생리 파라미터 (사용자 설정 없을 때 fallback)
_DEFAULT_HR_REST = 50
_DEFAULT_HR_MAX = 185
_DEFAULT_LTHR_RATIO = 0.87  # LTHR ≈ max_hr * 0.87


def calc_trimp(
    duration_min: float,
    hr_avg: float,
    hr_rest: float,
    hr_max: float,
    gender: str = "male",
) -> float | None:
    """TRIMPexp 계산 (순수 함수).

    Args:
        duration_min: 운동 시간 (분).
        hr_avg: 평균 심박수.
        hr_rest: 안정 심박수.
        hr_max: 최대 심박수.
        gender: 'male' | 'female'.

    Returns:
        TRIMP 값 또는 None (데이터 부족).
    """
    if duration_min <= 0 or hr_avg <= 0 or hr_max <= hr_rest:
        return None

    hr_ratio = (hr_avg - hr_rest) / (hr_max - hr_rest)
    if hr_ratio <= 0:
        return None

    y = 1.92 if gender == "male" else 1.67
    return duration_min * hr_ratio * 0.64 * math.exp(y * hr_ratio)


def calc_hrss(trimp: float, hr_lthr: float, hr_rest: float, hr_max: float, gender: str = "male") -> float | None:
    """HRSS 계산 (LTHR 기준 1시간 = 100점으로 정규화).

    Args:
        trimp: TRIMPexp 값.
        hr_lthr: 젖산 역치 심박수.
        hr_rest: 안정 심박수.
        hr_max: 최대 심박수.
        gender: 'male' | 'female'.

    Returns:
        HRSS 값 또는 None.
    """
    if hr_max <= hr_rest or hr_lthr <= hr_rest:
        return None

    lthr_ratio = (hr_lthr - hr_rest) / (hr_max - hr_rest)
    if lthr_ratio <= 0:
        return None

    y = 1.92 if gender == "male" else 1.67
    trimp_ref = 60.0 * lthr_ratio * 0.64 * math.exp(y * lthr_ratio)
    if trimp_ref <= 0:
        return None

    return (trimp / trimp_ref) * 100.0


def _get_user_hr_params(conn: sqlite3.Connection) -> tuple[int, int, int]:
    """DB에서 사용자 HR 파라미터 조회. (hr_rest, hr_max, hr_lthr)"""
    # daily_wellness에서 최근 7일 평균 안정 심박
    row = conn.execute(
        """SELECT AVG(resting_hr) FROM daily_wellness
           WHERE resting_hr IS NOT NULL
           ORDER BY date DESC LIMIT 7""",
    ).fetchone()
    hr_rest = int(row[0]) if row and row[0] else _DEFAULT_HR_REST

    # estimate_max_hr: 이상치 제거된 최대심박 추정 (기본값 190)
    hr_max = int(estimate_max_hr(conn))

    hr_lthr = int(hr_max * _DEFAULT_LTHR_RATIO)
    return hr_rest, hr_max, hr_lthr


def calc_and_save_trimp_for_activity(
    conn: sqlite3.Connection,
    activity_id: int,
) -> float | None:
    """활동별 TRIMP 계산 후 저장.

    Args:
        conn: SQLite 커넥션.
        activity_id: activity_summaries.id.

    Returns:
        TRIMP 값 또는 None.
    """
    row = conn.execute(
        """SELECT start_time, avg_hr, max_hr, duration_sec
           FROM activity_summaries WHERE id=?""",
        (activity_id,),
    ).fetchone()
    if row is None:
        return None

    start_time, avg_hr, max_hr, duration_sec = row
    if not avg_hr or not duration_sec:
        return None

    hr_rest, hr_max_db, _ = _get_user_hr_params(conn)
    effective_max = max(max_hr or hr_max_db, hr_max_db)

    duration_min = duration_sec / 60.0
    trimp = calc_trimp(duration_min, avg_hr, hr_rest, effective_max)
    if trimp is None:
        return None

    activity_date = start_time[:10]
    save_metric(conn, date=activity_date, metric_name="TRIMP", value=trimp, activity_id=activity_id)
    return trimp


def calc_and_save_daily_trimp(conn: sqlite3.Connection, target_date: str) -> float:
    """날짜별 TRIMP 합산 저장.

    해당 날짜 모든 활동의 TRIMP를 합산해 일별 부하로 저장.

    Args:
        conn: SQLite 커넥션.
        target_date: YYYY-MM-DD.

    Returns:
        합산 TRIMP (0이면 활동 없음).
    """
    activities = conn.execute(
        """SELECT id FROM v_canonical_activities
           WHERE DATE(start_time) = ? AND activity_type='running'""",
        (target_date,),
    ).fetchall()

    total_trimp = 0.0
    for (act_id,) in activities:
        t = calc_and_save_trimp_for_activity(conn, act_id)
        if t:
            total_trimp += t

    # 일별 합산 저장 (activity_id=None)
    save_metric(conn, date=target_date, metric_name="TRIMP", value=total_trimp)
    return total_trimp


def get_daily_trimp(conn: sqlite3.Connection, target_date: str) -> float:
    """특정 날짜 TRIMP 조회 (없으면 계산 후 반환)."""
    row = conn.execute(
        """SELECT metric_value FROM computed_metrics
           WHERE date=? AND metric_name='TRIMP' AND activity_id IS NULL""",
        (target_date,),
    ).fetchone()
    if row and row[0] is not None:
        return float(row[0])
    return calc_and_save_daily_trimp(conn, target_date)


def get_trimp_series(conn: sqlite3.Connection, start_date: str, end_date: str) -> list[float]:
    """날짜 범위의 일별 TRIMP 리스트 (start~end 순서, 없는 날은 0).

    Returns:
        [trimp_day0, trimp_day1, ...] start_date부터 end_date까지.
    """
    rows = conn.execute(
        """SELECT date, metric_value FROM computed_metrics
           WHERE metric_name='TRIMP' AND activity_id IS NULL
             AND date BETWEEN ? AND ?
           ORDER BY date ASC""",
        (start_date, end_date),
    ).fetchall()
    trimp_map = {r[0]: r[1] or 0.0 for r in rows}

    result = []
    td = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    while td <= end:
        result.append(float(trimp_map.get(td.isoformat(), 0.0)))
        td += timedelta(days=1)
    return result
