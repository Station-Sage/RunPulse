"""FEARP (Field-Equivalent Adjusted Running Pace) — 환경 보정 페이스.

실제 페이스를 표준 조건(15°C, 습도 50%, 평지, 해발 0m)으로 환산.

공식:
    temp_factor     = 1 + max(0, temp_c - 15) * 0.004
    humidity_factor = 1 + max(0, humidity_pct - 50) * 0.001
    altitude_factor = 1 - altitude_m * 0.00011
    grade_factor    = GAP effort_factor

    fearp = actual_pace_sec_km / (temp_factor * humidity_factor / altitude_factor / grade_factor)

Fallback: GPS 고도 없으면 grade_factor=1.0; 날씨 실패 시 temp=15, humidity=50
"""
from __future__ import annotations

import sqlite3
from datetime import datetime

from src.metrics.gap import calc_gap_effort_factor
from src.metrics.store import save_metric
from src.weather.provider import get_weather_for_activity


def calc_fearp(
    actual_pace_sec_km: float,
    grade_pct: float = 0.0,
    temp_c: float = 15.0,
    humidity_pct: float = 50.0,
    altitude_m: float = 0.0,
) -> float:
    """FEARP 계산 (순수 함수).

    Args:
        actual_pace_sec_km: 실제 평균 페이스 (초/km).
        grade_pct: 평균 경사도 (%).
        temp_c: 기온 (°C). 기본 15°C (표준 조건).
        humidity_pct: 습도 (%). 기본 50%.
        altitude_m: 해발 고도 (m). 기본 0.

    Returns:
        표준 조건 등가 페이스 (초/km). 낮을수록 실제로 빠름.
    """
    temp_factor = 1.0 + max(0.0, temp_c - 15.0) * 0.004
    humidity_factor = 1.0 + max(0.0, humidity_pct - 50.0) * 0.001
    altitude_factor = max(0.01, 1.0 - altitude_m * 0.00011)
    grade_factor = calc_gap_effort_factor(grade_pct)

    # 분모가 클수록 환경 조건이 어려움 → fearp가 낮아짐 (더 빠른 평지 등가)
    # grade_factor는 오르막(>1)일수록 분모를 키워 fearp를 낮춤 (=GAP 방향과 동일)
    denominator = temp_factor * humidity_factor * grade_factor / altitude_factor
    if denominator <= 0:
        return actual_pace_sec_km
    return actual_pace_sec_km / denominator


def fearp_breakdown(
    actual_pace_sec_km: float,
    grade_pct: float = 0.0,
    temp_c: float = 15.0,
    humidity_pct: float = 50.0,
    altitude_m: float = 0.0,
) -> dict:
    """FEARP 각 환경 요인 분해.

    Returns:
        {fearp, temp_factor, humidity_factor, altitude_factor, grade_factor, actual_pace}
    """
    temp_factor = 1.0 + max(0.0, temp_c - 15.0) * 0.004
    humidity_factor = 1.0 + max(0.0, humidity_pct - 50.0) * 0.001
    altitude_factor = max(0.01, 1.0 - altitude_m * 0.00011)
    grade_factor = calc_gap_effort_factor(grade_pct)

    denominator = temp_factor * humidity_factor * grade_factor / altitude_factor
    fearp = actual_pace_sec_km / denominator if denominator > 0 else actual_pace_sec_km

    return {
        "fearp": round(fearp, 1),
        "actual_pace": actual_pace_sec_km,
        "temp_factor": round(temp_factor, 4),
        "humidity_factor": round(humidity_factor, 4),
        "altitude_factor": round(altitude_factor, 4),
        "grade_factor": round(grade_factor, 4),
    }


def calc_and_save_fearp(conn: sqlite3.Connection, activity_id: int) -> float | None:
    """활동 ID로 FEARP 계산 후 computed_metrics에 저장.

    Args:
        conn: SQLite 커넥션.
        activity_id: activity_summaries.id.

    Returns:
        FEARP 값(초/km) 또는 None.
    """
    row = conn.execute(
        """SELECT start_time, avg_pace_sec_km, elevation_gain, distance_km,
                  start_lat, start_lon
           FROM activity_summaries WHERE id=?""",
        (activity_id,),
    ).fetchone()
    if row is None:
        return None

    start_time, pace, elev_gain, dist_km, lat, lon = row
    if not pace or pace <= 0:
        return None

    # 평균 경사도: elevation_gain / (distance_km * 10) * 100 (%)
    avg_grade = 0.0
    if elev_gain and dist_km and dist_km > 0:
        avg_grade = (elev_gain / (dist_km * 1000)) * 100  # m/m → %

    # 날씨 조회 우선순위:
    # 1) activity_detail_metrics.weather_* (Garmin/Strava에서 동기화된 값 — 가장 정확)
    # 2) Open-Meteo API (GPS 좌표 기반, RunPulse 독립 외부 소스)
    # RunPulse 2차 메트릭은 서비스 데이터 포함 모든 소스를 입력으로 사용 가능 (D-V2-16)
    temp_c: float = 15.0
    humidity_pct: float = 50.0

    cached = conn.execute(
        """SELECT metric_name, metric_value FROM activity_detail_metrics
           WHERE activity_id=? AND metric_name IN ('weather_temp_c','weather_humidity_pct')""",
        (activity_id,),
    ).fetchall()
    cached_map = {r[0]: r[1] for r in cached if r[1] is not None}

    if "weather_temp_c" in cached_map:
        temp_c = float(cached_map["weather_temp_c"])
        humidity_pct = float(cached_map.get("weather_humidity_pct", 50.0))
    elif lat is not None and lon is not None:
        weather = get_weather_for_activity(conn, start_time, lat, lon)
        if weather:
            temp_c = float(weather.get("temp_c") or 15.0)
            humidity_pct = float(weather.get("humidity_pct") or 50.0)

    # 고도: Open-Meteo가 해당 위치 기준으로 온도 반환하므로 추가 고도 보정 생략
    # 향후 고도 데이터 보강 시 여기서 적용

    breakdown = fearp_breakdown(
        actual_pace_sec_km=float(pace),
        grade_pct=avg_grade,
        temp_c=temp_c,
        humidity_pct=humidity_pct,
    )

    activity_date = start_time[:10]
    save_metric(
        conn,
        date=activity_date,
        metric_name="FEARP",
        value=breakdown["fearp"],
        activity_id=activity_id,
        extra_json=breakdown,
    )
    return breakdown["fearp"]
