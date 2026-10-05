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


def test_schema_version_and_default_one(monkeypatch):
    monkeypatch.delenv("PLAN_RULES_V2_ENABLED", raising=False)
    assert SCHEMA_VERSION >= 26
    c = _conn()
    gid = add_goal(c, "x", 42.195, "2026-11-22")
    assert get_rules_version(c, gid) == 1


def test_flag_on_new_goal_is_v2_and_existing_stays_v1(monkeypatch):
    monkeypatch.delenv("PLAN_RULES_V2_ENABLED", raising=False)
    c = _conn()
    old = add_goal(c, "old", 42.195, "2026-11-22")
    monkeypatch.setenv("PLAN_RULES_V2_ENABLED", "true")
    new = add_goal(c, "new", 42.195, "2027-03-01")
    assert (get_rules_version(c, old), get_rules_version(c, new)) == (1, 2)
    monkeypatch.setenv("PLAN_RULES_V2_ENABLED", "0")
    assert get_rules_version(c, add_goal(c, "off", 10, "2027-04-01")) == 1


def test_explicit_version_and_downgrade(monkeypatch):
    monkeypatch.delenv("PLAN_RULES_V2_ENABLED", raising=False)
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
