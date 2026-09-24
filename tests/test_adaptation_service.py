"""tests/test_adaptation_service.py — adaptation_service.get_adaptation_status() 단위 테스트."""
from __future__ import annotations

import pytest

from src.services.adaptation_service import _acwr_zone, _hrv_zone, get_adaptation_status
from src.services.today_service import save_checkin


# ── _acwr_zone 구간 경계 ────────────────────────────────────────────────────

@pytest.mark.parametrize("v,expected", [
    (0.7, "저부하"),
    (0.8, "적정"),
    (1.3, "적정"),
    (1.4, "주의"),
    (1.5, "주의"),
    (1.6, "위험"),
])
def test_acwr_zone_boundaries(v, expected):
    assert _acwr_zone(v) == expected


# ── _hrv_zone 구간 경계 ─────────────────────────────────────────────────────

@pytest.mark.parametrize("delta,expected", [
    (-4, "정상"),
    (-5, "정상"),
    (-6, "경계"),
    (-10, "경계"),
    (-11, "저하"),
])
def test_hrv_zone_boundaries(delta, expected):
    assert _hrv_zone(delta) == expected


# ── 데이터 전무 → 전부 None ─────────────────────────────────────────────────

def test_get_adaptation_status_all_none(db_conn):
    result = get_adaptation_status(db_conn, date="2026-09-24")
    assert result["acwr"] is None
    assert result["hrv"] is None
    assert result["fatigue_avg"] is None
    assert result["date"] == "2026-09-24"


# ── ACWR: date 이전 최신값 선택, 미래 행 무시 ────────────────────────────────

def test_get_adaptation_status_acwr_latest_before_date(db_conn):
    db_conn.execute(
        "INSERT INTO metric_store (scope_type, scope_id, metric_name, provider, numeric_value, is_primary)"
        " VALUES ('daily', '2026-09-22', 'acwr', 'runpulse', 1.12, 1)"
    )
    # 미래 날짜 행 — 무시돼야 함
    db_conn.execute(
        "INSERT INTO metric_store (scope_type, scope_id, metric_name, provider, numeric_value, is_primary)"
        " VALUES ('daily', '2026-09-25', 'acwr', 'runpulse', 1.9, 1)"
    )
    db_conn.commit()

    result = get_adaptation_status(db_conn, date="2026-09-24")
    assert result["acwr"] is not None
    assert result["acwr"]["value"] == 1.12
    assert result["acwr"]["zone"] == "적정"
    assert result["acwr"]["date"] == "2026-09-22"


# ── HRV: value·baseline·delta_pct·zone ────────────────────────────────────

@pytest.mark.parametrize("value,baseline,expected_delta,expected_zone", [
    (58.0, 62.0, -6, "경계"),
    (61.0, 62.0, -2, "정상"),
    (50.0, 62.0, -19, "저하"),
])
def test_get_adaptation_status_hrv_zone(db_conn, value, baseline, expected_delta, expected_zone):
    db_conn.execute(
        "INSERT INTO daily_wellness (date, hrv_last_night, hrv_weekly_avg) VALUES (?, ?, ?)",
        ("2026-09-24", value, baseline),
    )
    db_conn.commit()

    result = get_adaptation_status(db_conn, date="2026-09-24")
    h = result["hrv"]
    assert h is not None
    assert h["value"] == value
    assert h["baseline"] == baseline
    assert h["delta_pct"] == expected_delta
    assert h["zone"] == expected_zone


def test_get_adaptation_status_hrv_null_baseline(db_conn):
    """hrv_weekly_avg가 NULL이면 delta_pct·zone은 None이고 value는 있음."""
    db_conn.execute(
        "INSERT INTO daily_wellness (date, hrv_last_night, hrv_weekly_avg) VALUES (?, ?, ?)",
        ("2026-09-24", 58.0, None),
    )
    db_conn.commit()

    result = get_adaptation_status(db_conn, date="2026-09-24")
    h = result["hrv"]
    assert h is not None
    assert h["value"] == 58.0
    assert h["delta_pct"] is None
    assert h["zone"] is None


# ── 피로도: 최근 7일 이내 체크인만 집계 ───────────────────────────────────────

def test_get_adaptation_status_fatigue_avg(db_conn):
    """최근 7일 체크인 3건(4,6,8) → value=6.0, n=3. 8일 전은 제외."""
    save_checkin(db_conn, fatigue=4, input_date="2026-09-22")
    save_checkin(db_conn, fatigue=6, input_date="2026-09-23")
    save_checkin(db_conn, fatigue=8, input_date="2026-09-24")
    # 8일 전 — 제외
    save_checkin(db_conn, fatigue=10, input_date="2026-09-16")

    result = get_adaptation_status(db_conn, date="2026-09-24")
    f = result["fatigue_avg"]
    assert f is not None
    assert f["value"] == 6.0
    assert f["n"] == 3
