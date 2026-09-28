"""tests/test_metrics_explain.py — get_metric_explain() 분해 v2(explain=1) 테스트.

99-summary.md §7 2-5, 10-today/design.md §7 API 계약("terms와 sources가 모두 빈
응답은 계약 위반"). TSB/CTL/ATL/UTRS 4개만 지원 — 그 외는 None(라우트가 v1 폴백).
"""
from __future__ import annotations

import sqlite3

from src.db_setup import create_tables
from src.metrics.engine import run_activity_metrics, run_daily_metrics
from src.services.metrics_explain import get_metric_explain


def _conn():
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys=ON")
    create_tables(conn)
    return conn


def _seed_and_compute(conn, date="2026-04-01"):
    conn.execute(
        "INSERT INTO activity_summaries "
        "(source, source_id, name, activity_type, start_time, "
        "distance_m, moving_time_sec, avg_hr, max_hr, avg_speed_ms) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        ["garmin", "1", "Morning Run", "running", f"{date} 08:00:00",
         10000, 3000, 155, 185, 3.33],
    )
    conn.execute(
        "INSERT INTO daily_wellness (date, resting_hr, body_battery_high, sleep_score) "
        "VALUES (?, ?, ?, ?)", [date, 52, 80, 85],
    )
    conn.commit()
    run_activity_metrics(conn, 1)
    conn.commit()
    run_daily_metrics(conn, date)


class TestUnsupportedSlug:
    def test_returns_none_for_slug_without_explainer(self):
        conn = _conn()
        _seed_and_compute(conn)
        assert get_metric_explain(conn, "daily", "2026-04-01", "vo2max") is None

    def test_returns_none_for_no_data(self):
        conn = _conn()
        _seed_and_compute(conn)
        assert get_metric_explain(conn, "daily", "2026-04-02", "tsb") is None


class TestTSBExplain:
    def test_terms_have_ctl_and_atl_with_opposite_signs(self):
        conn = _conn()
        _seed_and_compute(conn)
        r = get_metric_explain(conn, "daily", "2026-04-01", "tsb")
        assert r is not None
        assert r["slug"] == "tsb"
        slugs = {t["slug"]: t for t in r["formula"]["terms"]}
        assert slugs["ctl"]["sign"] == "+"
        assert slugs["atl"]["sign"] == "-"
        # 계약: terms·sources 둘 다 비면 안 된다
        assert r["formula"]["terms"] and r["sources"]

    def test_formula_text_and_bands_present(self):
        conn = _conn()
        _seed_and_compute(conn)
        r = get_metric_explain(conn, "daily", "2026-04-01", "tsb")
        assert "CTL" in r["formula"]["text"]
        bands = r["meaning"]["bands"]
        assert bands and bands[-1]["max"] is None  # 마지막 구간은 상한 없음


class TestPMCExplain:
    def test_ctl_terms_have_prev_and_today_load(self):
        conn = _conn()
        _seed_and_compute(conn)
        r = get_metric_explain(conn, "daily", "2026-04-01", "ctl")
        assert r is not None
        slugs = [t["slug"] for t in r["formula"]["terms"]]
        assert "ctl_prev" in slugs and "trimp_today" in slugs
        assert r["formula"]["terms"] and r["sources"]

    def test_atl_alpha_is_one_seventh(self):
        conn = _conn()
        _seed_and_compute(conn)
        r = get_metric_explain(conn, "daily", "2026-04-01", "atl")
        today = next(t for t in r["formula"]["terms"] if t["slug"] == "trimp_today")
        assert abs(today["weight"] - 1 / 7) < 1e-4


class TestUTRSExplain:
    def test_terms_have_contribution_and_loss(self):
        conn = _conn()
        _seed_and_compute(conn)
        r = get_metric_explain(conn, "daily", "2026-04-01", "utrs")
        assert r is not None
        assert r["formula"]["terms"] and r["sources"]
        for t in r["formula"]["terms"]:
            assert "contribution" in t and "loss" in t

    def test_contributions_sum_to_score(self):
        conn = _conn()
        _seed_and_compute(conn)
        r = get_metric_explain(conn, "daily", "2026-04-01", "utrs")
        total = sum(t["contribution"] for t in r["formula"]["terms"])
        assert abs(total - r["value"]) < 1.0  # round() 누적 오차 허용

    def test_sources_is_wellness_day(self):
        conn = _conn()
        _seed_and_compute(conn)
        r = get_metric_explain(conn, "daily", "2026-04-01", "utrs")
        assert r["sources"][0]["type"] == "wellness_day"
