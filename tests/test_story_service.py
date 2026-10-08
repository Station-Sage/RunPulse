"""story_service — 기간 파싱, 월/주 Story 조회, 강도 분포 부족 처리, API 라우트."""
from __future__ import annotations

import sqlite3

import pytest

from src.services import story_period as sp
from src.services import story_service as ss


@pytest.fixture
def conn(tmp_path, monkeypatch):
    from src import db_setup
    from src.utils.db_helpers import upsert_metric

    p = tmp_path / "running.db"
    monkeypatch.setattr(db_setup, "get_db_path", lambda uid=None: p)
    db_setup.init_db()
    c = sqlite3.connect(p)
    rows = [
        ("a1", "2026-09-02T07:00:00", 10000, 3000, 2),
        ("a2", "2026-09-10T07:00:00", 21000, 7000, 4),
        ("a3", "2026-08-12T07:00:00", 8000, 2400, 2),
    ]
    for sid, st, dist, dur, zone in rows:
        c.execute(
            "INSERT INTO activity_summaries (source, source_id, activity_type, start_time,"
            " distance_m, duration_sec) VALUES ('garmin', ?, 'running', ?, ?, ?)",
            (sid, st, dist, dur),
        )
        aid = c.execute("SELECT id FROM activity_summaries WHERE source_id=?", (sid,)).fetchone()[0]
        for z in range(1, 6):
            upsert_metric(c, "activity", str(aid), f"hr_zone_time_{z}", "garmin",
                          numeric_value=float(dur * (0.6 if z == zone else 0.1)))
    c.commit()
    yield c
    c.close()


def test_parse_period():
    assert sp._parse_period("2026-09")["scope"] == "month"
    assert sp._parse_period("2026-W39")["scope"] == "week"
    for bad in ("", "2026-13", "2026-W54", "xx"):
        with pytest.raises(ValueError):
            sp._parse_period(bad)


def test_date_ranges():
    assert sp._month_date_range(2026, 2) == ("2026-02-01", "2026-02-28")
    start, end = sp._week_date_range(2026, 39)
    assert start < end


def test_month_story(conn):
    r = ss.get_story(conn, "2026-09")
    assert r["period"]["id"] == "2026-09" and r["paragraph"]
    assert r["intensity"]["status"] == "ok"
    assert len(r["key_sessions"]) >= 1
    assert r["compare"] is not None


def test_empty_month_does_not_raise(conn):
    r = ss.get_story(conn, "2020-01")
    assert r["period"]["id"] == "2020-01" and r["key_sessions"] == []


def test_intensity_insufficient_without_zones(conn):
    conn.execute("DELETE FROM metric_store WHERE metric_name LIKE 'hr_zone_time_%'")
    conn.commit()
    assert ss.get_story(conn, "2026-09")["intensity"]["status"] == "insufficient"


def test_block_without_active_plan_raises(conn):
    with pytest.raises(ValueError):
        ss.get_story(conn, "b-1-build")


def test_block_dates_follow_phase_weeks(conn, monkeypatch):
    from types import SimpleNamespace as W

    from src.training import goals, planner_config, planner_schedule

    monkeypatch.setattr(goals, "get_active_goal", lambda c: {
        "distance_km": 42.195, "distance_label": "full", "race_date": "2026-11-22", "plan_weeks": 4})
    monkeypatch.setattr(planner_config, "get_vdot_adj", lambda c: 50.0)
    sched = [W(phase="base"), W(phase="build"), W(phase="build"), W(phase="taper")]
    monkeypatch.setattr(planner_schedule, "schedule_for_goal", lambda *a: sched)
    # 대회 주 월요일 11/16 - 3주 = 10/26 시작
    assert sp._get_block_dates(conn, "1", "build") == ("2026-11-02", "2026-11-15")
    with pytest.raises(ValueError):
        sp._get_block_dates(conn, "1", "peak")


def test_route(conn, monkeypatch, tmp_path):
    from flask import Flask

    import src.api.routes_story as rs
    from src.api import api_bp

    monkeypatch.setattr(rs, "db_path", lambda: tmp_path / "running.db")
    monkeypatch.setattr(rs, "get_current_user_id", lambda: "u")
    monkeypatch.setattr(rs, "load_config", lambda user_id=None: {})
    app = Flask(__name__)
    app.register_blueprint(api_bp)
    with app.test_client() as c:
        ok = c.get("/api/v1/library/story/2026-09")
        assert ok.status_code == 200 and ok.get_json()["data"]["period"]["id"] == "2026-09"
        bad = c.get("/api/v1/library/story/zzz")
        assert bad.status_code == 400 and bad.get_json()["error"]["code"] == "INVALID_PERIOD"
