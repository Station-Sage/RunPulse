"""Relative Effort (Strava 방식) — 심박존 기반 노력도 점수.

공식:
    zone_coefficients = [0.5, 1.0, 2.0, 3.5, 5.5]  # Zone 1~5
    RE = sum(time_in_zone_sec[i] / 60 * coeff[i] for i in range(5))
"""
from __future__ import annotations

import sqlite3

from src.metrics.store import save_metric

# Strava 공식 Zone 1~5 계수
_ZONE_COEFFICIENTS = [0.5, 1.0, 2.0, 3.5, 5.5]


def calc_relative_effort(time_in_zones_sec: list[float]) -> float:
    """Relative Effort 계산 (순수 함수).

    Args:
        time_in_zones_sec: [zone1_sec, zone2_sec, zone3_sec, zone4_sec, zone5_sec].

    Returns:
        Relative Effort 점수.
    """
    zs = (list(time_in_zones_sec) + [0.0] * 5)[:5]
    return sum(sec / 60.0 * coeff for sec, coeff in zip(zs, _ZONE_COEFFICIENTS))


def calc_and_save_relative_effort(
    conn: sqlite3.Connection, activity_id: int
) -> float | None:
    """활동 ID로 Relative Effort 계산 후 computed_metrics에 저장.

    HR존 시간 데이터(hr_zone_time_1..5)가 없으면 avg_hr/duration으로 근사.

    Args:
        conn: SQLite 커넥션.
        activity_id: activity_summaries.id.

    Returns:
        RE 값 또는 None.
    """
    # HR존 시간 데이터 조회
    zone_secs = []
    for zone_idx in range(1, 6):
        row = conn.execute(
            """SELECT metric_value FROM activity_detail_metrics
               WHERE activity_id=? AND metric_name=?""",
            (activity_id, f"hr_zone_time_{zone_idx}"),
        ).fetchone()
        zone_secs.append(float(row[0]) if row and row[0] is not None else 0.0)

    # HR존 데이터 없으면 avg_hr 기반 근사
    if sum(zone_secs) <= 0:
        zone_secs = _estimate_zones_from_avg_hr(conn, activity_id)

    if sum(zone_secs) <= 0:
        return None

    re = calc_relative_effort(zone_secs)

    # 활동 날짜 조회
    row = conn.execute(
        "SELECT start_time FROM activity_summaries WHERE id=?", (activity_id,)
    ).fetchone()
    if row is None:
        return None

    activity_date = row[0][:10]
    save_metric(
        conn,
        date=activity_date,
        metric_name="RelativeEffort",
        value=re,
        activity_id=activity_id,
        extra_json={"zone_sec": zone_secs},
    )
    return re


def _estimate_zones_from_avg_hr(
    conn: sqlite3.Connection, activity_id: int
) -> list[float]:
    """avg_hr과 duration으로 단일 존 배정 (근사).

    HR 데이터가 없거나 존 분포 데이터가 없을 때 fallback.
    """
    row = conn.execute(
        """SELECT a.avg_hr, a.max_hr, a.duration_sec
           FROM activity_summaries a WHERE a.id=?""",
        (activity_id,),
    ).fetchone()
    if row is None or not row[0] or not row[1] or not row[2]:
        return [0.0] * 5

    avg_hr, max_hr, duration_sec = row
    ratio = avg_hr / max_hr
    zone_secs = [0.0] * 5

    # 평균 HR 비율로 단일 존 배정 (근사)
    if ratio < 0.60:
        zone_secs[0] = float(duration_sec)
    elif ratio < 0.70:
        zone_secs[1] = float(duration_sec)
    elif ratio < 0.80:
        zone_secs[2] = float(duration_sec)
    elif ratio < 0.90:
        zone_secs[3] = float(duration_sec)
    else:
        zone_secs[4] = float(duration_sec)

    return zone_secs
