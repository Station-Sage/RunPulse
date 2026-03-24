"""VDOT 추정 모듈 — best_efforts / 레이스 기록 기반 Jack Daniels VDOT 역산.

소스:
  1. activity_detail_metrics.best_efforts (Strava)
  2. activity_summaries (고강도 레이스급 활동)
  3. daily_fitness.garmin_vo2max (외부 VO2max → VDOT 근사)

Jack Daniels 공식:
  VO2 = -4.60 + 0.182258 * v + 0.000104 * v^2  (v = m/min)
  %VO2max = 0.8 + 0.1894393 * e^(-0.012778*t) + 0.2989558 * e^(-0.1932605*t)
  VDOT = VO2 / %VO2max
"""
from __future__ import annotations

import json
import math
import sqlite3
from datetime import date, timedelta

from src.metrics.store import save_metric


def _vo2_from_velocity(v: float) -> float:
    """속도(m/min) → VO2 (ml/kg/min)."""
    return -4.60 + 0.182258 * v + 0.000104 * v ** 2


def _pct_vo2max(t_min: float) -> float:
    """%VO2max (레이스 지속시간 t분 기준)."""
    return 0.8 + 0.1894393 * math.exp(-0.012778 * t_min) + 0.2989558 * math.exp(-0.1932605 * t_min)


def estimate_vdot(distance_m: float, time_sec: float) -> float | None:
    """거리(m)와 시간(초)에서 VDOT 추정.

    Args:
        distance_m: 거리 (미터).
        time_sec: 소요 시간 (초).

    Returns:
        VDOT 값 또는 None.
    """
    if distance_m <= 0 or time_sec <= 0:
        return None
    t_min = time_sec / 60.0
    v = distance_m / t_min  # m/min
    vo2 = _vo2_from_velocity(v)
    pct = _pct_vo2max(t_min)
    if pct <= 0:
        return None
    return vo2 / pct


# best_efforts 거리 매핑 (키 → 미터)
_DIST_MAP = {
    "400m": 400, "1k": 1000, "1 mile": 1609,
    "5k": 5000, "10k": 10000, "15k": 15000,
    "10 mile": 16090, "20k": 20000,
    "Half-Marathon": 21097, "Marathon": 42195,
}

# VDOT 추정에 신뢰도 높은 거리 (1500m ~ 마라톤)
_RELIABLE_DISTANCES = {"1k", "1 mile", "5k", "10k", "15k", "10 mile", "20k", "Half-Marathon", "Marathon"}

# 거리별 가중치 (장거리일수록 VDOT 추정 신뢰도 높음)
_WEIGHT = {
    "1k": 0.5, "1 mile": 0.7, "5k": 1.0, "10k": 1.2,
    "15k": 1.3, "10 mile": 1.3, "20k": 1.4,
    "Half-Marathon": 1.5, "Marathon": 1.5,
}


def estimate_vdot_from_best_efforts(best_efforts: dict) -> dict | None:
    """best_efforts dict에서 가중 평균 VDOT 추정.

    Args:
        best_efforts: {"5k": 1386, "10k": 2865, ...} (초 단위).

    Returns:
        {"vdot": float, "source_efforts": dict, "best_distance": str} 또는 None.
    """
    estimates = []
    for key, time_sec in best_efforts.items():
        if key not in _RELIABLE_DISTANCES:
            continue
        dist_m = _DIST_MAP.get(key)
        if not dist_m:
            continue
        vdot = estimate_vdot(dist_m, time_sec)
        if vdot and 20 < vdot < 85:
            weight = _WEIGHT.get(key, 1.0)
            estimates.append((key, vdot, weight, time_sec))

    if not estimates:
        return None

    total_weight = sum(e[2] for e in estimates)
    weighted_vdot = sum(e[1] * e[2] for e in estimates) / total_weight

    best = max(estimates, key=lambda e: e[1])

    return {
        "vdot": round(weighted_vdot, 1),
        "vdot_best": round(best[1], 1),
        "best_distance": best[0],
        "source_efforts": {e[0]: {"time_sec": e[3], "vdot": round(e[1], 1)} for e in estimates},
        "method": "best_efforts_weighted",
    }


