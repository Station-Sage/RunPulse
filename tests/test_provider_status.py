"""provider_status_service.get_provider_status() 단위 테스트."""
import pytest
from src.services.provider_status_service import get_provider_status


# ── 헬퍼 ────────────────────────────────────────────────────────────────────

def _insert_activity(conn, source: str, source_id: str) -> None:
    conn.execute(
        "INSERT INTO activity_summaries (source, source_id, name, activity_type, start_time)"
        " VALUES (?, ?, 'Test', 'running', '2024-01-01 00:00:00')",
        (source, source_id),
    )


def _insert_payload(conn, source: str, fetched_at: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO source_payloads"
        " (source, entity_type, entity_id, payload, fetched_at)"
        " VALUES (?, 'activity', ?, '{}', ?)",
        (source, f"{source}-1", fetched_at),
    )


# ── 테스트 ───────────────────────────────────────────────────────────────────

def test_empty_db_returns_four_providers(db_conn):
    """데이터가 없어도 4개 provider가 항상 반환된다."""
    result = get_provider_status(db_conn)
    assert len(result) == 4
    providers = [r["provider"] for r in result]
    assert providers == ["garmin", "strava", "intervals", "runalyze"]


def test_empty_db_has_data_false(db_conn):
    """데이터 없는 provider는 has_data=False."""
    result = get_provider_status(db_conn)
    for item in result:
        assert item["has_data"] is False
        assert item["activity_count"] == 0
        assert item["last_synced_at"] is None


def test_garmin_activity_sets_has_data(db_conn):
    """garmin 활동이 있으면 has_data=True, activity_count=1."""
    _insert_activity(db_conn, "garmin", "G1")
    result = get_provider_status(db_conn)
    garmin = next(r for r in result if r["provider"] == "garmin")
    assert garmin["has_data"] is True
    assert garmin["activity_count"] == 1
    # 다른 provider는 그대로
    strava = next(r for r in result if r["provider"] == "strava")
    assert strava["has_data"] is False


def test_activity_count_aggregates_correctly(db_conn):
    """같은 source 여러 활동의 count가 정확히 집계된다."""
    _insert_activity(db_conn, "strava", "S1")
    _insert_activity(db_conn, "strava", "S2")
    _insert_activity(db_conn, "strava", "S3")
    result = get_provider_status(db_conn)
    strava = next(r for r in result if r["provider"] == "strava")
    assert strava["activity_count"] == 3


def test_last_synced_at_from_source_payloads(db_conn):
    """last_synced_at은 source_payloads.fetched_at 최댓값이다."""
    for eid, ts in [("g1", "2024-03-01 10:00:00"), ("g2", "2024-06-15 08:30:00"), ("g3", "2024-01-01 00:00:00")]:
        db_conn.execute(
            "INSERT INTO source_payloads (source, entity_type, entity_id, payload, fetched_at)"
            " VALUES ('garmin', 'activity', ?, '{}', ?)",
            (eid, ts),
        )
    result = get_provider_status(db_conn)
    garmin = next(r for r in result if r["provider"] == "garmin")
    assert garmin["last_synced_at"] == "2024-06-15 08:30:00"


def test_last_synced_at_none_when_no_payload(db_conn):
    """source_payloads 행이 없으면 last_synced_at=None."""
    _insert_activity(db_conn, "intervals", "I1")
    result = get_provider_status(db_conn)
    intervals = next(r for r in result if r["provider"] == "intervals")
    assert intervals["last_synced_at"] is None


def test_provider_order_fixed(db_conn):
    """반환 순서가 garmin·strava·intervals·runalyze 고정이다."""
    _insert_activity(db_conn, "runalyze", "R1")
    _insert_activity(db_conn, "intervals", "I1")
    result = get_provider_status(db_conn)
    assert [r["provider"] for r in result] == ["garmin", "strava", "intervals", "runalyze"]


def test_unknown_source_not_in_result(db_conn):
    """activity_summaries에 알 수 없는 source가 있어도 결과에 포함되지 않는다."""
    _insert_activity(db_conn, "polar", "P1")
    result = get_provider_status(db_conn)
    assert len(result) == 4
    assert all(r["provider"] != "polar" for r in result)
