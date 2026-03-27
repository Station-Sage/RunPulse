"""Marathon Shape (Runalyze 방식) — 마라톤 훈련 완성도.

공식:
    target_weekly_km = vdot * 0.8
    target_long_km   = vdot * 0.35
    weekly_shape   = min(1.0, weekly_km_avg / target_weekly_km)
    long_run_shape = min(1.0, longest_run_km / target_long_km)
    shape_pct = (weekly_shape * 2/3 + long_run_shape * 1/3) * 100

기준:
    < 40%:  훈련 부족 (레이스 준비 안 됨)
    40-60%: 기초 훈련
    60-80%: 훈련 진행 중
    80-90%: 충분한 준비
    > 90%:  최적 준비
"""
from __future__ import annotations

import math
import sqlite3
from datetime import date, timedelta

from src.metrics.store import save_metric


def calc_marathon_shape(
    weekly_km_avg: float,
    longest_run_km: float,
    vdot: float,
) -> float | None:
    """Marathon Shape 계산 (순수 함수).

    Args:
        weekly_km_avg: 최근 4주 평균 주간 거리 (km).
        longest_run_km: 최근 4주 최장 거리 (km).
        vdot: VDOT 값.

    Returns:
        Marathon Shape 퍼센트 (0~100) 또는 None (VDOT 없음).
    """
    if not vdot or vdot <= 0:
        return None

    target_weekly_km = vdot * 0.8
    target_long_km = vdot * 0.35

    if target_weekly_km <= 0 or target_long_km <= 0:
        return None

    weekly_shape = min(1.0, weekly_km_avg / target_weekly_km)
    long_run_shape = min(1.0, longest_run_km / target_long_km)
    shape_pct = (weekly_shape * 2 / 3 + long_run_shape * 1 / 3) * 100

    return round(shape_pct, 1)


def marathon_shape_label(shape_pct: float) -> str:
    """Marathon Shape 상태 레이블.

    Returns:
        'insufficient' | 'base' | 'building' | 'ready' | 'peak'
    """
    if shape_pct < 40:
        return "insufficient"
    if shape_pct < 60:
        return "base"
    if shape_pct < 80:
        return "building"
    if shape_pct < 90:
        return "ready"
    return "peak"


def _get_recent_running_data(
    conn: sqlite3.Connection, target_date: str, weeks: int = 4
) -> tuple[float, float]:
    """최근 n주 평균 주간 거리 + 최장 거리 조회.

    Returns:
        (weekly_km_avg, longest_run_km)
    """
    td = date.fromisoformat(target_date)
    start_date = (td - timedelta(weeks=weeks)).isoformat()

    # 최장 거리
    row = conn.execute(
        """SELECT COALESCE(MAX(distance_km), 0)
           FROM v_canonical_activities
           WHERE DATE(start_time) BETWEEN ? AND ?
             AND activity_type = 'running'
             AND distance_km IS NOT NULL""",
        (start_date, target_date),
    ).fetchone()
    longest_km = float(row[0]) if row and row[0] else 0.0

    # 주별 총 거리 → 평균
    row = conn.execute(
        """SELECT COALESCE(SUM(distance_km), 0)
           FROM v_canonical_activities
           WHERE DATE(start_time) BETWEEN ? AND ?
             AND activity_type = 'running'
             AND distance_km IS NOT NULL""",
        (start_date, target_date),
    ).fetchone()
    total_km = float(row[0]) if row and row[0] else 0.0
    weekly_avg = total_km / weeks if weeks > 0 else 0.0

    return weekly_avg, longest_km


def _get_vdot(conn: sqlite3.Connection, target_date: str) -> float | None:
    """해당 날짜의 VDOT 값 조회.

    우선순위: 자체 추정(Jack Daniels) > Runalyze > Garmin VO2Max.
    RunPulse 계산이 최우선. 외부 소스는 참고/fallback.
    """
    # 1. 자체 추정: 최근 best effort로 VDOT 추정
    estimated = _estimate_vdot_from_activities(conn, target_date)
    if estimated is not None:
        return estimated

    # 2. Runalyze VDOT 또는 Garmin VO2Max (fallback)
    row = conn.execute(
        """SELECT runalyze_vdot, garmin_vo2max FROM daily_fitness
           WHERE (runalyze_vdot IS NOT NULL OR garmin_vo2max IS NOT NULL)
           AND date <= ? ORDER BY date DESC LIMIT 1""",
        (target_date,),
    ).fetchone()
    if row:
        if row[0] is not None:
            return float(row[0])
        if row[1] is not None:
            return float(row[1])

    return None


def _vo2_from_velocity(v: float) -> float:
    """Jack Daniels VO2 공식 — 속도(m/min)에서 산소 소비량(ml/kg/min) 추정.

    VO2 = -4.60 + 0.182258·v + 0.000104·v²
    출처: Daniels' Running Formula, 3rd Edition.
    """
    return -4.60 + 0.182258 * v + 0.000104 * v * v


def _pct_vo2max_from_time(t_min: float) -> float:
    """Jack Daniels %VO2max 공식 — 레이스 시간(분)에서 지속 가능 %VO2max.

    %VO2max = 0.8 + 0.1894393·e^(-0.012778·t) + 0.2989558·e^(-0.1932605·t)
    출처: Daniels' Running Formula, 3rd Edition.
    """
    return (0.8
            + 0.1894393 * math.exp(-0.012778 * t_min)
            + 0.2989558 * math.exp(-0.1932605 * t_min))


