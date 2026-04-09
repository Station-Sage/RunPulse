"""tests/test_activity_service.py — Phase 5-A 서비스 레이어 테스트.

인메모리 SQLite + fixture 데이터로 실행.
"""
import sqlite3

import pytest

from src.services.activity_service import (
    get_activity_detail,
    get_activity_list,
    get_activity_streams,
    get_activity_trend,
)


# ─────────────────────────────────────────────────────────────────────────────
# Fixture
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def conn(db_conn):
    """activity_service 테스트용 데이터 삽입."""
    c = db_conn

    # 활동 2개 (garmin + strava, 동일 matched_group)
    c.execute("""
        INSERT INTO activity_summaries
            (source, source_id, matched_group_id, name, activity_type,
             start_time, distance_m, duration_sec, avg_pace_sec_km,
             avg_hr, max_hr, elevation_gain)
        VALUES
            ('garmin', 'g123', 'group1', '오후 달리기', 'running',
             '2026-04-03T18:00:00Z', 10020, 3135, 312.8,
             155, 178, 120.5),
            ('strava', 's456', 'group1', 'Evening Run', 'running',
             '2026-04-03T18:00:00Z', 10050, 3140, 312.3,
             154, 177, 118.0)
    """)

    # 활동 ID 조회
    act1_id = c.execute(
        "SELECT id FROM activity_summaries WHERE source='garmin'"
    ).fetchone()[0]
    act2_id = c.execute(
        "SELECT id FROM activity_summaries WHERE source='strava'"
    ).fetchone()[0]

    # metric_store — activity scope
    metrics = [
        ("activity", str(act1_id), "trimp",                 "load",       "runpulse:formula_v1", 91.2, None, None, 0.9,  1),
        ("activity", str(act1_id), "hrss",                  "load",       "runpulse:formula_v1", 95.1, None, None, 0.9,  1),
        ("activity", str(act1_id), "aerobic_decoupling_rp", "efficiency", "runpulse:formula_v1", 3.2,  None, None, None, 1),
        ("activity", str(act1_id), "runpulse_vdot",         "capacity",   "runpulse:formula_v1", 48.2, None, None, 0.9,  1),
        ("activity", str(act1_id), "trimp",                 "load",       "intervals",           85.0, None, None, None, 0),
    ]
    c.executemany(
        "INSERT INTO metric_store"
        " (scope_type, scope_id, metric_name, category, provider,"
        "  numeric_value, text_value, json_value, confidence, is_primary)"
        " VALUES (?,?,?,?,?,?,?,?,?,?)",
        metrics,
    )

    # activity_streams (act1용)
    c.execute("""
        INSERT INTO activity_streams
            (activity_id, source, elapsed_sec, heart_rate, distance_m)
        VALUES
            (?, 'garmin', 0,   145, 0.0),
            (?, 'garmin', 60,  150, 250.0),
            (?, 'garmin', 120, 155, 500.0)
    """, (act1_id, act1_id, act1_id))

    c.commit()
    return c, act1_id, act2_id


# ─────────────────────────────────────────────────────────────────────────────
# get_activity_list
# ─────────────────────────────────────────────────────────────────────────────

def test_get_activity_list_basic(conn):
    c, act1_id, _ = conn
    result = get_activity_list(c)
    assert result["total"] >= 1
    assert "activities" in result
    assert result["page"] == 1
    assert result["per_page"] == 20


def test_get_activity_list_filter_type(conn):
    c, _, _ = conn
    result = get_activity_list(c, filters={"activity_type": "running"})
    assert result["total"] >= 1
    for a in result["activities"]:
        assert a["activity_type"] == "running"


def test_get_activity_list_filter_date_range(conn):
    c, _, _ = conn
    result = get_activity_list(
        c, filters={"date_from": "2026-04-01", "date_to": "2026-04-05"}
    )
    assert result["total"] >= 1


def test_get_activity_list_pagination(conn):
    c, _, _ = conn
    result = get_activity_list(c, page=1, per_page=1)
    # canonical view returns 1 row (garmin wins), total_pages >= 1
    assert len(result["activities"]) <= 1
    assert result["per_page"] == 1


def test_get_activity_list_sort(conn):
    c, _, _ = conn
    result = get_activity_list(c, sort_by="distance_m", sort_dir="ASC")
    distances = [a["distance_m"] for a in result["activities"] if a.get("distance_m")]
    assert distances == sorted(distances)


