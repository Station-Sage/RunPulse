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
