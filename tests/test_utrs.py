"""UTRS (Unified Training Readiness Score) 단위 테스트 — 설계서 4-6."""
import sqlite3, pytest
from src.db_setup import create_tables
from src.metrics.base import CalcContext
from src.metrics.utrs import UTRSCalculator
from src.utils.db_helpers import upsert_metric


def _conn():
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys=ON")
    create_tables(conn)
    return conn


class TestUTRS:
    def test_full_inputs_confidence_1(self):
        """설계서 4-6: 5개 입력 모두 있을 때 confidence=1.0."""
        conn = _conn()
        conn.execute(
            "INSERT INTO daily_wellness "
            "(date, body_battery_high, sleep_score, resting_hr, "
            " hrv_weekly_avg, avg_stress) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ["2026-04-01", 80, 85, 52, 55.0, 35])
        upsert_metric(conn, "daily", "2026-04-01", "tsb",
                       "runpulse:formula_v1", numeric_value=5.0, category="rp_load")
        conn.commit()
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = UTRSCalculator().compute(ctx)
        assert len(results) == 1
        assert results[0].confidence == 1.0

    def test_partial_inputs_lower_confidence(self):
        """설계서 4-6: 일부 입력만 있으면 confidence < 1.0."""
        conn = _conn()
        conn.execute(
            "INSERT INTO daily_wellness (date, body_battery_high, sleep_score) "
            "VALUES (?, ?, ?)", ["2026-04-01", 80, 85])
        conn.commit()
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = UTRSCalculator().compute(ctx)
        assert len(results) == 1
        assert results[0].confidence < 1.0
        # body_battery(0.30) + sleep(0.20) = 0.50 → confidence = 0.5
        assert results[0].confidence == 0.5

    def test_three_inputs_confidence(self):
        """3개 입력 → confidence = (0.30+0.25+0.20)/1.0 = 0.75."""
        conn = _conn()
        conn.execute(
            "INSERT INTO daily_wellness (date, body_battery_high, sleep_score) "
            "VALUES (?, ?, ?)", ["2026-04-01", 80, 85])
        upsert_metric(conn, "daily", "2026-04-01", "tsb",
                       "runpulse:formula_v1", numeric_value=5.0, category="rp_load")
        conn.commit()
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = UTRSCalculator().compute(ctx)
        assert len(results) == 1
        assert results[0].confidence == 0.75

    def test_score_range(self):
        """결과가 0~100 범위."""
        conn = _conn()
        conn.execute(
            "INSERT INTO daily_wellness "
            "(date, body_battery_high, sleep_score, resting_hr, "
            " hrv_weekly_avg, avg_stress) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ["2026-04-01", 80, 85, 52, 55.0, 35])
        upsert_metric(conn, "daily", "2026-04-01", "tsb",
                       "runpulse:formula_v1", numeric_value=5.0, category="rp_load")
        conn.commit()
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = UTRSCalculator().compute(ctx)
        assert 0 <= results[0].numeric_value <= 100

    def test_json_has_components(self):
        """json_value에 components 딕셔너리 포함."""
        conn = _conn()
        conn.execute(
            "INSERT INTO daily_wellness (date, body_battery_high, sleep_score) "
            "VALUES (?, ?, ?)", ["2026-04-01", 80, 85])
        conn.commit()
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = UTRSCalculator().compute(ctx)
        import json
        jv = json.loads(results[0].json_value) if isinstance(results[0].json_value, str) else results[0].json_value
        assert "components" in jv
        assert "body_battery" in jv["components"]

    def test_no_inputs(self):
        """설계서 4-6: 모든 입력 없으면 빈 결과."""
        conn = _conn()
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        assert UTRSCalculator().compute(ctx) == []
