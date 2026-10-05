import json
import sqlite3

from src.services.metrics_basis_events import basis_change_events, load_json


def _conn(anchors):
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.executescript(
        """CREATE TABLE metric_store (id INTEGER PRIMARY KEY, scope_type TEXT, scope_id TEXT, metric_name TEXT,
        category TEXT, numeric_value REAL, text_value TEXT, json_value TEXT, source TEXT, is_primary INTEGER DEFAULT 1,
        provider TEXT DEFAULT 'runpulse', algorithm_version TEXT DEFAULT '1', confidence REAL, created_at TEXT, updated_at TEXT);
        CREATE TABLE v_canonical_activities (id INTEGER, distance_m REAL);
        INSERT INTO v_canonical_activities VALUES (7, 10000), (9, 21097);"""
    )
    for d, a in anchors:
        js = json.dumps({"anchor": a}) if a is not None else None
        c.execute(
            "INSERT INTO metric_store (scope_type, scope_id, metric_name, numeric_value, json_value, is_primary) "
            "VALUES ('daily', ?, 'race_pred_vdot', 50, ?, 1)", (d, js))
    return c


def test_id_change_gives_one_event():
    c = _conn([("2026-05-01", {"activity_id": 7, "date": "2026-04-01"}),
               ("2026-05-02", {"activity_id": 7, "date": "2026-04-01"}),
               ("2026-05-03", {"activity_id": 9, "date": "2026-05-02"})])
    ev = basis_change_events(c, "race_pred_marathon_sec", "2026-05-01", "2026-05-03")
    assert len(ev) == 1 and ev[0]["date"] == "2026-05-03" and ev[0]["kind"] == "basis_change"
    assert ev[0]["label"] == "기준 대회 변경: 하프 2026-05-02"


def test_no_change_and_missing_key_and_other_slug():
    same = _conn([("2026-05-01", {"activity_id": 7}), ("2026-05-02", {"activity_id": 7})])
    assert basis_change_events(same, "race_pred_10k_sec", "2026-05-01", "2026-05-02") == []
    miss = _conn([("2026-05-01", {"activity_id": 7}), ("2026-05-02", None), ("2026-05-03", {"activity_id": 7})])
    assert basis_change_events(miss, "race_pred_10k_sec", "2026-05-01", "2026-05-03") == []
    assert basis_change_events(same, "ctl", "2026-05-01", "2026-05-02") == []


def test_load_json_tolerates_bad_input():
    assert load_json(None) == {} and load_json({"json_value": "{x"}) == {}
