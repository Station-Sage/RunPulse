"""ADTI (Aerobic Decoupling Trend Index) — 유산소 분리 추세 지수.

8주 Aerobic Decoupling 값의 선형 회귀 기울기.

기준:
  < -0.5%/주  : 우수한 개선 (유산소 능력 향상 중)
  -0.5 ~ 0    : 완만한 개선
  > 0         : 악화 (피로 누적 또는 유산소 능력 저하)

데이터 요건: 최소 3개 이상의 Decoupling 데이터 포인트 필요.
Sprint 2에서 Decoupling 계산(V2-1-9) 구현 후 연동.
"""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from src.metrics.store import load_metric_series, save_metric


def calc_adti(weekly_decoupling: list[float]) -> float | None:
    """ADTI 계산 (순수 함수) — 선형 회귀 기울기.

    Args:
        weekly_decoupling: 주 단위 Aerobic Decoupling 값 리스트 (%).
                           오래된 것부터 최신 순서.

    Returns:
        기울기 (%/주) 또는 None (데이터 부족).
    """
    if len(weekly_decoupling) < 3:
        return None

    n = len(weekly_decoupling)
    x_vals = list(range(n))
    x_mean = sum(x_vals) / n
    y_mean = sum(weekly_decoupling) / n

    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_vals, weekly_decoupling))
    denominator = sum((x - x_mean) ** 2 for x in x_vals)

    if denominator == 0:
        return 0.0
    return numerator / denominator


def adti_status(adti: float) -> str:
    """ADTI 상태 분류.

    Returns:
        'improving' | 'stable' | 'declining'
    """
    if adti < -0.5:
        return "improving"
    if adti <= 0.0:
        return "stable"
    return "declining"


def calc_and_save_adti(conn: sqlite3.Connection, target_date: str) -> float | None:
    """ADTI 계산 후 computed_metrics에 저장.

    최근 8주의 Aerobic Decoupling 일별 값을 주 단위로 집계 후 기울기 계산.

    Args:
        conn: SQLite 커넥션.
        target_date: YYYY-MM-DD.

    Returns:
        ADTI 값 또는 None (데이터 부족).
    """
    td = date.fromisoformat(target_date)
    start_date = (td - timedelta(weeks=8)).isoformat()

    # Aerobic Decoupling 시계열 (activity별 또는 일별)
    series = load_metric_series(
        conn,
        metric_name="AerobicDecoupling",
        start_date=start_date,
        end_date=target_date,
    )

    if len(series) < 3:
        return None  # 데이터 부족

    # 일별 → 주 단위 평균 집계 (8개 버킷)
    weekly: dict[int, list[float]] = {}
    for dt_str, val in series:
        dt = date.fromisoformat(dt_str)
        week_idx = (td - dt).days // 7
        weekly.setdefault(week_idx, []).append(val)

    # 주 단위 평균 (오래된 것 → 최신 순)
    sorted_weeks = sorted(weekly.keys(), reverse=True)  # 오래된 week_idx가 큰 값
    weekly_avg = [sum(weekly[w]) / len(weekly[w]) for w in sorted_weeks]

    adti = calc_adti(weekly_avg)
    if adti is not None:
        save_metric(
            conn,
            date=target_date,
            metric_name="ADTI",
            value=adti,
            extra_json={
                "status": adti_status(adti),
                "data_points": len(series),
                "weeks_covered": len(sorted_weeks),
            },
        )
    return adti
