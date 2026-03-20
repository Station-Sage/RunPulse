"""주간 추세 및 ACWR 부상 위험도 계산."""

import sqlite3
from datetime import date, timedelta


def _week_start(d: date) -> date:
    """월요일 기준 주 시작일."""
    return d - timedelta(days=d.weekday())


def weekly_trends(conn: sqlite3.Connection, weeks: int = 8) -> list[dict]:
    """최근 N주 주간 집계 지표.

    Args:
        conn: SQLite 연결.
        weeks: 조회할 주 수.

    Returns:
        주별 집계 리스트 (week_start, run_count, total_distance_km,
        total_duration_sec, avg_pace_sec_km, pct_change_distance).
    """
    today = date.today()
    current_monday = _week_start(today)
    results = []

    for i in range(weeks - 1, -1, -1):
        wk_start = current_monday - timedelta(weeks=i)
        wk_end = wk_start + timedelta(weeks=1)

        rows = conn.execute("""
            SELECT COALESCE(matched_group_id, CAST(id AS TEXT)) AS gk,
                   AVG(distance_km)     AS dist,
                   AVG(duration_sec)    AS dur,
                   AVG(avg_pace_sec_km) AS pace
            FROM activity_summaries
            WHERE start_time >= ? AND start_time < ?
              AND activity_type IN ('running', 'run', 'virtualrun', 'treadmill', 'highintensityintervaltraining')
            GROUP BY gk
        """, (wk_start.isoformat(), wk_end.isoformat())).fetchall()

        total_dist = round(sum(r[1] or 0 for r in rows), 2)
        total_dur = int(sum(r[2] or 0 for r in rows))
        paces = [r[3] for r in rows if r[3] is not None]
        avg_pace = round(sum(paces) / len(paces)) if paces else None

        results.append(dict(
            week_start=wk_start.isoformat(),
            run_count=len(rows),
            total_distance_km=total_dist,
            total_duration_sec=total_dur,
            avg_pace_sec_km=avg_pace,
        ))

    # 주간 거리 변화율 계산
    results[0]["pct_change_distance"] = None
    for i in range(1, len(results)):
        prev = results[i - 1]["total_distance_km"]
        curr = results[i]["total_distance_km"]
        if prev and prev != 0:
            results[i]["pct_change_distance"] = round((curr - prev) / prev * 100, 1)
        else:
            results[i]["pct_change_distance"] = None

    return results


def _load_sum(conn: sqlite3.Connection, start: str, end: str,
              source: str, metric_name: str) -> float:
    """기간 내 특정 부하 지표 합계 (없으면 0)."""
    row = conn.execute("""
        SELECT COALESCE(SUM(sm.metric_value), 0)
        FROM activity_detail_metrics sm
        JOIN activity_summaries a ON sm.activity_id = a.id
        WHERE a.start_time >= ? AND a.start_time < ?
          AND a.activity_type IN ('running', 'run', 'virtualrun', 'treadmill', 'highintensityintervaltraining')
          AND sm.source = ? AND sm.metric_name = ?
    """, (start, end, source, metric_name)).fetchone()
    return row[0] or 0.0


def _acwr_status(acwr: float) -> str:
    """ACWR 값으로 위험도 판정."""
    if acwr < 0.8:
        return "low"
    elif acwr <= 1.3:
        return "safe"
    elif acwr <= 1.5:
        return "caution"
    else:
        return "danger"


def calculate_acwr(
    conn: sqlite3.Connection,
    acute_days: int = 7,
    chronic_days: int = 28,
) -> dict | None:
    """4개 소스 부하 지표로 ACWR 계산 (교차 검증).

    각 지표별 ACWR = acute 합 / (chronic 합 / chronic_days * acute_days).

    Args:
        conn: SQLite 연결.
        acute_days: 급성 기간 (일, 기본 7).
        chronic_days: 만성 기간 (일, 기본 28).

    Returns:
        {"garmin_tl": {"acwr": 1.2, "status": "safe"}, ..., "average": {...}}
        사용 가능한 지표가 없으면 None.
    """
    today = date.today()
    end = (today + timedelta(days=1)).isoformat()
    acute_start = (today - timedelta(days=acute_days)).isoformat()
    chronic_start = (today - timedelta(days=chronic_days)).isoformat()

    indicators = [
        ("garmin_tl",       "garmin",    "training_load"),
        ("strava_re",       "strava",    "relative_effort"),
        ("intervals_hrss",  "intervals", "icu_hrss"),
        ("runalyze_trimp",  "runalyze",  "trimp"),
    ]

    results: dict = {}
    acwr_values: list[float] = []

    for key, source, metric in indicators:
        acute = _load_sum(conn, acute_start, end, source, metric)
        chronic = _load_sum(conn, chronic_start, end, source, metric)

        if acute == 0 and chronic == 0:
            continue

        if chronic == 0:
            acwr_val = None
        else:
            chronic_in_acute = (chronic / chronic_days) * acute_days
            acwr_val = round(acute / chronic_in_acute, 3) if chronic_in_acute > 0 else None

        if acwr_val is not None:
            results[key] = {"acwr": acwr_val, "status": _acwr_status(acwr_val)}
            acwr_values.append(acwr_val)

    if not results:
        return None

    avg_acwr = round(sum(acwr_values) / len(acwr_values), 3)
    results["average"] = {"acwr": avg_acwr, "status": _acwr_status(avg_acwr)}
    return results


