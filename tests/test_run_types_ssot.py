"""러닝 타입 SSOT(NRA-8) — HIIT 는 러닝이 아니고, 모든 러닝 판정 사본이 activity_types 하나를 본다."""
import sqlite3

from src.utils import activity_types as at


def test_hiit_excluded_and_core_types_included():
    assert "highintensityintervaltraining" not in at.RUN_TYPES
    assert {"running", "trail_running", "treadmill", "virtual_run", "indoor_running"} <= set(at.RUN_TYPES)
    assert at.RUN_SQL.startswith("('") and "highintensity" not in at.RUN_SQL


def test_run_sql_filters_rows():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE a (t TEXT)")
    conn.executemany("INSERT INTO a VALUES (?)", [("running",), ("treadmill",), ("highintensityintervaltraining",), ("cycling",)])
    got = sorted(r[0] for r in conn.execute(f"SELECT t FROM a WHERE t IN {at.RUN_SQL}"))
    assert got == ["running", "treadmill"]


def test_copies_are_ssot():
    from src.metrics import classifier, context_runs
    from src.training import run_history, week_compliance
    assert classifier.RUN_TYPES is at.RUN_TYPES and context_runs.RUN_TYPES is at.RUN_TYPES
    assert week_compliance.RUN_TYPES is at.RUN_TYPES and run_history.RUN_TYPES == at.RUN_SQL
