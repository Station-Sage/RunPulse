"""matcher_context._get_condition_snapshot — 저장된 CRS 가 스냅샷에 채워지는지 (ADJ-22)."""
from src.training.matcher import save_skipped_outcome
from src.training.matcher_context import _get_condition_snapshot
from src.utils.db_helpers import upsert_metric

D = "2026-09-22"


def _store(conn, d, jv):
    upsert_metric(conn, "daily", d, "crs", "runpulse:formula_v1",
                  numeric_value=jv.get("crs"), category="readiness", json_value=jv)


def test_snapshot_fills_crs_from_stored_row(db_conn):
    _store(db_conn, D, {"level": 2, "crs": 61.5})
    assert _get_condition_snapshot(db_conn, D)[0] == 61.5


def test_snapshot_crs_none_without_row_or_other_day(db_conn):
    assert _get_condition_snapshot(db_conn, D)[0] is None
    _store(db_conn, "2026-09-21", {"level": 2, "crs": 61.5})
    assert _get_condition_snapshot(db_conn, D)[0] is None


def test_snapshot_crs_none_on_invalid_row(db_conn):
    _store(db_conn, D, {"level": 99, "crs": 61.5})
    assert _get_condition_snapshot(db_conn, D)[0] is None


def test_snapshot_other_fields_unaffected_by_crs(db_conn):
    """CRS 유무가 tsb·acwr 스냅샷(기존 읽기 방식)을 바꾸지 않는다."""
    upsert_metric(db_conn, "daily", "2026-09-21", "tsb", "runpulse:formula_v1", numeric_value=-4.0)
    upsert_metric(db_conn, "daily", "2026-09-21", "acwr", "runpulse:formula_v1", numeric_value=1.1)
    _, tsb0, _, _, acwr0 = _get_condition_snapshot(db_conn, D)
    _store(db_conn, D, {"level": 2, "crs": 61.5})
    _, tsb1, _, _, acwr1 = _get_condition_snapshot(db_conn, D)
    assert (tsb0, acwr0) == (tsb1, acwr1) == (-4.0, 1.1)


def test_skipped_outcome_persists_crs(db_conn):
    _store(db_conn, D, {"level": 1, "crs": 38.0})
    cur = db_conn.execute(
        "INSERT INTO planned_workouts (date, workout_type, distance_km, source) "
        "VALUES (?, 'easy', 8.0, 'planner')", (D,))
    save_skipped_outcome(db_conn, cur.lastrowid, D, 8.0)
    row = db_conn.execute("SELECT crs_at_session, outcome_label FROM session_outcomes").fetchone()
    assert row == (38.0, "skipped")


def _daily(conn, d, name, v):
    upsert_metric(conn, "daily", d, name, "runpulse:formula_v1", numeric_value=v, category="load")


def test_snapshot_tsb_acwr_stale_rule(db_conn):
    """FRS-28(d): 1일 전 값은 사용, STALE_DAYS(2일) 이상 오래된 값은 None."""
    _daily(db_conn, "2026-09-21", "tsb", -5.0)
    _daily(db_conn, "2026-09-20", "acwr", 1.1)
    snap = _get_condition_snapshot(db_conn, D)
    assert snap[1] == -5.0 and snap[4] is None
