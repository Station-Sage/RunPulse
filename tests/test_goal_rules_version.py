"""U16e: 목표별 계획 규칙 버전 고정·플래그·마이그레이션."""
import sqlite3

import pytest

from src.db_schema_v26 import ensure_v26
from src.db_setup import SCHEMA_VERSION, create_tables
from src.training.goals import add_goal, get_rules_version, set_rules_version


def _conn():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    return c


def test_schema_version_and_default_two():
    assert SCHEMA_VERSION >= 26
    c = _conn()
    gid = add_goal(c, "x", 42.195, "2026-11-22")
    assert get_rules_version(c, gid) == 2


def test_new_goal_fills_plan_weeks_and_explicit_v1_allowed():
    c = _conn()
    gid = add_goal(c, "x", 42.195, "2099-01-01")
    assert c.execute("SELECT plan_weeks FROM goals WHERE id=?", (gid,)).fetchone()[0] is not None
    old = add_goal(c, "old", 10, "2027-04-01", rules_version=1)
    assert get_rules_version(c, old) == 1


def test_explicit_version_and_downgrade():
    c = _conn()
    gid = add_goal(c, "v2", 42.195, "2027-03-01", rules_version=2)
    assert get_rules_version(c, gid) == 2
    set_rules_version(c, gid, 1)
    assert get_rules_version(c, gid) == 1
    with pytest.raises(ValueError):
        set_rules_version(c, gid, 3)


def test_migration_adds_column_to_legacy_goals_idempotent():
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE goals (id INTEGER PRIMARY KEY, name TEXT)")
    c.execute("INSERT INTO goals (name) VALUES ('legacy')")
    ensure_v26(c)
    ensure_v26(c)
    assert c.execute("SELECT plan_rules_version FROM goals").fetchone()[0] == 1


def test_get_rules_version_missing_goal_is_one():
    assert get_rules_version(_conn(), 999) == 1
