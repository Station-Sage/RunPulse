"""능동 인사이트 규칙·사건 수명주기 (V2-REPAIR D1)."""
import sqlite3

import pytest

from src.db_schema_v47 import ensure_v47
from src.services import insight_rules as R
from src.services import insight_service as S

DAY = "2026-11-18"


def sig(name, value, fresh="fresh"):
    return {"signal": name, "role": None, "value": value, "detail": None, "as_of": DAY, "freshness": fresh, "provider": "t"}


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    ensure_v47(c)
    ensure_v47(c)  # 멱등
    return c


def kinds(cands):
    return sorted(c["kind"] for c in cands)


@pytest.mark.parametrize("acwr,expect,sev", [(1.49, [], None), (1.5, ["load_spike"], "watch"), (1.79, ["load_spike"], "watch"),
                                              (1.8, ["load_spike"], "act")])
def test_load_spike_boundaries(acwr, expect, sev):
    c = R.evaluate_signal_rules([sig("acwr", acwr)])
    assert kinds(c) == expect
    if sev:
        assert c[0]["severity"] == sev


def test_recovery_low_needs_two_members():
    assert R.evaluate_signal_rules([sig("crs", 1)]) == []
    c = R.evaluate_signal_rules([sig("crs", 0), sig("checkin_fatigue", 7)])
    assert kinds(c) == ["recovery_low"] and c[0]["severity"] == "act"
    c = R.evaluate_signal_rules([sig("crs", 1), sig("checkin_fatigue", 7)])
    assert c[0]["severity"] == "watch"
    assert R.evaluate_signal_rules([sig("crs", 2), sig("checkin_fatigue", 6)]) == []


def test_missing_signal_ignored():
    assert R.evaluate_signal_rules([sig("acwr", 2.0, "missing")]) == []


def test_pain_flag_hides_illness():
    c = R.evaluate_signal_rules([sig("illness", True)])
    assert kinds(c) == ["pain_flag"] and c[0]["signals"] == [] and "질병" not in c[0]["text"]
    c = R.evaluate_signal_rules([sig("checkin_pain", "moderate")])
    assert c[0]["signals"][0]["signal"] == "checkin_pain"
    assert R.evaluate_signal_rules([sig("checkin_pain", "mild")]) == []


def test_data_gap_boundaries():
    assert R.evaluate_data_gap(DAY, {"garmin": "2026-11-16"}) == []
    assert R.evaluate_data_gap(DAY, {"garmin": None}) == []
    c = R.evaluate_data_gap(DAY, {"garmin": "2026-11-15"})
    assert c[0]["dedupe_key"] == "data_gap:garmin" and c[0]["severity"] == "info"
    assert R.evaluate_data_gap(DAY, {"garmin": "2026-11-11"})[0]["severity"] == "watch"


def test_refresh_dedupes_and_updates(conn):
    S.refresh(conn, DAY, signals=[sig("acwr", 1.6)], last_success={})
    S.refresh(conn, DAY, signals=[sig("acwr", 1.9)], last_success={})
    ev = S.list_events(conn)
    assert len(ev) == 1 and ev[0]["severity"] == "act" and ev[0]["signals"][0]["value"] == 1.9


def test_refresh_resolves_when_cleared(conn):
    S.refresh(conn, DAY, signals=[sig("acwr", 1.6)], last_success={"garmin": "2026-11-10"})
    assert len(S.list_events(conn)) == 2
    S.refresh(conn, DAY, signals=[sig("acwr", 1.0)], last_success={"garmin": DAY})
    assert S.list_events(conn) == []
    assert conn.execute("SELECT COUNT(*) FROM insight_events WHERE state='resolved'").fetchone()[0] == 2


def test_dismiss_suppresses_for_seven_days(conn):
    S.refresh(conn, DAY, signals=[sig("acwr", 1.6)], last_success={})
    eid = S.list_events(conn)[0]["id"]
    assert S.dismiss(conn, eid) and not S.dismiss(conn, eid)
    S.refresh(conn, DAY, signals=[sig("acwr", 1.6)], last_success={})
    assert S.list_events(conn) == []
    conn.execute("UPDATE insight_events SET dismissed_at='2026-11-01 00:00:00'")
    S.refresh(conn, DAY, signals=[sig("acwr", 1.6)], last_success={})
    assert len(S.list_events(conn)) == 1


def test_order_and_seen(conn):
    S.refresh(conn, DAY, signals=[sig("acwr", 1.6), sig("illness", True)], last_success={"garmin": "2026-11-14"})
    ev = S.list_events(conn)
    assert [e["severity"] for e in ev] == ["act", "watch", "info"]
    assert S.mark_seen(conn, ev[0]["id"]) and not S.mark_seen(conn, ev[0]["id"])
    assert len(S.list_events(conn)) == 3


def test_rule_failure_keeps_open_events(conn):
    S.refresh(conn, DAY, signals=[sig("acwr", 1.6)], last_success={})

    def boom():
        raise RuntimeError("x")
    S.refresh(conn, DAY, signals=None, last_success={}) if False else None
    import src.services.insight_service as m
    orig = m.insight_rules.evaluate_signal_rules
    m.insight_rules.evaluate_signal_rules = lambda s: (_ for _ in ()).throw(RuntimeError("x"))
    try:
        S.refresh(conn, DAY, signals=[], last_success={})
    finally:
        m.insight_rules.evaluate_signal_rules = orig
    assert len(S.list_events(conn)) == 1
