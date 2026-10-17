"""RC-a: race_calendar 서비스·상태 전이·목표 동기화."""
import pytest

from src.services import race_calendar_query as q
from src.services import race_calendar_service as svc
from src.services import race_calendar_state as st
from src.services import race_goal_sync as sync
from src.services.goal_service import create_goal_with_race
from src.services.race_calendar_query import RaceError
from src.training import goals

TODAY = "2026-10-17"


def _race(conn, name="R", date="2026-12-06", km=42.195, prio="B", **kw):
    return svc.add(conn, {"name": name, "race_date": date, "distance_km": km, "priority": prio, **kw})


def test_add_defaults_and_duplicate(db_conn):
    r = _race(db_conn)
    assert (r["status"], r["adapt_choice"], r["plan_state"]) == ("planned", "unasked", "none")
    with pytest.raises(RaceError) as e:
        _race(db_conn, name="dup")
    assert e.value.code == "DUPLICATE"


def test_add_second_a_conflicts(db_conn):
    _race(db_conn, prio="A")
    with pytest.raises(RaceError) as e:
        _race(db_conn, date="2026-11-01", km=10, prio="A")
    assert e.value.code == "A_CONFLICT" and e.value.extra["existing_a"]["active_goal_id"] is None


def test_past_date_allowed(db_conn):
    assert _race(db_conn, date="2025-01-01")["status"] == "planned"


def test_lazy_done_and_zones(db_conn):
    _race(db_conn, date="2026-09-01")
    _race(db_conn, date="2026-11-01", km=10)
    assert q.lazy_done(db_conn, TODAY) == 1
    z = q.list_zones(db_conn, TODAY)
    assert len(z["past"]) == 1 and len(z["upcoming"]) == 1 and not z["needs_review"]


def test_needs_review_zone(db_conn):
    r = _race(db_conn, date="2026-11-01")
    db_conn.execute("UPDATE race_calendar SET status='done' WHERE id=?", (r["id"],))
    assert q.is_needs_review(q.require(db_conn, r["id"]), TODAY)
    assert len(q.list_zones(db_conn, TODAY)["needs_review"]) == 1


def test_update_applied_goes_stale_and_editable_whitelist(db_conn):
    r = _race(db_conn)
    db_conn.execute("UPDATE race_calendar SET plan_state='applied', adapt_choice='adapt' WHERE id=?", (r["id"],))
    u = svc.update(db_conn, r["id"], {"race_date": "2026-12-13", "status": "done"})
    assert u["plan_state"] == "stale" and u["status"] == "planned"


def test_update_not_found(db_conn):
    with pytest.raises(RaceError) as e:
        svc.update(db_conn, 999, {"name": "x"})
    assert e.value.http == 404


def test_cancel_saves_prev_and_blocks_goal_race(db_conn):
    r = _race(db_conn, adapt_choice=None) if False else _race(db_conn)
    db_conn.execute("UPDATE race_calendar SET adapt_choice='later' WHERE id=?", (r["id"],))
    c = svc.cancel(db_conn, r["id"])
    assert c["status"] == "cancelled" and c["cancel_prev_adapt_choice"] == "later"
    g = create_goal_with_race(db_conn, name="G", distance_km=42.195, race_date="2026-12-20")
    with pytest.raises(RaceError) as e:
        svc.cancel(db_conn, g["race_id"])
    assert e.value.code == "GOAL_LINKED"


def test_restore_future_restores_prev_values(db_conn):
    r = _race(db_conn)
    db_conn.execute("UPDATE race_calendar SET adapt_choice='no_adapt' WHERE id=?", (r["id"],))
    svc.cancel(db_conn, r["id"])
    out = st.restore(db_conn, r["id"], TODAY)
    assert (out["status"], out["adapt_choice"], out["cancel_prev_adapt_choice"]) == ("planned", "no_adapt", None)


def test_restore_past_needs_confirm(db_conn):
    r = _race(db_conn, date="2026-09-01")
    svc.cancel(db_conn, r["id"])
    with pytest.raises(RaceError) as e:
        st.restore(db_conn, r["id"], TODAY)
    assert e.value.code == "CONFIRM_PAST"
    assert st.restore(db_conn, r["id"], TODAY, confirm_past=True)["status"] == "done"


def test_restore_non_cancelled_409(db_conn):
    r = _race(db_conn)
    with pytest.raises(RaceError) as e:
        st.restore(db_conn, r["id"], TODAY)
    assert e.value.code == "NOT_CANCELLED"


def test_restore_a_conflict_demote(db_conn):
    a1 = _race(db_conn, name="A1", prio="A")
    svc.cancel(db_conn, a1["id"])
    a2 = _race(db_conn, name="A2", date="2026-11-22", km=21.1, prio="A")
    with pytest.raises(RaceError) as e:
        st.restore(db_conn, a1["id"], TODAY)
    assert e.value.code == "A_CONFLICT"
    st.restore(db_conn, a1["id"], TODAY, demote_existing_a=True)
    assert q.require(db_conn, a2["id"])["priority"] == "B"


