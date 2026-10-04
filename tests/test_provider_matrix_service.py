"""tests/test_provider_matrix_service.py — S6 소스 비교 매트릭스/쌍 서비스 단위 테스트.

인메모리 SQLite(db_conn 픽스처). 실 사용자 DB 사용 금지. today는 주입해 결정적으로 검증한다.
"""
from __future__ import annotations

from datetime import date, timedelta

from src.services.provider_matrix_collect import cell_summary, summarize_pairs
from src.services.provider_matrix_service import get_matrix
from src.services.provider_pairs_service import get_pairs
from src.utils.provider_matrix_rows import ROWS, compare_group_for_slug, normalize_provider

TODAY = date.today().isoformat()


def _insert_activity(conn, source, source_id, group_id=None, **kwargs):
    defaults = {
        "name": f"{source} run",
        "activity_type": "running",
        "start_time": "2026-04-03T18:00:00Z",
        "distance_m": 10000,
        "duration_sec": 3600,
        "avg_hr": 155,
    }
    defaults.update(kwargs)
    conn.execute(
        "INSERT INTO activity_summaries"
        " (source, source_id, matched_group_id, name, activity_type,"
        "  start_time, distance_m, duration_sec, avg_hr)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            source, source_id, group_id,
            defaults["name"], defaults["activity_type"],
            defaults["start_time"], defaults["distance_m"],
            defaults["duration_sec"], defaults["avg_hr"],
        ),
    )
    return conn.execute(
        "SELECT id FROM activity_summaries WHERE source=? AND source_id=?",
        (source, source_id),
    ).fetchone()[0]


def _insert_activity_group(conn, group_id, primary_source, activity_date, distance_m=10000):
    conn.execute(
        "INSERT OR REPLACE INTO activity_groups"
        " (group_id, primary_source, activity_date, distance_m, member_count)"
        " VALUES (?, ?, ?, ?, ?)",
        (group_id, primary_source, activity_date, distance_m, 2),
    )


def _insert_metric(conn, scope_id, metric_name, provider, numeric_value=None):
    conn.execute(
        "INSERT INTO metric_store"
        " (scope_type, scope_id, metric_name, category, provider,"
        "  numeric_value, is_primary)"
        " VALUES ('activity', ?, ?, 'load', ?, ?, 1)",
        (str(scope_id), metric_name, provider, numeric_value),
    )


def _days_ago(n: int) -> str:
    d = date.today() - timedelta(days=n)
    return f"{d.isoformat()}T18:00:00Z"



def _seed_runs(conn, n, garmin_load, intervals_load, rp_load=None):
    for i in range(n):
        gid = f"g{i}"
        day = (date.today() - timedelta(days=i + 1)).isoformat()
        _insert_activity_group(conn, gid, "garmin", day)
        t = f"{day}T18:00:00Z"
        ga = _insert_activity(conn, "garmin", f"ga{i}", gid, start_time=t)
        ia = _insert_activity(conn, "intervals", f"ia{i}", gid, start_time=t)
        _insert_metric(conn, ga, "training_load", "garmin", garmin_load)
        _insert_metric(conn, ia, "training_load", "intervals", intervals_load)
        if rp_load is not None:
            _insert_metric(conn, ga, "hrss", "runpulse:formula_v1", rp_load)
    conn.commit()


def _row(m, key):
    return next(r for s in m["sections"] for r in s["rows"] if r["key"] == key)


def test_empty_db_no_data(db_conn):
    m = get_matrix(db_conn, 28, TODAY)
    assert m["state"] == "no_data" and m["sample_n"] == 0 and m["sections"] == []


def test_scale_row_has_ratio_and_no_warning(db_conn):
    _seed_runs(db_conn, 4, 120, 40, 38)
    r = _row(get_matrix(db_conn, 28, TODAY), "training_load")
    assert r["compare"] == "scale" and r["diff"]["status"] == "scale"
    assert r["diff"]["median"] > 2 and r["pairs_n"] == 4
    assert set(r["cells"]) == {"garmin", "intervals", "runpulse"}


def test_fewer_than_three_pairs_insufficient(db_conn):
    _seed_runs(db_conn, 2, 120, 40)
    r = _row(get_matrix(db_conn, 28, TODAY), "training_load")
    assert r["diff"]["status"] == "insufficient"


def test_non_running_excluded(db_conn):
    _insert_activity_group(db_conn, "gx", "garmin", TODAY)
    a = _insert_activity(db_conn, "garmin", "x1", "gx", activity_type="cycling", start_time=f"{TODAY}T08:00:00Z")
    _insert_metric(db_conn, a, "training_load", "garmin", 100)
    db_conn.commit()
    assert get_matrix(db_conn, 28, TODAY)["sample_n"] == 0


def test_summarize_same_threshold():
    big = summarize_pairs([(130, 100)] * 3, "garmin", "intervals", "same", 15.0)
    small = summarize_pairs([(105, 100)] * 3, "garmin", "intervals", "same", 15.0)
    assert big["status"] == "differs" and small["status"] == "similar"


def test_cell_summary_stale():
    c = cell_summary([("2026-01-01", 5.0)], "2026-09-07", "2026-10-04")
    assert c["stale"] is True and c["median"] is None and c["latest"] == 5.0
    assert cell_summary([], "a", "b") is None


def test_pairs_outlier_and_unknown_group(db_conn):
    _seed_runs(db_conn, 6, 100, 100)
    ga = db_conn.execute("SELECT id FROM activity_summaries WHERE source_id='ga0'").fetchone()[0]
    db_conn.execute("UPDATE metric_store SET numeric_value=900 WHERE scope_id=? AND provider='garmin'", (str(ga),))
    db_conn.commit()
    p = get_pairs(db_conn, "training_load", 28, TODAY)
    assert p["state"] == "ok" and len(p["pairs"]) == 6
    assert [x["outlier"] for x in p["pairs"]].count(True) == 1
    assert get_pairs(db_conn, "nope", 28, TODAY) is None
    assert get_pairs(db_conn, "vo2max_vdot", 28, TODAY)["state"] == "not_comparable"


def test_row_definitions_sane():
    keys = [r.key for r in ROWS]
    assert len(keys) == len(set(keys))
    assert all(len(r.members) >= 2 for r in ROWS)
    assert compare_group_for_slug("hrss")["key"] == "training_load"
    assert compare_group_for_slug("zzz") is None
    assert normalize_provider("runpulse:formula_v1") == "runpulse"
