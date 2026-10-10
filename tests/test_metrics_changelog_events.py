import sqlite3

from src.services.metrics_changelog_events import changelog_events, recompute_caption, version_events


def _conn(rows, slug="ctl", milestone=None):
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.executescript(
        """CREATE TABLE metric_store (id INTEGER PRIMARY KEY, scope_type TEXT, scope_id TEXT, metric_name TEXT,
        numeric_value REAL, is_primary INTEGER DEFAULT 1, provider TEXT, algorithm_version TEXT);
        CREATE TABLE milestones (id INTEGER PRIMARY KEY, type TEXT, date TEXT, metric_name TEXT);"""
    )
    for d, prov, ver in rows:
        c.execute("INSERT INTO metric_store (scope_type, scope_id, metric_name, numeric_value, provider, algorithm_version)"
                  " VALUES ('daily', ?, ?, 50, ?, ?)", (d, slug, prov, ver))
    if milestone:
        c.execute("INSERT INTO milestones (type, date, metric_name) VALUES ('algo_recompute', ?, ?)", (milestone, slug))
    return c


RP = "runpulse:formula_v1"
SPAN = [("2026-09-20", RP, "2.0"), ("2026-10-05", RP, "2.0")]


def test_direct_and_propagated_merge_into_one_event():
    ev = changelog_events(_conn(SPAN), "ctl", "2026-09-20", "2026-10-05")
    assert len(ev) == 1 and ev[0]["date"] == "2026-09-28" and ev[0]["source"] == "changelog" and ev[0]["recomputed"]
    assert "체력·피로" in ev[0]["reason"] and "입력 지표" in ev[0]["reason"]


def test_propagation_only_reports_via():
    ev = changelog_events(_conn(SPAN, "atl"), "atl", "2026-09-20", "2026-10-05")
    assert len(ev) == 1 and "입력 지표" in ev[0]["reason"]
    trimp = changelog_events(_conn(SPAN, "trimp"), "trimp", "2026-09-20", "2026-10-05")
    assert trimp[0]["from"] == "banister_1991" and "via" not in trimp[0]


def test_out_of_range_and_unrelated_metric_excluded():
    assert changelog_events(_conn(SPAN), "ctl", "2026-10-01", "2026-10-05") == []
    assert changelog_events(_conn(SPAN, "hrv"), "hrv", "2026-09-20", "2026-10-05") == []


def test_source_provider_series_excluded():
    rows = [("2026-09-20", "intervals", "1.0"), ("2026-10-05", "intervals", "1.0")]
    assert changelog_events(_conn(rows), "ctl", "2026-09-20", "2026-10-05") == []


def test_new_calculator_has_no_marker():
    assert changelog_events(_conn([("2026-10-01", RP, "trimp_est_v1"), ("2026-10-09", RP, "trimp_est_v1")], "trimp_est"),
                            "trimp_est", "2026-10-01", "2026-10-09") == []


def test_data_event_merged_with_changelog_reason():
    ev = version_events(_conn([("2026-09-25", RP, "banister_1991"), ("2026-09-30", RP, "banister_1991_v2")], "trimp"),
                        "trimp", "2026-09-25", "2026-09-30")
    assert len(ev) == 1 and ev[0]["date"] == "2026-09-30" and ev[0]["source"] == "data" and ev[0]["recomputed"] is False
    assert "심박" in ev[0]["reason"]


def test_provider_switch_event_kept():
    ev = version_events(_conn([("2026-09-25", "intervals", "1.0"), ("2026-09-26", RP, "2.0")]), "ctl", "2026-09-25", "2026-09-26")
    assert len(ev) == 1 and ev[0]["label"].startswith("출처 변경")


def test_caption_uses_changelog_reason_then_milestone_fallback():
    n = recompute_caption(_conn(SPAN), "ctl", "2026-09-20", "2026-10-05")
    assert n and n["text"].startswith("9/28부터") and "다시 계산" in n["text"] and "—" in n["text"]
    rows = [("2026-10-01", RP, "2.0"), ("2026-10-05", RP, "2.0")]
    n2 = recompute_caption(_conn(rows, milestone="2026-10-06"), "ctl", "2026-10-01", "2026-10-05")
    assert n2 and n2["text"].startswith("10/6부터 계산 v2.0")
