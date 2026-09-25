"""tests/test_activity_impact_service.py — activity_impact_service 단위 테스트.

인메모리 SQLite + fixture 데이터로 실행. 실 DB 열기 없음.
"""
from datetime import date

import pytest

from src.services.activity_impact_service import get_activity_impact


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _insert_activity(c, source, source_id, activity_type, start_time, distance_m, avg_pace_sec_km=None):
    c.execute(
        "INSERT INTO activity_summaries"
        " (source, source_id, name, activity_type, start_time, distance_m, avg_pace_sec_km)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (source, source_id, "테스트 활동", activity_type, start_time, distance_m, avg_pace_sec_km),
    )
    return c.execute("SELECT id FROM activity_summaries WHERE source_id = ?", (source_id,)).fetchone()[0]


def _insert_daily_metric(c, date_str, metric_name, value):
    c.execute(
        "INSERT INTO metric_store (scope_type, scope_id, metric_name, category, provider, numeric_value, is_primary)"
        " VALUES ('daily', ?, ?, 'load', 'runpulse:formula_v1', ?, 1)",
        (date_str, metric_name, value),
    )


def _insert_goal(c, name, race_date, status="active"):
    c.execute(
        "INSERT INTO goals (name, race_date, status, distance_km)"
        " VALUES (?, ?, ?, 42.195)",
        (name, race_date, status),
    )


# ─────────────────────────────────────────────────────────────────────────────
# 비러닝 활동 → None
# ─────────────────────────────────────────────────────────────────────────────

def test_non_running_returns_none(db_conn):
    aid = _insert_activity(db_conn, "garmin", "x1", "cycling", "2026-09-01T10:00:00Z", 20000, 200.0)
    db_conn.commit()
    result = get_activity_impact(db_conn, aid, today=date(2026, 9, 1))
    assert result is None


def test_no_distance_returns_none(db_conn):
    aid = _insert_activity(db_conn, "garmin", "x2", "running", "2026-09-01T10:00:00Z", None, 300.0)
    db_conn.commit()
    result = get_activity_impact(db_conn, aid, today=date(2026, 9, 1))
    assert result is None


def test_missing_activity_returns_none(db_conn):
    result = get_activity_impact(db_conn, 99999, today=date(2026, 9, 1))
    assert result is None


# ─────────────────────────────────────────────────────────────────────────────
# CTL delta 계산
# ─────────────────────────────────────────────────────────────────────────────

def test_ctl_delta_computed(db_conn):
    """전날 CTL과 당일 CTL 차이가 ctl_delta로 반환된다."""
    aid = _insert_activity(db_conn, "garmin", "r1", "running", "2026-09-10T18:00:00Z", 10000, 300.0)
    _insert_daily_metric(db_conn, "2026-09-09", "ctl", 70.0)
    _insert_daily_metric(db_conn, "2026-09-10", "ctl", 72.3)
    _insert_daily_metric(db_conn, "2026-09-10", "tsb", -5.5)
    db_conn.commit()

    result = get_activity_impact(db_conn, aid, today=date(2026, 9, 10))
    assert result is not None
    assert result["ctl_delta"] == 2.3
    assert result["tsb"] == -5.5


def test_ctl_delta_none_when_no_prev_day(db_conn):
    """전날 CTL 없으면 ctl_delta는 None."""
    aid = _insert_activity(db_conn, "garmin", "r2", "running", "2026-09-10T18:00:00Z", 10000, 300.0)
    _insert_daily_metric(db_conn, "2026-09-10", "ctl", 72.0)
    db_conn.commit()

    result = get_activity_impact(db_conn, aid, today=date(2026, 9, 10))
    assert result is not None
    assert result["ctl_delta"] is None


def test_tsb_none_when_missing(db_conn):
    """당일 TSB 없으면 tsb는 None."""
    aid = _insert_activity(db_conn, "garmin", "r3", "running", "2026-09-10T18:00:00Z", 10000, 300.0)
    _insert_daily_metric(db_conn, "2026-09-09", "ctl", 70.0)
    _insert_daily_metric(db_conn, "2026-09-10", "ctl", 72.0)
    db_conn.commit()

    result = get_activity_impact(db_conn, aid, today=date(2026, 9, 10))
    assert result is not None
    assert result["tsb"] is None


# ─────────────────────────────────────────────────────────────────────────────
# similar 활동 비교
# ─────────────────────────────────────────────────────────────────────────────

def test_similar_with_4_activities(db_conn):
    """유사 활동 4건 → similar.n == 4, pace_rank 계산."""
    # 이전 활동 4개 (페이스: 290, 295, 305, 310)
    for i, (pace, dist) in enumerate([(290.0, 10000), (295.0, 10200), (305.0, 9800), (310.0, 10100)]):
        _insert_activity(
            db_conn, "garmin", f"prev{i}", "running",
            f"2026-09-0{i+1}T10:00:00Z", dist, pace
        )

    # 대상 활동: 페이스 300, 거리 10000
    aid = _insert_activity(
        db_conn, "garmin", "main", "running", "2026-09-20T10:00:00Z", 10000, 300.0
    )
    db_conn.commit()

    result = get_activity_impact(db_conn, aid, today=date(2026, 9, 20))
    assert result is not None
    s = result["similar"]
    assert s is not None
    assert s["n"] == 4
    # 300보다 빠른(pace <300) 것: 290, 295 → 2개, pace_rank=3
    assert s["pace_rank"] == 3
    assert s["avg_pace_sec_km"] == round((290.0 + 295.0 + 305.0 + 310.0) / 4, 1)
    assert s["pace_diff_sec"] == round(300.0 - s["avg_pace_sec_km"], 1)


