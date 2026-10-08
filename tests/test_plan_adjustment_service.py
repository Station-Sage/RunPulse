"""plan_adjustment_service: 제안 upsert 멱등, 수락/되돌리기 전이, rev 충돌, stale."""
import sqlite3

import pytest

from src.db_setup import create_tables
from src.services import plan_adjustment_service as svc

D = "2026-10-08"


def _conn(monkeypatch, adjusted=True, to="easy"):
    c = sqlite3.connect(":memory:")
    create_tables(c)
    c.execute("INSERT INTO planned_workouts(id,date,workout_type,distance_km) VALUES (7,?, 'interval', 10.0)", (D,))
    c.commit()
    state = {"w": {"id": 7, "date": D, "workout_type": "interval", "distance_km": 10.0,
                   "adjusted": adjusted, "adjusted_type": to, "adjustment_reason": "피로 높음",
                   "adjustment_reason_parts": ["수면 부족"]}}
    monkeypatch.setattr(svc, "adjust_todays_plan", lambda conn, config=None, date=None: state["w"])
    return c, state


def test_ensure_proposal_idempotent_and_rev_bump(monkeypatch):
    c, st = _conn(monkeypatch)
    a = svc.ensure_proposal(c, D, today=D)
    assert a["decision"] == "proposed" and a["after"]["workout_type"] == "easy" and a["after"]["distance_km"] == 10.0
    assert svc.ensure_proposal(c, D, today=D)["id"] == a["id"] and svc.ensure_proposal(c, D, today=D)["rev"] == a["rev"]
    st["w"]["adjusted_type"] = "rest"
    b = svc.ensure_proposal(c, D, today=D)
    assert b["id"] == a["id"] and b["rev"] == a["rev"] + 1 and b["after"]["distance_km"] is None


def test_no_proposal_when_not_adjusted_or_future(monkeypatch):
    c, _ = _conn(monkeypatch, adjusted=False)
    assert svc.get_day_adjustment(c, D, today=D) == {"state": "none", "adjustment": None}
    assert svc.get_day_adjustment(c, "2026-10-09", today=D)["state"] == "future"


def test_accept_revert_flow(monkeypatch):
    c, _ = _conn(monkeypatch)
    a = svc.ensure_proposal(c, D, today=D)
    r = svc.accept(c, a["id"], rev=a["rev"], via="plan", today=D)
    assert r["state"] == "accepted" and r["decided_via"] == "plan"
    assert svc.accept(c, a["id"], rev=a["rev"], today=D)["state"] == "accepted"
    assert svc.get_day_adjustment(c, D, today=D)["state"] == "accepted"
    assert svc.revert(c, a["id"], today=D)["state"] == "undone"
    assert svc.get_day_adjustment(c, D, today=D)["state"] == "undone"
    assert svc.accept(c, a["id"], rev=a["rev"], today=D)["state"] == "accepted"


def test_decline_state_and_no_new_proposal(monkeypatch):
    c, _ = _conn(monkeypatch)
    a = svc.ensure_proposal(c, D, today=D)
    assert svc.revert(c, a["id"], today=D)["state"] == "declined"
    assert svc.ensure_proposal(c, D, today=D)["id"] == a["id"]
    assert c.execute("SELECT COUNT(*) FROM plan_adjustments").fetchone()[0] == 1


def test_conflicts(monkeypatch):
    c, _ = _conn(monkeypatch)
    a = svc.ensure_proposal(c, D, today=D)
    with pytest.raises(svc.AdjustmentConflict) as e:
        svc.accept(c, a["id"], rev=a["rev"] + 5, today=D)
    assert e.value.code == "REV_MISMATCH" and e.value.current["id"] == a["id"]
    with pytest.raises(svc.AdjustmentConflict) as e:
        svc.accept(c, a["id"], rev=a["rev"], today="2026-10-09")
    assert e.value.code == "LOCKED"
    with pytest.raises(svc.AdjustmentConflict) as e:
        svc.accept(c, 999, rev=1, today=D)
    assert e.value.code == "NOT_FOUND"
    c.execute("UPDATE planned_workouts SET distance_km = 12 WHERE id = 7")
    with pytest.raises(svc.AdjustmentConflict) as e:
        svc.accept(c, a["id"], rev=a["rev"], today=D)
    assert e.value.code == "STALE"


def test_expired_and_list(monkeypatch):
    c, _ = _conn(monkeypatch)
    a = svc.ensure_proposal(c, D, today=D)
    assert svc.get_day_adjustment(c, D, ensure=False, today="2026-10-10")["state"] == "expired"
    rows = svc.list_adjustments(c, goal_id=None, start="2026-10-01", end="2026-10-31", today=D)
    assert [r["id"] for r in rows] == [a["id"]] and rows[0]["state"] == "proposed"


def test_create_user_adjustment_reduce_rest_and_replace(monkeypatch):
    c, _ = _conn(monkeypatch)
    a = svc.create_user_adjustment(c, 7, "reduce", {"pct": 20, "reason": "fatigue"}, today=D, via="plan")
    assert a["state"] == "accepted" and a["source"] == "user" and a["after"]["distance_km"] == 8.0
    b = svc.create_user_adjustment(c, 7, "rest", today=D)
    assert b["after"]["workout_type"] == "rest" and b["id"] != a["id"]
    assert svc._get(c, a["id"])["decision"] == "reverted"
    assert svc.revert(c, b["id"], today=D)["state"] == "undone"


def test_create_user_adjustment_errors(monkeypatch):
    c, _ = _conn(monkeypatch)
    with pytest.raises(ValueError):
        svc.create_user_adjustment(c, 7, "reduce", {"pct": 0}, today=D)
    with pytest.raises(ValueError):
        svc.create_user_adjustment(c, 7, "bogus", today=D)
    for args, code in (((7, "move"), "UNSUPPORTED"), ((99, "rest"), "NOT_FOUND")):
        with pytest.raises(svc.AdjustmentConflict) as e:
            svc.create_user_adjustment(c, *args, today=D)
        assert e.value.code == code
    with pytest.raises(svc.AdjustmentConflict) as e:
        svc.create_user_adjustment(c, 7, "rest", today="2026-10-09")
    assert e.value.code == "LOCKED"
