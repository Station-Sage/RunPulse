"""adjuster_v3 제안·signals_json 저장·rev 규칙 (ADR-035 개정)."""
import sqlite3

from src.db_setup import create_tables
from src.services import adjuster_v3, plan_adjustment_proposal as prop
from src.services import plan_adjustment_service as svc
from src.services.user_settings_service import set_setting

D = "2026-10-08"
HOLD = {"hold": False, "reasons": []}


def _conn(wtype="interval", acwr=1.9, fatigue=8):
    c = sqlite3.connect(":memory:")
    create_tables(c)
    c.execute("INSERT INTO planned_workouts(id,date,workout_type,distance_km) VALUES (7,?,?,10.0)", (D, wtype))
    if acwr is not None:
        c.execute("INSERT INTO metric_store(scope_type,scope_id,metric_name,numeric_value,is_primary,provider)"
                  " VALUES ('daily',?,'acwr',?,1,'runpulse:formula_v1')", (D, acwr))
    if fatigue is not None:
        c.execute("INSERT INTO user_inputs(input_date,input_type,fatigue,pain) VALUES (?, 'checkin', ?, 'none')", (D, fatigue))
    c.commit()
    return c


def _crs(monkeypatch, level):
    monkeypatch.setattr("src.metrics.crs.evaluate", lambda conn, day: {"level": level, "level_label": "x", "crs": 30.0})


def test_and_trigger_proposes_replace_with_signals(monkeypatch):
    _crs(monkeypatch, 1)
    c = _conn()
    w, sig = adjuster_v3.propose(c, D, HOLD)
    assert w["adjusted_type"] == "easy" and w["source"] == "checkin" and w["rule_version"] == "adjuster_v3"
    assert {s["signal"] for s in sig if s["role"] == "trigger"} == {"crs", "acwr", "checkin_fatigue"}


def test_single_signal_does_not_trigger(monkeypatch):
    _crs(monkeypatch, 3)
    c = _conn(fatigue=3)
    w, _ = adjuster_v3.propose(c, D, HOLD)
    assert w is None or w["source"] == "readiness"


def test_rest_and_race_rows_excluded(monkeypatch):
    _crs(monkeypatch, 1)
    for t in ("rest", "race"):
        assert adjuster_v3.propose(_conn(t), D, HOLD) == (None, [])


def test_ensure_proposal_v3_stores_signals_and_rev_rule(monkeypatch):
    _crs(monkeypatch, 1)
    c = _conn()
    set_setting(c, "adjuster_version", "v3")
    a = svc.ensure_proposal(c, D, today=D)
    assert a["source"] == "checkin"
    assert a["rule_version"] == "adjuster_v3" and len(a["signals"]) >= 3
    c.execute("UPDATE metric_store SET numeric_value=1.95 WHERE metric_name='acwr'")
    c.commit()
    b = svc.ensure_proposal(c, D, today=D)
    assert b["id"] == a["id"] and b["rev"] == a["rev"]
    assert [s for s in b["signals"] if s["signal"] == "acwr"][0]["value"] == 1.95
    c.execute("UPDATE metric_store SET numeric_value=1.0 WHERE metric_name='acwr'")
    c.commit()
    d = svc.ensure_proposal(c, D, today=D)
    assert d["id"] == a["id"] and d["rev"] == a["rev"] + 1


def test_default_version_is_v2(monkeypatch):
    c = _conn()
    monkeypatch.setattr(prop, "todays_adjustment_with_hold", lambda conn, date=None: None)
    assert prop._propose(c, D) == (None, None)


def test_get_day_adjustment_exposes_signals_and_evidence_items(monkeypatch):
    from src.services import coach_evidence
    _crs(monkeypatch, 1)
    c = _conn()
    set_setting(c, "adjuster_version", "v3")
    monkeypatch.setattr(svc, "_today", lambda t=None: t or D)
    r = svc.get_day_adjustment(c, D, today=D)
    assert r["adjustment"]["signals"] and r["adjustment"]["source"] == "checkin"
    items = coach_evidence._trigger_items(c, D)
    assert {i["metric"] for i in items} == {"crs", "acwr", "checkin_fatigue"}
    assert all(i["label"] and i["_rest"] for i in items)


def test_trigger_items_empty_for_manual_or_none():
    from src.services import coach_evidence
    assert coach_evidence._trigger_items(_conn(), D) == []


def test_trigger_label():
    from src.services.adjustment_labels import trigger_label
    assert trigger_label({"signal": "acwr", "value": 1.8}) == "ACWR 1.80"
    assert trigger_label({"signal": "pain", "value": None}) == "통증 기록"
    assert trigger_label({"signal": "crs", "value": None}) is None


def test_weekly_job_rolls_back_v3(monkeypatch):
    from datetime import date
    from src.services import weekly_adapt_job
    from src.services.user_settings_service import get_setting
    c = _conn()
    set_setting(c, "adjuster_version", "v3")
    monkeypatch.setattr("src.services.adjuster_frequency.should_rollback", lambda conn, today: ["weekly_over"])
    assert weekly_adapt_job.run(c, date.fromisoformat(D)) == 0
    assert get_setting(c, "adjuster_version", "v2") == "v2"