def test_similar_with_2_activities_returns_none(db_conn):
    """유사 활동 2건 → similar is None."""
    for i, pace in enumerate([290.0, 300.0]):
        _insert_activity(
            db_conn, "garmin", f"s{i}", "running",
            f"2026-09-0{i+1}T10:00:00Z", 10000, pace
        )

    aid = _insert_activity(
        db_conn, "garmin", "main2", "running", "2026-09-20T10:00:00Z", 10000, 295.0
    )
    db_conn.commit()

    result = get_activity_impact(db_conn, aid, today=date(2026, 9, 20))
    assert result is not None
    assert result["similar"] is None


def test_similar_excludes_future_activities(db_conn):
    """이후 활동은 similar 계산에서 제외된다."""
    # 이전 2개
    for i, pace in enumerate([290.0, 295.0]):
        _insert_activity(
            db_conn, "garmin", f"past{i}", "running",
            f"2026-09-0{i+1}T10:00:00Z", 10000, pace
        )
    # 이후 3개
    for i, pace in enumerate([280.0, 285.0, 288.0]):
        _insert_activity(
            db_conn, "garmin", f"future{i}", "running",
            f"2026-09-2{i+1}T10:00:00Z", 10000, pace
        )

    aid = _insert_activity(
        db_conn, "garmin", "main3", "running", "2026-09-10T10:00:00Z", 10000, 300.0
    )
    db_conn.commit()

    result = get_activity_impact(db_conn, aid, today=date(2026, 9, 10))
    assert result is not None
    # 이전 2개만 → similar is None (3건 미만)
    assert result["similar"] is None


# ─────────────────────────────────────────────────────────────────────────────
# race 맥락
# ─────────────────────────────────────────────────────────────────────────────

def test_race_present(db_conn):
    """활성 미래 목표 있으면 race dict 반환."""
    aid = _insert_activity(db_conn, "garmin", "r10", "running", "2026-09-10T10:00:00Z", 10000, 300.0)
    _insert_goal(db_conn, "서울 마라톤", "2026-11-08")
    db_conn.commit()

    result = get_activity_impact(db_conn, aid, today=date(2026, 9, 10))
    assert result is not None
    assert result["race"] is not None
    assert result["race"]["name"] == "서울 마라톤"
    assert result["race"]["days_left"] == (date(2026, 11, 8) - date(2026, 9, 10)).days


def test_race_none_when_no_goal(db_conn):
    """활성 목표 없으면 race is None."""
    aid = _insert_activity(db_conn, "garmin", "r11", "running", "2026-09-10T10:00:00Z", 10000, 300.0)
    db_conn.commit()

    result = get_activity_impact(db_conn, aid, today=date(2026, 9, 10))
    assert result is not None
    assert result["race"] is None


def test_race_ignores_past_goals(db_conn):
    """과거 목표는 무시한다."""
    aid = _insert_activity(db_conn, "garmin", "r12", "running", "2026-09-10T10:00:00Z", 10000, 300.0)
    _insert_goal(db_conn, "지난 대회", "2026-08-01")
    db_conn.commit()

    result = get_activity_impact(db_conn, aid, today=date(2026, 9, 10))
    assert result is not None
    assert result["race"] is None


# ─────────────────────────────────────────────────────────────────────────────
# activity_service 통합: impact 키 포함 여부
# ─────────────────────────────────────────────────────────────────────────────

def test_get_activity_detail_includes_impact_key(db_conn):
    """get_activity_detail 반환값에 impact 키가 포함된다."""
    from src.services.activity_service import get_activity_detail

    aid = _insert_activity(db_conn, "garmin", "d1", "running", "2026-09-10T10:00:00Z", 10000, 300.0)
    db_conn.commit()

    detail = get_activity_detail(db_conn, aid)
    assert "impact" in detail


def test_get_activity_detail_impact_none_for_non_running(db_conn):
    """비러닝 활동 상세의 impact는 None."""
    from src.services.activity_service import get_activity_detail

    aid = _insert_activity(db_conn, "garmin", "d2", "cycling", "2026-09-10T10:00:00Z", 30000, 150.0)
    db_conn.commit()

    detail = get_activity_detail(db_conn, aid)
    assert detail["impact"] is None


def test_race_uses_activity_date_not_today(db_conn):
    """과거 활동엔 그 시점의 D-day만 붙고, 120일 넘게 남은 목표는 맥락에서 제외한다."""
    old = _insert_activity(db_conn, "garmin", "r13", "running", "2024-03-01T10:00:00Z", 10000, 300.0)
    near = _insert_activity(db_conn, "garmin", "r14", "running", "2026-09-10T10:00:00Z", 10000, 300.0)
    _insert_goal(db_conn, "서울 마라톤", "2026-11-08")
    db_conn.commit()

    assert get_activity_impact(db_conn, old, today=date(2026, 9, 25))["race"] is None
    assert get_activity_impact(db_conn, near, today=date(2026, 9, 25))["race"]["days_left"] == 59
