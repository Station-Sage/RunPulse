"""race_plan_link (RC-b) — 배치 적용·되돌리기·재적용·보호 행·신호 창."""
from src.services import adjustment_signals_race as sig
from src.services import race_calendar_service as svc
from src.services import race_calendar_state as st
from src.services import race_plan_link as link

TODAY = "2026-10-17"


def _plan(conn, start="2026-10-18", n=14):
    from datetime import date, timedelta
    d0 = date.fromisoformat(start)
    gid = conn.execute("INSERT INTO goals(name, distance_km, status) VALUES ('old', 42.195, 'completed')").lastrowid
    for i in range(n):
        conn.execute("INSERT INTO planned_workouts(date, workout_type, distance_km, source, goal_id)"
                     " VALUES (?,?,?,'planner',?)",
                     ((d0 + timedelta(days=i)).isoformat(), "rest" if i % 7 == 3 else "easy", 10.0, gid))


def _race(conn, date="2026-10-25", km=21.0975, prio="B"):
    return svc.add(conn, {"name": "R", "race_date": date, "distance_km": km, "priority": prio})


def test_windows_distance_based_and_bc_rounded_up():
    assert sig.windows_for("A", 10) == (3, 2)
    assert sig.windows_for("A", 21.0975) == (7, 4)
    assert sig.windows_for("A", 42.195) == (14, 7)
    assert sig.windows_for("B", 42.195) == (7, 4)
    assert sig.windows_for("C", 21.0975) == (4, 2)
    assert sig.windows_for("B", 10, taper=5, recovery=1) == (5, 1)


def test_apply_and_undo_roundtrip(db_conn):
    _plan(db_conn)
    r = _race(db_conn)
    res = link.apply(db_conn, r["id"], TODAY)
    assert res["n"] > 0
    rows = db_conn.execute("SELECT decision, source FROM plan_adjustments").fetchall()
    assert rows and all(x == ("accepted", "race") for x in rows)
    assert db_conn.execute("SELECT COUNT(*) FROM planned_workouts WHERE adj_accepted=1").fetchone()[0] == res["n"]
    assert link.undo(db_conn, r["id"]) == res["n"]
    assert db_conn.execute("SELECT COUNT(*) FROM planned_workouts WHERE adj_accepted=1").fetchone()[0] == 0


def test_protected_rows_untouched(db_conn):
    _plan(db_conn)
    db_conn.execute("UPDATE planned_workouts SET completed=1 WHERE date='2026-10-24'")
    r = _race(db_conn)
    link.apply(db_conn, r["id"], TODAY)
    assert db_conn.execute("SELECT COUNT(*) FROM plan_adjustments a JOIN planned_workouts w ON w.id=a.workout_id"
                           " WHERE w.completed=1 OR w.workout_type='rest'").fetchone()[0] == 0


def test_no_plan_gives_zero_rows(db_conn):
    r = _race(db_conn)
    assert link.apply(db_conn, r["id"], TODAY)["n"] == 0


def test_cancel_undoes_applied(db_conn):
    _plan(db_conn)
    r = _race(db_conn)
    link.apply(db_conn, r["id"], TODAY)
    db_conn.execute("UPDATE race_calendar SET adapt_choice='adapt', plan_state='applied' WHERE id=?", (r["id"],))
    svc.cancel(db_conn, r["id"])
    assert db_conn.execute("SELECT COUNT(*) FROM plan_adjustments WHERE decision='accepted'").fetchone()[0] == 0


def test_restore_reapplies_batch(db_conn):
    _plan(db_conn)
    r = _race(db_conn)
    link.apply(db_conn, r["id"], TODAY)
    db_conn.execute("UPDATE race_calendar SET adapt_choice='adapt', plan_state='applied' WHERE id=?", (r["id"],))
    svc.cancel(db_conn, r["id"])
    out = st.restore(db_conn, r["id"], TODAY)
    assert out["restore"]["replan_applied"] is True and out["plan_state"] == "applied"
    assert db_conn.execute("SELECT COUNT(*) FROM plan_adjustments WHERE decision='accepted'").fetchone()[0] > 0


def test_live_proposed_auto_is_replaced_accepted_is_skipped(db_conn):
    _plan(db_conn)
    wid = db_conn.execute("SELECT id FROM planned_workouts WHERE date='2026-10-24'").fetchone()[0]
    wid2 = db_conn.execute("SELECT id FROM planned_workouts WHERE date='2026-10-23'").fetchone()[0]
    ins = ("INSERT INTO plan_adjustments(workout_id, date, source, before_json, after_json, rule_version, decision)"
           " VALUES (?,?,'readiness','{{}}','{{}}','v','{}')")
    db_conn.execute(ins.format("proposed"), (wid, "2026-10-24"))
    db_conn.execute(ins.format("accepted"), (wid2, "2026-10-23"))
    r = _race(db_conn)
    link.apply(db_conn, r["id"], TODAY)
    assert db_conn.execute("SELECT decision FROM plan_adjustments WHERE workout_id=? AND source='readiness'",
                           (wid,)).fetchone()[0] == "reverted"
    assert db_conn.execute("SELECT COUNT(*) FROM plan_adjustments WHERE workout_id=? AND source='race'",
                           (wid2,)).fetchone()[0] == 0


def test_needs_review_excluded_from_signal(db_conn):
    r = _race(db_conn, date="2026-10-20")
    db_conn.execute("UPDATE race_calendar SET status='done' WHERE id=?", (r["id"],))
    assert sig.collect_race(db_conn, TODAY) is None