def estimate_vdot_from_activity(distance_km: float, duration_sec: int, avg_hr: int | None = None) -> dict | None:
    """단일 활동에서 VDOT 추정 (고강도 레이스급 활동 대상).

    Args:
        distance_km: 거리 (km).
        duration_sec: 소요 시간 (초).
        avg_hr: 평균 심박수 (선택).

    Returns:
        {"vdot": float, "method": "race_estimate"} 또는 None.
    """
    if distance_km < 1.0 or duration_sec < 180:
        return None
    vdot = estimate_vdot(distance_km * 1000, duration_sec)
    if vdot and 20 < vdot < 85:
        return {
            "vdot": round(vdot, 1),
            "distance_km": distance_km,
            "duration_sec": duration_sec,
            "avg_hr": avg_hr,
            "method": "race_estimate",
        }
    return None


def calc_and_save_vdot(conn: sqlite3.Connection, target_date: str) -> float | None:
    """VDOT 계산 후 computed_metrics에 저장.

    우선순위:
      1. best_efforts (Strava) — 가장 신뢰도 높음
      2. 고강도 활동 (5K~마라톤, HR > 85% maxHR) — 레이스 추정
      3. daily_fitness.garmin_vo2max — 외부 VO2max 근사

    Args:
        conn: SQLite 커넥션.
        target_date: 대상 날짜 (YYYY-MM-DD).

    Returns:
        VDOT 값 또는 None.
    """
    result = None

    # 방법 1: best_efforts에서 추정
    cur = conn.execute(
        "SELECT adm.metric_json FROM activity_detail_metrics adm "
        "JOIN activity_summaries a ON adm.activity_id = a.id "
        "WHERE adm.metric_name='best_efforts' AND adm.metric_json IS NOT NULL "
        "AND a.start_time <= ? "
        "ORDER BY a.start_time DESC LIMIT 10",
        (target_date + "T23:59:59",)
    )
    all_efforts = {}
    for row in cur.fetchall():
        try:
            efforts = json.loads(row[0])
            for k, v in efforts.items():
                if k not in all_efforts or v < all_efforts[k]:
                    all_efforts[k] = v
        except (json.JSONDecodeError, TypeError):
            pass

    if all_efforts:
        est = estimate_vdot_from_best_efforts(all_efforts)
        if est:
            result = est

    # 방법 2: 고강도 활동에서 추정 (best_efforts 없을 때)
    if not result:
        cur2 = conn.execute(
            "SELECT distance_km, duration_sec, avg_hr FROM activity_summaries "
            "WHERE start_time <= ? AND distance_km BETWEEN 3.0 AND 45.0 "
            "AND avg_hr IS NOT NULL AND avg_hr > 150 "
            "ORDER BY start_time DESC LIMIT 20",
            (target_date + "T23:59:59",)
        )
        best_vdot = None
        best_info = None
        for row in cur2.fetchall():
            est = estimate_vdot_from_activity(row[0], row[1], row[2])
            if est and (best_vdot is None or est["vdot"] > best_vdot):
                best_vdot = est["vdot"]
                best_info = est
        if best_info:
            result = best_info

    # 방법 3: Garmin VO2max에서 근사
    if not result:
        cur3 = conn.execute(
            "SELECT garmin_vo2max FROM daily_fitness "
            "WHERE date <= ? AND garmin_vo2max IS NOT NULL "
            "ORDER BY date DESC LIMIT 1",
            (target_date,)
        )
        row = cur3.fetchone()
        if row and row[0]:
            result = {
                "vdot": round(row[0] * 0.95, 1),
                "garmin_vo2max": row[0],
                "method": "garmin_vo2max_approx",
            }

    if not result:
        return None

    vdot_val = result["vdot"]
    save_metric(conn, target_date, "VDOT", vdot_val, extra_json=result)
    return vdot_val
