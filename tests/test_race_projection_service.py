"""tests/test_race_projection_service.py — 레이스 아침 폼 예측."""
from __future__ import annotations

from src.services.race_projection_service import (
    _taper_factor,
    project_race_form,
)

DATE = "2026-09-24"


def _metric(c, scope_type, scope_id, name, value):
    c.execute(
        "INSERT INTO metric_store (scope_type, scope_id, metric_name, category, provider,"
        " numeric_value, is_primary) VALUES (?, ?, ?, 'load', 'runpulse:formula_v1', ?, 1)",
        (scope_type, str(scope_id), name, value),
    )


def _activity(c, act_id, start_date):
    c.execute(
        "INSERT INTO activity_summaries (id, source, source_id, activity_type, start_time, distance_m)"
        " VALUES (?, 'garmin', ?, 'running', ?, 10000)",
        (act_id, f"g{act_id}", f"{start_date}T07:00:00"),
    )


def test_taper_factor_bands():
    assert _taper_factor(20) == 1.0
    assert _taper_factor(14) == 0.75
    assert _taper_factor(8) == 0.75
    assert _taper_factor(7) == 0.55
    assert _taper_factor(4) == 0.55
    assert _taper_factor(3) == 0.35
    assert _taper_factor(1) == 0.35


def test_none_without_ctl_atl(db_conn):
    assert project_race_form(db_conn, "2026-10-25", DATE) is None


def test_none_when_race_past_today_or_too_far(db_conn):
    _metric(db_conn, "daily", DATE, "ctl", 40)
    _metric(db_conn, "daily", DATE, "atl", 50)
    assert project_race_form(db_conn, DATE, DATE) is None
    assert project_race_form(db_conn, "2026-09-01", DATE) is None
    assert project_race_form(db_conn, "2027-06-01", DATE) is None


def test_taper_gives_higher_tsb_than_keep(db_conn):
    _metric(db_conn, "daily", DATE, "ctl", 40)
    _metric(db_conn, "daily", DATE, "atl", 60)
    for i, d in enumerate(["2026-09-20", "2026-09-22", "2026-09-24"]):
        _activity(db_conn, 100 + i, d)
        _metric(db_conn, "activity", 100 + i, "trimp", 120)
    r = project_race_form(db_conn, "2026-10-25", DATE)
    assert r["days_left"] == 31
    assert r["base_daily_load"] == round(360 / 28, 1)
    taper, keep = r["scenarios"]
    assert taper["key"] == "taper" and keep["key"] == "keep"
    assert taper["tsb"] > keep["tsb"]
    assert len(taper["series"]) == 30  # 내일~레이스 전날
    assert r["current"]["tsb"] == -20.0


def test_zero_load_decays_toward_positive_tsb(db_conn):
    _metric(db_conn, "daily", DATE, "ctl", 40)
    _metric(db_conn, "daily", DATE, "atl", 60)
    r = project_race_form(db_conn, "2026-10-01", DATE)
    assert r["base_daily_load"] == 0
    # 부하 0: ATL이 CTL보다 빨리 감쇠 → TSB 상승
    assert r["scenarios"][0]["tsb"] > r["current"]["tsb"]


def test_scenarios_have_ctl_change_pct(db_conn):
    _metric(db_conn, "daily", DATE, "ctl", 40)
    _metric(db_conn, "daily", DATE, "atl", 50)
    out = project_race_form(db_conn, "2026-10-25", DATE)
    for sc in out["scenarios"]:
        assert sc["ctl_change_pct"] == round((sc["ctl"] - 40) / 40 * 100, 1)
        assert sc["status"]
