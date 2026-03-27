"""DARP (Dynamic Adjusted Race Predictor) — 내구성 + 훈련 준비도 보정 레이스 예측.

공식:
    base_time = Daniels VDOT 테이블 기반 예측 시간
    di_adj    = DI 기반 내구성 보정 (하프/풀만, DI 낮으면 시간 추가)
    shape_adj = Race Shape 기반 훈련 준비도 보정 (준비 부족하면 시간 추가)
    darp_time = base_time × (1 + di_penalty) × (1 + shape_penalty)

저장: computed_metrics (date, None, 'DARP_{distance}')
"""
from __future__ import annotations

import sqlite3
from datetime import date

from src.metrics.di import get_di
from src.metrics.store import save_metric


def calc_darp(vdot: float, distance_key: str,
              di: float | None = None,
              race_shape: float | None = None,
              ef: float | None = None) -> dict | None:
    """DARP 계산 — Daniels 테이블 + DI + Race Shape + EF 보정.

    Args:
        vdot: VDOT 값.
        distance_key: '5k' | '10k' | 'half' | 'full'.
        di: DI 값 (0~100). 없으면 DI 보정 생략.
        race_shape: Race Shape (0~100). 없으면 Shape 보정 생략.
        ef: Efficiency Factor (보통 1.0~1.8). 없으면 EF 보정 생략.

    Returns:
        {..., 'di_penalty', 'shape_penalty', 'ef_bonus', ...}
    """
    from src.metrics.daniels_table import get_race_predictions, get_training_paces

    if vdot <= 0:
        return None

    _DIST_MAP = {"5k": 5.0, "10k": 10.0, "half": 21.0975, "full": 42.195}
    _RACE_KEY = {"5k": "5k", "10k": "10k", "half": "half", "full": "full"}
    dist_km = _DIST_MAP.get(distance_key)
    race_key = _RACE_KEY.get(distance_key)
    if dist_km is None or race_key is None:
        return None

    # 1. Daniels 테이블에서 기본 예측 시간
    predictions = get_race_predictions(vdot)
    base_time = predictions.get(race_key)
    if not base_time or base_time <= 0:
        return None

    # 2. DI 보정 (하프/풀만) — DI 0~100 스케일
    #    DI 70(양호) → 0% 페널티
    #    DI 50 → +2% 페널티
    #    DI 30 → +5% 페널티
    #    DI 0  → +8% 페널티
    di_penalty = 0.0
    if di is not None and distance_key in ("half", "full"):
        di_clamped = max(0.0, min(100.0, di))
        if di_clamped < 70:
            di_penalty = (70 - di_clamped) / 70 * 0.08  # 최대 8%

    # 3. Race Shape 보정 (10K 이상) — Shape 0~100 스케일
    #    Shape 80+(준비 완료) → 0% 페널티
    #    Shape 60 → +3% 페널티
    #    Shape 40 → +7% 페널티
    #    Shape 20 → +12% 페널티
    #    5K는 훈련 준비도 영향이 상대적으로 작음 → 계수 축소
    shape_penalty = 0.0
    if race_shape is not None:
        shape_clamped = max(0.0, min(100.0, race_shape))
        if shape_clamped < 80:
            base_penalty = (80 - shape_clamped) / 80 * 0.15  # 최대 15%
            # 거리별 영향 계수: 5K 30%, 10K 50%, 하프 80%, 풀 100%
            dist_factor = {"5k": 0.3, "10k": 0.5, "half": 0.8, "full": 1.0}
            shape_penalty = base_penalty * dist_factor.get(distance_key, 1.0)

    # 4. EF 보정 — 효율이 높으면 보너스 (시간 단축)
    #    EF 1.0(기준) → 0%, EF 1.3(우수) → -2%, EF 1.5+(탁월) → -3%
    #    EF < 1.0(저효율) → +2% 페널티
    #    10K 이상에서만 유의미
    ef_bonus = 0.0
    if ef is not None and distance_key in ("10k", "half", "full"):
        if ef >= 1.0:
            ef_bonus = -min(0.03, (ef - 1.0) * 0.06)  # 최대 -3%
        else:
            ef_bonus = min(0.03, (1.0 - ef) * 0.06)   # 최대 +3%

    # 5. 최종 예측
    adjusted_time = base_time * (1.0 + di_penalty) * (1.0 + shape_penalty) * (1.0 + ef_bonus)
    adjusted_pace = adjusted_time / dist_km

    # 페이스 정보 (Daniels 기준)
    paces = get_training_paces(vdot)

    return {
        "pace_sec_km": round(adjusted_pace, 1),
        "time_sec": round(adjusted_time),
        "distance_km": dist_km,
        "base_time_sec": base_time,
        "di_penalty": round(di_penalty, 4),
        "shape_penalty": round(shape_penalty, 4),
        "ef_bonus": round(ef_bonus, 4),
        "vdot": vdot,
        "avg_pace_sec": round(adjusted_pace),
        "m_pace": paces.get("M"),
    }


