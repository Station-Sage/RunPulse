"""BOOST 보류(ADR-050 F4) — adjuster boost_hold 주입, todays_adjustment_with_hold, Hero hold_reason."""
from __future__ import annotations

import re
import sqlite3
from datetime import date
from pathlib import Path

import pytest

from src.db_setup import create_tables, migrate_db
from src.services import plan_service
from src.training.adjuster import RULE_VERSION, adjust_todays_plan

TODAY = date.today().isoformat()
HOLD = {"hold": True, "reasons": [{"code": "crs_stale", "params": {}, "text": "x"}]}
FREE = {"hold": False, "reasons": []}


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    migrate_db(c)
    c.execute("INSERT INTO planned_workouts (date, workout_type, distance_km, completed, source)"
              " VALUES (?, 'easy', 10.0, 0, 'planner')", (TODAY,))
    c.execute("INSERT INTO daily_wellness (date, body_battery_high, sleep_score) VALUES (?, 90, 85)", (TODAY,))
    c.execute("INSERT INTO metric_store (scope_type, scope_id, metric_name, provider, numeric_value, is_primary)"
              " VALUES ('daily', ?, 'tsb', 'runpulse', 15, 1)", (TODAY,))
    c.commit()
    yield c
    c.close()


def test_boost_allowed_without_hold(conn):
    r = adjust_todays_plan(conn, date=TODAY)
    assert r["volume_boost"] is True and r["boost_held"] is False and r["hold_reason"] is None
    assert r["rule_version"] == RULE_VERSION == "adjuster_v2"


def test_boost_allowed_when_hold_false(conn):
    r = adjust_todays_plan(conn, date=TODAY, boost_hold=FREE)
    assert r["volume_boost"] is True and r["boost_held"] is False


def test_boost_held(conn):
    r = adjust_todays_plan(conn, date=TODAY, boost_hold=HOLD)
    assert r["volume_boost"] is False and r["boost_held"] is True
    assert r["hold_reason"] == HOLD["reasons"]


def test_hold_irrelevant_when_no_boost_condition(conn):
    conn.execute("UPDATE metric_store SET numeric_value=5 WHERE metric_name='tsb'")  # 경계: TSB 10 이하
    r = adjust_todays_plan(conn, date=TODAY, boost_hold=HOLD)
    assert r["volume_boost"] is False and r["boost_held"] is False and r["hold_reason"] is None


def test_wrapper_holds_without_crs(conn):
    r = plan_service.todays_adjustment_with_hold(conn, TODAY)
    assert r["volume_boost"] is False and r["boost_held"] is True
    assert r["hold_reason"]


def test_wrapper_holds_on_hold_error(conn, monkeypatch):
    import src.services.metric_freshness as mf
    monkeypatch.setattr(mf, "crs_boost_hold", lambda c, d: (_ for _ in ()).throw(RuntimeError("x")))
    assert plan_service.todays_adjustment_with_hold(conn, TODAY)["boost_held"] is True


def test_wrapper_releases(conn, monkeypatch):
    import src.services.metric_freshness as mf
    monkeypatch.setattr(mf, "crs_boost_hold", lambda c, d: FREE)
    r = plan_service.todays_adjustment_with_hold(conn, TODAY)
    assert r["volume_boost"] is True and r["boost_held"] is False


def test_hero_held_is_as_planned_with_reason(conn, monkeypatch):
    from src.services import today_hero
    monkeypatch.setattr(today_hero, "todays_adjustment_with_hold",
                        lambda c, d: adjust_todays_plan(c, date=d, boost_hold=HOLD))
    monkeypatch.setattr(today_hero, "race_days_left", lambda c, d: None)
    monkeypatch.setattr(today_hero, "_has_active_goal", lambda c: True)
    week = {"days": [{"date": TODAY, "state": "upcoming", "workout_type": "easy", "session_id": 1,
                      "title": "t", "planned_km": 10}]}
    out = today_hero.build_briefing_state(conn, TODAY, week)
    assert out["verdict"] == "as_planned" and out["hold_reason"] == HOLD["reasons"]


def test_no_direct_adjust_todays_plan_calls():
    """호출부는 plan_service.todays_adjustment_with_hold 를 거쳐야 한다 (보류 판정 누락 방지)."""
    root = Path(__file__).resolve().parent.parent / "src"
    allowed = {"training/adjuster.py", "services/plan_service.py"}
    pat = re.compile(r"\badjust_todays_plan\s*\(")
    bad = [str(p.relative_to(root)) for p in root.rglob("*.py")
           if str(p.relative_to(root)) not in allowed
           and any(pat.search(l) and not l.lstrip().startswith(("#", '"""')) for l in p.read_text().splitlines())]
    assert bad == []
