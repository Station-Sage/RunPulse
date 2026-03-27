"""computed_metrics 테이블 저장/조회 헬퍼."""
from __future__ import annotations

import json
import sqlite3
from typing import Any


def save_metric(
    conn: sqlite3.Connection,
    date: str,
    metric_name: str,
    value: float | None = None,
    activity_id: int | None = None,
    extra_json: dict | None = None,
) -> None:
    """computed_metrics UPSERT.

    SQLite UNIQUE 제약은 NULL을 각각 다른 값으로 취급하므로,
    activity_id IS NULL인 경우 ON CONFLICT가 동작하지 않음.
    명시적 SELECT → UPDATE/INSERT 패턴으로 처리.

    Args:
        conn: SQLite 커넥션.
        date: YYYY-MM-DD.
        metric_name: 메트릭 이름 (예: 'LSI', 'FEARP').
        value: 숫자 값.
        activity_id: 활동별 메트릭이면 activity_id, 일별이면 None.
        extra_json: 추가 JSON 데이터 (예: TIDS 분포).
    """
    json_str = json.dumps(extra_json, ensure_ascii=False) if extra_json else None

    existing = conn.execute(
        """SELECT id FROM computed_metrics
           WHERE date=? AND metric_name=?
             AND (activity_id IS ? OR (activity_id IS NULL AND ? IS NULL))""",
        (date, metric_name, activity_id, activity_id),
    ).fetchone()

    if existing:
        conn.execute(
            """UPDATE computed_metrics
               SET metric_value=?, metric_json=?, computed_at=datetime('now')
               WHERE id=?""",
            (value, json_str, existing[0]),
        )
    else:
        conn.execute(
            """INSERT INTO computed_metrics
               (date, activity_id, metric_name, metric_value, metric_json)
               VALUES (?, ?, ?, ?, ?)""",
            (date, activity_id, metric_name, value, json_str),
        )
    conn.commit()


def load_metric(
    conn: sqlite3.Connection,
    date: str,
    metric_name: str,
    activity_id: int | None = None,
) -> float | None:
    """단일 메트릭 값 조회.

    Returns:
        metric_value 또는 None.
    """
    row = conn.execute(
        """SELECT metric_value FROM computed_metrics
           WHERE date=? AND metric_name=?
             AND (activity_id IS ? OR (activity_id IS NULL AND ? IS NULL))""",
        (date, metric_name, activity_id, activity_id),
    ).fetchone()
    return row[0] if row else None


def load_metric_json(
    conn: sqlite3.Connection,
    date: str,
    metric_name: str,
    activity_id: int | None = None,
) -> dict | None:
    """메트릭 JSON 데이터 조회.

    Returns:
        dict 또는 None.
    """
    row = conn.execute(
        """SELECT metric_json FROM computed_metrics
           WHERE date=? AND metric_name=?
             AND (activity_id IS ? OR (activity_id IS NULL AND ? IS NULL))""",
        (date, metric_name, activity_id, activity_id),
    ).fetchone()
    if row is None or row[0] is None:
        return None
    return json.loads(row[0])


