"""GAP (Grade Adjusted Pace) 및 NGP (Normalized Grade Pace) 계산.

GAP — Strava 공식: 경사 보정 페이스 (평지 등가 페이스)
NGP — TrainingPeaks 방식: power-weighted 4th-root 정규화 페이스
"""
from __future__ import annotations

import math


def calc_gap(actual_pace_sec_km: float, grade_pct: float) -> float:
    """단일 구간 GAP 계산 (Strava 공식).

    Args:
        actual_pace_sec_km: 실제 페이스 (초/km).
        grade_pct: 경사도 (%). 양수=오르막, 음수=내리막.

    Returns:
        경사 보정 페이스 (초/km).
    """
    g = max(grade_pct, -10.0)  # 내리막 최대 -10% 적용
    effort_factor = 1.0 + 0.0333 * g + 0.0001 * g**2
    return actual_pace_sec_km / effort_factor


def calc_gap_effort_factor(grade_pct: float) -> float:
    """GAP effort_factor만 반환 (FEARP 등에서 재사용).

    Args:
        grade_pct: 경사도 (%).

    Returns:
        effort_factor (1.0 기준, 오르막 > 1.0, 완만한 내리막 < 1.0).
    """
    g = max(grade_pct, -10.0)
    return 1.0 + 0.0333 * g + 0.0001 * g**2


def calc_ngp_from_laps(
    lap_speeds_m_per_min: list[float],
    lap_grades_pct: list[float],
    lap_durations_sec: list[float],
) -> float | None:
    """NGP (Normalized Grade Pace) 계산 — 4차 멱승 가중 평균.

    각 구간의 GAP 속도를 4제곱 가중 평균 후 0.25제곱으로 환산.
    rTSS 계산에 사용.

    Args:
        lap_speeds_m_per_min: 구간별 속도 (m/min).
        lap_grades_pct: 구간별 경사도 (%).
        lap_durations_sec: 구간별 소요 시간 (초).

    Returns:
        NGP 속도 (m/min) 또는 None (데이터 부족).
    """
    if not lap_speeds_m_per_min or not lap_durations_sec:
        return None
    if len(lap_speeds_m_per_min) != len(lap_durations_sec):
        return None

    grades = lap_grades_pct or [0.0] * len(lap_speeds_m_per_min)

    weighted_sum = 0.0
    total_duration = 0.0
    for speed, grade, dur in zip(lap_speeds_m_per_min, grades, lap_durations_sec):
        if dur <= 0 or speed <= 0:
            continue
        ef = calc_gap_effort_factor(grade)
        gap_speed = speed * ef  # GAP 속도 (m/min)
        weighted_sum += (gap_speed**4) * dur
        total_duration += dur

    if total_duration <= 0:
        return None

    return (weighted_sum / total_duration) ** 0.25


def ngp_from_overall(pace_sec_km: float, avg_grade_pct: float = 0.0) -> float:
    """전체 평균 페이스 + 평균 경사도로 근사 NGP 계산.

    랩 데이터 없을 때 fallback으로 사용.

    Args:
        pace_sec_km: 평균 페이스 (초/km).
        avg_grade_pct: 평균 경사도 (%).

    Returns:
        NGP 페이스 (초/km).
    """
    return calc_gap(pace_sec_km, avg_grade_pct)


def pace_to_speed(pace_sec_km: float) -> float:
    """페이스(초/km) → 속도(m/min) 변환."""
    if pace_sec_km <= 0:
        return 0.0
    return 1000.0 / (pace_sec_km / 60.0)


def speed_to_pace(speed_m_per_min: float) -> float:
    """속도(m/min) → 페이스(초/km) 변환."""
    if speed_m_per_min <= 0:
        return 0.0
    return 1000.0 / speed_m_per_min * 60.0
