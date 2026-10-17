"""plan_adjustments 행 읽기 공통부 — 컬럼 목록·dict 변환·live 조회·자동 source 집합 (ADR-035)."""
from __future__ import annotations

import json
import sqlite3

from src.db_schema_v37 import SOURCES  # noqa: F401

COLS = ("id, goal_id, workout_id, date, source, op, before_json, after_json, reasons_json, signals_json,"
        " rule_version, decision, rev, accepted_at, decided_at, decided_via, created_at, updated_at")
MANUAL_SOURCES = ("user", "coach")
AUTO_SOURCES = tuple(s for s in SOURCES if s not in MANUAL_SOURCES)
AUTO_SQL = ",".join(f"'{s}'" for s in AUTO_SOURCES)


def to_dict(r: tuple) -> dict:
    keys = [c.strip() for c in COLS.split(",")]
    d = dict(zip(keys, r))
    for k, default in (("before", "{}"), ("after", "{}"), ("reasons", "[]"), ("signals", "[]")):
        d[k] = json.loads(d.pop(f"{k}_json") or default)
    return d


def get_row(conn: sqlite3.Connection, adj_id: int) -> dict | None:
    r = conn.execute(f"SELECT {COLS} FROM plan_adjustments WHERE id = ?", (adj_id,)).fetchone()
    return to_dict(r) if r else None


def live_auto(conn: sqlite3.Connection, date: str) -> dict | None:
    """해당 날짜의 자동(비수동) 조정 중 accepted 우선 최신 1건."""
    r = conn.execute(f"SELECT {COLS} FROM plan_adjustments WHERE date = ? AND source IN ({AUTO_SQL})"
                     " ORDER BY (decision = 'accepted') DESC, id DESC LIMIT 1", (date,)).fetchone()
    return to_dict(r) if r else None
