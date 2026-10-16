"""스키마 v37 — plan_adjustments 재생성(source 11종·signals_json·묶음 유니크·crs 재분류)."""
import json
import sqlite3

import pytest

from src import db_schema_v37 as v37
from src.db_schema_v37 import classify_crs, dry_run, ensure_v37

_OLD = """
CREATE TABLE plan_adjustments (
    id INTEGER PRIMARY KEY AUTOINCREMENT, goal_id INTEGER, workout_id INTEGER NOT NULL, date TEXT NOT NULL,
    source TEXT NOT NULL CHECK (source IN ('crs','user','coach')),
    op TEXT NOT NULL DEFAULT 'replace' CHECK (op IN ('replace','reduce','rest','skip','move')),
    before_json TEXT NOT NULL, after_json TEXT NOT NULL, reasons_json TEXT NOT NULL DEFAULT '[]',
    rule_version TEXT NOT NULL,
    decision TEXT NOT NULL DEFAULT 'proposed' CHECK (decision IN ('proposed','accepted','reverted')),
    rev INTEGER NOT NULL DEFAULT 1, accepted_at TEXT, decided_at TEXT,
    decided_via TEXT CHECK (decided_via IN ('plan','session','today','coach') OR decided_via IS NULL),
    created_at TEXT NOT NULL DEFAULT (datetime('now')), updated_at TEXT NOT NULL DEFAULT (datetime('now')));
CREATE UNIQUE INDEX ux_plan_adj_live ON plan_adjustments(workout_id, date, source)
    WHERE decision IN ('proposed','accepted');
"""


def _old_db(path=":memory:"):
    c = sqlite3.connect(path)
    c.executescript(_OLD)
    return c


def _ins(c, wid, src="crs", rv="adjuster_v1", reasons="[]", decision="proposed", date="2026-10-01"):
    c.execute("INSERT INTO plan_adjustments(workout_id,date,source,before_json,after_json,reasons_json,rule_version,decision)"
              " VALUES (?,?,?,'{}','{}',?,?,?)", (wid, date, src, reasons, rv, decision))


def test_classify_crs():
    assert classify_crs("pain_v1", "[]") == "pain"
    assert classify_crs("adjuster_v1", json.dumps([{"key": "readiness"}])) == "readiness"
    assert classify_crs("adjuster_v1", json.dumps([{"key": "pain"}])) == "pain"
    assert classify_crs("adjuster_v1", "[]") == "readiness"
    assert classify_crs("adjuster_v1", "not json") == "readiness"


def test_rebuild_reclassifies_and_keeps_rows():
    c = _old_db()
    _ins(c, 1, rv="pain_v1")
    _ins(c, 2)
    _ins(c, 3, src="user")
    ensure_v37(c)
    rows = dict(c.execute("SELECT id, source FROM plan_adjustments"))
    assert rows == {1: "pain", 2: "readiness", 3: "user"}
    assert c.execute("SELECT signals_json FROM plan_adjustments WHERE id=1").fetchone()[0] == "[]"
    assert c.execute("SELECT COUNT(*) FROM plan_adjustments WHERE source='crs'").fetchone()[0] == 0


def test_idempotent_and_new_sources_allowed():
    c = _old_db()
    ensure_v37(c)
    ensure_v37(c)
    _ins(c, 1, src="illness")
    with pytest.raises(sqlite3.IntegrityError):
        _ins(c, 2, src="bogus")


def test_grouped_unique_index():
    c = _old_db()
    ensure_v37(c)
    _ins(c, 1, src="pain")
    with pytest.raises(sqlite3.IntegrityError):
        _ins(c, 1, src="acwr")
    _ins(c, 1, src="user")
    _ins(c, 1, src="coach")
    _ins(c, 1, src="acwr", decision="reverted")


def test_duplicate_live_rolls_back_and_dry_run_reports():
    c = _old_db()
    _ins(c, 1)
    c.execute("DROP INDEX ux_plan_adj_live")
    _ins(c, 1, src="crs")
    assert dry_run(c)["live_auto_duplicates"] == 1
    with pytest.raises(sqlite3.IntegrityError):
        ensure_v37(c)
    assert c.execute("SELECT COUNT(*) FROM plan_adjustments").fetchone()[0] == 2
    assert c.execute("SELECT 1 FROM sqlite_master WHERE name='plan_adjustments_new'").fetchone() is None
    assert "'illness'" not in c.execute("SELECT sql FROM sqlite_master WHERE name='plan_adjustments'").fetchone()[0]


def test_dry_run_distribution_no_write():
    c = _old_db()
    _ins(c, 1, rv="pain_v1")
    _ins(c, 2)
    r = dry_run(c)
    assert (r["rows"], r["crs_to_pain"], r["crs_to_readiness"]) == (2, 1, 1)
    assert c.execute("SELECT COUNT(*) FROM plan_adjustments WHERE source='crs'").fetchone()[0] == 2


def test_file_db_backup(tmp_path):
    p = str(tmp_path / "running.db")
    c = _old_db(p)
    _ins(c, 1)
    c.commit()
    ensure_v37(c)
    assert list(tmp_path.glob("running.db.bak-v36-*"))
    assert v37.SOURCES[-1] == "coach"
