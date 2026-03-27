"""RMR (Runner Maturity Radar) — 러너 성숙도 레이더.

5개 축 (각 0-100):
    유산소용량 : clamp(vo2max / 65 * 100, 0, 100)
    역치강도   : clamp(hr_lthr / hr_max * 100, 0, 100)
    지구력     : di_summary * 100
    동작효율성 : cadence_score * 0.5 + vr_score * 0.5
    회복력     : (body_battery_score + sleep_score) / 2

cadence_score: 170-185 spm = 100, 이탈 시 감점
vr_score     : VR 6~8% = 100 (낮을수록 좋음)
"""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from src.metrics.di import get_di
from src.metrics.store import estimate_max_hr, save_metric

_AXIS_NAMES = ["유산소용량", "역치강도", "지구력", "동작효율성", "회복력"]
_OPTIMAL_CADENCE = 178  # 170-185 spm 중간값
_CADENCE_PENALTY = 3    # 1spm 이탈당 3점 감점
_OPTIMAL_VR_LOW = 6.0   # VR 6-8% 최적
_OPTIMAL_VR_HIGH = 8.0


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def calc_rmr(
    vo2max: float | None,
    hr_lthr: float | None,
    hr_max: float | None,
    di: float | None,
    avg_cadence: float | None,
    vertical_ratio_pct: float | None,
    body_battery: float | None,
    sleep_score: float | None,
) -> dict:
    """RMR 계산 (순수 함수).

    데이터 없는 항목은 중립값(50) 사용.

    Returns:
        {'axes': {name: score}, 'overall': avg, 'available': [...]}
    """
    available = []

    # 유산소용량
    if vo2max is not None and vo2max > 0:
        aerobic = _clamp(vo2max / 65.0 * 100.0, 0, 100)
        available.append("유산소용량")
    else:
        aerobic = 50.0

    # 역치강도
    if hr_lthr is not None and hr_max and hr_max > 0:
        threshold = _clamp(hr_lthr / hr_max * 100.0, 0, 100)
        available.append("역치강도")
    else:
        threshold = 50.0

    # 지구력 (DI * 100)
    if di is not None:
        # DI 0~1.2 범위를 0~100으로 정규화 (1.0 = 100점)
        endurance = _clamp(di * 100.0, 0, 100)
        available.append("지구력")
    else:
        endurance = 50.0

    # 동작효율성 = cadence_score * 0.5 + vr_score * 0.5
    cadence_score = 50.0
    vr_score = 50.0
    if avg_cadence is not None and avg_cadence > 0:
        cadence_score = _clamp(100.0 - abs(avg_cadence - _OPTIMAL_CADENCE) * _CADENCE_PENALTY, 0, 100)
        available.append("케이던스")
    if vertical_ratio_pct is not None and vertical_ratio_pct > 0:
        excess = max(0.0, vertical_ratio_pct - _OPTIMAL_VR_LOW)
        vr_score = _clamp(100.0 - excess * 20.0, 0, 100)
        available.append("수직진동비")
    movement = (cadence_score + vr_score) / 2.0
    if "케이던스" in available or "수직진동비" in available:
        if "동작효율성" not in available:
            available.append("동작효율성")

    # 회복력 = (body_battery + sleep_score) / 2
    bb_score = float(body_battery) if body_battery is not None else 50.0
    sl_score = float(sleep_score) if sleep_score is not None else 50.0
    recovery = (bb_score + sl_score) / 2.0
    if body_battery is not None or sleep_score is not None:
        available.append("회복력")

    axes = {
        "유산소용량": round(aerobic, 1),
        "역치강도": round(threshold, 1),
        "지구력": round(endurance, 1),
        "동작효율성": round(movement, 1),
        "회복력": round(recovery, 1),
    }
    overall = sum(axes.values()) / 5.0

    return {
        "axes": axes,
        "overall": round(overall, 1),
        "available": available,
    }


def calc_and_save_rmr(conn: sqlite3.Connection, target_date: str) -> dict | None:
    """RMR 계산 후 저장.

    Args:
        conn: SQLite 커넥션.
        target_date: YYYY-MM-DD.

    Returns:
        RMR 결과 딕셔너리 또는 None.
    """
    # VO2max
    row = conn.execute(
        """SELECT COALESCE(garmin_vo2max, runalyze_evo2max)
           FROM daily_fitness WHERE date <= ? AND
           (garmin_vo2max IS NOT NULL OR runalyze_evo2max IS NOT NULL)
           ORDER BY date DESC LIMIT 1""",
        (target_date,),
    ).fetchone()
    vo2max = float(row[0]) if row and row[0] else None

    # HR 파라미터
    hr_max_est = estimate_max_hr(conn, target_date)
    hr_max = hr_max_est if hr_max_est != 190.0 else None  # 190 = 기본값 → 데이터 없음
    hr_lthr = (hr_max * 0.87) if hr_max else None

    # DI
    di = get_di(conn, target_date)

    # 케이던스 (최근 4주 평균)
    td = date.fromisoformat(target_date)
    start_4w = (td - timedelta(weeks=4)).isoformat()
    row = conn.execute(
        """SELECT AVG(avg_cadence) FROM v_canonical_activities
           WHERE avg_cadence IS NOT NULL
             AND DATE(start_time) BETWEEN ? AND ?""",
        (start_4w, target_date),
    ).fetchone()
    avg_cadence = float(row[0]) if row and row[0] else None

    # Vertical Ratio (activity_detail_metrics)
    row = conn.execute(
        """SELECT AVG(m.metric_value)
           FROM activity_detail_metrics m
           JOIN activity_summaries a ON a.id = m.activity_id
           WHERE m.metric_name = 'vertical_ratio'
             AND DATE(a.start_time) BETWEEN ? AND ?""",
        (start_4w, target_date),
    ).fetchone()
    vr_pct = float(row[0]) if row and row[0] else None

    # Body Battery & Sleep
    row = conn.execute(
        """SELECT body_battery, sleep_score FROM daily_wellness
           WHERE date <= ? AND (body_battery IS NOT NULL OR sleep_score IS NOT NULL)
           ORDER BY date DESC LIMIT 1""",
        (target_date,),
    ).fetchone()
    body_battery = float(row[0]) if row and row[0] else None
    sleep_score = float(row[1]) if row and row[1] else None

    result = calc_rmr(vo2max, hr_lthr, hr_max, di, avg_cadence, vr_pct, body_battery, sleep_score)

    save_metric(
        conn,
        date=target_date,
        metric_name="RMR",
        value=result["overall"],
        extra_json=result,
    )
    return result
