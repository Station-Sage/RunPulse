"""v28: 목표 생성 시 사용자 입력 시작 부하(최근 주간 km·최장 롱런 km)."""
import sqlite3

from src.db_schema_v28 import ensure_v28
from src.db_setup import SCHEMA_VERSION
from src.training.goals import add_goal, get_reported_load, set_reported_load
from tests.helpers_pred import mem_conn


def test_reported_load_roundtrip_and_default_none():
    assert SCHEMA_VERSION >= 28
    c = mem_conn()
    gid = add_goal(c, "g", 42.195, "2030-11-24")
    assert get_reported_load(c, gid) == (None, None)
    set_reported_load(c, gid, 25.0, 14.0)
    assert get_reported_load(c, gid) == (25.0, 14.0)
    assert get_reported_load(c, 999) == (None, None)


def test_v28_migration_idempotent_and_missing_column_safe():
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE goals (id INTEGER PRIMARY KEY, name TEXT)")
    c.execute("INSERT INTO goals (name) VALUES ('legacy')")
    assert get_reported_load(c, 1) == (None, None)          # 컬럼 없음 → None
    ensure_v28(c)
    ensure_v28(c)
    assert c.execute("SELECT reported_weekly_km, reported_long_km FROM goals").fetchone() == (None, None)
