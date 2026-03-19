"""두 기간의 활동을 비교하는 모듈."""

import sqlite3
from datetime import date, timedelta


def _week_start(d: date) -> date:
    """월요일 기준 주 시작일."""
    return d - timedelta(days=d.weekday())


def _get_basics(conn: sqlite3.Connection, start: str, end: str) -> dict:
    """기간 내 기본 지표 (matched_group_id로 중복 제거)."""
    rows = conn.execute("""
        SELECT COALESCE(matched_group_id, CAST(id AS TEXT)) AS gk,
               AVG(distance_km)     AS dist,
               AVG(duration_sec)    AS dur,
               AVG(avg_pace_sec_km) AS pace,
               AVG(avg_hr)          AS hr
        FROM activities
        WHERE start_time >= ? AND start_time < ?
          AND activity_type = 'running'
        GROUP BY gk
    """, (start, end)).fetchall()

    if not rows:
        return dict(
            run_count=0, total_distance_km=0.0, total_duration_sec=0,
            avg_pace_sec_km=None, avg_hr=None,
        )

    total_dist = sum(r[1] or 0 for r in rows)
    total_dur = sum(r[2] or 0 for r in rows)
    paces = [r[3] for r in rows if r[3] is not None]
    hrs = [r[4] for r in rows if r[4] is not None]

    return dict(
        run_count=len(rows),
        total_distance_km=round(total_dist, 2),
        total_duration_sec=int(total_dur),
        avg_pace_sec_km=round(sum(paces) / len(paces)) if paces else None,
        avg_hr=round(sum(hrs) / len(hrs)) if hrs else None,
    )


def _metric_sum(conn: sqlite3.Connection, start: str, end: str,
                source: str, metric_name: str) -> float | None:
    """기간 내 특정 소스/지표 합계."""
    row = conn.execute("""
        SELECT SUM(sm.metric_value)
        FROM source_metrics sm
        JOIN activities a ON sm.activity_id = a.id
        WHERE a.start_time >= ? AND a.start_time < ?
          AND a.activity_type = 'running'
          AND sm.source = ? AND sm.metric_name = ?
    """, (start, end, source, metric_name)).fetchone()
    return row[0]


def _metric_avg(conn: sqlite3.Connection, start: str, end: str,
                source: str, metric_name: str) -> float | None:
    """기간 내 특정 소스/지표 평균."""
    row = conn.execute("""
        SELECT AVG(sm.metric_value)
        FROM source_metrics sm
        JOIN activities a ON sm.activity_id = a.id
        WHERE a.start_time >= ? AND a.start_time < ?
          AND a.activity_type = 'running'
          AND sm.source = ? AND sm.metric_name = ?
    """, (start, end, source, metric_name)).fetchone()
    return row[0]


def _last_day_metric(conn: sqlite3.Connection, start: str, end: str,
                     source: str, metric_name: str) -> float | None:
    """기간 마지막 날의 특정 소스/지표 값."""
    row = conn.execute("""
        SELECT sm.metric_value
        FROM source_metrics sm
        JOIN activities a ON sm.activity_id = a.id
        WHERE a.start_time >= ? AND a.start_time < ?
          AND a.activity_type = 'running'
          AND sm.source = ? AND sm.metric_name = ?
        ORDER BY a.start_time DESC
        LIMIT 1
    """, (start, end, source, metric_name)).fetchone()
    return row[0] if row else None


