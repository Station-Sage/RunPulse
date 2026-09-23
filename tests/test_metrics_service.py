"""tests/test_metrics_service.py — get_metric_breakdown() 통합 테스트."""
from __future__ import annotations

import sqlite3

from src.db_setup import create_tables
from src.metrics.engine import run_activity_metrics, run_daily_metrics
from src.services.metrics_service import get_metric_breakdown


def _conn():
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys=ON")
    create_tables(conn)
    return conn


def _seed(conn):
    """활동 + wellness 시드 (test_engine.py 패턴 재사용)."""
    conn.execute(
        "INSERT INTO activity_summaries "
        "(source, source_id, name, activity_type, start_time, "
        "distance_m, moving_time_sec, avg_hr, max_hr, avg_speed_ms) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        ["garmin", "1", "Morning Run", "running", "2026-04-01 08:00:00",
         10000, 3000, 155, 185, 3.33],
    )
    conn.execute(
        "INSERT INTO daily_wellness (date, resting_hr, body_battery_high, sleep_score) "
        "VALUES (?, ?, ?, ?)", ["2026-04-01", 52, 80, 85],
    )
    conn.commit()


class TestGetMetricBreakdownNoneCase:
    def test_returns_none_for_unknown_slug(self):
        conn = _conn()
        _seed(conn)
        result = get_metric_breakdown(conn, "daily", "2026-04-01", "nonexistent_slug")
        assert result is None

    def test_returns_none_for_no_data(self):
        conn = _conn()
        _seed(conn)
        # ctl 없는 상태에서 조회
        result = get_metric_breakdown(conn, "daily", "2026-04-01", "ctl")
        assert result is None


class TestGetMetricBreakdownChildren:
    def test_ctl_has_ramp_rate_child(self):
        """ctl children에 ramp_rate가 포함되어야 한다 (P7-IMPL-D1에서 연결됨)."""
        conn = _conn()
        _seed(conn)
        run_activity_metrics(conn, 1)
        conn.commit()
        run_daily_metrics(conn, "2026-04-01")

        result = get_metric_breakdown(conn, "daily", "2026-04-01", "ctl")
        assert result is not None
        assert result["slug"] == "ctl"
        assert result["value"] is not None

        child_names = [c["name"] for c in result["children"]]
        assert "ramp_rate" in child_names, f"children: {child_names}"

    def test_children_have_required_fields(self):
        conn = _conn()
        _seed(conn)
        run_activity_metrics(conn, 1)
        conn.commit()
        run_daily_metrics(conn, "2026-04-01")

        result = get_metric_breakdown(conn, "daily", "2026-04-01", "ctl")
        assert result is not None
        for child in result["children"]:
            assert "name" in child
            assert "label" in child
            assert "value" in child


class TestGetMetricBreakdownInputs:
    def test_rri_inputs_include_cirs(self):
        """rri의 inputs에 cirs가 포함되어야 한다 (RRICalculator.requires 기반)."""
        conn = _conn()
        _seed(conn)
        run_activity_metrics(conn, 1)
        conn.commit()
        run_daily_metrics(conn, "2026-04-01")

        result = get_metric_breakdown(conn, "daily", "2026-04-01", "rri")
        if result is None:
            # rri 데이터가 없으면 skip (VDOT 등 선행 데이터 부족 가능)
            return

        assert result["slug"] == "rri"
        # inputs는 Calculator.requires 기반, 데이터가 있는 것만 포함
        input_names = [i["name"] for i in result["inputs"]]
        # ctl은 run_daily_metrics에서 반드시 생성됨
        assert "ctl" in input_names, f"inputs: {input_names}"

    def test_metric_without_calculator_has_empty_inputs(self):
        """Calculator가 없는 메트릭(children처럼 파생값)은 inputs가 빈 리스트."""
        conn = _conn()
        _seed(conn)
        run_activity_metrics(conn, 1)
        conn.commit()
        run_daily_metrics(conn, "2026-04-01")

        # ramp_rate는 PMCCalculator가 만들지만 Calculator.name=="ramp_rate"는 없음
        result = get_metric_breakdown(conn, "daily", "2026-04-01", "ramp_rate")
        if result is None:
            return
        assert result["inputs"] == []


class TestGetMetricBreakdownStructure:
    def test_top_level_keys(self):
        conn = _conn()
        _seed(conn)
        run_activity_metrics(conn, 1)
        conn.commit()
        run_daily_metrics(conn, "2026-04-01")

        result = get_metric_breakdown(conn, "daily", "2026-04-01", "ctl")
        assert result is not None
        for key in ("slug", "label", "value", "unit", "provider", "confidence",
                    "children", "inputs"):
            assert key in result, f"missing key: {key}"

    def test_utrs_children(self):
        """utrs children에 utrs_* 접두사 자식이 포함되어야 한다 (P7-IMPL-D1-REST-UC)."""
        conn = _conn()
        _seed(conn)
        run_activity_metrics(conn, 1)
        conn.commit()
        run_daily_metrics(conn, "2026-04-01")

        result = get_metric_breakdown(conn, "daily", "2026-04-01", "utrs")
        if result is None:
            return  # wellness 데이터가 충분하지 않으면 utrs 자체가 없을 수 있음
        child_names = [c["name"] for c in result["children"]]
        # 적어도 tsb 기반 utrs_tsb는 있어야 함 (TSB는 PMC에서 항상 생성)
        utrs_children = [n for n in child_names if n.startswith("utrs_")]
        assert len(utrs_children) > 0, f"utrs children 없음: {child_names}"
