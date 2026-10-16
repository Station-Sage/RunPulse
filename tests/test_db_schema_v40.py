"""스키마 v40 + planner_store(PLN-38) 테스트."""
import re
import sqlite3
from pathlib import Path

import pytest

from src.db_schema_v40 import ensure_v40
from src.db_setup import create_tables
from src.training.planner_store import save_weekly_plan, write_planner_rows
from src.training.plan_replace import replace_range


def _pre():
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE planned_workouts (id INTEGER PRIMARY KEY, date TEXT, workout_type TEXT, source TEXT)")
    c.execute("CREATE TABLE user_training_prefs (id INTEGER PRIMARY KEY)")
    return c


def _cols(c, t):
    return {r[1] for r in c.execute(f"PRAGMA table_info({t})")}


def test_adds_columns_and_idempotent():
    c = _pre()
    ensure_v40(c)
    ensure_v40(c)
    assert {"goal_id", "adj_accepted"} <= _cols(c, "planned_workouts")
    assert "workout_weekdays_mask" in _cols(c, "user_training_prefs")


def test_check_rejects_planner_without_goal():
    c = _pre()
    ensure_v40(c)
    with pytest.raises(sqlite3.IntegrityError):
        c.execute("INSERT INTO planned_workouts (date, workout_type, source) VALUES ('2026-01-01','easy','planner')")
    c.execute("INSERT INTO planned_workouts (date, workout_type, source) VALUES ('2026-01-01','easy','manual')")
    with pytest.raises(sqlite3.IntegrityError):
        c.execute("UPDATE planned_workouts SET adj_accepted=2")


def test_existing_planner_row_blocks_migration():
    c = _pre()
    c.execute("INSERT INTO planned_workouts (date, workout_type, source) VALUES ('2026-01-01','easy','planner')")
    with pytest.raises(sqlite3.OperationalError):
        ensure_v40(c)
    assert "adj_accepted" not in _cols(c, "planned_workouts")


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    return c


def _goal(c, name="G", status="active"):
    return c.execute("INSERT INTO goals (name, distance_km, status) VALUES (?,42.195,?)", (name, status)).lastrowid


def _plan(d):
    return [{"date": d, "workout_type": "easy", "distance_km": 5}]


def test_write_requires_goal_id(conn):
    with pytest.raises(ValueError):
        write_planner_rows(conn, _plan("2030-01-01"), goal_id=None)


def test_write_restore_keeps_id(conn):
    g = _goal(conn)
    ids = write_planner_rows(conn, [{"id": 999, "date": "2030-01-01", "workout_type": "easy", "source": "planner"}],
                             goal_id=g, restore=True)
    assert ids == [999]


def test_save_weekly_plan_scoped_delete(conn):
    a, b = _goal(conn, "A", "completed"), _goal(conn, "B")
    save_weekly_plan(conn, _plan("2030-01-01"), goal_id=a)
    save_weekly_plan(conn, _plan("2030-01-01"), goal_id=b)
    save_weekly_plan(conn, _plan("2030-01-01"), goal_id=b)
    rows = conn.execute("SELECT goal_id FROM planned_workouts ORDER BY goal_id").fetchall()
    assert rows == [(a,), (b,)]


def test_save_weekly_plan_requires_goal_id(conn):
    _goal(conn)
    with pytest.raises(TypeError):
        save_weekly_plan(conn, _plan("2030-01-01"))
    with pytest.raises(ValueError):
        save_weekly_plan(conn, _plan("2030-01-01"), goal_id=None)


def test_replace_range_goal_scoped(conn):
    a, b = _goal(conn, "A", "completed"), _goal(conn, "B")
    save_weekly_plan(conn, _plan("2030-01-01"), goal_id=a)
    save_weekly_plan(conn, _plan("2030-01-01"), goal_id=b)
    replace_range(conn, _plan("2030-01-05"), "2030-01-01", "2030-01-31", goal_id=b)
    got = sorted(conn.execute("SELECT date, goal_id FROM planned_workouts").fetchall())
    assert got == [("2030-01-01", a), ("2030-01-05", b)]


def test_insert_planned_workouts_only_in_allowed_files():
    allowed = {"training/planner_store.py", "sync/plan_ingest.py", "web/views_training_crud.py",
               "web/views_training_goal_crud.py", "db_schema_v27.py"}
    src = Path(__file__).resolve().parents[1] / "src"
    hits = {str(p.relative_to(src)) for p in src.rglob("*.py")
            if re.search(r"INTO\s+planned_workouts", p.read_text(encoding="utf-8"))}
    assert hits <= allowed, hits - allowed


def test_check_adj_accepted_mismatch(tmp_path):
    from scripts.check_data_consistency import _check_adj_accepted

    p = tmp_path / "r.db"
    c = sqlite3.connect(p)
    create_tables(c)
    g = _goal(c)
    wid = write_planner_rows(c, _plan("2030-01-01"), goal_id=g)[0]
    c.commit()
    assert _check_adj_accepted(str(p))[0][0] == "✅"
    c.execute("UPDATE planned_workouts SET adj_accepted=1 WHERE id=?", (wid,))
    c.commit()
    assert _check_adj_accepted(str(p))[0][0] == "🔴"
    c.close()
