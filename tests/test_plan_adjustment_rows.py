"""plan_adjustment_rows: AUTO_SOURCES 가 v37 live 인덱스 CASE 식과 일치, to_dict signals, live_auto."""
import re
import sqlite3

import pytest

from src.db_setup import create_tables
from src.services import plan_adjustment_rows as rows

D = "2026-10-08"


def _conn():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    c.execute("INSERT INTO planned_workouts(id,date,workout_type,distance_km) VALUES (7,?, 'interval', 10.0)", (D,))
    c.commit()
    return c


def _ins(c, source, decision="proposed"):
    c.execute("INSERT INTO plan_adjustments(workout_id,date,source,op,before_json,after_json,reasons_json,"
              "rule_version,decision) VALUES (7,?,?,'rest','{}','{}','[]','x',?)", (D, source, decision))


def test_auto_sources_match_index_case_expression():
    c = _conn()
    sql = c.execute("SELECT sql FROM sqlite_master WHERE name='ux_plan_adj_live'").fetchone()[0]
    manual = set(re.search(r"source IN \(([^)]*)\)", sql).group(1).replace("'", "").replace(" ", "").split(","))
    assert manual == set(rows.MANUAL_SOURCES)
    assert set(rows.AUTO_SOURCES) | manual == set(rows.SOURCES)


def test_two_live_auto_sources_conflict_and_manual_coexists():
    c = _conn()
    _ins(c, "pain")
    with pytest.raises(sqlite3.IntegrityError):
        _ins(c, "readiness")
    _ins(c, "user", "accepted")


def test_live_auto_and_to_dict_signals():
    c = _conn()
    _ins(c, "readiness", "accepted")
    c.execute("UPDATE plan_adjustments SET signals_json='[{\"signal\":\"crs\"}]'")
    d = rows.live_auto(c, D)
    assert d["source"] == "readiness" and d["signals"] == [{"signal": "crs"}]
    assert rows.get_row(c, d["id"])["id"] == d["id"]
    assert rows.live_auto(c, "2026-01-01") is None
