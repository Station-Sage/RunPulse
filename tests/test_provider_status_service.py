"""tests/test_provider_status_service.py — get_provider_coverage 단위 테스트."""
from __future__ import annotations

import sqlite3

import pytest

from src.db_setup import create_tables, migrate_db
from src.services.provider_status_service import get_provider_coverage


@pytest.fixture
def coverage_conn(tmp_path):
    db_file = tmp_path / "running.db"
    conn = sqlite3.connect(str(db_file))
    create_tables(conn)
    migrate_db(conn)
    conn.executemany(
        "INSERT INTO activity_summaries"
        " (source, source_id, name, activity_type, start_time, distance_m, duration_sec)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            ("garmin", "g1", "Run A", "running", "2023-10-05T08:00:00Z", 5000, 1800),
            ("garmin", "g2", "Run B", "running", "2023-12-10T08:00:00Z", 5000, 1800),
            ("garmin", "g3", "Run C", "running", "2023-12-20T08:00:00Z", 5000, 1800),
            ("strava", "s1", "Run D", "running", "2024-01-07T08:00:00Z", 5000, 1800),
        ],
    )
    conn.commit()
    yield conn
    conn.close()


def test_months_range(coverage_conn):
    result = get_provider_coverage(coverage_conn, start_month="2023-10", today="2024-01-15")
    assert result["months"] == ["2023-10", "2023-11", "2023-12", "2024-01"]


def test_garmin_counts(coverage_conn):
    result = get_provider_coverage(coverage_conn, start_month="2023-10", today="2024-01-15")
    providers = {p["provider"]: p for p in result["providers"]}
    assert providers["garmin"]["counts"] == [1, 0, 2, 0]
    assert providers["garmin"]["total"] == 3


def test_strava_counts(coverage_conn):
    result = get_provider_coverage(coverage_conn, start_month="2023-10", today="2024-01-15")
    providers = {p["provider"]: p for p in result["providers"]}
    assert providers["strava"]["counts"] == [0, 0, 0, 1]
    assert providers["strava"]["total"] == 1


def test_intervals_runalyze_all_zero(coverage_conn):
    result = get_provider_coverage(coverage_conn, start_month="2023-10", today="2024-01-15")
    providers = {p["provider"]: p for p in result["providers"]}
    assert providers["intervals"]["total"] == 0
    assert all(c == 0 for c in providers["intervals"]["counts"])
    assert providers["runalyze"]["total"] == 0
    assert all(c == 0 for c in providers["runalyze"]["counts"])


def test_providers_length_always_four(coverage_conn):
    result = get_provider_coverage(coverage_conn, start_month="2023-10", today="2024-01-15")
    assert len(result["providers"]) == 4


def test_months_first(coverage_conn):
    result = get_provider_coverage(coverage_conn, start_month="2023-10", today="2024-01-15")
    assert result["months"][0] == "2023-10"


def test_empty_db_returns_all_zeros(tmp_path):
    db_file = tmp_path / "empty.db"
    conn = sqlite3.connect(str(db_file))
    create_tables(conn)
    migrate_db(conn)
    result = get_provider_coverage(conn, start_month="2024-01", today="2024-03-01")
    assert result["months"] == ["2024-01", "2024-02", "2024-03"]
    for p in result["providers"]:
        assert p["total"] == 0
        assert all(c == 0 for c in p["counts"])
    conn.close()
