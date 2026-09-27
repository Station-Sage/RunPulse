"""tests/test_provider_status_service.py — get_provider_coverage 단위 테스트."""
from __future__ import annotations

import sqlite3

import pytest

from src.db_setup import create_tables, migrate_db
from src.services.provider_status_service import get_provider_coverage


@pytest.fixture
def coverage_conn(tmp_path):
    db_file = tmp_path / "running.db"
    conn = sqlite3.connect(str(db_file))
    create_tables(conn)
    migrate_db(conn)
    conn.executemany(
        "INSERT INTO activity_summaries"
        " (source, source_id, name, activity_type, start_time, distance_m, duration_sec)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            ("garmin", "g1", "Run A", "running", "2023-10-05T08:00:00Z", 5000, 1800),
            ("garmin", "g2", "Run B", "running", "2023-12-10T08:00:00Z", 5000, 1800),
            ("garmin", "g3", "Run C", "running", "2023-12-20T08:00:00Z", 5000, 1800),
            ("strava", "s1", "Run D", "running", "2024-01-07T08:00:00Z", 5000, 1800),
        ],
    )
    conn.commit()
    yield conn
    conn.close()


def test_months_range(coverage_conn):
    result = get_provider_coverage(coverage_conn, start_month="2023-10", today="2024-01-15")
    assert result["months"] == ["2023-10", "2023-11", "2023-12", "2024-01"]


def test_garmin_counts(coverage_conn):
    result = get_provider_coverage(coverage_conn, start_month="2023-10", today="2024-01-15")
    providers = {p["provider"]: p for p in result["providers"]}
    assert providers["garmin"]["counts"] == [1, 0, 2, 0]
    assert providers["garmin"]["total"] == 3


def test_strava_counts(coverage_conn):
    result = get_provider_coverage(coverage_conn, start_month="2023-10", today="2024-01-15")
    providers = {p["provider"]: p for p in result["providers"]}
    assert providers["strava"]["counts"] == [0, 0, 0, 1]
    assert providers["strava"]["total"] == 1


def test_intervals_runalyze_all_zero(coverage_conn):
    result = get_provider_coverage(coverage_conn, start_month="2023-10", today="2024-01-15")
    providers = {p["provider"]: p for p in result["providers"]}
    assert providers["intervals"]["total"] == 0
    assert all(c == 0 for c in providers["intervals"]["counts"])
    assert providers["runalyze"]["total"] == 0
    assert all(c == 0 for c in providers["runalyze"]["counts"])


def test_providers_length_always_four(coverage_conn):
    result = get_provider_coverage(coverage_conn, start_month="2023-10", today="2024-01-15")
    assert len(result["providers"]) == 4


def test_months_first(coverage_conn):
    result = get_provider_coverage(coverage_conn, start_month="2023-10", today="2024-01-15")
    assert result["months"][0] == "2023-10"


def test_empty_db_returns_all_zeros(tmp_path):
    db_file = tmp_path / "empty.db"
    conn = sqlite3.connect(str(db_file))
    create_tables(conn)
    migrate_db(conn)
    result = get_provider_coverage(conn, start_month="2024-01", today="2024-03-01")
    assert result["months"] == ["2024-01", "2024-02", "2024-03"]
    for p in result["providers"]:
        assert p["total"] == 0
        assert all(c == 0 for c in p["counts"])
    conn.close()


def test_enabled_sources_default_and_filter():
    from src.utils.config import enabled_sources
    assert enabled_sources({}) == ["garmin", "strava", "intervals", "runalyze"]
    assert enabled_sources({"sync_sources": ["intervals", "garmin"]}) == ["garmin", "intervals"]


def test_coverage_marks_disabled_sources(coverage_conn):
    r = get_provider_coverage(coverage_conn, start_month="2023-10", today="2024-01-15",
                              config={"sync_sources": ["garmin", "intervals"]})
    on = {p["provider"]: p["sync_enabled"] for p in r["providers"]}
    assert on == {"garmin": True, "strava": False, "intervals": True, "runalyze": False}


def test_start_basic_sync_skips_disabled(monkeypatch):
    from src.web import bg_sync
    started = []
    monkeypatch.setattr(bg_sync, "start_job", lambda svc, *a, **k: started.append(svc) or f"job-{svc}")
    out = bg_sync.start_basic_sync(["garmin", "strava", "runalyze"], {}, "2026-09-27",
                                   {"sync_sources": ["garmin"]}, "u")
    assert started == ["garmin"] and list(out) == ["garmin"]


def test_set_sync_source_toggles_and_keeps_order():
    from src.utils.config import set_sync_source
    cfg = {"sync_sources": ["garmin", "intervals"]}
    assert set_sync_source(cfg, "strava", True) == ["garmin", "strava", "intervals"]
    assert set_sync_source(cfg, "garmin", False) == ["strava", "intervals"]
    assert set_sync_source({}, "runalyze", False) == ["garmin", "strava", "intervals"]     # 키 없으면 전부 켜짐에서 시작


def test_sync_page_widgets_reflect_sources():
    from src.web.sync_ui import _source_checkboxes
    from src.web.views_sync import _sync_sources_html
    html = _source_checkboxes("basic", {"garmin", "strava"}, off={"strava"})
    assert "Strava (꺼짐)" in html and "id='basic-chk-strava'" in html and "disabled" in html
    card = _sync_sources_html({"garmin"}, {"garmin", "strava"})
    assert "name='src_garmin' value='1' checked" in card and "name='src_strava' value='1' " in card
    assert card.count("checked") == 1 and "(미연결)" in card


def test_sync_sources_post_saves_checked_only(monkeypatch):
    from flask import Flask
    import src.web.views_sync as vs
    saved = {}
    monkeypatch.setattr(vs, "load_config", lambda **k: {"garmin": {}})
    monkeypatch.setattr(vs, "save_config", lambda c: saved.update(c))
    monkeypatch.setattr("src.web.helpers.get_current_user_id", lambda: "u")
    app = Flask(__name__)
    app.register_blueprint(vs.sync_bp)
    r = app.test_client().post("/sync/sources", data={"src_garmin": "1", "src_runalyze": "1"})
    assert r.status_code == 302 and saved["sync_sources"] == ["garmin", "runalyze"]
