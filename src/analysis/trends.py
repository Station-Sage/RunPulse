"""주간 추세 및 ACWR 부상 위험도 계산."""

import sqlite3
from datetime import date, timedelta

from src.utils.vo2max_source import garmin_vo2max_between


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
                   AVG(distance_m) / 1000.0 AS dist,
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


def calculate_acwr(conn: sqlite3.Connection) -> dict | None:
    """정식 ACWR(metric_store 'acwr', EWMA 7/42, D1f)의 최신 일별 값.

    Returns:
        {"average": {"acwr": 1.1, "status": "safe", "date": "YYYY-MM-DD"}}. 값이 없으면 None.
        (소비처 호환을 위해 "average" 키 형태 유지)
    """
    row = conn.execute(
        "SELECT scope_id, numeric_value FROM metric_store"
        " WHERE scope_type='daily' AND metric_name='acwr' AND is_primary=1"
        " AND numeric_value IS NOT NULL AND scope_id <= ?"
        " ORDER BY scope_id DESC LIMIT 1",
        (date.today().isoformat(),),
    ).fetchone()
    if not row:
        return None
    val = round(float(row[1]), 3)
    return {"average": {"acwr": val, "status": _acwr_status(val), "date": row[0]}}


def _fitness_last_from_daily_metrics(
    conn: sqlite3.Connection,
    wk_start: str,
    wk_end: str,
    provider: str,
    metric_name: str,
) -> float | None:
    """metric_store(scope_type='daily')에서 주간 마지막 값 조회. CTL/ATL/TSB 등 일별 집계 메트릭용."""
    row = conn.execute("""
        SELECT numeric_value
        FROM metric_store
        WHERE scope_type='daily'
          AND scope_id >= ? AND scope_id < ?
          AND provider = ? AND metric_name = ?
          AND is_primary = 1
        ORDER BY scope_id DESC
        LIMIT 1
    """, (wk_start, wk_end, provider, metric_name)).fetchone()
    return row[0] if row else None


def _fitness_last_from_activity_metrics(
    conn: sqlite3.Connection,
    wk_start: str,
    wk_end: str,
    provider: str,
    metric_name: str,
) -> float | None:
    """metric_store(scope_type='activity')에서 주간 마지막 값 조회. VO2max/VDOT 등 활동별 메트릭용."""
    row = conn.execute("""
        SELECT sm.numeric_value
        FROM metric_store sm
        JOIN activity_summaries a ON sm.scope_id = CAST(a.id AS TEXT)
        WHERE sm.scope_type = 'activity'
          AND a.start_time >= ? AND a.start_time < ?
          AND a.activity_type IN ('running', 'run', 'virtualrun', 'treadmill', 'highintensityintervaltraining')
          AND sm.provider = ? AND sm.metric_name = ?
        ORDER BY a.start_time DESC
        LIMIT 1
    """, (wk_start, wk_end, provider, metric_name)).fetchone()
    return row[0] if row else None


def fitness_trend(conn: sqlite3.Connection, weeks: int = 8) -> list[dict]:
    """피트니스 지표 주간 추세.

    metric_store에서 직접 조회.
    - 'daily' scope: intervals CTL/ATL/TSB (일별 집계)
    - 'activity' scope: runalyze VO2Max/VDOT, garmin VO2Max (활동별)

    Args:
        conn: SQLite 연결.
        weeks: 조회할 주 수.

    Returns:
        주별 피트니스 지표 리스트.
    """
    today = date.today()
    current_monday = _week_start(today)

    # (result_key, scope_type, provider, metric_name)
    fitness_specs = [
        ("intervals_ctl",    "daily",    "intervals", "ctl"),
        ("intervals_atl",    "daily",    "intervals", "atl"),
        ("intervals_tsb",    "daily",    "intervals", "tsb"),
        ("runalyze_evo2max", "activity", "runalyze",  "effective_vo2max"),
        ("runalyze_vdot",    "activity", "runalyze",  "vdot"),
    ]

    results = []
    for i in range(weeks - 1, -1, -1):
        wk_start = current_monday - timedelta(weeks=i)
        wk_end = wk_start + timedelta(weeks=1)
        wk_start_str = wk_start.isoformat()
        wk_end_str = wk_end.isoformat()
        entry: dict = {"week_start": wk_start_str}

        for result_key, scope_type, provider, metric_name in fitness_specs:
            if scope_type == "daily":
                val = _fitness_last_from_daily_metrics(
                    conn, wk_start_str, wk_end_str, provider, metric_name
                )
            else:
                val = _fitness_last_from_activity_metrics(
                    conn, wk_start_str, wk_end_str, provider, metric_name
                )
            entry[result_key] = val

        entry["garmin_vo2max"] = garmin_vo2max_between(
            conn, wk_start_str, (wk_end - timedelta(days=1)).isoformat()
        )[0]

        results.append(entry)

    return results
