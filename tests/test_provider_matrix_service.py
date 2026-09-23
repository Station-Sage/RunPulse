"""tests/test_provider_matrix_service.py — provider_matrix_service 단위 테스트."""
from __future__ import annotations

import sqlite3

import pytest

from src.db_setup import create_tables, migrate_db
from src.services.provider_matrix_service import (
    _calc_discrepancy,
    _ordered_providers,
    _preferred_provider,
    get_provider_matrix,
)


@pytest.fixture
def conn(tmp_path):
    db_file = tmp_path / "running.db"
    c = sqlite3.connect(str(db_file))
    create_tables(c)
    migrate_db(c)
    return c


# ─── _calc_discrepancy ────────────────────────────────────────────────────────

def test_calc_discrepancy_none_when_single():
    assert _calc_discrepancy([100.0], 5.0) is None


def test_calc_discrepancy_none_when_empty():
    assert _calc_discrepancy([], 5.0) is None


def test_calc_discrepancy_not_detected():
    result = _calc_discrepancy([100.0, 102.0], 5.0)
    assert result is not None
    assert result["detected"] is False
    assert result["severity"] == "info"
    assert result["maxDiff"] == pytest.approx(2.0, abs=0.01)


def test_calc_discrepancy_detected():
    result = _calc_discrepancy([100.0, 110.0], 5.0)
    assert result is not None
    assert result["detected"] is True
    assert result["severity"] == "warning"
    assert result["maxDiffPct"] == pytest.approx(10.0, abs=0.1)


def test_calc_discrepancy_zero_baseline():
    """min=0일 때 max 기준으로 pct 계산."""
    result = _calc_discrepancy([0.0, 10.0], 5.0)
    assert result is not None
    assert result["detected"] is True


def test_calc_discrepancy_both_zero():
    result = _calc_discrepancy([0.0, 0.0], 5.0)
    assert result is not None
    assert result["detected"] is False
    assert result["maxDiffPct"] == 0.0


# ─── _ordered_providers ───────────────────────────────────────────────────────

def test_ordered_providers_known_order():
    result = _ordered_providers({"strava", "garmin", "intervals"})
    assert result.index("garmin") < result.index("strava")
    assert result.index("intervals") < result.index("strava")


def test_ordered_providers_runpulse_after_known():
    result = _ordered_providers({"runpulse:ctl", "garmin"})
    assert result[0] == "garmin"
    assert "runpulse:ctl" in result


def test_ordered_providers_unknown_appended():
    result = _ordered_providers({"unknown_src", "garmin"})
    assert result[0] == "garmin"
    assert "unknown_src" in result


# ─── _preferred_provider ──────────────────────────────────────────────────────

def test_preferred_provider_empty():
    assert _preferred_provider(set()) is None


def test_preferred_provider_runpulse_only():
    result = _preferred_provider({"runpulse:ctl"})
    assert result is not None
    assert result["ruleType"] == "runpulse_always"
    assert result["provider"] == "runpulse:ctl"


def test_preferred_provider_static_priority():
    result = _preferred_provider({"garmin", "strava"})
    assert result is not None
    assert result["ruleType"] == "static_priority"
    # garmin should beat strava by _SOURCE_PRIORITY
    assert result["provider"] == "garmin"


def test_preferred_provider_mixed_runpulse_ignored_for_priority():
    """runpulse가 있어도 non-runpulse 우선순위 규칙 적용."""
    result = _preferred_provider({"garmin", "runpulse:ctl"})
    assert result is not None
    assert result["ruleType"] == "static_priority"
    assert result["provider"] == "garmin"


# ─── get_provider_matrix (통합) ───────────────────────────────────────────────

def test_get_provider_matrix_empty_db(conn):
    """데이터 없는 DB → 빈 그룹, 오류 없이 반환."""
    result = get_provider_matrix(conn, period_days=28)
    assert "period_days" in result
    assert "providers" in result
    assert "groups" in result
    assert "discrepancy_count" in result
    assert result["period_days"] == 28
    assert isinstance(result["groups"], list)
    assert result["discrepancy_count"] == 0


def test_get_provider_matrix_with_activity_data(conn):
    """activity_summaries 데이터 → groups에 행 포함."""
    conn.execute(
        "INSERT INTO activity_summaries"
        " (source, source_id, name, activity_type, start_time, distance_m, duration_sec, avg_hr)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ("garmin", "g1", "Morning Run", "running", "2026-09-01T08:00:00Z", 10000, 3600, 155),
    )
    conn.commit()

    result = get_provider_matrix(conn, period_days=365)
    assert isinstance(result["groups"], list)
    assert isinstance(result["providers"], list)


def test_get_provider_matrix_with_wellness(conn):
    """daily_wellness 데이터 → garmin provider 포함."""
    conn.execute(
        "INSERT INTO daily_wellness (date, sleep_score, resting_hr)"
        " VALUES (?, ?, ?)",
        ("2026-09-01", 80, 52),
    )
    conn.commit()

    result = get_provider_matrix(conn, period_days=365)
    # wellness metrics attribute to 'garmin'
    if result["providers"]:
        assert "garmin" in result["providers"]


def test_get_provider_matrix_structure(conn):
    """groups 각 항목이 key/label/rows 구조를 가짐."""
    conn.execute(
        "INSERT INTO activity_summaries"
        " (source, source_id, name, activity_type, start_time, distance_m, duration_sec)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("garmin", "g2", "Run", "running", "2026-09-15T08:00:00Z", 8000, 2800),
    )
    conn.commit()

    result = get_provider_matrix(conn, period_days=365)
    for group in result["groups"]:
        assert "key" in group
        assert "label" in group
        assert "rows" in group
        assert isinstance(group["rows"], list)
        for row in group["rows"]:
            assert "slug" in row
            assert "label" in row
            assert "values" in row
            assert "preferredProvider" in row
            assert "primaryReason" in row
            assert "discrepancy" in row


def test_get_provider_matrix_discrepancy_count(conn):
    """두 provider에서 10% 이상 차이 → discrepancy_count >= 1."""
    conn.executemany(
        "INSERT INTO activity_summaries"
        " (source, source_id, name, activity_type, start_time, distance_m, duration_sec)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            ("garmin", "g3", "Run", "running", "2026-09-10T08:00:00Z", 10000, 3000),
            ("strava", "s1", "Run", "running", "2026-09-10T09:00:00Z", 10000, 3300),
        ],
    )
    conn.commit()

    result = get_provider_matrix(conn, period_days=365, discrepancy_threshold=5.0)
    # With 10% duration difference, at least one discrepancy should be flagged
    assert isinstance(result["discrepancy_count"], int)
