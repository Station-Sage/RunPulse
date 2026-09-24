"""tests/test_engine_backfill.py — 부하(TRIMP) 누락 보정 백필."""
from __future__ import annotations

from src.metrics.engine import backfill_missing_loads, find_missing_load_dates

TODAY = "2026-08-20"


def _act(c, aid, date, avg_hr=150, dur=3000, atype="running"):
    c.execute(
        "INSERT INTO activity_summaries (id, source, source_id, activity_type, start_time, avg_hr, max_hr,"
        " duration_sec, distance_m) VALUES (?, 'garmin', ?, ?, ?, ?, 175, ?, 10000)",
        (aid, f"g{aid}", atype, f"{date}T07:00:00", avg_hr, dur),
    )


def test_find_missing_only_running_with_hr_and_duration(db_conn):
    _act(db_conn, 1, "2026-08-10")
    _act(db_conn, 2, "2026-08-12", avg_hr=None)  # HR 없음 → TRIMP 계산 불가, 대상 아님
    _act(db_conn, 3, "2026-08-13", atype="swimming")
    _act(db_conn, 4, "2024-01-01")  # 730일 밖
    assert find_missing_load_dates(db_conn, today=TODAY) == ["2026-08-10"]


def test_backfill_computes_trimp_and_ctl_then_is_idempotent(db_conn):
    _act(db_conn, 1, "2026-08-10")
    _act(db_conn, 2, "2026-08-14")
    res = backfill_missing_loads(db_conn, today=TODAY)
    assert "2026-08-10" in res and TODAY in res  # 가장 이른 누락일 ~ 오늘 연속
    n = db_conn.execute(
        "SELECT COUNT(*) FROM metric_store WHERE scope_type='activity' AND metric_name='trimp' AND is_primary=1"
    ).fetchone()[0]
    assert n == 2
    ctl = db_conn.execute(
        "SELECT numeric_value FROM metric_store WHERE metric_name='ctl' AND scope_type='daily'"
        " AND is_primary=1 AND scope_id=?", (TODAY,)
    ).fetchone()
    assert ctl is not None and ctl[0] > 0
    # 이미 보정됐으면 다시 하지 않는다
    assert find_missing_load_dates(db_conn, today=TODAY) == []
    assert backfill_missing_loads(db_conn, today=TODAY) == {}


def test_nothing_to_do_returns_empty(db_conn):
    assert backfill_missing_loads(db_conn, today=TODAY) == {}