def _get_source_metrics(conn: sqlite3.Connection, start: str, end: str) -> dict:
    """4개 소스 고유 지표 수집."""
    return {
        # garmin
        "garmin_training_effect_avg": _metric_avg(
            conn, start, end, "garmin", "training_effect_aerobic"
        ),
        "garmin_training_load_total": _metric_sum(
            conn, start, end, "garmin", "training_load"
        ),
        # strava
        "strava_suffer_score_total": _metric_sum(
            conn, start, end, "strava", "relative_effort"
        ),
        # intervals (기간 마지막 날 스냅샷)
        "intervals_ctl_last": _last_day_metric(conn, start, end, "intervals", "ctl"),
        "intervals_atl_last": _last_day_metric(conn, start, end, "intervals", "atl"),
        "intervals_tsb_last": _last_day_metric(conn, start, end, "intervals", "tsb"),
        # runalyze (기간 마지막 날 스냅샷)
        "runalyze_vo2max_last": _last_day_metric(
            conn, start, end, "runalyze", "effective_vo2max"
        ),
        "runalyze_vdot_last": _last_day_metric(conn, start, end, "runalyze", "vdot"),
    }


def _calc_changes(p1: dict, p2: dict) -> tuple[dict, dict]:
    """변화량(delta)과 변화율(pct) 계산."""
    delta: dict = {}
    pct: dict = {}
    for key in p2:
        v1 = p1.get(key)
        v2 = p2.get(key)
        if v1 is None or v2 is None:
            delta[key] = None
            pct[key] = None
        else:
            delta[key] = round(v2 - v1, 4)
            pct[key] = round((v2 - v1) / v1 * 100, 1) if v1 != 0 else None
    return delta, pct


def compare_periods(
    conn: sqlite3.Connection,
    period1_start: str,
    period1_end: str,
    period2_start: str,
    period2_end: str,
) -> dict:
    """두 기간의 지표를 비교하여 변화량/변화율 반환.

    Args:
        conn: SQLite 연결.
        period1_start: 기간1 시작 (ISO 날짜, 포함).
        period1_end: 기간1 종료 (ISO 날짜, 미포함).
        period2_start: 기간2 시작 (ISO 날짜, 포함).
        period2_end: 기간2 종료 (ISO 날짜, 미포함).

    Returns:
        {"period1": {...}, "period2": {...}, "delta": {...}, "pct": {...}}
    """
    b1 = _get_basics(conn, period1_start, period1_end)
    b2 = _get_basics(conn, period2_start, period2_end)
    s1 = _get_source_metrics(conn, period1_start, period1_end)
    s2 = _get_source_metrics(conn, period2_start, period2_end)

    p1 = {**b1, **s1}
    p2 = {**b2, **s2}
    delta, pct = _calc_changes(p1, p2)

    return dict(period1=p1, period2=p2, delta=delta, pct=pct)


def compare_today_vs_yesterday(conn: sqlite3.Connection) -> dict:
    """오늘 vs 어제 비교."""
    today = date.today()
    yesterday = today - timedelta(days=1)
    tomorrow = today + timedelta(days=1)
    return compare_periods(
        conn,
        yesterday.isoformat(), today.isoformat(),
        today.isoformat(), tomorrow.isoformat(),
    )


def compare_this_week_vs_last(conn: sqlite3.Connection) -> dict:
    """이번 주 vs 지난 주 비교 (월요일 기준)."""
    today = date.today()
    this_monday = _week_start(today)
    last_monday = this_monday - timedelta(weeks=1)
    next_monday = this_monday + timedelta(weeks=1)
    return compare_periods(
        conn,
        last_monday.isoformat(), this_monday.isoformat(),
        this_monday.isoformat(), next_monday.isoformat(),
    )


def compare_this_month_vs_last(conn: sqlite3.Connection) -> dict:
    """이번 달 vs 지난 달 비교."""
    today = date.today()
    this_month = date(today.year, today.month, 1)
    if today.month == 1:
        last_month = date(today.year - 1, 12, 1)
    else:
        last_month = date(today.year, today.month - 1, 1)
    if today.month == 12:
        next_month = date(today.year + 1, 1, 1)
    else:
        next_month = date(today.year, today.month + 1, 1)
    return compare_periods(
        conn,
        last_month.isoformat(), this_month.isoformat(),
        this_month.isoformat(), next_month.isoformat(),
    )
