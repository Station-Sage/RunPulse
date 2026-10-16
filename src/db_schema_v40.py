"""스키마 v40 — planned_workouts.goal_id(planner 행 CHECK)·adj_accepted + user_training_prefs.workout_weekdays_mask.

테이블 재생성·백필 없음, 멱등. goal_id 의 CHECK 는 planner 행이 남아 있으면 ADD COLUMN 이 실패한다(레거시 삭제 누락 검출).
goal_id 를 가장 먼저 추가하므로 실패 시 다른 컬럼은 건드리지 않는다.
"""
from __future__ import annotations

import logging
import sqlite3

log = logging.getLogger(__name__)

_COLUMNS = (
    ("planned_workouts", "goal_id",
     "INTEGER CHECK (source <> 'planner' OR goal_id IS NOT NULL)"),
    ("planned_workouts", "adj_accepted",
     "INTEGER NOT NULL DEFAULT 0 CHECK (adj_accepted IN (0,1))"),
    ("user_training_prefs", "workout_weekdays_mask", "INTEGER"),
)


def _has_col(conn: sqlite3.Connection, table: str, col: str) -> bool:
    return any(r[1] == col for r in conn.execute(f"PRAGMA table_info({table})"))


def ensure_v40(conn: sqlite3.Connection) -> None:
    """v40 컬럼 3개를 없을 때만 추가. planner 행이 있으면 goal_id 추가에서 sqlite3.OperationalError 로 중단."""
    todo = [c for c in _COLUMNS if not _has_col(conn, c[0], c[1])]
    if not todo:
        return
    check = conn.execute("PRAGMA integrity_check").fetchone()[0]
    if check != "ok":
        raise RuntimeError(f"v40 중단: integrity_check={check}")
    for table, col, ddl in todo:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}")
    log.info("v40: %s 추가", ", ".join(f"{t}.{c}" for t, c, _ in todo))