def calc_and_save_darp(conn: sqlite3.Connection, target_date: str) -> dict:
    """4개 거리 DARP 계산 후 저장.

    VDOT 소스: computed_metrics.VDOT 우선.
    DI: computed_metrics.DI.
    Race Shape: computed_metrics.MarathonShape (거리별 재계산).
    """
    # VDOT 조회 (computed_metrics 우선)
    row = conn.execute(
        "SELECT metric_value FROM computed_metrics "
        "WHERE metric_name='VDOT' AND metric_value IS NOT NULL AND date<=? "
        "ORDER BY date DESC LIMIT 1",
        (target_date,),
    ).fetchone()
    if not row or not row[0]:
        # fallback: daily_fitness
        row = conn.execute(
            "SELECT runalyze_vdot, garmin_vo2max FROM daily_fitness "
            "WHERE (runalyze_vdot IS NOT NULL OR garmin_vo2max IS NOT NULL) "
            "AND date<=? ORDER BY date DESC LIMIT 1",
            (target_date,),
        ).fetchone()
        if not row:
            return {}
        vdot = float(row[0]) if row[0] else (float(row[1]) if row[1] else None)
        if not vdot:
            return {}
    else:
        vdot = float(row[0])

    di = get_di(conn, target_date)

    # EF (최근 7일 평균)
    ef_val = None
    ef_row = conn.execute(
        "SELECT AVG(metric_value) FROM computed_metrics "
        "WHERE metric_name='EF' AND activity_id IS NOT NULL "
        "AND metric_value IS NOT NULL AND date>=date(?, '-7 days') AND date<=?",
        (target_date, target_date),
    ).fetchone()
    if ef_row and ef_row[0]:
        ef_val = round(float(ef_row[0]), 3)

    # Race Shape (거리별로 다름 → 각 거리에 맞는 shape 계산)
    from src.metrics.marathon_shape import calc_marathon_shape, _get_race_targets
    from src.metrics.marathon_shape import (
        _get_recent_running_data, _calc_consistency, _calc_long_run_stats,
    )
    _DIST_KM = {"5k": 5.0, "10k": 10.0, "half": 21.0975, "full": 42.195}

    results = {}
    for dist_key, dist_km in _DIST_KM.items():
        # 거리별 Race Shape 계산
        targets = _get_race_targets(vdot, dist_km)
        weeks = targets["consistency_weeks"]
        weekly_avg, longest = _get_recent_running_data(conn, target_date, weeks=min(weeks, 4))
        consistency = _calc_consistency(conn, target_date, weeks=weeks)
        long_count, long_quality = _calc_long_run_stats(
            conn, target_date, weeks=weeks,
            threshold_km=targets["long_threshold"], vdot=vdot)
        shape = calc_marathon_shape(
            weekly_avg, longest, vdot,
            consistency_score=consistency,
            race_distance_km=dist_km,
            long_run_count=long_count,
            long_run_quality=long_quality,
        )

        result = calc_darp(vdot, dist_key, di=di, race_shape=shape, ef=ef_val)
        if result:
            result["race_shape"] = shape
            result["ef"] = ef_val
            save_metric(
                conn,
                date=target_date,
                metric_name=f"DARP_{dist_key}",
                value=result["time_sec"],  # 시간(초)을 저장 (이전: pace)
                extra_json=result,
            )
            results[dist_key] = result

    return results
