import sqlite3

from src.services.metrics_version_events import recompute_note, version_change_events


def _conn(rows, milestone=None):
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.executescript(
        """CREATE TABLE metric_store (id INTEGER PRIMARY KEY, scope_type TEXT, scope_id TEXT, metric_name TEXT,
        numeric_value REAL, is_primary INTEGER DEFAULT 1, provider TEXT, algorithm_version TEXT);
        CREATE TABLE milestones (id INTEGER PRIMARY KEY, type TEXT, date TEXT, metric_name TEXT);"""
    )
    for d, prov, ver in rows:
        c.execute("INSERT INTO metric_store (scope_type, scope_id, metric_name, numeric_value, provider, algorithm_version)"
                  " VALUES ('daily', ?, 'ctl', 50, ?, ?)", (d, prov, ver))
    if milestone:
        c.execute("INSERT INTO milestones (type, date, metric_name) VALUES ('algo_recompute', ?, 'ctl')", (milestone,))
    return c


def test_mixed_versions_give_one_event():
    c = _conn([("2026-09-24", "runpulse:formula_v1", "1.0"), ("2026-09-25", "runpulse:formula_v1", "1.0"),
               ("2026-09-26", "runpulse:formula_v1", "2.0")])
    ev = version_change_events(c, "ctl", "2026-09-24", "2026-09-26")
    assert [(e["date"], e["label"]) for e in ev] == [("2026-09-26", "계산 방식 변경: v1.0→v2.0")]


def test_provider_switch_gives_one_event():
    c = _conn([("2026-09-24", "intervals", "1.0"), ("2026-09-25", "runpulse:formula_v1", "1.0")])
    ev = version_change_events(c, "ctl", "2026-09-24", "2026-09-25")
    assert len(ev) == 1 and ev[0]["label"] == "출처 변경: Intervals→RunPulse"


def test_single_version_and_no_data():
    c = _conn([("2026-09-24", "runpulse:formula_v1", "2.0"), ("2026-09-25", "runpulse:formula_v1", "2.0")])
    assert version_change_events(c, "ctl", "2026-09-24", "2026-09-25") == []
    assert version_change_events(c, "none", "2026-09-24", "2026-09-25") == []


def test_recompute_note_present_and_absent():
    rows = [("2026-09-24", "runpulse:formula_v1", "2.0"), ("2026-09-25", "runpulse:formula_v1", "2.0")]
    n = recompute_note(_conn(rows, "2026-09-26"), "ctl", "2026-09-24", "2026-09-25")
    assert n and n["text"].startswith("9/26부터 계산 v2.0")
    assert recompute_note(_conn(rows), "ctl", "2026-09-24", "2026-09-25") is None
    mixed = [("2026-09-24", "runpulse:formula_v1", "1.0"), ("2026-09-25", "runpulse:formula_v1", "2.0")]
    assert recompute_note(_conn(mixed, "2026-09-26"), "ctl", "2026-09-24", "2026-09-25") is None
