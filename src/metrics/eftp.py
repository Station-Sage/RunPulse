"""eFTP (Estimated Functional Threshold Pace) — 기능적 역치 페이스 추정.

1차: Intervals.icu icu_ftp 값 (sync 시 저장)
2차: 최근 활동에서 rFTP 자체 추정 — 60분 전후 고강도 활동의 평균 페이스

단위: sec/km (낮을수록 빠름)
저장: computed_metrics (date, 'eFTP', value=sec/km, extra_json)
"""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from src.metrics.store import save_metric


def calc_and_save_eftp(conn: sqlite3.Connection, target_date: str) -> float | None:
    """eFTP 계산 후 저장.

    우선순위:
      1. Intervals.icu icu_ftp (activity_summaries에서 가장 최근)
      2. 최근 12주 40~70분 고강도 활동에서 페이스 추정

    Returns:
        eFTP (sec/km) 또는 None.
    """
    td = date.fromisoformat(target_date)

    # 1. VDOT 기반 Daniels T-pace (가장 정확)
    vdot_val = None
    vdot_src = "unknown"
    for mname in ("VDOT",):
        vdot_row = conn.execute(
            "SELECT metric_value FROM computed_metrics WHERE metric_name=? "
            "AND metric_value IS NOT NULL AND date<=? ORDER BY date DESC LIMIT 1",
            (mname, target_date),
        ).fetchone()
        if vdot_row and vdot_row[0]:
            vdot_val = float(vdot_row[0])
            vdot_src = mname.lower()
            break
    if vdot_val:
        from src.metrics.daniels_table import get_training_paces
        paces = get_training_paces(vdot_val)
        t_pace = paces.get("T")
        if t_pace:
            save_metric(conn, target_date, "eFTP", t_pace,
                        extra_json={"source": f"daniels_t_pace ({vdot_src})",
                                    "pace_sec_km": t_pace,
                                    "vdot": vdot_val,
                                    "vdot_source": vdot_src})
            return t_pace

    # 2. Intervals.icu FTP (VDOT 없을 때 fallback)
    icu_row = conn.execute(
        """SELECT metric_value FROM computed_metrics
           WHERE metric_name='icu_ftp' AND date<=? AND metric_value IS NOT NULL
           ORDER BY date DESC LIMIT 1""",
        (target_date,),
    ).fetchone()
    if icu_row and icu_row[0]:
        eftp = float(icu_row[0])
        save_metric(conn, target_date, "eFTP", eftp,
                    extra_json={"source": "intervals", "pace_sec_km": eftp})
        return eftp

    # 3. 자체 추정: 고강도 활동의 역치 페이스 추정
    #    HR 기반: 최대심박 85%+ 활동 → 역치 근처 노력
    start = (td - timedelta(weeks=12)).isoformat()

    from src.metrics.store import estimate_max_hr

    # 사용자 최대심박 추정 (이상치 제거)
    max_hr = estimate_max_hr(conn, target_date, weeks=12)
    hr_threshold = max_hr * 0.82  # 역치 최소 노력도

    # 30~70분, HR 역치 이상 활동 (고강도)
    rows = conn.execute(
        """SELECT avg_pace_sec_km, duration_sec, avg_hr, distance_km
           FROM v_canonical_activities
           WHERE activity_type='running'
             AND duration_sec BETWEEN 1800 AND 4200
             AND avg_pace_sec_km IS NOT NULL AND avg_pace_sec_km > 180
             AND avg_hr IS NOT NULL AND avg_hr >= ?
             AND DATE(start_time) BETWEEN ? AND ?
           ORDER BY avg_pace_sec_km ASC
           LIMIT 5""",
        (hr_threshold, start, target_date),
    ).fetchall()
    if not rows:
        # 더 넓은 범위: 20~90분, HR 75%+ (템포~역치)
        hr_min = max_hr * 0.75
        rows = conn.execute(
            """SELECT avg_pace_sec_km, duration_sec, avg_hr, distance_km
               FROM v_canonical_activities
               WHERE activity_type='running'
                 AND duration_sec BETWEEN 1200 AND 5400
                 AND avg_pace_sec_km IS NOT NULL AND avg_pace_sec_km > 180
                 AND avg_hr IS NOT NULL AND avg_hr >= ?
                 AND DATE(start_time) BETWEEN ? AND ?
               ORDER BY avg_pace_sec_km ASC
               LIMIT 5""",
            (hr_min, start, target_date),
        ).fetchall()

    if not rows:
        return None

    # 상위 3개 활동의 가중 평균 (빠른 활동 가중치 높음)
    top = rows[:3]
    total_weight = 0.0
    weighted_pace = 0.0
    for pace, dur, hr, dist in top:
        # 시간이 60분에 가까울수록 가중치 높음
        time_weight = 1.0 - abs(dur - 3600) / 3600 * 0.5
        weight = max(0.3, time_weight)
        weighted_pace += float(pace) * weight
        total_weight += weight

    if total_weight <= 0:
        return None

    eftp = round(weighted_pace / total_weight)
    save_metric(conn, target_date, "eFTP", eftp, extra_json={
        "source": "estimated",
        "pace_sec_km": eftp,
        "sample_count": len(top),
    })
    return eftp
