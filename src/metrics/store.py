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
    """최대심박 추정 — 고강도 활동 기반 + 이상치 제거.

    방법:
    1. 고강도 활동(avg_hr > max_hr×0.75) 중 max_hr 상위 10개 수집
    2. IQR 이상치 제거 (Q3 + 1.5×IQR 초과 제거)
    3. 남은 값 중 최대값 = 추정 maxHR

    Fallback: 데이터 없으면 Tanaka (2001) 공식 또는 190 기본값.
    Reference: Tanaka et al. (2001) "Age-predicted maximal heart rate revisited"
               208 - 0.7 × age

    Args:
        conn: DB 연결.
        target_date: 기준일 (None이면 전체).
        weeks: 최근 N주 활동만.

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

    # 고강도 활동의 max_hr 수집 (이지런 제외)
    # avg_hr / max_hr > 0.75 → 전체적으로 고강도였던 활동
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
        # 이지런 포함 전체에서 상위 수집 (fallback)
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

    if not vals:
        return 190.0

    # 이상치 제거 후 최대값 = 추정 maxHR
    return max(vals)


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
