"""tests/test_wellness_day.py — 웰니스 /:date 일 상세(헤드라인·기준선·nav·week)와 trend band."""
from datetime import date, timedelta

import pytest

from src.services.wellness_day import MIN_N, build_day, percentile_band
from src.services.wellness_service import get_wellness_detail, get_wellness_trend

DAY = date(2026, 4, 30)  # Thursday


def _ins(c, d, hrv=40.0, rhr=52, sleep=25000, bb=80, utrs=None):
    c.execute(
        "INSERT INTO daily_wellness (date, sleep_score, sleep_duration_sec, hrv_last_night,"
        " resting_hr, body_battery_high, body_battery_low, updated_at) VALUES (?,?,?,?,?,?,?,?)",
        (d, 80, sleep, hrv, rhr, bb, 20, f"{d} 10:00:00"),
    )
    if utrs is not None:
        c.execute(
            "INSERT INTO metric_store (scope_type, scope_id, metric_name, category, provider,"
            " numeric_value, is_primary) VALUES ('daily', ?, 'utrs', 'readiness', 'runpulse:formula_v1', ?, 1)",
            (d, utrs),
        )


@pytest.fixture
def conn(db_conn):
    for i in range(1, 29):  # d-28..d-1, HRV는 약간의 변동
        d = (DAY - timedelta(days=i)).isoformat()
        _ins(db_conn, d, hrv=40.0 + (i % 3), rhr=52 + (i % 2), sleep=25000 + (i % 4) * 300, utrs=60)
    _ins(db_conn, DAY.isoformat(), hrv=60.0, rhr=45, sleep=25100, bb=80, utrs=75)
    db_conn.commit()
    return db_conn


def test_percentile_band_requires_min_n():
    assert percentile_band([1.0] * (MIN_N - 1)) is None
    assert percentile_band([None, *range(10)]) == {"p25": 2.2, "p75": 6.8}


def test_headline_reasons_by_abs_z_and_status(conn):
    out = build_day(conn, DAY.isoformat(), today=DAY.isoformat())
    h = out["headline"]
    assert h["status"] == "good" and h["status_label"] == "좋음"
    slugs = [r["slug"] for r in h["reasons"]]
    assert slugs[0] in ("hrv_last_night", "resting_hr") and len(slugs) <= 2
    assert h["text"].startswith("회복 좋음 — ") and h["text"].endswith(".")
    hrv = next(r for r in h["reasons"] if r["slug"] == "hrv_last_night")
    assert hrv["direction"] == "up" and hrv["good"] is True


def test_headline_without_reasons_when_usual(db_conn):
    for i in range(0, 10):
        _ins(db_conn, (DAY - timedelta(days=i)).isoformat(), utrs=60)
    out = build_day(db_conn, DAY.isoformat(), today=DAY.isoformat())
    assert out["headline"]["text"] == "회복 보통 — 평소와 비슷해요."


def test_baselines_exclude_current_day_and_omit_small_n(conn, db_conn):
    b = build_day(conn, DAY.isoformat(), today="2099-01-01")["baselines"]
    assert b["hrv_last_night"]["n"] == 28 and b["hrv_last_night"]["mean7"] < 45  # 당일 60 제외
    assert b["sleep_duration_sec"]["n"] == 28
    few = build_day(conn, (DAY - timedelta(days=25)).isoformat(), today="2099-01-01")["baselines"]
    assert "hrv_last_night" not in few  # d-28..d-1에 3건뿐


def test_no_record_day_has_week_and_nav(conn):
    out = build_day(conn, "2026-05-02", today="2026-05-02")
    assert out["has_record"] is False and out["headline"] is None
    assert out["nav"] == {"prev": DAY.isoformat(), "next": None}
    assert len(out["week"]) == 7 and out["week"][0]["date"] == "2026-04-27"


def test_as_of_only_for_today(conn):
    assert build_day(conn, DAY.isoformat(), today="2099-01-01")["as_of"] is None
    assert build_day(conn, DAY.isoformat(), today=DAY.isoformat())["as_of"]["steps"]


def test_detail_keeps_legacy_fields(conn):
    out = get_wellness_detail(conn, date=DAY.isoformat())
    assert out["core"]["resting_hr"] == 45 and "readiness_summary" in out and out["readiness"]["utrs"]["value"] == 75


def test_trend_end_and_band(conn):
    t = get_wellness_trend(conn, days=29, end=DAY.isoformat())
    assert t["dates"][-1] == DAY.isoformat() and "p25" in t["band"]["hrv_last_night"]
    assert "weight_kg" not in t["band"]