def estimate_max_hr(conn: sqlite3.Connection, target_date: str | None = None,
                    weeks: int = 12) -> float:
    """최대심박 추정 — Stream 기반 지속 HR + 활동 기반 fallback.

    방법 (우선순위):
    A. Strava stream: 10초 이상 연속 유지된 최고 HR (진짜 maxHR)
    B. 활동 max_hr: 고강도 활동 기반, IQR 이상치 제거

    Reference: Tanaka et al. (2001) — fallback 190 기본값

    Returns:
        추정 최대심박 (bpm).
    """
    from datetime import date as _d, timedelta as _td

    date_filter = ""
    params: list = []
    if target_date:
        start = (_d.fromisoformat(target_date) - _td(weeks=weeks)).isoformat()
        date_filter = "AND DATE(start_time) BETWEEN ? AND ?"
        params = [start, target_date]

    # 0. computed_metrics에 저장된 최근 maxHR 확인 (이미 계산된 값)
    if target_date:
        cached = conn.execute(
            "SELECT metric_value FROM computed_metrics "
            "WHERE metric_name='maxHR' AND metric_value IS NOT NULL AND date<=? "
            "ORDER BY date DESC LIMIT 1",
            (target_date,),
        ).fetchone()
        # 최근 4주 이내 계산된 값이면 재사용
        if cached and cached[0]:
            cache_date = conn.execute(
                "SELECT date FROM computed_metrics "
                "WHERE metric_name='maxHR' AND metric_value IS NOT NULL AND date<=? "
                "ORDER BY date DESC LIMIT 1",
                (target_date,),
            ).fetchone()
            if cache_date:
                from datetime import date as _d2
                days_old = (_d.fromisoformat(target_date) - _d.fromisoformat(cache_date[0])).days
                if days_old <= 28:
                    return float(cached[0])

    # A. Stream 기반: 30초 연속 유지된 최고 HR
    stream_max = _estimate_max_hr_from_streams(conn, date_filter, params)
    if stream_max and stream_max > 150:
        # 시계열 저장
        if target_date:
            save_metric(conn, target_date, "maxHR", stream_max,
                        extra_json={"method": "stream_30s", "sustained_sec": 30})
        return stream_max

    # B. 활동 max_hr 기반 (fallback)
    rows = conn.execute(
        f"SELECT max_hr FROM v_canonical_activities "
        f"WHERE activity_type='running' AND max_hr > 120 AND max_hr < 230 "
        f"AND avg_hr IS NOT NULL AND avg_hr > 0 "
        f"AND CAST(avg_hr AS REAL) / CAST(max_hr AS REAL) > 0.75 "
        f"{date_filter} "
        f"ORDER BY max_hr DESC LIMIT 10",
        params,
    ).fetchall()

    if not rows:
        rows = conn.execute(
            f"SELECT max_hr FROM v_canonical_activities "
            f"WHERE activity_type='running' AND max_hr > 120 AND max_hr < 230 "
            f"{date_filter} "
            f"ORDER BY max_hr DESC LIMIT 10",
            params,
        ).fetchall()

    if not rows:
        return 190.0

    vals = sorted([float(r[0]) for r in rows])

    # IQR 이상치 제거
    if len(vals) >= 4:
        q1 = vals[len(vals) // 4]
        q3 = vals[len(vals) * 3 // 4]
        iqr = q3 - q1
        upper_bound = q3 + 1.5 * iqr
        vals = [v for v in vals if v <= upper_bound]

    result = max(vals) if vals else 190.0
    # 시계열 저장
    if target_date and result > 150:
        save_metric(conn, target_date, "maxHR", result,
                    extra_json={"method": "activity_iqr"})
    return result


def _estimate_max_hr_from_streams(conn, date_filter: str, params: list,
                                   sustain_sec: int = 30) -> float | None:
    """Strava stream에서 N초 이상 연속 유지된 최고 HR.

    30초 슬라이딩 윈도우 평균의 최대값 = 추정 maxHR.
    References:
    - ACSM (2018): GXT에서 마지막 1분 peak HR
    - Beltz et al. (2016): 3분 all-out 마지막 30초 평균
    - Robergs & Landwehr (2002): 마지막 1분 최고 HR

    Args:
        sustain_sec: 최소 연속 유지 시간 (초). 기본 30초.
    """
    try:
        from src.analysis.efficiency import _get_stream_path, _load_stream
    except ImportError:
        return None

    # 최근 고강도 활동 (avg_hr/max_hr > 0.8)
    acts = conn.execute(
        f"SELECT id FROM v_canonical_activities "
        f"WHERE activity_type='running' AND max_hr > 150 "
        f"AND avg_hr IS NOT NULL AND CAST(avg_hr AS REAL) / CAST(max_hr AS REAL) > 0.80 "
        f"{date_filter} "
        f"ORDER BY max_hr DESC LIMIT 10",
        params,
    ).fetchall()

    best_sustained = 0.0

    for (aid,) in acts:
        path = _get_stream_path(conn, aid)
        if not path:
            continue
        stream = _load_stream(path)
        if not stream:
            continue
        hr = stream.get("heartrate", [])
        if len(hr) < sustain_sec:
            continue

        # 슬라이딩 윈도우: N초 연속 평균 HR의 최대값
        for i in range(len(hr) - sustain_sec + 1):
            window = hr[i:i + sustain_sec]
            if any(h is None or h < 50 for h in window):
                continue
            avg_window = sum(window) / sustain_sec
            if avg_window > best_sustained:
                best_sustained = avg_window

    return round(best_sustained) if best_sustained > 150 else None


def load_metric_series(
    conn: sqlite3.Connection,
    metric_name: str,
    start_date: str,
    end_date: str,
    activity_id: int | None = None,
) -> list[tuple[str, float]]:
    """날짜 범위의 메트릭 시계열 조회.

    Returns:
        [(date, value), ...] 날짜 오름차순.
    """
    rows = conn.execute(
        """SELECT date, metric_value FROM computed_metrics
           WHERE metric_name=? AND date BETWEEN ? AND ?
             AND (activity_id IS ? OR (activity_id IS NULL AND ? IS NULL))
             AND metric_value IS NOT NULL
           ORDER BY date ASC""",
        (metric_name, start_date, end_date, activity_id, activity_id),
    ).fetchall()
    return [(r[0], r[1]) for r in rows]
