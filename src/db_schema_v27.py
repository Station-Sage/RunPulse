"""스키마 v27 — planned_workouts.workout_type CHECK 확장(marathon·long_mp·threshold, U16h)."""
from __future__ import annotations

import sqlite3

_OLD = "'race')"
_NEW = "'race', 'marathon', 'long_mp', 'threshold')"


def ensure_v27(conn: sqlite3.Connection) -> None:
    """CHECK 에 새 유형이 없으면 테이블을 재생성한다(컬럼·행·인덱스 보존). 멱등."""
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='planned_workouts'").fetchone()
    if not row or not row[0] or "'long_mp'" in row[0] or _OLD not in row[0]:
        return
    new_sql = row[0].replace(_OLD, _NEW, 1).replace("planned_workouts", "planned_workouts__v27", 1)
    indexes = [r[0] for r in conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='index' AND tbl_name='planned_workouts' AND sql IS NOT NULL")]
    cols = ", ".join(f'"{r[1]}"' for r in conn.execute("PRAGMA table_info(planned_workouts)"))
    conn.execute("DROP TABLE IF EXISTS planned_workouts__v27")
    conn.execute(new_sql)
    conn.execute(f"INSERT INTO planned_workouts__v27 ({cols}) SELECT {cols} FROM planned_workouts")
    conn.execute("DROP TABLE planned_workouts")
    conn.execute("ALTER TABLE planned_workouts__v27 RENAME TO planned_workouts")
    for sql in indexes:
        conn.execute(sql)
    conn.commit()
