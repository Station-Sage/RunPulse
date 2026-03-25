"""DARP (Dynamic Adjusted Race Predictor) — 내구성 보정 레이스 예측.

공식:
    target_pace = vdot_to_pace(vdot, distance_km)   # Jack Daniels 역산
    di_penalty  = max(0, 1.0 - DI) * 0.05           # DI < 1 → 후반 페이스 저하
    darp_pace   = target_pace * (1 + di_penalty)     # 하프마라톤 이상에만 DI 보정
    darp_time   = darp_pace * distance_km

저장: computed_metrics (date, None, 'DARP_{distance}')
     e.g., 'DARP_5k', 'DARP_10k', 'DARP_half', 'DARP_full'
"""
from __future__ import annotations

import math
import sqlite3
from datetime import date

from src.metrics.di import get_di
from src.metrics.store import save_metric

# Jack Daniels 거리별 퍼센트 VO2max 대응 (대략 레이스 페이스)
# VDOT에서 특정 거리 페이스 역산:
# velocity(m/min) = VDOT과 pct_VO2max로부터 역산
# 대신 실용적 근사: 거리별 계수를 통해 마라톤 페이스 대비 비율 사용

# Jack Daniels VDOT → 거리별 레이스 페이스 (sec/km) 근사 계수
# 계수 = 마라톤 페이스 대비 (1.0 = 마라톤 페이스)
_DISTANCE_PACE_FACTOR = {
    "5k":   0.828,  # 5K는 마라톤보다 ~17% 빠름
    "10k":  0.893,  # 10K는 마라톤보다 ~11% 빠름
    "half": 0.946,  # 하프는 마라톤보다 ~5% 빠름
    "full": 1.000,  # 마라톤 기준
}

# DI 보정을 적용할 최소 거리 (하프마라톤 이상)
_DI_APPLY_DISTANCES = {"half", "full"}


def vdot_to_marathon_pace_sec_km(vdot: float) -> float:
    """VDOT → 마라톤 페이스 (초/km) 역산 (Jack Daniels 근사).

    공식: velocity(m/min) = (VDOT × 0.9) / 0.2 (대략적 VO2max ~90% 사용)
    실제로는 이진 탐색으로 정확히 계산하나, 근사식으로 충분.
    """
    if vdot <= 0:
        return 0.0
    # VO2max에서 마라톤 강도 ~79% 사용 (Daniels 기준)
    # velocity ≈ sqrt(VDOT * 3.5) * 3  (경험적 근사)
    # 더 정확한 공식: 반복법으로 Daniels-Gilbert 풀기
    vo2_marathon = vdot * 0.79  # 마라톤 강도 79% VO2max
    # velocity = (vo2 + 4.6) / (0.182258 + 0.000104 * velocity) → 이진 탐색
    velocity = _solve_velocity(vo2_marathon)
    if velocity <= 0:
        return 0.0
    return 1000.0 / velocity * 60.0  # m/min → sec/km


def _solve_velocity(target_vo2: float, iterations: int = 30) -> float:
    """VO2 목표값에서 속도(m/min) 역산 (이진 탐색)."""
    lo, hi = 50.0, 500.0
    for _ in range(iterations):
        mid = (lo + hi) / 2.0
        vo2 = -4.60 + 0.182258 * mid + 0.000104 * mid**2
        if vo2 < target_vo2:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def calc_darp(vdot: float, distance_key: str, di: float | None = None) -> dict | None:
    """DARP 계산 (순수 함수).

    Args:
        vdot: VDOT 값.
        distance_key: '5k' | '10k' | 'half' | 'full'.
        di: DI 값 (없으면 DI 보정 생략).

    Returns:
        {'pace_sec_km': ..., 'time_sec': ..., 'distance_km': ..., 'di_penalty': ...}
        또는 None.
    """
    if vdot <= 0 or distance_key not in _DISTANCE_PACE_FACTOR:
        return None

    marathon_pace = vdot_to_marathon_pace_sec_km(vdot)
    if marathon_pace <= 0:
        return None

    factor = _DISTANCE_PACE_FACTOR[distance_key]
    target_pace = marathon_pace * factor

    # DI 보정 (하프마라톤 이상에만)
    di_penalty = 0.0
    if di is not None and distance_key in _DI_APPLY_DISTANCES:
        di_penalty = max(0.0, 1.0 - di) * 0.05

    darp_pace = target_pace * (1.0 + di_penalty)

    distances = {"5k": 5.0, "10k": 10.0, "half": 21.0975, "full": 42.195}
    dist_km = distances[distance_key]
    darp_time_sec = darp_pace * dist_km

    return {
        "pace_sec_km": round(darp_pace, 1),
        "time_sec": round(darp_time_sec),
        "distance_km": dist_km,
        "di_penalty": round(di_penalty, 4),
        "vdot": vdot,
    }


def calc_and_save_darp(conn: sqlite3.Connection, target_date: str) -> dict:
    """4개 거리 DARP 계산 후 저장.

    Args:
        conn: SQLite 커넥션.
        target_date: YYYY-MM-DD.

    Returns:
        {distance_key: result_dict, ...} — 계산된 것만 포함.
    """
    # VDOT 조회
    row = conn.execute(
        """SELECT runalyze_vdot FROM daily_fitness
           WHERE runalyze_vdot IS NOT NULL AND date <= ?
           ORDER BY date DESC LIMIT 1""",
        (target_date,),
    ).fetchone()
    if row is None or not row[0]:
        row = conn.execute(
            """SELECT metric_value FROM computed_metrics
               WHERE metric_name='VDOT' AND metric_value IS NOT NULL AND date <= ?
               ORDER BY date DESC LIMIT 1""",
            (target_date,),
        ).fetchone()
        if row is None or not row[0]:
            return {}
    vdot = float(row[0])

    di = get_di(conn, target_date)

    results = {}
    for dist_key in ("5k", "10k", "half", "full"):
        result = calc_darp(vdot, dist_key, di)
        if result:
            save_metric(
                conn,
                date=target_date,
                metric_name=f"DARP_{dist_key}",
                value=result["pace_sec_km"],
                extra_json=result,
            )
            results[dist_key] = result

    return results