def _fitness_last_from_daily(
    conn: sqlite3.Connection,
    wk_start: str,
    wk_end: str,
    source: str,
    col: str,
) -> float | None:
    """daily_fitness에서 주간 마지막 값 조회."""
    _valid = {"ctl", "atl", "tsb", "ramp_rate", "garmin_vo2max",
              "runalyze_evo2max", "runalyze_vdot", "runalyze_marathon_shape"}
    if col not in _valid:
        return None
    try:
        row = conn.execute(
            f"SELECT {col} FROM daily_fitness "
            f"WHERE date >= ? AND date < ? AND source = ? AND {col} IS NOT NULL "
            "ORDER BY date DESC LIMIT 1",
            (wk_start, wk_end, source),
        ).fetchone()
        return row[0] if row else None
    except sqlite3.OperationalError:
        return None


def _fitness_last_from_metrics(
    conn: sqlite3.Connection,
    wk_start: str,
    wk_end: str,
    source: str,
    metric_name: str,
) -> float | None:
    """source_metrics에서 주간 마지막 값 조회 (fallback)."""
    row = conn.execute("""
        SELECT sm.metric_value
        FROM activity_detail_metrics sm
        JOIN activity_summaries a ON sm.activity_id = a.id
        WHERE a.start_time >= ? AND a.start_time < ?
          AND a.activity_type IN ('running', 'run', 'virtualrun', 'treadmill', 'highintensityintervaltraining')
          AND sm.source = ? AND sm.metric_name = ?
        ORDER BY a.start_time DESC
        LIMIT 1
    """, (wk_start, wk_end, source, metric_name)).fetchone()
    return row[0] if row else None


def fitness_trend(conn: sqlite3.Connection, weeks: int = 8) -> list[dict]:
    """피트니스 지표 주간 추세.

    daily_fitness를 우선 참조하고, 데이터 없으면 source_metrics로 폴백.
    intervals CTL/ATL/TSB, runalyze VO2Max/VDOT, garmin VO2Max의 주별 마지막 값.

    Args:
        conn: SQLite 연결.
        weeks: 조회할 주 수.

    Returns:
        주별 피트니스 지표 리스트.
    """
    today = date.today()
    current_monday = _week_start(today)

    # (result_key, daily_fitness_source, daily_fitness_col, fallback_source, fallback_metric)
    fitness_specs = [
        ("intervals_ctl",   "intervals", "ctl",             "intervals", "ctl"),
        ("intervals_atl",   "intervals", "atl",             "intervals", "atl"),
        ("intervals_tsb",   "intervals", "tsb",             "intervals", "tsb"),
        ("runalyze_evo2max","runalyze",  "runalyze_evo2max","runalyze",  "effective_vo2max"),
        ("runalyze_vdot",   "runalyze",  "runalyze_vdot",   "runalyze",  "vdot"),
        ("garmin_vo2max",   "garmin",    "garmin_vo2max",   "garmin",    "vo2max"),
    ]

    results = []
    for i in range(weeks - 1, -1, -1):
        wk_start = current_monday - timedelta(weeks=i)
        wk_end = wk_start + timedelta(weeks=1)
        wk_start_str = wk_start.isoformat()
        wk_end_str = wk_end.isoformat()
        entry: dict = {"week_start": wk_start_str}

        for result_key, df_src, df_col, fb_src, fb_metric in fitness_specs:
            # daily_fitness 우선 조회, 없으면 source_metrics 폴백
            val = _fitness_last_from_daily(conn, wk_start_str, wk_end_str, df_src, df_col)
            if val is None:
                val = _fitness_last_from_metrics(conn, wk_start_str, wk_end_str, fb_src, fb_metric)
            entry[result_key] = val

        results.append(entry)

    return results