def test_restore_over_goal_race_requires_goal_link(db_conn):
    a1 = _race(db_conn, name="A1", prio="A")
    svc.cancel(db_conn, a1["id"])
    g = create_goal_with_race(db_conn, name="G", distance_km=21.1, race_date="2026-11-22")
    with pytest.raises(RaceError):
        st.restore(db_conn, a1["id"], TODAY, demote_existing_a=True)
    st.restore(db_conn, a1["id"], TODAY, goal_link={"race_id": a1["id"]})
    assert q.active_goal_race_id(db_conn) == a1["id"]
    assert goals.get_goal(db_conn, g["id"])["race_date"] == a1["race_date"]
    assert sync.check_invariants(db_conn) == []


def test_restore_goal_link_wrong_target(db_conn):
    a1 = _race(db_conn, prio="A")
    svc.cancel(db_conn, a1["id"])
    create_goal_with_race(db_conn, name="G", distance_km=21.1, race_date="2026-11-22")
    with pytest.raises(RaceError) as e:
        st.restore(db_conn, a1["id"], TODAY, goal_link={"race_id": 12345})
    assert e.value.code == "GOAL_LINK_TARGET"


def test_restore_reapply_unavailable_becomes_stale(db_conn):
    r = _race(db_conn)
    db_conn.execute("UPDATE race_calendar SET adapt_choice='adapt', plan_state='applied' WHERE id=?", (r["id"],))
    svc.cancel(db_conn, r["id"])
    out = st.restore(db_conn, r["id"], TODAY)
    assert (out["adapt_choice"], out["plan_state"]) == ("adapt", "stale") and out["restore"]["replan_applied"] is False


def test_reopen(db_conn):
    r = _race(db_conn, date="2026-11-01")
    db_conn.execute("UPDATE race_calendar SET status='done', adapt_choice='adapt' WHERE id=?", (r["id"],))
    out = st.reopen(db_conn, r["id"], TODAY)
    assert (out["status"], out["adapt_choice"]) == ("planned", "unasked")
    with pytest.raises(RaceError):
        st.reopen(db_conn, r["id"], TODAY)


def test_create_goal_with_race_demotes_old_a_and_syncs_cache(db_conn):
    g1 = create_goal_with_race(db_conn, name="G1", distance_km=42.195, race_date="2026-12-06", target_time_sec=12000)
    r1 = q.require(db_conn, g1["race_id"])
    assert (r1["priority"], r1["goal_type"], r1["plan_state"]) == ("A", "time", "applied")
    g2 = create_goal_with_race(db_conn, name="G2", distance_km=21.1, race_date="2026-11-22")
    assert q.require(db_conn, g1["race_id"])["priority"] == "B"
    assert goals.get_goal(db_conn, g1["id"])["status"] == "cancelled"
    assert g2["race_date"] == "2026-11-22" and sync.check_invariants(db_conn) == []


def test_add_goal_compat_creates_linked_race(db_conn):
    gid = goals.add_goal(db_conn, "G", 10, race_date="2026-11-08")
    g = goals.get_goal(db_conn, gid)
    assert g["race_id"] and q.require(db_conn, g["race_id"])["priority"] == "A"


def test_add_goal_without_date_has_no_race_then_attach(db_conn):
    gid = goals.add_goal(db_conn, "G", 10)
    assert goals.get_goal(db_conn, gid)["race_id"] is None
    goals.update_goal(db_conn, gid, race_date="2026-11-08")
    g = goals.get_goal(db_conn, gid)
    assert g["race_id"] and g["race_date"] == "2026-11-08"


def test_update_goal_delegates_to_race(db_conn):
    gid = goals.add_goal(db_conn, "G", 10, race_date="2026-11-08")
    goals.update_goal(db_conn, gid, race_date="2026-11-15", distance_km=21.1)
    g = goals.get_goal(db_conn, gid)
    r = q.require(db_conn, g["race_id"])
    assert (r["race_date"], r["distance_km"]) == ("2026-11-15", 21.1) == (g["race_date"], g["distance_km"])


def test_push_cache_rc21_exception_keeps_null_date(db_conn):
    r = _race(db_conn, prio="A")
    db_conn.execute("INSERT INTO goals (name, distance_km, status, race_id) VALUES ('old', 42.195, 'cancelled', ?)",
                    (r["id"],))
    svc.update(db_conn, r["id"], {"name": "renamed"})
    sync.push_cache(db_conn, r["id"], date_changed=False)
    assert db_conn.execute("SELECT race_date FROM goals WHERE race_id=?", (r["id"],)).fetchone()[0] is None


def test_demote_a_blocked_for_goal_race(db_conn):
    g = create_goal_with_race(db_conn, name="G", distance_km=10, race_date="2026-11-08")
    with pytest.raises(RaceError):
        sync.demote_a(db_conn, g["race_id"])


def test_check_invariants_detects_drift(db_conn):
    g = create_goal_with_race(db_conn, name="G", distance_km=10, race_date="2026-11-08")
    db_conn.execute("UPDATE goals SET race_date='2026-01-01' WHERE id=?", (g["id"],))
    assert sync.check_invariants(db_conn)
