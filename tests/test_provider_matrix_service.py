"""tests/test_provider_matrix_service.py — provider_matrix_service 단위 테스트.

인메모리 SQLite(db_conn 픽스처) 기반. 실 사용자 DB 사용 금지.
_insert_activity/_insert_activity_group/_insert_metric은
test_provider_comparison_service.py의 픽스처 패턴을 재사용.
"""
from __future__ import annotations

from datetime import date, timedelta

from src.services.provider_matrix_service import (
    _mode_primary_source,
    get_provider_comparison_period,
)


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


# ─────────────────────────────────────────────────────────────────────────────
# 기본 케이스
# ─────────────────────────────────────────────────────────────────────────────

def test_no_activities_in_period_returns_no_data(db_conn):
    result = get_provider_comparison_period(db_conn, days=28)
    assert result["state"] == "no_data"
    assert result["rows"] == []
    assert result["mode"] == "period"
    assert result["days"] == 28


def test_activity_outside_period_excluded(db_conn):
    """days=28보다 오래된 활동은 집계에서 빠져 no_data."""
    gid = "grp-old"
    a = _insert_activity(db_conn, "garmin", "g-old", gid, start_time=_days_ago(100))
    _insert_activity_group(db_conn, gid, "garmin", _days_ago(100)[:10])
    _insert_metric(db_conn, a, "trimp", "runpulse:formula_v1", numeric_value=90.0)
    db_conn.commit()

    result = get_provider_comparison_period(db_conn, days=28)
    assert result["state"] == "no_data"


def test_semantic_group_with_data_appears(db_conn):
    gid = "grp-1"
    a = _insert_activity(db_conn, "garmin", "g1", gid, start_time=_days_ago(2))
    _insert_activity_group(db_conn, gid, "garmin", _days_ago(2)[:10])
    _insert_metric(db_conn, a, "trimp", "runpulse:formula_v1", numeric_value=91.5)
    db_conn.commit()

    result = get_provider_comparison_period(db_conn, days=28)
    assert result["state"] == "loaded"
    trimp_row = next((r for r in result["rows"] if r["slug"] == "trimp"), None)
    assert trimp_row is not None
    assert trimp_row["values"]["runpulse:formula_v1"]["available"] is True
    assert trimp_row["values"]["runpulse:formula_v1"]["value"] == 91.5


def test_group_without_any_data_excluded(db_conn):
    """어느 provider도 값이 없는 그룹은 rows에서 제외."""
    gid = "grp-2"
    a = _insert_activity(db_conn, "garmin", "g2", gid, start_time=_days_ago(1))
    _insert_activity_group(db_conn, gid, "garmin", _days_ago(1)[:10])
    db_conn.commit()

    result = get_provider_comparison_period(db_conn, days=28)
    assert result["state"] == "no_data"
    assert result["rows"] == []


# ─────────────────────────────────────────────────────────────────────────────
# 기간 내 최신값 채택 — provider마다 서로 다른 활동에서 나와도 각자 최신값
# ─────────────────────────────────────────────────────────────────────────────

def test_each_provider_takes_its_own_latest_value(db_conn):
    """garmin은 1주 전, intervals는 2주 전 활동 — 둘 다 기간 내지만 서로 다른 날짜."""
    gid_old = "grp-old-intervals"
    a_old = _insert_activity(
        db_conn, "intervals", "i-old", gid_old, start_time=_days_ago(14),
    )
    _insert_activity_group(db_conn, gid_old, "intervals", _days_ago(14)[:10])
    _insert_metric(db_conn, a_old, "training_load_score", "intervals", numeric_value=60.0)

    gid_new = "grp-new-garmin"
    a_new = _insert_activity(
        db_conn, "garmin", "g-new", gid_new, start_time=_days_ago(7),
    )
    _insert_activity_group(db_conn, gid_new, "garmin", _days_ago(7)[:10])
    _insert_metric(db_conn, a_new, "training_load", "garmin", numeric_value=85.0)
    db_conn.commit()

    result = get_provider_comparison_period(db_conn, days=28)
    tl_row = next(r for r in result["rows"] if r["slug"] == "training_load")
    assert tl_row["values"]["garmin"]["value"] == 85.0
    assert tl_row["values"]["intervals"]["value"] == 60.0


def test_more_recent_activity_value_wins_over_older_same_provider(db_conn):
    """같은 provider가 여러 활동에 값을 남겼으면 가장 최근 활동 값을 채택."""
    gid_new = "grp-recent"
    a_new = _insert_activity(db_conn, "garmin", "g-recent", gid_new, start_time=_days_ago(1))
    _insert_activity_group(db_conn, gid_new, "garmin", _days_ago(1)[:10])
    _insert_metric(db_conn, a_new, "training_load", "garmin", numeric_value=99.0)

    gid_older = "grp-older"
    a_older = _insert_activity(db_conn, "garmin", "g-older", gid_older, start_time=_days_ago(10))
    _insert_activity_group(db_conn, gid_older, "garmin", _days_ago(10)[:10])
    _insert_metric(db_conn, a_older, "training_load", "garmin", numeric_value=50.0)
    db_conn.commit()

    result = get_provider_comparison_period(db_conn, days=28)
    tl_row = next(r for r in result["rows"] if r["slug"] == "training_load")
    assert tl_row["values"]["garmin"]["value"] == 99.0


# ─────────────────────────────────────────────────────────────────────────────
# _mode_primary_source — 최빈값
# ─────────────────────────────────────────────────────────────────────────────

def test_mode_primary_source_empty_returns_none(db_conn):
    assert _mode_primary_source(db_conn, []) is None


def test_mode_primary_source_majority_vote(db_conn):
    """3개 그룹 중 2개가 garmin, 1개가 strava → garmin."""
    _insert_activity_group(db_conn, "g1", "garmin", "2026-09-01")
    _insert_activity_group(db_conn, "g2", "garmin", "2026-09-02")
    _insert_activity_group(db_conn, "g3", "strava", "2026-09-03")
    db_conn.commit()

    result = _mode_primary_source(db_conn, ["g1", "g2", "g3"])
    assert result == "garmin"


def test_solo_activity_excluded_from_primary_source_vote(db_conn):
    """matched_group_id 없는 단독 활동은 group_ids 계산에 애초에 포함되지 않음."""
    _insert_activity(db_conn, "garmin", "g-solo", None, start_time=_days_ago(1))
    db_conn.commit()

    result = get_provider_comparison_period(db_conn, days=28)
    # 단독 활동은 metric 없으니 no_data — group_ids가 빈 리스트였는지는
    # _mode_primary_source(conn, [])가 None을 반환하는 것으로 간접 확인됨
    assert result["state"] == "no_data"
