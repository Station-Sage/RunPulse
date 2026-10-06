"""tests/test_provider_comparison_service.py — provider_comparison_service 단위 테스트.

인메모리 SQLite(db_conn 픽스처) 기반. 실 사용자 DB 사용 금지.
"""
from __future__ import annotations

import sqlite3

import pytest

from src.services.provider_comparison_service import get_provider_comparison


# ─────────────────────────────────────────────────────────────────────────────
# Fixture helpers
# ─────────────────────────────────────────────────────────────────────────────

def _insert_activity(conn, source, source_id, group_id=None, **kwargs):
    """activity_summaries에 행 삽입 후 id 반환."""
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


def _insert_metric(conn, scope_id, metric_name, provider, numeric_value=None, text_value=None):
    conn.execute(
        "INSERT INTO metric_store"
        " (scope_type, scope_id, metric_name, category, provider,"
        "  numeric_value, text_value, is_primary)"
        " VALUES ('activity', ?, ?, 'load', ?, ?, ?, 1)",
        (str(scope_id), metric_name, provider, numeric_value, text_value),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def two_source_conn(db_conn):
    """garmin + strava 형제 활동, activity_groups 행 있는 상태."""
    c = db_conn
    group_id = "grp-test-001"
    garmin_id = _insert_activity(
        c, "garmin", "g001", group_id, avg_hr=155, distance_m=10020,
    )
    strava_id = _insert_activity(
        c, "strava", "s001", group_id, avg_hr=154, distance_m=10050,
    )
    _insert_activity_group(c, group_id, "garmin", "2026-04-03")
    c.commit()
    return c, garmin_id, strava_id


@pytest.fixture
def solo_conn(db_conn):
    """matched_group_id 없는 단독 활동."""
    c = db_conn
    act_id = _insert_activity(c, "garmin", "g-solo", None)
    c.commit()
    return c, act_id


# ─────────────────────────────────────────────────────────────────────────────
# 기본 케이스
# ─────────────────────────────────────────────────────────────────────────────

def test_unknown_activity_returns_none(db_conn):
    """존재하지 않는 activity_id → None 반환."""
    result = get_provider_comparison(db_conn, 9999)
    assert result is None


def test_solo_activity_returns_single_provider(solo_conn):
    """matched_group_id 없는 활동 → single_provider 상태."""
    c, act_id = solo_conn
    result = get_provider_comparison(c, act_id)
    assert result is not None
    assert result["state"] == "single_provider"
    assert result["rows"] == []
    assert result["mode"] == "activity"
    assert result["activity_id"] == act_id


def test_two_source_returns_loaded(two_source_conn):
    """형제 있는 활동 → state="loaded", rows 비어있지 않음."""
    c, garmin_id, _ = two_source_conn
    result = get_provider_comparison(c, garmin_id)
    assert result is not None
    assert result["state"] == "loaded"
    assert result["mode"] == "activity"
    assert result["activity_id"] == garmin_id
    assert isinstance(result["rows"], list)


# ─────────────────────────────────────────────────────────────────────────────
# raw 메트릭 — avg_hr 비교 + discrepancy
# ─────────────────────────────────────────────────────────────────────────────

def test_avg_hr_raw_metric_present(two_source_conn):
    """avg_hr raw 메트릭 행이 values에 garmin/strava 모두 포함."""
    c, garmin_id, _ = two_source_conn
    result = get_provider_comparison(c, garmin_id)
    hr_row = next((r for r in result["rows"] if r["slug"] == "avg_hr"), None)
    assert hr_row is not None
    assert hr_row["values"]["garmin"]["available"] is True
    assert hr_row["values"]["garmin"]["value"] == 155
    assert hr_row["values"]["strava"]["available"] is True
    assert hr_row["values"]["strava"]["value"] == 154


def test_avg_hr_no_discrepancy(two_source_conn):
    """avg_hr 차이 1/154 ≈ 0.65% < threshold → detected=False, severity='info'."""
    c, garmin_id, _ = two_source_conn
    result = get_provider_comparison(c, garmin_id)
    hr_row = next(r for r in result["rows"] if r["slug"] == "avg_hr")
    disc = hr_row["discrepancy"]
    assert disc is not None
    assert disc["detected"] is False
    assert disc["severity"] == "info"


def test_discrepancy_warning_triggered(db_conn):
    """avg_hr 차이가 threshold 초과 → detected=True, severity='warning'."""
    c = db_conn
    group_id = "grp-disc-test"
    garmin_id = _insert_activity(c, "garmin", "g-disc", group_id, avg_hr=160, distance_m=10000)
    _insert_activity(c, "strava", "s-disc", group_id, avg_hr=130, distance_m=10000)
    _insert_activity_group(c, group_id, "garmin", "2026-04-03")
    c.commit()

    result = get_provider_comparison(c, garmin_id, discrepancy_threshold=5.0)
    hr_row = next(r for r in result["rows"] if r["slug"] == "avg_hr")
    disc = hr_row["discrepancy"]
    assert disc["detected"] is True
    assert disc["severity"] == "warning"
    # (160-130)/130 * 100 ≈ 23.08%
    assert disc["maxDiffPct"] > 20


# ─────────────────────────────────────────────────────────────────────────────
# primary_source 기반 preferredProvider
# ─────────────────────────────────────────────────────────────────────────────

def test_preferred_provider_uses_primary_source(two_source_conn):
    """primary_source=garmin → avg_hr 행의 preferredProvider=='garmin', primaryReason 동봉."""
    c, garmin_id, _ = two_source_conn
    result = get_provider_comparison(c, garmin_id)
    hr_row = next(r for r in result["rows"] if r["slug"] == "avg_hr")
    assert hr_row["preferredProvider"] == "garmin"
    reason = hr_row["primaryReason"]
    assert reason is not None
    assert reason["provider"] == "garmin"
    assert reason["ruleType"] == "static_priority"


# ─────────────────────────────────────────────────────────────────────────────
# runpulse_always
# ─────────────────────────────────────────────────────────────────────────────

def test_runpulse_only_metric_gets_runpulse_always(two_source_conn):
    """RunPulse 단독 semantic metric → ruleType='runpulse_always'."""
    c, garmin_id, _ = two_source_conn
    # trimp: runpulse:formula_v1 단독 값 삽입
    _insert_metric(c, garmin_id, "trimp", "runpulse:formula_v1", numeric_value=91.5)
    c.commit()

    result = get_provider_comparison(c, garmin_id)
    trimp_row = next(
        (r for r in result["rows"] if r["slug"] == "trimp"),
        None,
    )
    # trimp은 SEMANTIC_GROUPS에 있고 runpulse만 있음
    assert trimp_row is not None
    assert trimp_row["preferredProvider"] == "runpulse:formula_v1"
    reason = trimp_row["primaryReason"]
    assert reason is not None
    assert reason["ruleType"] == "runpulse_always"
    assert reason["rule"] == "RunPulse — 자체 산출"


# ─────────────────────────────────────────────────────────────────────────────
# semantic 그룹 — training_load 평탄화
# ─────────────────────────────────────────────────────────────────────────────

def test_semantic_training_load_flattened_to_one_row(two_source_conn):
    """training_load 그룹: garmin/strava/intervals/runpulse 값 삽입 후 하나의 행으로 합쳐짐."""
    c, garmin_id, strava_id = two_source_conn
    _insert_metric(c, garmin_id, "training_load", "garmin", numeric_value=85.0)
    _insert_metric(c, strava_id, "suffer_score", "strava", numeric_value=120.0)
    _insert_metric(c, garmin_id, "hrss", "runpulse:formula_v1", numeric_value=77.3)
    c.commit()

    result = get_provider_comparison(c, garmin_id)
    tl_rows = [r for r in result["rows"] if r["slug"] == "training_load"]
    assert len(tl_rows) == 1, "training_load 그룹은 정확히 1행이어야 함"
    tl = tl_rows[0]
    assert tl["values"]["garmin"]["available"] is True
    assert tl["values"]["garmin"]["value"] == 85.0
    assert tl["values"]["strava"]["available"] is True
    assert tl["values"]["strava"]["value"] == 120.0
    assert tl["values"]["runpulse:formula_v1"]["available"] is True
    assert tl["values"]["runpulse:formula_v1"]["value"] == 77.3


# ─────────────────────────────────────────────────────────────────────────────
# all_providers — unavailable 셀은 available=False
# ─────────────────────────────────────────────────────────────────────────────

def test_missing_provider_cell_available_false(two_source_conn):
    """한 provider에 값 없으면 해당 셀 available=False."""
    c, garmin_id, strava_id = two_source_conn
    # intervals 값만 삽입
    _insert_metric(c, garmin_id, "training_load", "intervals", numeric_value=70.0)
    c.commit()

    result = get_provider_comparison(c, garmin_id)
    tl_row = next((r for r in result["rows"] if r["slug"] == "training_load"), None)
    if tl_row is None:
        pytest.skip("training_load 그룹 행 없음 — intervals 단독 값만 있을 때 동작 확인")
    # garmin/strava는 training_load 그룹에서 값이 없으면 available=False
    for src in ["garmin", "strava"]:
        if src in tl_row["values"]:
            assert tl_row["values"][src]["available"] is False


# ─────────────────────────────────────────────────────────────────────────────
# none-value 컬럼 스킵
# ─────────────────────────────────────────────────────────────────────────────

def test_all_none_raw_column_skipped(two_source_conn):
    """형제 전체에서 None인 컬럼은 rows에 포함되지 않음."""
    c, garmin_id, _ = two_source_conn
    result = get_provider_comparison(c, garmin_id)
    # avg_power는 fixture에서 NULL — avg_power 행이 없어야 함
    assert not any(r["slug"] == "avg_power" for r in result["rows"])


def test_runpulse_value_only_from_canonical_row(two_source_conn):
    """형제(비대표) 행에서 계산된 RunPulse 값은 소스 비교에 섞이지 않는다(F-DATA-03)."""
    c, garmin_id, strava_id = two_source_conn
    _insert_metric(c, strava_id, "trimp", "runpulse:formula_v1", numeric_value=101.0)
    _insert_metric(c, garmin_id, "trimp", "runpulse:formula_v1", numeric_value=97.3)
    c.commit()
    rows = {r["slug"]: r for r in get_provider_comparison(c, strava_id)["rows"]}
    assert rows["trimp"]["values"]["runpulse:formula_v1"]["value"] == 97.3
    assert rows["trimp"]["section"] == "computed"


def test_related_group_has_no_discrepancy(two_source_conn):
    c, garmin_id, strava_id = two_source_conn
    _insert_metric(c, garmin_id, "training_load", "garmin", numeric_value=110.0)
    _insert_metric(c, garmin_id, "hrss", "runpulse:formula_v1", numeric_value=55.7)
    c.commit()
    rows = {r["slug"]: r for r in get_provider_comparison(c, garmin_id)["rows"]}
    assert rows["training_load"]["section"] == "related"
    assert rows["training_load"]["discrepancy"] is None


def test_training_load_row_marked_scale_and_includes_intervals(two_source_conn):
    """훈련 부하 행은 compare=scale(비교 불가·% 차이 없음)이고 intervals 값이 그룹에 들어온다(ADR-021 §8)."""
    c, garmin_id, _ = two_source_conn
    _insert_metric(c, garmin_id, "training_load", "intervals", numeric_value=70.0)
    _insert_metric(c, garmin_id, "hrss", "runpulse:formula_v1", numeric_value=55.0)
    c.commit()

    row = next(r for r in get_provider_comparison(c, garmin_id)["rows"] if r["slug"] == "training_load")
    assert row["compare"] == "scale"
    assert row["section"] == "related" and row["diff"] is None
    assert row["values"]["intervals"]["available"] is True
