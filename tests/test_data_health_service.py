"""tests/test_data_health_service.py — 부하 커버리지."""
from __future__ import annotations

from src.services.data_health_service import get_load_coverage

TODAY = "2026-09-24"


def _act(c, aid, date, avg_hr=150):
    c.execute(
        "INSERT INTO activity_summaries (id, source, source_id, activity_type, start_time, avg_hr, duration_sec, distance_m)"
        " VALUES (?, 'garmin', ?, 'running', ?, ?, 3000, 10000)",
        (aid, f"g{aid}", f"{date}T07:00:00", avg_hr),
    )


def _trimp(c, aid):
    c.execute(
        "INSERT INTO metric_store (scope_type, scope_id, metric_name, category, provider, numeric_value, is_primary)"
        " VALUES ('activity', ?, 'trimp', 'load', 'runpulse:formula_v1', 100, 1)",
        (str(aid),),
    )


def test_empty(db_conn):
    assert get_load_coverage(db_conn, today=TODAY) == {"window_days": 90, "runs": 0, "missing": 0, "missing_ratio": 0.0}


def test_counts_missing_within_window_only(db_conn):
    _act(db_conn, 1, "2026-09-20"); _trimp(db_conn, 1)
    _act(db_conn, 2, "2026-09-10")
    _act(db_conn, 3, "2026-08-01")
    _act(db_conn, 4, "2026-09-05", avg_hr=None)  # HR 없음 → 모집단 제외
    _act(db_conn, 5, "2025-01-01")  # 창 밖
    r = get_load_coverage(db_conn, today=TODAY)
    assert (r["runs"], r["missing"], r["missing_ratio"]) == (3, 2, 0.67)