def estimate_vdot(distance_km: float, duration_sec: float) -> float | None:
    """Jack Daniels VDOT 추정 (정확한 공식).

    VDOT = VO2(v) / %VO2max(t)
    - v = 레이스 속도 (m/min)
    - t = 레이스 시간 (min)

    Args:
        distance_km: 레이스 거리 (km).
        duration_sec: 완주 시간 (초).

    Returns:
        VDOT 추정값 또는 None.
    """
    if distance_km <= 0 or duration_sec <= 0:
        return None

    v = (distance_km * 1000) / (duration_sec / 60)  # m/min
    t_min = duration_sec / 60

    vo2 = _vo2_from_velocity(v)
    pct = _pct_vo2max_from_time(t_min)
    if pct <= 0:
        return None

    vdot = round(vo2 / pct, 1)
    if vdot < 15 or vdot > 90:
        return None
    return vdot


def _estimate_vdot_from_activities(conn: sqlite3.Connection, target_date: str) -> float | None:
    """최근 활동에서 VDOT 추정 (Jack Daniels 정확 공식).

    12주 이내 5K~하프 거리의 베스트 페이스 활동으로 추정.
    여러 거리 결과가 있으면 가장 높은 VDOT을 채택.
    """
    td = date.fromisoformat(target_date)
    start = (td - timedelta(weeks=12)).isoformat()

    # 최근 12주 이내 5~21km 활동 (빠른 페이스 순 상위 5개)
    rows = conn.execute(
        """SELECT distance_km, duration_sec FROM v_canonical_activities
           WHERE activity_type='running'
             AND distance_km BETWEEN 4.5 AND 22
             AND duration_sec > 0
             AND DATE(start_time) BETWEEN ? AND ?
           ORDER BY (CAST(duration_sec AS REAL) / distance_km) ASC
           LIMIT 5""",
        (start, target_date),
    ).fetchall()
    if not rows:
        return None

    best_vdot: float | None = None
    for dist_km, dur_sec in rows:
        v = estimate_vdot(float(dist_km), float(dur_sec))
        if v is not None and (best_vdot is None or v > best_vdot):
            best_vdot = v

    return best_vdot


def calc_and_save_vdot(conn: sqlite3.Connection, target_date: str) -> float | None:
    """VDOT 계산 후 저장. 외부 소스 우선, 없으면 Jack Daniels 추정.

    Returns:
        VDOT 값 또는 None.
    """
    vdot = _get_vdot(conn, target_date)
    if vdot is not None:
        # 소스 판별: 자체 추정이 가능했으면 estimated, 아니면 외부
        estimated = _estimate_vdot_from_activities(conn, target_date)
        if estimated is not None:
            source = "estimated"
        else:
            row = conn.execute(
                "SELECT runalyze_vdot, garmin_vo2max FROM daily_fitness "
                "WHERE (runalyze_vdot IS NOT NULL OR garmin_vo2max IS NOT NULL) "
                "AND date<=? ORDER BY date DESC LIMIT 1",
                (target_date,),
            ).fetchone()
            source = "runalyze" if row and row[0] is not None else (
                "garmin" if row and row[1] is not None else "unknown"
            )
        # 외부 소스 값도 참고로 저장
        ref_runalyze = None
        ref_garmin = None
        ref_row = conn.execute(
            "SELECT runalyze_vdot, garmin_vo2max FROM daily_fitness "
            "WHERE date<=? ORDER BY date DESC LIMIT 1",
            (target_date,),
        ).fetchone()
        if ref_row:
            ref_runalyze = float(ref_row[0]) if ref_row[0] else None
            ref_garmin = float(ref_row[1]) if ref_row[1] else None
        save_metric(
            conn, date=target_date, metric_name="VDOT", value=vdot,
            extra_json={
                "source": source, "vdot": vdot,
                "runalyze_vdot": ref_runalyze, "garmin_vo2max": ref_garmin,
            },
        )
    return vdot


def calc_and_save_marathon_shape(
    conn: sqlite3.Connection, target_date: str
) -> float | None:
    """Marathon Shape 계산 후 computed_metrics에 저장.

    Args:
        conn: SQLite 커넥션.
        target_date: YYYY-MM-DD.

    Returns:
        shape_pct 또는 None.
    """
    vdot = _get_vdot(conn, target_date)
    if vdot is None:
        return None

    weekly_km_avg, longest_km = _get_recent_running_data(conn, target_date)

    shape = calc_marathon_shape(weekly_km_avg, longest_km, vdot)
    if shape is not None:
        save_metric(
            conn,
            date=target_date,
            metric_name="MarathonShape",
            value=shape,
            extra_json={
                "label": marathon_shape_label(shape),
                "weekly_km_avg": round(weekly_km_avg, 1),
                "longest_run_km": round(longest_km, 1),
                "vdot": vdot,
                "target_weekly_km": round(vdot * 0.8, 1),
                "target_long_km": round(vdot * 0.35, 1),
            },
        )
    return shape
