"""훈련 방식 레지스트리 + 스키마 v51 마이그레이션."""
import sqlite3

from src.db_schema_v51 import ensure_v51
from src.training.methods import DEFAULT_METHOD, candidates_for, effective_method, get_method


def _db():
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE goals (id INTEGER PRIMARY KEY, name TEXT)")
    c.execute("CREATE TABLE plan_replans (id INTEGER PRIMARY KEY, goal_id INTEGER)")
    c.execute("INSERT INTO goals(name) VALUES ('g')")
    c.execute("INSERT INTO plan_replans(goal_id) VALUES (1)")
    return c


def test_v51_adds_columns_idempotent_and_backfills_default():
    c = _db()
    ensure_v51(c)
    ensure_v51(c)
    assert c.execute("SELECT plan_method FROM goals").fetchone()[0] == "balanced"
    assert c.execute("SELECT plan_method FROM plan_replans").fetchone()[0] is None


def test_v51_no_tables_is_noop():
    c = sqlite3.connect(":memory:")
    ensure_v51(c)
    assert c.execute("SELECT count(*) FROM sqlite_master").fetchone()[0] == 0


def test_get_method_fallback():
    assert get_method(None).id == DEFAULT_METHOD
    assert get_method("nope").id == DEFAULT_METHOD


def test_effective_method_reads_goal_and_tolerates_missing_column():
    c = _db()
    assert effective_method(c, 1, None) == "balanced"
    ensure_v51(c)
    c.execute("UPDATE goals SET plan_method='unknown' WHERE id=1")
    assert effective_method(c, 1, None) == "balanced"
    assert effective_method(c, None, None) == "balanced"


def test_candidates_guard_never_empty():
    assert [m.id for m in candidates_for("10k", 3)] == ["balanced"]
    assert [m.id for m in candidates_for("ultra")] == ["balanced"]


# ── 2단계: 파이프라인 주입·재계획 연동 ──
from datetime import date, timedelta  # noqa: E402
import dataclasses  # noqa: E402
import pytest  # noqa: E402

from src.services import plan_replan_service as R  # noqa: E402
from src.training import methods as M  # noqa: E402
from src.training.goals import add_goal  # noqa: E402
from src.training.planner import generate_weekly_plan, save_weekly_plan  # noqa: E402
from tests.helpers_pred import mem_conn, with_days  # noqa: E402

_TODAY = date.today()
_MON = R.next_monday(_TODAY)


def _fx():
    conn = with_days(mem_conn())
    gid = add_goal(conn, "g", 21.0975, (_MON + timedelta(weeks=10, days=5)).isoformat(), None, rules_version=2)
    conn.execute("UPDATE goals SET plan_weeks=14, distance_label='half' WHERE id=?", (gid,))
    conn.commit()
    for i in range(12):
        save_weekly_plan(conn, generate_weekly_plan(conn, gid, week_start=_MON - timedelta(weeks=1) + timedelta(weeks=i)), goal_id=gid)
    return conn, gid


@pytest.fixture
def alt_method(monkeypatch):
    def adjust(plan, ctx):
        for r in plan:
            if r["workout_type"] != "rest":
                r["distance_km"] = round(r["distance_km"] * 0.5, 1)
        return plan
    m = dataclasses.replace(M.METHODS["balanced"], id="alt", label="alt", adjust=adjust)
    monkeypatch.setitem(M.METHODS, "alt", m)
    return m


def test_balanced_unchanged_and_hook_applies(alt_method):
    conn, gid = _fx()
    ws = _MON + timedelta(weeks=2)
    base = generate_weekly_plan(conn, gid, week_start=ws)
    conn.execute("UPDATE goals SET plan_method='alt' WHERE id=?", (gid,))
    alt = generate_weekly_plan(conn, gid, week_start=ws)
    assert [r["distance_km"] for r in alt] != [r["distance_km"] for r in base]
    conn.execute("UPDATE goals SET plan_method='balanced' WHERE id=?", (gid,))
    assert generate_weekly_plan(conn, gid, week_start=ws) == base


def test_replan_method_change_keeps_past_and_undo(alt_method):
    conn, gid = _fx()
    past = conn.execute("SELECT id,date,distance_km FROM planned_workouts WHERE date<? ORDER BY id", (_MON.isoformat(),)).fetchall()
    out = R.apply(conn, {"expect_anchor": _MON.isoformat(), "plan_method": "alt"}, _TODAY)
    assert out["method_changed"] and out["plan_method"] == "alt"
    assert M.effective_method(conn, gid, _MON + timedelta(weeks=3)) == "alt"
    assert M.effective_method(conn, gid, _MON - timedelta(weeks=1)) == "balanced"
    assert conn.execute("SELECT id,date,distance_km FROM planned_workouts WHERE date<? ORDER BY id", (_MON.isoformat(),)).fetchall() == past
    R.undo(conn, out["replan_id"], _TODAY)
    assert M.effective_method(conn, gid, _MON + timedelta(weeks=3)) == "balanced"


def test_replan_rejects_unknown_method_and_state():
    conn, gid = _fx()
    with pytest.raises(R.ReplanError) as e:
        R.preview(conn, {"plan_method": "nope"}, _TODAY)
    assert e.value.code == "METHOD_UNSUPPORTED"
    st = R.methods_state(conn, _TODAY)
    assert st["current"] == "balanced" and [m["id"] for m in st["methods"]] == ["balanced"]
    assert R.preview(conn, {}, _TODAY)["method_changed"] is False
