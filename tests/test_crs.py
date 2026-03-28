"""crs.py 테스트 — 게이트 필터 + CRS 점수."""

from datetime import date, timedelta

import pytest

from src.metrics.crs import (
    LEVEL_BOOST,
    LEVEL_FULL,
    LEVEL_REST,
    LEVEL_Z1,
    LEVEL_Z1_Z2,
    _gate_acwr,
    _gate_body_battery,
    _gate_cirs,
    _gate_hrv,
    _gate_tsb,
    _compute_crs_score,
    evaluate,
)


# ── Gate 1: ACWR (Gabbett 2016) ──────────────────────────────────────────────

def test_gate_acwr_none_passes():
    """데이터 없으면 FULL 허용."""
    level, _ = _gate_acwr(None)
    assert level == LEVEL_FULL


def test_gate_acwr_optimal():
    level, _ = _gate_acwr(1.1)
    assert level == LEVEL_FULL


def test_gate_acwr_caution():
    """1.3 초과 → Z1_Z2 이하."""
    level, msg = _gate_acwr(1.4)
    assert level == LEVEL_Z1_Z2
    assert "1.3" in msg


def test_gate_acwr_danger():
    """1.5 초과 → Z1 이하 (Gabbett 2016)."""
    level, msg = _gate_acwr(1.6)
    assert level == LEVEL_Z1
    assert "1.5" in msg


def test_gate_acwr_low():
    """0.8 미만 → FULL (훈련 부족 메시지)."""
    level, _ = _gate_acwr(0.6)
    assert level == LEVEL_FULL


# ── Gate 2: HRV (Plews 2013) ─────────────────────────────────────────────────

def test_gate_hrv_none_passes():
    level, _ = _gate_hrv(None, None)
    assert level == LEVEL_FULL


def test_gate_hrv_normal():
    """오늘 HRV ≥ rolling 평균 → FULL."""
    level, _ = _gate_hrv(70.0, 65.0)
    assert level == LEVEL_FULL


def test_gate_hrv_boundary():
    """-10% 경계 → Z1_Z2."""
    rolling = 70.0
    today = rolling * 0.89  # -11% (경계 초과)
    level, _ = _gate_hrv(today, rolling)
    assert level == LEVEL_Z1_Z2


def test_gate_hrv_severe():
    """-15% 이하 → Z1 (Plews 2013)."""
    rolling = 70.0
    today = rolling * 0.84  # -16%
    level, msg = _gate_hrv(today, rolling)
    assert level == LEVEL_Z1
    assert "-15%" in msg or "Plews" in msg


def test_gate_hrv_zero_rolling():
    """rolling 평균 0이면 FULL (0으로 나누기 방지)."""
    level, _ = _gate_hrv(50.0, 0.0)
    assert level == LEVEL_FULL


# ── Gate 3: Body Battery ──────────────────────────────────────────────────────

def test_gate_bb_none_passes():
    level, _ = _gate_body_battery(None)
    assert level == LEVEL_FULL


def test_gate_bb_rest():
    """BB < 20 → REST."""
    level, _ = _gate_body_battery(15.0)
    assert level == LEVEL_REST


def test_gate_bb_z1():
    """20 ≤ BB < 35 → Z1 이하."""
    level, _ = _gate_body_battery(25.0)
    assert level == LEVEL_Z1


def test_gate_bb_z1_z2():
    """35 ≤ BB < 50 → Z1_Z2 이하."""
    level, _ = _gate_body_battery(40.0)
    assert level == LEVEL_Z1_Z2


def test_gate_bb_full():
    """BB ≥ 50 → FULL."""
    level, _ = _gate_body_battery(75.0)
    assert level == LEVEL_FULL


# ── Gate 4: TSB (Coggan 2003) ────────────────────────────────────────────────

def test_gate_tsb_none_passes():
    level, _ = _gate_tsb(None)
    assert level == LEVEL_FULL


def test_gate_tsb_normal():
    level, _ = _gate_tsb(-5.0)
    assert level == LEVEL_FULL


def test_gate_tsb_caution():
    """TSB < -20 → Z1_Z2 이하."""
    level, _ = _gate_tsb(-25.0)
    assert level == LEVEL_Z1_Z2


