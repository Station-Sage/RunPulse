"""U16h: marathon·long_mp 유형 배선(스키마 CHECK·구조·판정·매처·라벨·푸시)."""
import sqlite3

from src.db_schema_v27 import ensure_v27
from src.db_setup import create_tables
from src.training import match_select, outcome_v2, plan_structure
from src.utils.format_ko import WORKOUT_TYPE_KO


def _ins(c, t):
    c.execute("INSERT INTO planned_workouts(date, workout_type, distance_km) VALUES ('2026-11-01', ?, 10)", (t,))


def test_fresh_schema_accepts_new_types():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    for t in ("marathon", "long_mp", "threshold"):
        _ins(c, t)
    assert c.execute("SELECT COUNT(*) FROM planned_workouts").fetchone()[0] == 3


def test_v27_rebuild_keeps_rows_columns_and_indexes():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    c.execute("DROP TABLE planned_workouts")
    c.execute("""CREATE TABLE planned_workouts (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL,
        workout_type TEXT NOT NULL CHECK(workout_type IN ('easy', 'tempo', 'interval', 'long', 'rest', 'recovery', 'race')),
        distance_km REAL, extra TEXT)""")
    c.execute("CREATE INDEX idx_pw_date ON planned_workouts(date)")
    c.execute("INSERT INTO planned_workouts(date, workout_type, distance_km, extra) VALUES ('2026-01-01','easy',5,'x')")
    ensure_v27(c)
    ensure_v27(c)                                   # 멱등
    assert c.execute("SELECT date, workout_type, extra FROM planned_workouts").fetchall() == [("2026-01-01", "easy", "x")]
    _ins(c, "long_mp")
    names = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='index'")}
    assert "idx_pw_date" in names


def test_marathon_structure_and_outcome_on_target():
    st = plan_structure.structure_for_plan("marathon", 10.0, 295, 305)
    work = st["steps"][0]
    assert work["min_share"] == 0.6 and "max_only" not in work
    r = outcome_v2.compare_continuous(st, 3000, 10000)         # 5:00/km, 목표 4:55~5:05
    assert r["label"] == "on_target"


def test_long_mp_structure_is_max_only():
    work = plan_structure.structure_for_plan("long_mp", 24.0, 300, 360)["steps"][0]
    assert work["min_share"] == 0.8 and work["max_only"] is True


def test_matcher_and_labels():
    assert match_select.compatible("marathon", "easy") is False
    assert match_select.compatible("marathon", "tempo") is True
    assert match_select.compatible("long_mp", "long_run") is True
    assert WORKOUT_TYPE_KO["marathon"] and WORKOUT_TYPE_KO["long_mp"]
