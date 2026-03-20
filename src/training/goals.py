"""훈련 목표 CRUD."""

import sqlite3

_COLS = "id, name, race_date, distance_km, target_time_sec, target_pace_sec_km, status, created_at"


def _row_to_dict(row: tuple) -> dict:
    """DB 행을 dict로 변환."""
    keys = ["id", "name", "race_date", "distance_km", "target_time_sec",
            "target_pace_sec_km", "status", "created_at"]
    return dict(zip(keys, row))


def add_goal(
    conn: sqlite3.Connection,
    name: str,
    distance_km: float,
    race_date: str | None = None,
    target_time_sec: int | None = None,
    target_pace_sec_km: int | None = None,
) -> int:
    """목표 추가.

    Args:
        conn: SQLite 연결.
        name: 레이스/목표 이름.
        distance_km: 목표 거리 (km).
        race_date: 레이스 날짜 (YYYY-MM-DD).
        target_time_sec: 목표 완주 시간 (초).
        target_pace_sec_km: 목표 페이스 (초/km).

    Returns:
        새로 생성된 goal id.
    """
    cursor = conn.execute(
        """INSERT INTO goals
           (name, race_date, distance_km, target_time_sec, target_pace_sec_km, status)
           VALUES (?, ?, ?, ?, ?, 'active')""",
        (name, race_date, distance_km, target_time_sec, target_pace_sec_km),
    )
    conn.commit()
    return cursor.lastrowid


def list_goals(conn: sqlite3.Connection, status: str = "active") -> list[dict]:
    """목표 목록 조회.

    Args:
        conn: SQLite 연결.
        status: 'active' | 'completed' | 'cancelled' | 'all'.

    Returns:
        목표 dict 리스트 (최신순).
    """
    if status == "all":
        rows = conn.execute(
            f"SELECT {_COLS} FROM goals ORDER BY created_at DESC"
        ).fetchall()
    else:
        rows = conn.execute(
            f"SELECT {_COLS} FROM goals WHERE status = ? ORDER BY created_at DESC",
            (status,),
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_goal(conn: sqlite3.Connection, goal_id: int) -> dict | None:
    """id로 목표 단건 조회."""
    row = conn.execute(
        f"SELECT {_COLS} FROM goals WHERE id = ?", (goal_id,)
    ).fetchone()
    return _row_to_dict(row) if row else None


def get_active_goal(conn: sqlite3.Connection) -> dict | None:
    """가장 최근 active 목표 1개 반환."""
    row = conn.execute(
        f"SELECT {_COLS} FROM goals WHERE status = 'active' ORDER BY created_at DESC LIMIT 1"
    ).fetchone()
    return _row_to_dict(row) if row else None


def update_goal(conn: sqlite3.Connection, goal_id: int, **kwargs) -> bool:
    """목표 필드 업데이트.

    수정 가능 필드: name, race_date, distance_km, target_time_sec, target_pace_sec_km.

    Returns:
        업데이트 성공 여부.
    """
    allowed = {"name", "race_date", "distance_km", "target_time_sec", "target_pace_sec_km"}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return False
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [goal_id]
    cursor = conn.execute(f"UPDATE goals SET {set_clause} WHERE id = ?", values)
    conn.commit()
    return cursor.rowcount > 0


def _set_status(conn: sqlite3.Connection, goal_id: int, status: str) -> bool:
    """목표 상태 변경 내부 헬퍼."""
    cursor = conn.execute(
        "UPDATE goals SET status = ? WHERE id = ?", (status, goal_id)
    )
    conn.commit()
    return cursor.rowcount > 0


def complete_goal(conn: sqlite3.Connection, goal_id: int) -> bool:
    """목표를 completed로 변경."""
    return _set_status(conn, goal_id, "completed")


def cancel_goal(conn: sqlite3.Connection, goal_id: int) -> bool:
    """목표를 cancelled로 변경."""
    return _set_status(conn, goal_id, "cancelled")
