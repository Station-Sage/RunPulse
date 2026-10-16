"""스키마 v37 — plan_adjustments 재생성: source 11종 CHECK·signals_json·자동 source 묶음 유니크(ADJ-19 a)·crs 재분류."""
from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime

log = logging.getLogger(__name__)

SOURCES = ("pain", "illness", "checkin", "crs", "acwr", "readiness", "race", "travel", "altitude", "user", "coach")
_SRC_SQL = ",".join(f"'{s}'" for s in SOURCES)

_DDL = f"""
CREATE TABLE plan_adjustments_new (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    goal_id      INTEGER,
    workout_id   INTEGER NOT NULL,
    date         TEXT    NOT NULL,
    source       TEXT    NOT NULL CHECK (source IN ({_SRC_SQL})),
    op           TEXT    NOT NULL DEFAULT 'replace'
                         CHECK (op IN ('replace','reduce','rest','skip','move')),
    before_json  TEXT    NOT NULL,
    after_json   TEXT    NOT NULL,
    reasons_json TEXT    NOT NULL DEFAULT '[]',
    signals_json TEXT    NOT NULL DEFAULT '[]',
    rule_version TEXT    NOT NULL,
    decision     TEXT    NOT NULL DEFAULT 'proposed'
                         CHECK (decision IN ('proposed','accepted','reverted')),
    rev          INTEGER NOT NULL DEFAULT 1,
    accepted_at  TEXT,
    decided_at   TEXT,
    decided_via  TEXT CHECK (decided_via IN ('plan','session','today','coach') OR decided_via IS NULL),
    created_at   TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at   TEXT    NOT NULL DEFAULT (datetime('now'))
);
"""

LIVE_INDEX_DDL = (
    "CREATE UNIQUE INDEX IF NOT EXISTS ux_plan_adj_live ON plan_adjustments("
    "workout_id, date, (CASE WHEN source IN ('user','coach') THEN source ELSE 'auto' END)"
    ") WHERE decision IN ('proposed','accepted')"
)
_COLS = ("id, goal_id, workout_id, date, op, before_json, after_json, reasons_json, rule_version,"
         " decision, rev, accepted_at, decided_at, decided_via, created_at, updated_at")


def classify_crs(rule_version: str | None, reasons_json: str | None) -> str:
    """레거시 source='crs' 행의 새 source. 통증 근거면 pain, 그 외(판별 불가 포함)는 readiness(D16)."""
    if rule_version == "pain_v1":
        return "pain"
    try:
        keys = {r.get("key") for r in json.loads(reasons_json or "[]") if isinstance(r, dict)}
    except (ValueError, TypeError):
        keys = set()
    if "readiness" in keys:
        return "readiness"
    return "pain" if "pain" in keys else "readiness"


def _needs_rebuild(conn: sqlite3.Connection) -> bool:
    row = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='plan_adjustments'").fetchone()
    return row is not None and "'illness'" not in row[0]


def _main_db_path(conn: sqlite3.Connection) -> str | None:
    for _, name, path in conn.execute("PRAGMA database_list"):
        if name == "main":
            return path or None
    return None


def _backup(conn: sqlite3.Connection, path: str) -> str:
    dest = f"{path}.bak-v36-{datetime.now():%Y%m%d%H%M%S}"
    dst = sqlite3.connect(dest)
    try:
        conn.backup(dst)
    finally:
        dst.close()
    return dest


def dry_run(conn: sqlite3.Connection) -> dict:
    """쓰기 없이 재분류 분포·묶음 키 live 중복 건수를 보고한다."""
    out = {"rows": 0, "crs_to_pain": 0, "crs_to_readiness": 0, "live_auto_duplicates": 0}
    if not _needs_rebuild(conn):
        return out
    out["rows"] = conn.execute("SELECT COUNT(*) FROM plan_adjustments").fetchone()[0]
    for rv, rj in conn.execute("SELECT rule_version, reasons_json FROM plan_adjustments WHERE source='crs'"):
        out["crs_to_pain" if classify_crs(rv, rj) == "pain" else "crs_to_readiness"] += 1
    out["live_auto_duplicates"] = conn.execute(
        "SELECT COUNT(*) FROM (SELECT 1 FROM plan_adjustments WHERE decision IN ('proposed','accepted')"
        " AND source NOT IN ('user','coach') GROUP BY workout_id, date HAVING COUNT(*) > 1)").fetchone()[0]
    return out


def ensure_v37(conn: sqlite3.Connection) -> None:
    """plan_adjustments 를 복사 재생성한다. 파일 DB 는 백업 + integrity_check 선행, 실패 시 롤백. 멱등."""
    if not _needs_rebuild(conn):
        idx = conn.execute("SELECT sql FROM sqlite_master WHERE name='ux_plan_adj_live'").fetchone()
        if idx is None or "'auto'" not in idx[0]:
            conn.execute("DROP INDEX IF EXISTS ux_plan_adj_live")
            conn.execute(LIVE_INDEX_DDL)
        return
    n_before = conn.execute("SELECT COUNT(*) FROM plan_adjustments").fetchone()[0]
    path = _main_db_path(conn)
    if path and n_before:
        if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("v37 중단: integrity_check 실패")
        log.info("v37 백업: %s", _backup(conn, path))
    conn.execute("SAVEPOINT v37")
    try:
        conn.execute("DROP TABLE IF EXISTS plan_adjustments_new")
        conn.execute(_DDL.strip().rstrip(";"))
        conn.execute(f"INSERT INTO plan_adjustments_new({_COLS}, source) SELECT {_COLS}, source FROM plan_adjustments")
        for rid, rv, rj in conn.execute(
                "SELECT id, rule_version, reasons_json FROM plan_adjustments WHERE source='crs'").fetchall():
            conn.execute("UPDATE plan_adjustments_new SET source=? WHERE id=?", (classify_crs(rv, rj), rid))
        n_after = conn.execute("SELECT COUNT(*) FROM plan_adjustments_new").fetchone()[0]
        if n_after != n_before:
            raise RuntimeError(f"v37 행 수 불일치 {n_before}→{n_after}")
        conn.execute("DROP TABLE plan_adjustments")
        conn.execute("ALTER TABLE plan_adjustments_new RENAME TO plan_adjustments")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_plan_adj_date ON plan_adjustments(date, decision)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_plan_adj_goal ON plan_adjustments(goal_id, date)")
        conn.execute(LIVE_INDEX_DDL)
        conn.execute("RELEASE v37")
    except Exception:
        conn.execute("ROLLBACK TO v37")
        conn.execute("RELEASE v37")
        raise