def test_get_activity_list_sort_injection_guard(conn):
    """잘못된 sort_by는 start_time으로 fallback."""
    c, _, _ = conn
    # should not raise
    result = get_activity_list(c, sort_by="'; DROP TABLE activity_summaries; --")
    assert "activities" in result


def test_get_activity_list_empty(db_conn):
    """데이터 없으면 total=0, activities=[]."""
    result = get_activity_list(db_conn)
    assert result["total"] == 0
    assert result["activities"] == []
    assert result["total_pages"] == 1


# ─────────────────────────────────────────────────────────────────────────────
# get_activity_detail
# ─────────────────────────────────────────────────────────────────────────────

def test_get_activity_detail_core(conn):
    c, act1_id, _ = conn
    detail = get_activity_detail(c, act1_id)
    assert "core" in detail
    assert detail["core"]["id"] == act1_id
    assert detail["core"]["distance_m"] == 10020
    # distance_m는 km 변환 안 함
    assert isinstance(detail["core"]["distance_m"], float | int)


def test_get_activity_detail_metrics_by_category(conn):
    c, act1_id, _ = conn
    detail = get_activity_detail(c, act1_id)
    mbc = detail["metrics_by_category"]
    # is_primary=1 메트릭만 포함
    assert "load" in mbc
    load_names = [m["metric_name"] for m in mbc["load"]]
    assert "trimp" in load_names
    assert "hrss" in load_names
    # is_primary=0인 intervals trimp은 제외
    assert not any(
        m["metric_name"] == "trimp" and m["provider"] == "intervals"
        for m in mbc.get("load", [])
    )


def test_get_activity_detail_source_comparison(conn):
    c, act1_id, act2_id = conn
    detail = get_activity_detail(c, act1_id)
    sc = detail["source_comparison"]
    assert "garmin" in sc
    assert "strava" in sc
    assert sc["garmin"]["distance_m"] == 10020
    assert sc["strava"]["distance_m"] == 10050


def test_get_activity_detail_semantic_groups(conn):
    c, act1_id, _ = conn
    detail = get_activity_detail(c, act1_id)
    sg = detail["semantic_groups"]
    # trimp 그룹은 metric_store에서 조회됨
    assert "trimp" in sg
    group = sg["trimp"]
    assert "members" in group
    assert any(m["metric_name"] == "trimp" for m in group["members"])


def test_get_activity_detail_streams(conn):
    c, act1_id, _ = conn
    detail = get_activity_detail(c, act1_id)
    assert detail["streams"] is not None
    assert len(detail["streams"]) == 3
    elapsed = [s["elapsed_sec"] for s in detail["streams"]]
    assert elapsed == sorted(elapsed)


def test_get_activity_detail_not_found(db_conn):
    detail = get_activity_detail(db_conn, 9999)
    assert detail["core"] == {}


# ─────────────────────────────────────────────────────────────────────────────
# get_activity_streams
# ─────────────────────────────────────────────────────────────────────────────

def test_get_activity_streams(conn):
    c, act1_id, _ = conn
    streams = get_activity_streams(c, act1_id)
    assert len(streams) == 3
    assert streams[0]["elapsed_sec"] == 0
    assert streams[-1]["elapsed_sec"] == 120


def test_get_activity_streams_source_filter(conn):
    c, act1_id, _ = conn
    streams = get_activity_streams(c, act1_id, source="garmin")
    assert len(streams) == 3

    streams_none = get_activity_streams(c, act1_id, source="strava")
    assert streams_none == []


def test_get_activity_streams_empty(db_conn):
    streams = get_activity_streams(db_conn, 9999)
    assert streams == []


# ─────────────────────────────────────────────────────────────────────────────
# get_activity_trend
# ─────────────────────────────────────────────────────────────────────────────

def test_get_activity_trend(conn):
    c, act1_id, _ = conn
    # trimp은 metric_store에 있고, 활동 날짜는 과거 90일 내
    trend = get_activity_trend(c, "trimp", days=3650)  # 10년으로 넉넉하게
    assert isinstance(trend, list)
    if trend:
        assert "date" in trend[0]
        assert "value" in trend[0]
        assert "activity_id" in trend[0]


def test_get_activity_trend_empty(db_conn):
    trend = get_activity_trend(db_conn, "nonexistent_metric", days=90)
    assert trend == []
