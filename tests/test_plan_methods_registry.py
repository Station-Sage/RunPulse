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