def test_gate_tsb_danger():
    """TSB < -30 → Z1 이하 (Coggan 2003)."""
    level, msg = _gate_tsb(-35.0)
    assert level == LEVEL_Z1
    assert "-30" in msg


def test_gate_tsb_positive():
    """TSB > 15 → FULL (레이스 준비 최적)."""
    level, _ = _gate_tsb(20.0)
    assert level == LEVEL_FULL


# ── Gate 5: CIRS ─────────────────────────────────────────────────────────────

def test_gate_cirs_none_passes():
    level, _ = _gate_cirs(None)
    assert level == LEVEL_FULL


def test_gate_cirs_safe():
    level, _ = _gate_cirs(30.0)
    assert level == LEVEL_FULL


def test_gate_cirs_caution():
    level, _ = _gate_cirs(65.0)
    assert level == LEVEL_Z1_Z2


def test_gate_cirs_danger():
    """CIRS > 80 → Z1 이하."""
    level, msg = _gate_cirs(85.0)
    assert level == LEVEL_Z1
    assert "80" in msg


# ── CRS 점수 계산 ─────────────────────────────────────────────────────────────

def test_crs_score_range():
    """점수는 항상 0~100 범위."""
    for utrs in [None, 0, 50, 100]:
        for acwr in [None, 0.5, 1.1, 1.6]:
            for cirs in [None, 0, 50, 90]:
                s = _compute_crs_score(utrs, acwr, cirs)
                assert 0.0 <= s <= 100.0


def test_crs_score_high_acwr_lowers():
    """ACWR > 1.5 → 점수 40 이하로 제한."""
    s = _compute_crs_score(utrs=80.0, acwr=1.6, cirs=None)
    assert s <= 40.0


def test_crs_score_optimal_acwr_boosts():
    """ACWR 1.0~1.3 → 소폭 가점."""
    base = _compute_crs_score(utrs=60.0, acwr=None, cirs=None)
    boosted = _compute_crs_score(utrs=60.0, acwr=1.1, cirs=None)
    assert boosted >= base


def test_crs_score_high_cirs_lowers():
    """CIRS > 80 → 점수 35 이하로 제한."""
    s = _compute_crs_score(utrs=70.0, acwr=None, cirs=85.0)
    assert s <= 35.0


# ── evaluate() 통합 테스트 ────────────────────────────────────────────────────

def test_evaluate_no_data_returns_full(db_conn):
    """데이터 없으면 모든 게이트 통과 → FULL."""
    result = evaluate(db_conn, "2026-04-07")
    assert result["level"] == LEVEL_FULL


def test_evaluate_returns_required_keys(db_conn):
    """반환 dict 필수 키 확인."""
    result = evaluate(db_conn, "2026-04-07")
    required = {"level", "level_label", "crs", "gates", "signals", "boost_allowed"}
    assert required.issubset(result.keys())


def test_evaluate_gates_count(db_conn):
    """게이트 5개 반환."""
    result = evaluate(db_conn, "2026-04-07")
    assert len(result["gates"]) == 5


def test_evaluate_with_high_acwr(db_conn):
    """ACWR > 1.5 데이터 입력 → level ≤ Z1."""
    td = "2026-04-07"
    db_conn.execute(
        "INSERT INTO computed_metrics (activity_id, date, metric_name, metric_value) "
        "VALUES (NULL, ?, 'ACWR', 1.6)",
        (td,),
    )
    db_conn.commit()
    result = evaluate(db_conn, td)
    assert result["level"] <= LEVEL_Z1


def test_evaluate_level_is_min_of_gates(db_conn):
    """최종 레벨은 모든 게이트 중 최솟값."""
    result = evaluate(db_conn, "2026-04-07")
    min_gate_level = min(g["level"] for g in result["gates"])
    assert result["level"] == min_gate_level


def test_evaluate_with_low_body_battery(db_conn):
    """BB < 20 입력 → level == REST."""
    td = date.today().isoformat()
    db_conn.execute(
        "INSERT INTO daily_wellness (date, source, body_battery) VALUES (?, 'garmin', 15)",
        (td,),
    )
    db_conn.commit()
    result = evaluate(db_conn, td)
    assert result["level"] == LEVEL_REST
