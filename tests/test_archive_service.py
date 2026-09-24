"""tests/test_archive_service.py — 러닝 아카이브 집계."""
from __future__ import annotations

from src.services.archive_service import _months_back, get_archive

TODAY = "2026-09-24"


def _act(c, aid, date, dist_m, atype="running", name="런"):
    c.execute(
        "INSERT INTO activity_summaries (id, source, source_id, activity_type, name, start_time, distance_m, duration_sec)"
        " VALUES (?, 'garmin', ?, ?, ?, ?, ?, ?)",
        (aid, f"g{aid}", atype, name, f"{date}T07:00:00", dist_m, dist_m / 3),
    )


def _effort(c, aid, name, sec):
    c.execute(
        "INSERT INTO activity_best_efforts (activity_id, source, effort_name, elapsed_sec, distance_m)"
        " VALUES (?, 'strava', ?, ?, 5000)",
        (aid, name, sec),
    )


def test_months_back_crosses_year():
    assert _months_back(__import__("datetime").date(2026, 2, 10), 4) == ["2025-11", "2025-12", "2026-01", "2026-02"]


def test_empty_db(db_conn):
    r = get_archive(db_conn, TODAY)
    assert r["as_of"] == TODAY
    assert r["totals"] is None and r["heatmap"] == [] and r["personal_bests"] == []


def test_totals_monthly_heatmap_longest(db_conn):
    _act(db_conn, 1, "2023-10-29", 10000)
    _act(db_conn, 2, "2026-09-20", 24200, name="장거리")
    _act(db_conn, 3, "2026-09-20", 3000)
    _act(db_conn, 4, "2026-08-02", 5000)
    _act(db_conn, 5, "2026-09-01", 2000, atype="swimming")  # 러닝 아님
    r = get_archive(db_conn, TODAY)
    assert r["totals"]["runs"] == 4
    assert r["totals"]["distance_km"] == 42.2
    assert r["totals"]["since"] == "2023-10-29"
    assert r["longest"]["id"] == 2 and r["longest"]["distance_km"] == 24.2
    assert len(r["monthly"]) == 12 and r["monthly"][-1]["month"] == "2026-09"
    assert r["monthly"][-1]["km"] == 27.2 and r["monthly"][-1]["runs"] == 2
    assert next(m for m in r["monthly"] if m["month"] == "2026-07")["km"] == 0.0
    # 히트맵은 최근 371일, 같은 날은 합산
    d = {h["date"]: h["km"] for h in r["heatmap"]}
    assert d["2026-09-20"] == 27.2 and "2023-10-29" not in d
    assert r["totals"]["active_days_365"] == len(r["heatmap"])


def test_personal_bests_pick_min_and_skip_missing(db_conn):
    _act(db_conn, 1, "2026-05-09", 5000)
    _act(db_conn, 2, "2026-05-03", 5000)
    _effort(db_conn, 1, "5K", 1316)
    _effort(db_conn, 2, "5K", 1337)
    r = get_archive(db_conn, TODAY)
    assert [p["key"] for p in r["personal_bests"]] == ["5K"]
    pb = r["personal_bests"][0]
    assert pb["time_sec"] == 1316 and pb["activity_id"] == 1 and pb["date"] == "2026-05-09"
