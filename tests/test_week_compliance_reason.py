"""R3 — 준수 사유(reason/reasons)·actual_km/actual_pace·유효 행 우선순위(PLN-10)."""
from __future__ import annotations

from datetime import date

from tests.test_week_compliance import MON, TODAY, _act, _day, _plan, conn  # noqa: F401
from src.training import week_compliance as wc


def _compute(conn, end="2026-09-27"):
    return wc.compute(conn, MON, date.fromisoformat(end), MON, TODAY)


def test_volume_over_is_representative_and_pace_fast_secondary(conn):
    a = _act(conn, "2026-09-22", 12.0, pace=300.0)
    _plan(conn, "2026-09-22", "easy", 8.0, act_id=a, pace_min=360)
    d = _day(_compute(conn), "2026-09-22")
    assert d["reason"] == "volume_over" and d["reasons"] == ["volume_over", "pace_fast"]
    assert d["actual_km"] == 12.0 and d["actual_pace"] == 300.0


def test_volume_under(conn):
    a = _act(conn, "2026-09-22", 4.0)
    _plan(conn, "2026-09-22", "easy", 8.0, act_id=a)
    assert _day(_compute(conn), "2026-09-22")["reason"] == "volume_under"


def test_no_activity_reason_on_past_unmatched(conn):
    _plan(conn, "2026-09-22", "easy", 8.0)
    d = _day(_compute(conn), "2026-09-22")
    assert d["reasons"] == ["no_activity"] and "actual_km" not in d


def test_on_target_has_no_reason(conn):
    a = _act(conn, "2026-09-22", 8.0)
    _plan(conn, "2026-09-22", "easy", 8.0, act_id=a)
    assert "reason" not in _day(_compute(conn), "2026-09-22")


def test_matched_planner_beats_unmatched_external(conn):
    a = _act(conn, "2026-09-23", 8.0)
    _plan(conn, "2026-09-23", "easy", 8.0, act_id=a)
    _plan(conn, "2026-09-23", "easy", 10.0, source="garmin")
    assert _day(_compute(conn), "2026-09-23")["effective"]["source"] == "planner"


def test_accepted_adjustment_beats_unmatched_external():
    rows = [{"id": 1, "source": "garmin", "matched_activity_id": None},
            {"id": 2, "source": "planner", "matched_activity_id": None, "adjusted": True},
            {"id": 3, "source": "planner", "matched_activity_id": None}]
    assert wc._effective(rows)[0]["id"] == 2
