"""재처리(clear_first)로 활동 id 가 바뀌어도 사용자 입력 참조(activity_feedback·activity_shoe)를 보존한다.

두 테이블은 activity_summaries FK 가 없고 activity_id 만 가진다 — 삭제 전에 (source, source_id) 로 스냅샷을 뜨고
재구축 뒤 새 id 로 복원한다. 새 활동이 없는 행(payload 없는 활동)은 복원하지 않는다.
"""
from __future__ import annotations

import logging
import sqlite3

log = logging.getLogger(__name__)

REF_TABLES = ("activity_feedback", "activity_shoe")


def _has_table(conn: sqlite3.Connection, table: str) -> bool:
    return conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None


def snapshot_refs(conn: sqlite3.Connection, source: str | None) -> dict[str, list[tuple[str, str, dict]]]:
    """{table: [(source, source_id, row)]} — source 지정 시 그 소스 활동만."""
    out: dict[str, list[tuple[str, str, dict]]] = {}
    for table in REF_TABLES:
        if not _has_table(conn, table):
            continue
        sql = (f"SELECT a.source, a.source_id, t.* FROM {table} t "
               "JOIN activity_summaries a ON a.id = t.activity_id")
        params: tuple = ()
        if source:
            sql += " WHERE a.source = ?"
            params = (source,)
        cur = conn.execute(sql, params)
        cols = [d[0] for d in cur.description]
        out[table] = [(r[0], r[1], dict(zip(cols[2:], r[2:]))) for r in cur.fetchall()]
    return out


def restore_refs(conn: sqlite3.Connection, snap: dict[str, list[tuple[str, str, dict]]]) -> int:
    """스냅샷을 새 activity_id 로 되살린다. 복원한 행 수를 반환."""
    restored = 0
    for table, rows in snap.items():  # 옛 id 행을 먼저 모두 지운다(새 id 가 다른 옛 id 와 겹칠 수 있음)
        conn.executemany(f"DELETE FROM {table} WHERE activity_id = ?", [(r[2]["activity_id"],) for r in rows])
    for table, rows in snap.items():
        for src, sid, row in rows:
            new = conn.execute(
                "SELECT id FROM activity_summaries WHERE source = ? AND source_id = ?", (src, sid)
            ).fetchone()
            if new is None:
                continue
            row = {**row, "activity_id": new[0]}
            cols = ",".join(row)
            conn.execute(
                f"INSERT OR REPLACE INTO {table} ({cols}) VALUES ({','.join('?' * len(row))})", tuple(row.values())
            )
            restored += 1
    conn.commit()
    if restored:
        log.info("재처리 후 활동 참조 %d건 복원", restored)
    return restored
